"""Carga del catálogo de obligaciones como tareas de la organización.

No usa IA: crea tareas con datos del catálogo (norma, cita, frecuencia, evidencia sugerida).
Cada tarea lleva «Código del catálogo: ID» en la descripción; así se sabe qué puntos ya se
cargaron y no se repiten, sin tocar el esquema de la base.
"""
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser
from app.models.tables import Priority, Tenant
from app.models.tables import Task as TaskRow
from app.schemas.obligations import (
    ObligationItem,
    ObligationList,
    ObligationLoad,
    ObligationLoadResult,
)
from app.schemas.tasks import TaskCreate
from app.services import audit_service, obligations_catalog, task_service

MARKER = "Código del catálogo:"
_MARKER_RE = re.compile(re.escape(MARKER) + r"\s*([A-Z]{3}-\d{2})")

FRECUENCIA_TEXTO = {
    "una_vez": "una sola vez",
    "anual": "cada año",
    "mensual": "cada mes",
    "cada_2_meses": "cada 2 meses",
    "continua": "de forma permanente",
    "por_evento": "cada vez que ocurra",
}
# Fecha propuesta para la primera acción; «por evento» no lleva fecha
DIAS_INICIALES = {"una_vez": 60, "anual": 90, "mensual": 30, "cada_2_meses": 60, "continua": 30}


async def _tenant_sector(db: AsyncSession, tenant_id: str) -> str | None:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    return tenant.sector if tenant else None


async def _loaded_ids(db: AsyncSession, tenant_id: str) -> set[str]:
    rows = (
        await db.execute(
            select(TaskRow.description).where(
                TaskRow.tenant_id == tenant_id, TaskRow.description.contains(MARKER)
            )
        )
    ).scalars().all()
    found: set[str] = set()
    for text in rows:
        found.update(_MARKER_RE.findall(text or ""))
    return found


async def list_for_tenant(db: AsyncSession, actor: CurrentUser) -> ObligationList:
    sector = obligations_catalog.normalize_sector(await _tenant_sector(db, actor.tenant_id))
    loaded = await _loaded_ids(db, actor.tenant_id)
    items = [
        ObligationItem(**o.model_dump(), loaded=o.id in loaded)
        for o in obligations_catalog.for_sector(sector)
    ]
    return ObligationList(
        sector=sector, aviso=obligations_catalog.load_catalog().aviso, items=items
    )


def _description(o: obligations_catalog.Obligation) -> str:
    lines = [
        o.obligacion,
        f"Se cumple {FRECUENCIA_TEXTO[o.frecuencia]}.",
        f"Evidencia sugerida: {o.evidencia_sugerida}.",
        f"Fundamento: {o.norma}, {o.cita}.",
    ]
    if o.cita_textual:
        lines.append(f"Texto de la norma: «{o.cita_textual}»")
    if o.nota:
        lines.append(f"Nota: {o.nota}")
    if o.estado_verificacion != "verificado":
        lines.append("Atención: el texto de esta obligación aún no se confirma en fuente oficial.")
    lines.append(f"{MARKER} {o.id}")
    return "\n".join(lines)[:2000]


async def load(
    db: AsyncSession, actor: CurrentUser, body: ObligationLoad
) -> ObligationLoadResult:
    sector = obligations_catalog.normalize_sector(await _tenant_sector(db, actor.tenant_id))
    allowed = {o.id: o for o in obligations_catalog.for_sector(sector)}
    ids = list(dict.fromkeys(body.ids))  # sin repetidos, en el orden recibido
    unknown = [i for i in ids if i not in allowed]
    if unknown:
        raise AppError(
            400, "INVALID_INPUT", "Hay obligaciones que no aplican a tu organización.",
            {"fields": [{"loc": ["ids"], "msg": f"No válidas: {', '.join(unknown)}"}]},
        )

    loaded = await _loaded_ids(db, actor.tenant_id)
    today = datetime.now(UTC).date()
    created, skipped = [], []
    for oid in ids:
        if oid in loaded:
            skipped.append(oid)
            continue
        o = allowed[oid]
        days = DIAS_INICIALES.get(o.frecuencia)
        created.append(
            await task_service.create_task(
                db, actor,
                TaskCreate(
                    title=o.titulo,
                    description=_description(o),
                    priority=Priority.MEDIA,
                    due_date=today + timedelta(days=days) if days else None,
                    citation=f"{o.norma}, {o.cita}"[:300],
                ),
            )
        )
    await audit_service.record(
        db, actor, audit_service.OBLIGATIONS_LOADED, "TENANT", actor.tenant_id,
        {"created": [t.code for t in created], "skipped": len(skipped)},
    )
    return ObligationLoadResult(created=created, skipped=skipped)
