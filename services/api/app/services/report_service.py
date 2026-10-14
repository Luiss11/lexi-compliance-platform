"""ReportService: Panel de cumplimiento y Expediente de auditoría.

Índice de cumplimiento (explicable ante un auditor):
  cada tarea pesa según su prioridad (ALTA 3, MEDIA 2, BAJA 1) y aporta un avance:
    Pendiente 0 · En curso 0.25 · En revisión 0.6 ·
    Cumplida con evidencia sellada 1.0 · Cumplida SIN evidencia 0.5
  índice = suma(peso × avance) / suma(pesos) × 100.
Una tarea marcada como cumplida sin evidencia no se puede defender en una auditoría,
por eso solo cuenta la mitad y además genera una alerta.

Expediente: foto del estado de cumplimiento con cada evidencia re-verificada contra su
huella SHA-256 y un sello (SHA-256 del contenido canónico) para detectar cambios posteriores.
"""
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, Role
from app.core.text import fix_mojibake
from app.models.tables import (
    Document,
    DocumentStatus,
    EvidenceFile,
    Priority,
    Task,
    TaskStatus,
    Tenant,
    User,
)
from app.schemas.reports import (
    Alert,
    DashboardOut,
    DossierAudit,
    DossierDocument,
    DossierEvidence,
    DossierOut,
    DossierSummary,
    DossierTask,
    StatusCounts,
    Upcoming,
)
from app.services import audit_service, evidence_review_service, evidence_service
from app.services.hashing import sha256_bytes

S = TaskStatus
WEIGHT = {Priority.ALTA: 3, Priority.MEDIA: 2, Priority.BAJA: 1}
PROGRESS = {S.BACKLOG: 0.0, S.IN_PROGRESS: 0.25, S.IN_REVIEW: 0.6, S.DONE: 1.0}
DONE_WITHOUT_EVIDENCE = 0.5
DUE_SOON_DAYS = 14
MAX_ALERTS = 10
SEVERITY_ORDER = {"high": 0, "medium": 1, "info": 2}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)  # las columnas de Prisma son naive UTC


def score_label(score: int, total_tasks: int) -> str:
    if total_tasks == 0:
        return "Sin tareas"
    if score >= 80:
        return "Sólido"
    if score >= 50:
        return "En progreso"
    return "Crítico"


def compute_score(rows: list[tuple[Task, int]]) -> int:
    """rows: (tarea, número de evidencias)."""
    total = sum(WEIGHT[t.priority] for t, _ in rows)
    if not total:
        return 0
    got = 0.0
    for t, n_ev in rows:
        progress = PROGRESS[t.status]
        if t.status == S.DONE and n_ev == 0:
            progress = DONE_WITHOUT_EVIDENCE
        got += WEIGHT[t.priority] * progress
    return round(got / total * 100)


def _is_overdue(t: Task, now: datetime) -> bool:
    return t.due_date is not None and t.status != S.DONE and t.due_date < now


async def _task_rows(
    db: AsyncSession, actor: CurrentUser
) -> list[tuple[Task, str | None, int]]:
    """(tarea, nombre del responsable, nº de evidencias) del alcance del actor."""
    ev_counts = (
        select(EvidenceFile.task_id.label("tid"), func.count().label("n"))
        .group_by(EvidenceFile.task_id)
        .subquery()
    )
    query = (
        select(Task, User.name, func.coalesce(ev_counts.c.n, 0))
        .outerjoin(User, Task.assignee_id == User.id)
        .outerjoin(ev_counts, ev_counts.c.tid == Task.id)
        .where(Task.tenant_id == actor.tenant_id)
        .order_by(Task.created_at, Task.code)
    )
    if actor.role == Role.OPERATOR:
        query = query.where(Task.assignee_id == actor.id)
    return [(t, name, int(n)) for t, name, n in (await db.execute(query)).all()]


async def dashboard(db: AsyncSession, actor: CurrentUser) -> DashboardOut:
    is_manager = actor.role != Role.OPERATOR
    rows = await _task_rows(db, actor)
    now = _now()

    counts = StatusCounts()
    for t, _, _ in rows:
        key = {S.BACKLOG: "backlog", S.IN_PROGRESS: "in_progress",
               S.IN_REVIEW: "in_review", S.DONE: "done"}[t.status]
        setattr(counts, key, getattr(counts, key) + 1)

    score = compute_score([(t, n) for t, _, n in rows])
    overdue = sum(1 for t, _, _ in rows if _is_overdue(t, now))

    needs_ev = [(t, n) for t, _, n in rows if t.status in (S.IN_REVIEW, S.DONE)]
    coverage = (
        round(sum(1 for _, n in needs_ev if n > 0) / len(needs_ev) * 100) if needs_ev else None
    )
    evidence_files = sum(n for _, _, n in rows)

    # Próximos vencimientos (incluye vencidas), de la más urgente a la menos
    upcoming: list[Upcoming] = []
    for t, name, _ in rows:
        if t.due_date is None or t.status == S.DONE:
            continue
        days_left = (t.due_date.date() - now.date()).days
        if days_left <= DUE_SOON_DAYS:
            upcoming.append(
                Upcoming(
                    task_id=t.id, code=t.code, title=t.title, due_date=t.due_date.date(),
                    days_left=days_left, priority=t.priority.value, status=t.status.value,
                    assignee_name=name,
                )
            )
    upcoming.sort(key=lambda u: (u.days_left, u.code))

    alerts: list[Alert] = []
    for t, _, n in rows:
        if _is_overdue(t, now):
            days = (now.date() - t.due_date.date()).days
            alerts.append(Alert(
                kind="OVERDUE", severity="high", task_id=t.id, task_code=t.code,
                message=f"{t.code} está vencida hace {days} día(s): {t.title}",
            ))
        if t.status == S.DONE and n == 0:
            alerts.append(Alert(
                kind="DONE_WITHOUT_EVIDENCE", severity="high", task_id=t.id, task_code=t.code,
                message=f"{t.code} figura como cumplida pero no tiene evidencia sellada.",
            ))
        if t.status == S.BACKLOG and t.priority == Priority.ALTA:
            alerts.append(Alert(
                kind="HIGH_PRIORITY_PENDING", severity="medium", task_id=t.id, task_code=t.code,
                message=f"{t.code} es de prioridad alta y aún no se inicia: {t.title}",
            ))
        if t.status == S.IN_REVIEW and is_manager:
            alerts.append(Alert(
                kind="AWAITING_REVIEW", severity="info", task_id=t.id, task_code=t.code,
                message=f"{t.code} espera tu revisión: {t.title}",
            ))
        if is_manager and t.assignee_id is None and t.status != S.DONE:
            alerts.append(Alert(
                kind="UNASSIGNED", severity="medium", task_id=t.id, task_code=t.code,
                message=f"{t.code} no tiene responsable asignado.",
            ))

    # Evidencias que la revisión automática observó (solo tareas aún abiertas)
    open_ids = {t.id: t for t, _, _ in rows if t.status != S.DONE}
    if open_ids:
        flagged = (
            await db.execute(
                select(EvidenceFile.task_id, EvidenceFile.filename, EvidenceFile.ai_verdict)
                .where(
                    EvidenceFile.task_id.in_(list(open_ids)),
                    EvidenceFile.ai_verdict.in_(("INCOMPLETE", "INVALID")),
                )
                .order_by(EvidenceFile.created_at)
            )
        ).all()
        for tid, fname, verdict in flagged:
            t = open_ids[tid]
            alerts.append(Alert(
                kind="AI_FLAGGED", severity="medium", task_id=t.id, task_code=t.code,
                message=(
                    f"{t.code}: la revisión automática marcó «{fname}» como "
                    f"{'incompleta' if verdict == 'INCOMPLETE' else 'no válida'}."
                ),
            ))

    documents_total = documents_indexed = None
    if is_manager:
        docs = (
            await db.execute(
                select(Document.status, func.count())
                .where(Document.tenant_id == actor.tenant_id)
                .group_by(Document.status)
            )
        ).all()
        by_status = {st: n for st, n in docs}
        documents_total = sum(by_status.values())
        documents_indexed = by_status.get(DocumentStatus.INDEXED, 0)
        problems = by_status.get(DocumentStatus.NEEDS_REVIEW, 0) + by_status.get(
            DocumentStatus.ERROR, 0
        )
        if problems:
            alerts.append(Alert(
                kind="DOCUMENT_ISSUE", severity="medium",
                message=f"{problems} documento(s) normativo(s) requieren revisión o reindexado.",
            ))

    alerts.sort(key=lambda a: (SEVERITY_ORDER[a.severity], a.task_code or ""))

    return DashboardOut(
        scope="tenant" if is_manager else "mine",
        score=score,
        score_label=score_label(score, len(rows)),
        total_tasks=len(rows),
        counts=counts,
        overdue=overdue,
        due_soon=len(upcoming),
        evidence_files=evidence_files,
        evidence_coverage=coverage,
        documents_total=documents_total,
        documents_indexed=documents_indexed,
        alerts=alerts[:MAX_ALERTS],
        upcoming=upcoming[:6],
    )


def seal_of(payload: dict) -> str:
    """SHA-256 del JSON canónico (llaves ordenadas, sin espacios, UTF-8)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(canonical.encode("utf-8"))


async def dossier(db: AsyncSession, actor: CurrentUser) -> DossierOut:
    """Expediente de auditoría de toda la organización (solo ADMIN y COMPLIANCE)."""
    now = _now()
    # Lo que puede fallar por tablas aún no creadas se consulta PRIMERO, antes de cargar
    # objetos ORM: un rollback los expiraría.
    reviews = await evidence_review_service.latest_reviews(db, tenant_id=actor.tenant_id)
    audit_entries = await audit_service.recent(db, actor.tenant_id, limit=100)
    tenant_name = (
        await db.execute(select(Tenant.name).where(Tenant.id == actor.tenant_id))
    ).scalar_one_or_none() or ""
    generated_by = (
        await db.execute(select(User.name).where(User.id == actor.id))
    ).scalar_one_or_none()

    rows = await _task_rows(db, actor)
    titles = dict(
        (await db.execute(
            select(Document.id, Document.title).where(Document.tenant_id == actor.tenant_id)
        )).all()
    )

    ev_rows = (
        await db.execute(
            select(EvidenceFile, User.name)
            .join(Task, EvidenceFile.task_id == Task.id)
            .outerjoin(User, EvidenceFile.uploaded_by_id == User.id)
            .where(Task.tenant_id == actor.tenant_id)
            .order_by(EvidenceFile.created_at, EvidenceFile.id)
        )
    ).all()
    by_task: dict[str, list[DossierEvidence]] = {}
    failures = 0
    ai_flagged = sum(1 for ev, _ in ev_rows if ev.ai_verdict in ("INCOMPLETE", "INVALID"))
    for ev, uploader in ev_rows:
        state, _ = await evidence_service.check_integrity(actor.tenant_id, ev)
        if state != "OK":
            failures += 1
        by_task.setdefault(ev.task_id, []).append(
            DossierEvidence(
                id=ev.id, filename=fix_mojibake(ev.filename), mime_type=ev.mime_type, size_bytes=ev.size_bytes,
                sha256=ev.sha256, uploaded_by_name=uploader, uploaded_at=ev.created_at,
                integrity=state,
                ai_verdict=ev.ai_verdict,
                ai_summary=reviews[ev.id].summary if ev.id in reviews else None,
            )
        )

    tasks = [
        DossierTask(
            code=t.code, title=t.title, description=t.description, status=t.status.value,
            priority=t.priority.value, due_date=t.due_date.date() if t.due_date else None,
            overdue=_is_overdue(t, now), assignee_name=name, citation=t.citation,
            document_title=titles.get(t.document_id) if t.document_id else None,
            evidence=by_task.get(t.id, []),
        )
        for t, name, _ in rows
    ]

    docs = (
        await db.execute(
            select(Document)
            .where(Document.tenant_id == actor.tenant_id)
            .order_by(Document.created_at, Document.title)
        )
    ).scalars().all()
    documents = [
        DossierDocument(
            title=d.title, category=d.category, status=d.status.value, pages=d.pages,
            sha256=d.sha256, uploaded_at=d.created_at,
        )
        for d in docs
    ]

    score = compute_score([(t, n) for t, _, n in rows])
    summary = DossierSummary(
        score=score,
        score_label=score_label(score, len(rows)),
        total_tasks=len(rows),
        done=sum(1 for t, _, _ in rows if t.status == S.DONE),
        overdue=sum(1 for t, _, _ in rows if _is_overdue(t, now)),
        evidence_files=len(ev_rows),
        integrity_failures=failures,
        ai_flagged=ai_flagged,
    )

    out = DossierOut(
        tenant_name=tenant_name, generated_at=now, generated_by=generated_by,
        summary=summary, documents=documents, tasks=tasks,
        audit_trail=[
            DossierAudit(at=a.created_at, actor_name=a.actor_name, action=a.action,
                         entity_type=a.entity_type, details=a.details)
            for a in audit_entries
        ],
        seal="",
    )
    out.seal = seal_of(out.model_dump(mode="json", exclude={"seal"}))
    await audit_service.record(
        db, actor, audit_service.DOSSIER_GENERATED, "DOSSIER", None,
        {"seal": out.seal, "tasks": summary.total_tasks, "evidence_files": summary.evidence_files,
         "integrity_failures": summary.integrity_failures},
    )
    return out
