"""AuditService: bitácora de quién hizo qué (SDD §6, audit_logs).

- Solo inserta: no hay edición ni borrado.
- Es de mejor esfuerzo: si la tabla aún no existe o falla, se registra una advertencia y la
  acción del usuario sigue su curso. Una falla de la bitácora nunca debe tumbar una subida
  de evidencia o un cambio de estado.
- Se llama DESPUÉS de confirmar la acción principal (db.commit), con la respuesta ya armada.
"""
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser
from app.models.tables import AuditLog, User
from app.schemas.audit import AuditEntryOut, AuditList

log = logging.getLogger(__name__)

# Acciones registradas (el front las traduce a español)
TASK_CREATED = "TASK_CREATED"
TASK_UPDATED = "TASK_UPDATED"
TASK_STATUS_CHANGED = "TASK_STATUS_CHANGED"
EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
EVIDENCE_REVIEWED = "EVIDENCE_REVIEWED"
DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
DOCUMENT_REINDEXED = "DOCUMENT_REINDEXED"
DOSSIER_GENERATED = "DOSSIER_GENERATED"
GAPS_ANALYZED = "GAPS_ANALYZED"
GAPS_DISMISSED = "GAPS_DISMISSED"
TASK_DELETED = "TASK_DELETED"

MAX_LIMIT = 200


async def record(
    db: AsyncSession,
    actor: CurrentUser,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    try:
        db.add(
            AuditLog(
                id=str(uuid4()),
                tenant_id=actor.tenant_id,
                actor_id=actor.id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await db.commit()
    except Exception:  # noqa: BLE001 - la bitácora nunca debe romper la acción principal
        log.warning("No se pudo escribir en audit_logs (action=%s)", action, exc_info=True)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass


async def recent(db: AsyncSession, tenant_id: str, limit: int = 100) -> list[AuditEntryOut]:
    """Últimas entradas de la organización (para el expediente). Vacío si la tabla no existe."""
    try:
        return (await list_entries(db, tenant_id, limit=limit)).items
    except Exception:  # noqa: BLE001
        log.warning("No se pudo leer audit_logs", exc_info=True)
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
        return []


async def list_entries(
    db: AsyncSession,
    tenant_id: str,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditList:
    limit = max(1, min(limit, MAX_LIMIT))
    base = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if action:
        base = base.where(AuditLog.action == action)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            select(AuditLog, User.name)
            .outerjoin(User, AuditLog.actor_id == User.id)
            .where(AuditLog.tenant_id == tenant_id, *([AuditLog.action == action] if action else []))
            .order_by(AuditLog.created_at.desc(), AuditLog.id)
            .limit(limit)
            .offset(max(0, offset))
        )
    ).all()
    return AuditList(
        total=total,
        items=[
            AuditEntryOut(
                id=a.id, action=a.action, entity_type=a.entity_type, entity_id=a.entity_id,
                actor_name=name, details=a.details, created_at=a.created_at,
            )
            for a, name in rows
        ],
    )


async def list_for_managers(
    db: AsyncSession, actor: CurrentUser, action: str | None, limit: int, offset: int
) -> AuditList:
    try:
        return await list_entries(db, actor.tenant_id, action, limit, offset)
    except Exception as exc:  # noqa: BLE001 - tabla aún no creada
        log.warning("No se pudo leer audit_logs", exc_info=True)
        await db.rollback()
        raise AppError(
            503, "AUDIT_NOT_READY",
            "La bitácora aún no está disponible. Falta crear la tabla audit_logs en la base de datos.",
        ) from exc
