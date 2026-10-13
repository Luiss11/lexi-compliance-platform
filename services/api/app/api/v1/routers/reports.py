from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, Role, get_current_user, require_roles
from app.db.session import get_db
from app.schemas.reports import DashboardOut, DossierOut
from app.services import report_service

# GET /dashboard (cualquier rol; el operador ve solo lo suyo)
dashboard_router = APIRouter()
# GET /reports/dossier (solo ADMIN y COMPLIANCE)
router = APIRouter()

managers = require_roles(Role.ADMIN, Role.COMPLIANCE)


@dashboard_router.get("", response_model=DashboardOut)
async def get_dashboard(
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOut:
    return await report_service.dashboard(db, actor)


@router.get("/dossier", response_model=DossierOut)
async def get_dossier(
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> DossierOut:
    return await report_service.dossier(db, actor)
