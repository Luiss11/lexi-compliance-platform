"""Gestión de usuarios de una organización (solo ADMIN) y cambio de contraseña propia.

Reglas de seguridad:
- Todo se limita a la organización del token: nunca se ve ni se toca a otra organización.
- Se revisa en la base que quien actúa siga activo y siga siendo ADMIN (el token puede ser viejo).
- Nadie puede quitarse el rol de administrador ni desactivarse a sí mismo.
- La organización nunca se queda sin un administrador activo.
- Las contraseñas solo se guardan con bcrypt y jamás se escriben en la bitácora.
"""
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import limits
from app.core.errors import AppError, forbidden, unauthenticated
from app.core.security import CurrentUser, Role, hash_password, verify_password
from app.models.tables import User
from app.schemas.users import (
    PasswordChange,
    PasswordReset,
    UserAdminOut,
    UserCreate,
    UserList,
    UserUpdate,
)
from app.services import audit_service


def _out(u: User) -> UserAdminOut:
    return UserAdminOut(
        id=u.id, full_name=u.name, email=u.email, role=Role(u.role), active=bool(u.active)
    )


async def _require_active_admin(db: AsyncSession, actor: CurrentUser) -> User:
    me = (
        await db.execute(
            select(User).where(User.id == actor.id, User.tenant_id == actor.tenant_id)
        )
    ).scalar_one_or_none()
    if me is None or not me.active:
        raise unauthenticated()
    if me.role != Role.ADMIN.value:
        raise forbidden()
    return me


async def _get_member(db: AsyncSession, actor: CurrentUser, user_id: str) -> User:
    user = (
        await db.execute(
            select(User).where(User.id == user_id, User.tenant_id == actor.tenant_id)
        )
    ).scalar_one_or_none()
    if user is None:
        raise AppError(404, "NOT_FOUND", "No encontramos a ese usuario.")
    return user


async def _other_active_admins(db: AsyncSession, tenant_id: str, excluding: str) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(User).where(
                User.tenant_id == tenant_id,
                User.role == Role.ADMIN.value,
                User.active.is_(True),
                User.id != excluding,
            )
        )
    ).scalar_one()


async def list_users(db: AsyncSession, actor: CurrentUser) -> UserList:
    await _require_active_admin(db, actor)
    rows = (
        await db.execute(
            select(User).where(User.tenant_id == actor.tenant_id).order_by(User.name, User.id)
        )
    ).scalars().all()
    return UserList(items=[_out(u) for u in rows])


async def create_user(db: AsyncSession, actor: CurrentUser, body: UserCreate) -> UserAdminOut:
    await _require_active_admin(db, actor)
    taken = (
        await db.execute(
            select(User.id).where(User.tenant_id == actor.tenant_id, User.email == body.email)
        )
    ).first()
    if taken:
        raise AppError(
            409, "EMAIL_TAKEN", "Ya existe un usuario con ese correo en tu organización."
        )
    user = User(
        id=uuid4().hex,
        tenant_id=actor.tenant_id,
        name=body.full_name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role.value,
        active=True,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:  # dos altas simultáneas con el mismo correo
        await db.rollback()
        raise AppError(
            409, "EMAIL_TAKEN", "Ya existe un usuario con ese correo en tu organización."
        ) from exc
    await audit_service.record(
        db, actor, audit_service.USER_CREATED, "USER", user.id,
        {"email": user.email, "role": user.role},
    )
    return _out(user)


async def update_user(
    db: AsyncSession, actor: CurrentUser, user_id: str, body: UserUpdate
) -> UserAdminOut:
    await _require_active_admin(db, actor)
    user = await _get_member(db, actor, user_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return _out(user)

    new_role = changes["role"].value if changes.get("role") is not None else None
    new_active = changes.get("active")
    loses_admin = (
        user.role == Role.ADMIN.value
        and user.active
        and ((new_role is not None and new_role != Role.ADMIN.value) or new_active is False)
    )
    if user.id == actor.id and (
        (new_role is not None and new_role != user.role) or new_active is False
    ):
        raise AppError(
            409, "SELF_CHANGE",
            "No puedes cambiar tu propio rol ni desactivar tu propia cuenta. "
            "Pídelo a otra persona administradora.",
        )
    if loses_admin and await _other_active_admins(db, actor.tenant_id, user.id) == 0:
        raise AppError(
            409, "LAST_ADMIN", "La organización debe conservar al menos un administrador activo."
        )

    fields = []
    if changes.get("full_name") is not None and changes["full_name"] != user.name:
        user.name = changes["full_name"]
        fields.append("full_name")
    if new_role is not None and new_role != user.role:
        user.role = new_role
        fields.append("role")
    if new_active is not None and new_active != user.active:
        user.active = new_active
        fields.append("active")
    if not fields:
        return _out(user)
    await db.commit()
    await audit_service.record(
        db, actor, audit_service.USER_UPDATED, "USER", user.id,
        {"email": user.email, "fields": fields, "role": user.role, "active": bool(user.active)},
    )
    return _out(user)


async def reset_password(
    db: AsyncSession, actor: CurrentUser, user_id: str, body: PasswordReset
) -> None:
    await _require_active_admin(db, actor)
    user = await _get_member(db, actor, user_id)
    if user.id == actor.id:
        raise AppError(
            409, "SELF_CHANGE", "Para cambiar tu propia contraseña usa «Mi cuenta»."
        )
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    await audit_service.record(
        db, actor, audit_service.USER_PASSWORD_RESET, "USER", user.id, {"email": user.email}
    )


async def change_own_password(db: AsyncSession, actor: CurrentUser, body: PasswordChange) -> None:
    limits.check_password_change_allowed(actor.id)
    user = (
        await db.execute(
            select(User).where(User.id == actor.id, User.tenant_id == actor.tenant_id)
        )
    ).scalar_one_or_none()
    if user is None or not user.active:
        raise unauthenticated()
    if not verify_password(body.current_password, user.password_hash):
        limits.register_password_failure(actor.id)
        raise AppError(400, "INVALID_INPUT", "La contraseña actual no es correcta.",
                       {"fields": [{"loc": ["current_password"], "msg": "No es correcta."}]})
    if body.new_password == body.current_password:
        raise AppError(400, "INVALID_INPUT", "La nueva contraseña debe ser distinta a la actual.",
                       {"fields": [{"loc": ["new_password"], "msg": "Debe ser distinta."}]})
    limits.register_password_success(actor.id)
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    await audit_service.record(db, actor, audit_service.PASSWORD_CHANGED, "USER", user.id)
