from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    return await auth_service.login(db, body.tenant_slug, body.email, body.password)


@router.get("/me", response_model=MeResponse)
async def me(
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    return await auth_service.me(db, actor)
