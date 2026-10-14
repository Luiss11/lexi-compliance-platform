from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, Role, require_roles
from app.db.session import get_db
from app.schemas.audit import AuditList
from app.services import audit_service

router = APIRouter()

managers = require_roles(Role.ADMIN, Role.COMPLIANCE)


@router.get("", response_model=AuditList)
async def list_audit(
    action: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> AuditList:
    return await audit_service.list_for_managers(db, actor, action, limit, offset)
