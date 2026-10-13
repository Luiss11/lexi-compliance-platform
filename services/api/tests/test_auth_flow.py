"""Flujo de login de punta a punta contra SQLite en memoria (sin Postgres ni Docker)."""
import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import auth
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.security import (
    CurrentUser,
    Role,
    create_access_token,
    hash_password,
    require_roles,
    verify_password,
)
from app.db.session import get_db
from app.models.tables import Base, Tenant, User

PASSWORD = "lexi1234"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    pw = hash_password(PASSWORD, rounds=4)
    async with Session() as s:
        s.add_all(
            [
                Tenant(id="t1", name="Clínica Sonrisa", slug="clinica-sonrisa", sector="clinica"),
                Tenant(id="t2", name="Otro negocio", slug="otro", sector="retail"),
                User(id="u1", tenant_id="t1", name="Admin Demo", email="admin@demo.lexi",
                     password_hash=pw, role="ADMIN"),
                User(id="u2", tenant_id="t1", name="Operator Demo", email="operator@demo.lexi",
                     password_hash=pw, role="OPERATOR"),
            ]
        )
        await s.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth.router, prefix="/api/v1/auth")

    @app.get("/admin-only")
    async def admin_only(user: CurrentUser = Depends(require_roles(Role.ADMIN))):
        return {"ok": True, "role": user.role}

    async def override_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await engine.dispose()


def login_body(**kw):
    body = {"tenant_slug": "clinica-sonrisa", "email": "admin@demo.lexi", "password": PASSWORD}
    body.update(kw)
    return body


def test_password_hash_roundtrip():
    h = hash_password("secreto-largo", rounds=4)
    assert h != "secreto-largo"
    assert verify_password("secreto-largo", h)
    assert not verify_password("otro", h)


@pytest.mark.asyncio
async def test_login_ok_returns_token_and_user(client):
    res = await client.post("/api/v1/auth/login", json=login_body())
    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == settings.jwt_expires_minutes * 60
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["full_name"] == "Admin Demo"


@pytest.mark.asyncio
async def test_token_claims_have_no_personal_data(client):
    res = await client.post("/api/v1/auth/login", json=login_body())
    claims = jwt.decode(res.json()["access_token"], settings.jwt_secret,
                        algorithms=[settings.jwt_algorithm])
    assert set(claims) == {"sub", "tid", "role", "exp"}
    assert claims["tid"] == "t1"


@pytest.mark.asyncio
async def test_login_is_case_insensitive_for_email_and_slug(client):
    res = await client.post(
        "/api/v1/auth/login", json=login_body(email="ADMIN@Demo.Lexi", tenant_slug="Clinica-Sonrisa")
    )
    assert res.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override",
    [{"password": "mal"}, {"email": "nadie@demo.lexi"}, {"tenant_slug": "no-existe"},
     {"tenant_slug": "otro"}],
)
async def test_bad_credentials_share_one_message(client, override):
    res = await client.post("/api/v1/auth/login", json=login_body(**override))
    assert res.status_code == 401
    err = res.json()["error"]
    assert err["code"] == "INVALID_CREDENTIALS"
    assert err["message"] == "Correo o contraseña incorrectos."


@pytest.mark.asyncio
async def test_login_validation_error_uses_envelope(client):
    res = await client.post("/api/v1/auth/login", json={"email": "x@y.z"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_me_returns_user_and_tenant(client):
    token = (await client.post("/api/v1/auth/login", json=login_body())).json()["access_token"]
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "admin@demo.lexi"
    assert data["tenant"]["slug"] == "clinica-sonrisa"


@pytest.mark.asyncio
async def test_me_without_token_is_401(client):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_me_with_garbage_token_is_401(client):
    res = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer basura"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token_of_deleted_user_is_401(client):
    token = create_access_token("fantasma", "t1", Role.ADMIN)
    res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_rbac_blocks_operator_and_allows_admin(client):
    admin = create_access_token("u1", "t1", Role.ADMIN)
    operator = create_access_token("u2", "t1", Role.OPERATOR)
    ok = await client.get("/admin-only", headers={"Authorization": f"Bearer {admin}"})
    no = await client.get("/admin-only", headers={"Authorization": f"Bearer {operator}"})
    assert ok.status_code == 200
    assert no.status_code == 403
    assert no.json()["error"]["code"] == "FORBIDDEN"
