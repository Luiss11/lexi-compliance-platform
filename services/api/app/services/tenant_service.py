"""Alta de una organización nueva con su primer administrador.

Lo usa el proveedor (tú) desde la línea de comandos; no hay endpoint público, porque cualquiera
podría crear organizaciones. Ver app/tools/create_tenant.py.
"""
import re
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import Role, hash_password
from app.models.tables import AuditLog, Tenant, User
from app.schemas.users import check_password_strength
from app.services import audit_service

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _bad(field: str, message: str) -> AppError:
    return AppError(400, "INVALID_INPUT", message, {"fields": [{"loc": [field], "msg": message}]})


async def create_tenant(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    sector: str,
    admin_name: str,
    admin_email: str,
    admin_password: str,
) -> tuple[Tenant, User]:
    name, sector, admin_name = name.strip(), sector.strip(), admin_name.strip()
    slug, admin_email = slug.strip().lower(), admin_email.strip().lower()
    if len(name) < 2:
        raise _bad("name", "Escribe el nombre de la organización.")
    if not SLUG_RE.match(slug):
        raise _bad(
            "slug", "El identificador usa minúsculas, números y guiones (3 a 60 caracteres)."
        )
    if not sector:
        raise _bad("sector", "Indica el sector (por ejemplo: clinica o comercio).")
    if len(admin_name) < 2:
        raise _bad("admin_name", "Escribe el nombre de la persona administradora.")
    if not _EMAIL_RE.match(admin_email):
        raise _bad("admin_email", "Escribe un correo válido.")
    try:
        check_password_strength(admin_password)
    except ValueError as exc:
        raise _bad("admin_password", str(exc)) from exc

    exists = (await db.execute(select(Tenant.id).where(Tenant.slug == slug))).first()
    if exists:
        raise AppError(
            409, "SLUG_TAKEN", f"Ya existe una organización con el identificador «{slug}»."
        )

    tenant = Tenant(id=uuid4().hex, name=name, slug=slug, sector=sector)
    admin = User(
        id=uuid4().hex,
        tenant_id=tenant.id,
        name=admin_name,
        email=admin_email,
        password_hash=hash_password(admin_password),
        role=Role.ADMIN.value,
        active=True,
    )
    db.add_all([tenant, admin])
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(409, "SLUG_TAKEN", "Esa organización ya existe.") from exc

    # Bitácora de la organización nueva; sin actor porque lo hace el proveedor desde el servidor
    try:
        db.add(
            AuditLog(
                id=str(uuid4()), tenant_id=tenant.id, actor_id=None,
                action=audit_service.TENANT_CREATED, entity_type="TENANT", entity_id=tenant.id,
                details={"slug": slug, "sector": sector, "admin_email": admin_email},
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        await db.commit()
    except Exception:  # noqa: BLE001 - la bitácora nunca debe romper el alta
        await db.rollback()
    return tenant, admin
