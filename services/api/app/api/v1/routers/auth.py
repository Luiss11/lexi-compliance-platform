from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.schemas.users import PasswordChange
from app.services import auth_service, users_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> LoginResponse:
    ip = request.client.host if request.client else None
    return await auth_service.login(db, body.tenant_slug, body.email, body.password, ip)


@router.get("/me", response_model=MeResponse)
async def me(
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    return await auth_service.me(db, actor)


@router.post("/password", status_code=204)
async def change_password(
    body: PasswordChange,
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Cada persona cambia su propia contraseña (pide la actual)."""
    await users_service.change_own_password(db, actor, body)
    return Response(status_code=204)
