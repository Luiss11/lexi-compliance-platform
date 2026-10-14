"""EvidenceService: subir, listar, sellar con SHA-256 y verificar evidencias (RF-TSK-02).

Reglas (SDD §5.4 y §8.3):
- El hash se calcula sobre los bytes recibidos, ANTES de guardarlos: el hash guardado
  demuestra lo que mandó el operador.
- La evidencia es inmutable: el archivo se crea en modo exclusivo (nunca sobrescribe) y
  una nueva subida es una fila nueva con su propio hash.
- verify() recalcula el hash del archivo guardado; si no coincide (o falta) la evidencia
  se reporta como alterada.
- El tipo de archivo se decide por sus primeros bytes, no por lo que declare el navegador.
"""
import asyncio
import logging
import os
import re
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import CurrentUser, Role
from app.core.text import fix_mojibake
from app.models.tables import EvidenceFile, Task, TaskStatus, User
from app.schemas.evidence import EvidenceList, EvidenceOut, VerifyResult
from app.services import audit_service, task_service
from app.services.hashing import sha256_bytes

log = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024  # 10 MB (SDD §6.1 evidence_files.size_bytes)

# (firma de los primeros bytes, tipo MIME, extensión)
KINDS = [
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"%PDF-", "application/pdf", ".pdf"),
]
EXT_BY_MIME = {mime: ext for _, mime, ext in KINDS}


def _detect(data: bytes) -> tuple[str, str] | None:
    for magic, mime, ext in KINDS:
        if data.startswith(magic):
            return mime, ext
    return None


def _path(tenant_id: str, evidence_id: str, mime: str) -> str:
    return os.path.join(
        settings.storage_dir, tenant_id, "evidence", f"{evidence_id}{EXT_BY_MIME[mime]}"
    )


def _clean_name(filename: str | None, ext: str) -> str:
    name = os.path.basename(fix_mojibake(filename or "").replace("\\", "/"))
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()[:200]
    return name or f"evidencia{ext}"


def _write_new(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "xb") as fh:  # "x": falla si ya existe, nunca sobrescribe
        fh.write(data)


def _read(path: str) -> bytes | None:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _out(ev: EvidenceFile, uploader: str | None) -> EvidenceOut:
    out = EvidenceOut.model_validate(ev)
    out.filename = fix_mojibake(out.filename)  # corrige también las subidas anteriores al arreglo
    out.uploaded_by_name = uploader
    return out


async def uploader_name(db: AsyncSession, user_id: str) -> str | None:
    return (await db.execute(select(User.name).where(User.id == user_id))).scalar_one_or_none()


async def _load(db: AsyncSession, actor: CurrentUser, evidence_id: str) -> tuple[EvidenceFile, Task]:
    row = (
        await db.execute(
            select(EvidenceFile, Task)
            .join(Task, EvidenceFile.task_id == Task.id)
            .where(EvidenceFile.id == evidence_id, Task.tenant_id == actor.tenant_id)
        )
    ).first()
    # Otra organización, o un operador sin esa tarea asignada: 404, nunca 403
    if row is None or (actor.role == Role.OPERATOR and row[1].assignee_id != actor.id):
        raise AppError(404, "NOT_FOUND", "La evidencia no existe.")
    return row[0], row[1]


async def upload_evidence(
    db: AsyncSession, actor: CurrentUser, task_id: str, data: bytes, filename: str | None
) -> EvidenceOut:
    task = await task_service.load_task(db, actor, task_id)  # 404 si no es visible

    if task.status not in (TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW):
        raise AppError(
            409, "CONFLICT", "Solo se puede subir evidencia a tareas en curso o en revisión."
        )
    if not data:
        raise AppError(400, "INVALID_INPUT", "El archivo está vacío.")
    if len(data) > MAX_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "La evidencia supera el límite de 10 MB.")
    kind = _detect(data)
    if kind is None:
        raise AppError(415, "UNSUPPORTED_FILE", "Solo se aceptan fotos JPG, PNG o archivos PDF.")
    mime, ext = kind

    digest = sha256_bytes(data)  # sobre los bytes recibidos, antes de guardar
    duplicate = (
        await db.execute(
            select(EvidenceFile.id).where(EvidenceFile.task_id == task.id, EvidenceFile.sha256 == digest)
        )
    ).first()
    if duplicate:
        raise AppError(
            409, "DUPLICATE_EVIDENCE",
            "Este archivo ya está en la evidencia de esta tarea (misma huella SHA-256).",
            {"evidence_id": duplicate.id},
        )
    evidence_id = str(uuid4())
    path = _path(actor.tenant_id, evidence_id, mime)
    await asyncio.to_thread(_write_new, path, data)

    ev = EvidenceFile(
        id=evidence_id,
        task_id=task.id,
        uploaded_by_id=actor.id,
        filename=_clean_name(filename, ext),
        mime_type=mime,
        size_bytes=len(data),
        sha256=digest,
        ai_verdict="NOT_REVIEWED",
    )
    db.add(ev)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        await asyncio.to_thread(_remove, path)  # no dejar archivos huérfanos
        raise
    await db.refresh(ev)

    name = (await db.execute(select(User.name).where(User.id == actor.id))).scalar_one_or_none()
    out = _out(ev, name)
    await audit_service.record(
        db, actor, audit_service.EVIDENCE_UPLOADED, "EVIDENCE", out.id,
        {"task_code": task.code, "filename": out.filename, "sha256": out.sha256,
         "size_bytes": out.size_bytes},
    )
    return out


async def list_evidence(db: AsyncSession, actor: CurrentUser, task_id: str) -> EvidenceList:
    from app.services import evidence_review_service  # import tardío: evita ciclo

    task = await task_service.load_task(db, actor, task_id)
    rows = (
        await db.execute(
            select(EvidenceFile, User.name)
            .outerjoin(User, EvidenceFile.uploaded_by_id == User.id)
            .where(EvidenceFile.task_id == task.id)
            .order_by(EvidenceFile.created_at, EvidenceFile.id)
        )
    ).all()
    # Primero se arman las salidas: la consulta de revisiones puede hacer rollback si la
    # tabla aún no existe, y eso expira los objetos ORM ya cargados.
    items = [_out(ev, name) for ev, name in rows]
    reviews = await evidence_review_service.latest_reviews(db, [i.id for i in items])
    return EvidenceList(items=[evidence_review_service.apply_review(i, reviews.get(i.id)) for i in items])


async def check_integrity(tenant_id: str, ev: EvidenceFile) -> tuple[str, str | None]:
    """Recalcula la huella del archivo guardado: ("OK" | "TAMPERED" | "MISSING", huella actual)."""
    data = await asyncio.to_thread(_read, _path(tenant_id, ev.id, ev.mime_type))
    if data is None:
        return "MISSING", None
    computed = sha256_bytes(data)
    return ("OK" if computed == ev.sha256 else "TAMPERED"), computed


async def verify_evidence(db: AsyncSession, actor: CurrentUser, evidence_id: str) -> VerifyResult:
    ev, task = await _load(db, actor, evidence_id)
    state, computed = await check_integrity(task.tenant_id, ev)

    reason = None
    if state == "MISSING":
        reason = "El archivo guardado no está disponible."
    elif state == "TAMPERED":
        reason = "La huella del archivo ya no coincide."

    ok = state == "OK"
    result = VerifyResult(
        evidence_id=ev.id, ok=ok, tampered=not ok, stored_sha256=ev.sha256,
        computed_sha256=computed, reason=reason,
    )
    details = {"task_code": task.code, "filename": ev.filename, "state": state}
    if not ok:
        log.warning("EVIDENCE_TAMPERED evidence=%s task=%s tenant=%s", ev.id, task.id, task.tenant_id)
        await audit_service.record(
            db, actor, audit_service.EVIDENCE_TAMPERED, "EVIDENCE", ev.id,
            {**details, "stored_sha256": ev.sha256, "computed_sha256": computed},
        )
    else:
        await audit_service.record(db, actor, audit_service.EVIDENCE_VERIFIED, "EVIDENCE", ev.id, details)
    return result


async def get_file(db: AsyncSession, actor: CurrentUser, evidence_id: str) -> tuple[str, str, str]:
    """(ruta, tipo MIME, nombre) del archivo, para que el router lo sirva con autenticación."""
    ev, task = await _load(db, actor, evidence_id)
    path = _path(task.tenant_id, ev.id, ev.mime_type)
    if not os.path.isfile(path):
        raise AppError(404, "NOT_FOUND", "El archivo de la evidencia no está disponible.")
    return path, ev.mime_type, ev.filename
