from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, Role, require_roles
from app.db.session import get_db
from app.schemas.users import (
    PasswordReset,
    UserAdminOut,
    UserCreate,
    UserList,
    UserUpdate,
)
from app.services import users_service

router = APIRouter()

# Además de este filtro por token, el servicio revisa en la base que siga siendo ADMIN activo
admins = require_roles(Role.ADMIN)


@router.get("", response_model=UserList)
async def list_users(
    actor: CurrentUser = Depends(admins), db: AsyncSession = Depends(get_db)
) -> UserList:
    return await users_service.list_users(db, actor)


@router.post("", response_model=UserAdminOut, status_code=201)
async def create_user(
    body: UserCreate, actor: CurrentUser = Depends(admins), db: AsyncSession = Depends(get_db)
) -> UserAdminOut:
    return await users_service.create_user(db, actor, body)


@router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    actor: CurrentUser = Depends(admins),
    db: AsyncSession = Depends(get_db),
) -> UserAdminOut:
    return await users_service.update_user(db, actor, user_id, body)


@router.post("/{user_id}/password", status_code=204)
async def reset_password(
    user_id: str,
    body: PasswordReset,
    actor: CurrentUser = Depends(admins),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await users_service.reset_password(db, actor, user_id, body)
    return Response(status_code=204)
