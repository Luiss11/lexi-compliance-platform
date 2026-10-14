from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, Role, require_roles
from app.db.session import get_db
from app.schemas.gaps import GapAccept, GapAnalysis, GapDismiss, GapDismissed
from app.schemas.tasks import TaskList
from app.services import gap_service

router = APIRouter()

managers = require_roles(Role.ADMIN, Role.COMPLIANCE)


@router.post("/gaps/analyze", response_model=GapAnalysis)
async def analyze_gaps(
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> GapAnalysis:
    """Propone tareas para obligaciones de la normativa que aún no tienen tarea. No crea nada."""
    return await gap_service.analyze(db, actor)


@router.post("/gaps/accept", response_model=TaskList, status_code=201)
async def accept_gaps(
    body: GapAccept,
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    """Crea como tareas las propuestas que la persona eligió."""
    return TaskList(items=await gap_service.accept(db, actor, body))


@router.post("/gaps/dismiss", response_model=GapDismissed)
async def dismiss_gaps(
    body: GapDismiss,
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> GapDismissed:
    """Marca propuestas como no aplicables: no vuelven a salir."""
    return GapDismissed(dismissed=await gap_service.dismiss(db, actor, body))
