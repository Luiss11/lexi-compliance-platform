"""AuthService: login y datos del usuario actual (RF-SEC-01)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, unauthenticated
from app.core.security import (
    DUMMY_HASH,
    CurrentUser,
    Role,
    create_access_token,
    verify_password,
)
from app.models.tables import Tenant, User
from app.schemas.auth import LoginResponse, MeResponse, TenantOut, UserOut


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, full_name=user.name, email=user.email, role=Role(user.role))


def _tenant_out(tenant: Tenant) -> TenantOut:
    return TenantOut(id=tenant.id, name=tenant.name, slug=tenant.slug, sector=tenant.sector)


async def login(db: AsyncSession, tenant_slug: str, email: str, password: str) -> LoginResponse:
    result = await db.execute(
        select(User, Tenant)
        .join(Tenant, User.tenant_id == Tenant.id)
        .where(Tenant.slug == tenant_slug, User.email == email)
    )
    row = result.first()

    if row is None:
        # Misma duración que un login real: no revela si el correo o la organización existen
        verify_password(password, DUMMY_HASH)
        raise AppError(401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos.")

    user, _tenant = row
    if not verify_password(password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos.")

    token = create_access_token(user.id, user.tenant_id, Role(user.role))
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expires_minutes * 60,
        user=_user_out(user),
    )


async def me(db: AsyncSession, actor: CurrentUser) -> MeResponse:
    # El tenant sale del token, nunca de la petición
    result = await db.execute(
        select(User, Tenant)
        .join(Tenant, User.tenant_id == Tenant.id)
        .where(User.id == actor.id, User.tenant_id == actor.tenant_id)
    )
    row = result.first()
    if row is None:
        raise unauthenticated()
    user, tenant = row
    return MeResponse(user=_user_out(user), tenant=_tenant_out(tenant))
