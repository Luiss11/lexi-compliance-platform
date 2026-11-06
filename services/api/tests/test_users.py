# ruff: noqa: E501
"""Usuarios y contraseñas: permisos, aislamiento por organización y reglas de seguridad."""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import auth, users
from app.core.errors import register_exception_handlers
from app.core.security import Role, create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.tables import AuditLog, Base, Tenant, User

PW = "clave-segura-1"


def auth_h(user_id, tenant_id, role):
    return {"Authorization": f"Bearer {create_access_token(user_id, tenant_id, role)}"}


ADMIN = auth_h("a1", "t1", Role.ADMIN)
ADMIN2 = auth_h("a2", "t1", Role.ADMIN)
COMPLIANCE = auth_h("c1", "t1", Role.COMPLIANCE)
OPERATOR = auth_h("o1", "t1", Role.OPERATOR)
FOREIGN_ADMIN = auth_h("x1", "t2", Role.ADMIN)


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    pw = hash_password(PW, rounds=4)
    async with Session() as s:
        s.add_all(
            [
                Tenant(id="t1", name="Clínica", slug="clinica", sector="clinica"),
                Tenant(id="t2", name="Otro", slug="otro", sector="retail"),
                User(id="a1", tenant_id="t1", name="Admin Uno", email="a1@x.mx", password_hash=pw, role="ADMIN"),
                User(id="a2", tenant_id="t1", name="Admin Dos", email="a2@x.mx", password_hash=pw, role="ADMIN"),
                User(id="c1", tenant_id="t1", name="Comp", email="c1@x.mx", password_hash=pw, role="COMPLIANCE"),
                User(id="o1", tenant_id="t1", name="Oper", email="o1@x.mx", password_hash=pw, role="OPERATOR"),
                User(id="x1", tenant_id="t2", name="Foráneo", email="x1@x.mx", password_hash=pw, role="ADMIN"),
            ]
        )
        await s.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(users.router, prefix="/api/v1/users")
    app.include_router(auth.router, prefix="/api/v1/auth")

    async def override_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.session_factory = Session
        yield c
    await engine.dispose()


def new_user(**kw):
    body = {"full_name": "Nueva Persona", "email": "Nueva@Clinica.MX", "role": "OPERATOR",
            "password": "otra-clave-77"}
    body.update(kw)
    return body


async def db_user(client, user_id):
    async with client.session_factory() as s:
        return (await s.execute(select(User).where(User.id == user_id))).scalar_one()


# ---------------------------------------------------------------- permisos y aislamiento
@pytest.mark.asyncio
async def test_only_admin_can_manage_users(client):
    for headers in (COMPLIANCE, OPERATOR):
        assert (await client.get("/api/v1/users", headers=headers)).status_code == 403
        assert (await client.post("/api/v1/users", json=new_user(), headers=headers)).status_code == 403
        assert (await client.patch("/api/v1/users/o1", json={"role": "ADMIN"}, headers=headers)).status_code == 403
    assert (await client.get("/api/v1/users")).status_code == 401


@pytest.mark.asyncio
async def test_list_shows_only_own_organization(client):
    res = await client.get("/api/v1/users", headers=ADMIN)
    ids = {u["id"] for u in res.json()["items"]}
    assert ids == {"a1", "a2", "c1", "o1"}
    assert all("password" not in u and "password_hash" not in u for u in res.json()["items"])


@pytest.mark.asyncio
async def test_cannot_touch_users_of_another_organization(client):
    assert (await client.patch("/api/v1/users/x1", json={"active": False}, headers=ADMIN)).status_code == 404
    res = await client.post("/api/v1/users/x1/password", json={"new_password": "algo-seguro-12"}, headers=ADMIN)
    assert res.status_code == 404
    assert (await db_user(client, "x1")).active is True


@pytest.mark.asyncio
async def test_stale_admin_token_is_rejected_after_demotion(client):
    """El token dice ADMIN pero en la base ya no lo es: no debe poder administrar."""
    async with client.session_factory() as s:
        u = (await s.execute(select(User).where(User.id == "a2"))).scalar_one()
        u.role = "OPERATOR"
        await s.commit()
    assert (await client.get("/api/v1/users", headers=ADMIN2)).status_code == 403


@pytest.mark.asyncio
async def test_deactivated_admin_token_is_rejected(client):
    async with client.session_factory() as s:
        u = (await s.execute(select(User).where(User.id == "a2"))).scalar_one()
        u.active = False
        await s.commit()
    assert (await client.get("/api/v1/users", headers=ADMIN2)).status_code == 401


# --------------------------------------------------------------------------------- alta
@pytest.mark.asyncio
async def test_create_user_normalizes_email_and_hashes_password(client):
    res = await client.post("/api/v1/users", json=new_user(), headers=ADMIN)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "nueva@clinica.mx" and body["role"] == "OPERATOR" and body["active"] is True
    created = await db_user(client, body["id"])
    assert created.tenant_id == "t1"
    assert created.password_hash != "otra-clave-77"
    assert verify_password("otra-clave-77", created.password_hash)


@pytest.mark.asyncio
async def test_new_user_can_log_in(client):
    await client.post("/api/v1/users", json=new_user(email="nuevo@x.mx"), headers=ADMIN)
    res = await client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "clinica", "email": "nuevo@x.mx", "password": "otra-clave-77"},
    )
    assert res.status_code == 200 and res.json()["user"]["role"] == "OPERATOR"


@pytest.mark.asyncio
async def test_duplicate_email_in_same_org_is_rejected_but_ok_in_another(client):
    assert (await client.post("/api/v1/users", json=new_user(email="a1@x.mx"), headers=ADMIN)).status_code == 409
    res = await client.post("/api/v1/users", json=new_user(email="a1@X.MX"), headers=ADMIN)
    assert res.status_code == 409 and res.json()["error"]["code"] == "EMAIL_TAKEN"
    # el mismo correo en otra organización es válido
    assert (await client.post("/api/v1/users", json=new_user(email="a1@x.mx"), headers=FOREIGN_ADMIN)).status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize("password", ["corta1", "sololetrasmuylarga", "1234567890123", ""])
async def test_weak_passwords_are_rejected(client, password):
    res = await client.post("/api/v1/users", json=new_user(password=password), headers=ADMIN)
    assert res.status_code == 400 and res.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_invalid_email_and_role_are_rejected(client):
    assert (await client.post("/api/v1/users", json=new_user(email="no-es-correo"), headers=ADMIN)).status_code == 400
    assert (await client.post("/api/v1/users", json=new_user(role="SUPERUSER"), headers=ADMIN)).status_code == 400


# ------------------------------------------------------------------------- edición
@pytest.mark.asyncio
async def test_change_role_and_deactivate(client):
    res = await client.patch("/api/v1/users/o1", json={"role": "COMPLIANCE"}, headers=ADMIN)
    assert res.status_code == 200 and res.json()["role"] == "COMPLIANCE"
    res = await client.patch("/api/v1/users/o1", json={"active": False}, headers=ADMIN)
    assert res.json()["active"] is False
    assert (await db_user(client, "o1")).active is False


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role_or_deactivate_self(client):
    for body in ({"role": "OPERATOR"}, {"active": False}):
        res = await client.patch("/api/v1/users/a1", json=body, headers=ADMIN)
        assert res.status_code == 409 and res.json()["error"]["code"] == "SELF_CHANGE"
    # renombrarse sí se puede
    assert (await client.patch("/api/v1/users/a1", json={"full_name": "Nombre Nuevo"}, headers=ADMIN)).status_code == 200


@pytest.mark.asyncio
async def test_deactivating_the_other_admin_leaves_one_and_it_is_protected(client):
    assert (await client.patch("/api/v1/users/a2", json={"active": False}, headers=ADMIN)).status_code == 200
    # a1 queda como único administrador activo y no puede quitarse el rol
    res = await client.patch("/api/v1/users/a1", json={"role": "OPERATOR"}, headers=ADMIN)
    assert res.status_code == 409
    assert (await db_user(client, "a1")).role == "ADMIN"


@pytest.mark.asyncio
async def test_active_admin_count_ignores_inactive_and_other_organizations(client):
    from app.services import users_service

    async with client.session_factory() as s:
        assert await users_service._other_active_admins(s, "t1", excluding="a1") == 1  # a2
        assert await users_service._other_active_admins(s, "t2", excluding="x1") == 0
        a2 = (await s.execute(select(User).where(User.id == "a2"))).scalar_one()
        a2.active = False
        await s.commit()
        assert await users_service._other_active_admins(s, "t1", excluding="a1") == 0


@pytest.mark.asyncio
async def test_empty_patch_changes_nothing(client):
    res = await client.patch("/api/v1/users/o1", json={}, headers=ADMIN)
    assert res.status_code == 200 and res.json()["role"] == "OPERATOR"


# -------------------------------------------------------------- inicio de sesión y /me
@pytest.mark.asyncio
async def test_deactivated_user_cannot_log_in(client):
    await client.patch("/api/v1/users/o1", json={"active": False}, headers=ADMIN)
    body = {"tenant_slug": "clinica", "email": "o1@x.mx", "password": PW}
    res = await client.post("/api/v1/auth/login", json=body)
    assert res.status_code == 403 and res.json()["error"]["code"] == "ACCOUNT_DISABLED"
    # con contraseña incorrecta no se revela que la cuenta existe
    body["password"] = "incorrecta-99"
    assert (await client.post("/api/v1/auth/login", json=body)).status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_deactivated_user(client):
    await client.patch("/api/v1/users/o1", json={"active": False}, headers=ADMIN)
    assert (await client.get("/api/v1/auth/me", headers=OPERATOR)).status_code == 401


# --------------------------------------------------------------------- contraseñas
@pytest.mark.asyncio
async def test_admin_resets_another_users_password(client):
    res = await client.post("/api/v1/users/o1/password", json={"new_password": "reinicio-2026a"}, headers=ADMIN)
    assert res.status_code == 204
    assert verify_password("reinicio-2026a", (await db_user(client, "o1")).password_hash)


@pytest.mark.asyncio
async def test_admin_cannot_reset_own_password_that_way(client):
    res = await client.post("/api/v1/users/a1/password", json={"new_password": "reinicio-2026a"}, headers=ADMIN)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_change_own_password(client):
    res = await client.post(
        "/api/v1/auth/password",
        json={"current_password": PW, "new_password": "nueva-clave-55"}, headers=OPERATOR,
    )
    assert res.status_code == 204
    login = {"tenant_slug": "clinica", "email": "o1@x.mx"}
    assert (await client.post("/api/v1/auth/login", json={**login, "password": PW})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={**login, "password": "nueva-clave-55"})).status_code == 200


@pytest.mark.asyncio
async def test_change_password_requires_correct_current_and_a_different_new_one(client):
    res = await client.post(
        "/api/v1/auth/password",
        json={"current_password": "equivocada-1", "new_password": "nueva-clave-55"}, headers=OPERATOR,
    )
    assert res.status_code == 400 and res.json()["error"]["code"] == "INVALID_INPUT"
    res = await client.post(
        "/api/v1/auth/password", json={"current_password": PW, "new_password": PW}, headers=OPERATOR
    )
    assert res.status_code == 400
    res = await client.post(
        "/api/v1/auth/password", json={"current_password": PW, "new_password": "corta1"}, headers=OPERATOR
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_change_password_is_throttled(client):
    from app.core.config import settings

    body = {"current_password": "equivocada-1", "new_password": "nueva-clave-55"}
    for _ in range(settings.login_max_failures):
        assert (await client.post("/api/v1/auth/password", json=body, headers=OPERATOR)).status_code == 400
    res = await client.post("/api/v1/auth/password", json=body, headers=OPERATOR)
    assert res.status_code == 429 and "Retry-After" in res.headers
    # ni siquiera la contraseña correcta pasa mientras dure el bloqueo
    good = {"current_password": PW, "new_password": "nueva-clave-55"}
    assert (await client.post("/api/v1/auth/password", json=good, headers=OPERATOR)).status_code == 429


@pytest.mark.asyncio
async def test_audit_log_never_contains_passwords(client):
    await client.post("/api/v1/users", json=new_user(), headers=ADMIN)
    await client.post("/api/v1/users/o1/password", json={"new_password": "reinicio-2026a"}, headers=ADMIN)
    await client.post(
        "/api/v1/auth/password",
        json={"current_password": PW, "new_password": "nueva-clave-55"}, headers=COMPLIANCE,
    )
    async with client.session_factory() as s:
        rows = (await s.execute(select(AuditLog))).scalars().all()
    actions = {r.action for r in rows}
    assert {"USER_CREATED", "USER_PASSWORD_RESET", "PASSWORD_CHANGED"} <= actions
    dump = " ".join(str(r.details) for r in rows)
    for secret in ("otra-clave-77", "reinicio-2026a", "nueva-clave-55", PW):
        assert secret not in dump
