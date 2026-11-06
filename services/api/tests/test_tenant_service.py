"""Alta de organización con su primer administrador."""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.errors import AppError
from app.core.security import verify_password
from app.models.tables import AuditLog, Base, Tenant, User
from app.services import obligations_catalog, tenant_service

GOOD = {
    "name": "Clínica Dental Sonrisa", "slug": "clinica-sonrisa", "sector": "clinica",
    "admin_name": "Dra. Ana López", "admin_email": "Ana@Clinica.mx",
    "admin_password": "clave-segura-1",
}


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_creates_tenant_and_active_admin(db):
    tenant, admin = await tenant_service.create_tenant(db, **GOOD)
    assert tenant.slug == "clinica-sonrisa"
    assert admin.role == "ADMIN" and admin.active is True and admin.tenant_id == tenant.id
    assert admin.email == "ana@clinica.mx"
    assert admin.password_hash != GOOD["admin_password"]
    assert verify_password(GOOD["admin_password"], admin.password_hash)
    # el sector queda reconocible para el catálogo de obligaciones
    assert obligations_catalog.normalize_sector(tenant.sector) == "clinica"


@pytest.mark.asyncio
async def test_writes_audit_entry_without_secrets(db):
    tenant, _ = await tenant_service.create_tenant(db, **GOOD)
    query = select(AuditLog).where(AuditLog.tenant_id == tenant.id)
    rows = (await db.execute(query)).scalars().all()
    assert [r.action for r in rows] == ["TENANT_CREATED"]
    assert GOOD["admin_password"] not in str(rows[0].details)


@pytest.mark.asyncio
async def test_duplicate_slug_is_rejected(db):
    await tenant_service.create_tenant(db, **GOOD)
    with pytest.raises(AppError) as err:
        await tenant_service.create_tenant(db, **{**GOOD, "admin_email": "otro@x.mx"})
    assert err.value.code == "SLUG_TAKEN"
    assert len((await db.execute(select(Tenant))).scalars().all()) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"slug": "Con Espacios"}, {"slug": "ab"}, {"slug": "-guion"}, {"name": " "},
        {"sector": ""}, {"admin_email": "no-correo"}, {"admin_password": "corta1"},
        {"admin_name": "A"},
    ],
)
async def test_invalid_input_creates_nothing(db, change):
    with pytest.raises(AppError) as err:
        await tenant_service.create_tenant(db, **{**GOOD, **change})
    assert err.value.code == "INVALID_INPUT"
    assert (await db.execute(select(Tenant))).scalars().all() == []
    assert (await db.execute(select(User))).scalars().all() == []
