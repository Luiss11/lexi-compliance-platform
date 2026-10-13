"""Tareas: permisos por rol, aislamiento por organización y máquina de estados."""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import tasks
from app.core.errors import register_exception_handlers
from app.core.security import Role, create_access_token
from app.db.session import get_db
from app.models.tables import Base, EvidenceFile, Priority, Task, TaskStatus, Tenant, User


def auth(user_id: str, tenant_id: str, role: Role) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id, tenant_id, role)}"}


ADMIN = auth("u-admin", "t1", Role.ADMIN)
COMPLIANCE = auth("u-comp", "t1", Role.COMPLIANCE)
OPERATOR = auth("u-op", "t1", Role.OPERATOR)
OTHER_OP = auth("u-op2", "t1", Role.OPERATOR)
FOREIGN_ADMIN = auth("u-x", "t2", Role.ADMIN)


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        s.add_all(
            [
                Tenant(id="t1", name="Clínica", slug="clinica", sector="clinica"),
                Tenant(id="t2", name="Otro", slug="otro", sector="retail"),
                User(id="u-admin", tenant_id="t1", name="Admin", email="a@x", password_hash="x", role="ADMIN"),
                User(id="u-comp", tenant_id="t1", name="Comp", email="c@x", password_hash="x", role="COMPLIANCE"),
                User(id="u-op", tenant_id="t1", name="Op Uno", email="o@x", password_hash="x", role="OPERATOR"),
                User(id="u-op2", tenant_id="t1", name="Op Dos", email="o2@x", password_hash="x", role="OPERATOR"),
                User(id="u-x", tenant_id="t2", name="Foráneo", email="f@x", password_hash="x", role="ADMIN"),
            ]
        )
        await s.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(tasks.router, prefix="/api/v1/tasks")

    async def override_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.session_factory = Session
        yield c
    await engine.dispose()


async def add_evidence(client, task_id, uploader="u-op"):
    """Inserta una evidencia directamente en la base (la subida real se prueba en test_evidence)."""
    async with client.session_factory() as s:
        s.add(EvidenceFile(id=f"ev-{task_id}-{uploader}", task_id=task_id, uploaded_by_id=uploader,
                           filename="foto.jpg", mime_type="image/jpeg", size_bytes=10,
                           sha256="0" * 64, ai_verdict="NOT_REVIEWED"))
        await s.commit()


async def make(client, headers=ADMIN, **kw):
    body = {"title": "Aviso de privacidad", "priority": "ALTA"}
    body.update(kw)
    res = await client.post("/api/v1/tasks", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


@pytest.mark.asyncio
async def test_requires_auth(client):
    res = await client.get("/api/v1/tasks")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_create_defaults_and_codes(client):
    a = await make(client)
    b = await make(client, title="Contrato de empleados")
    assert a["status"] == "BACKLOG"
    assert a["code"] == "TSK-001" and b["code"] == "TSK-002"
    assert a["suggested_by_ai"] is False
    assert a["created_at"]


@pytest.mark.asyncio
async def test_codes_are_per_tenant(client):
    await make(client)
    other = await make(client, headers=FOREIGN_ADMIN)
    assert other["code"] == "TSK-001"


@pytest.mark.asyncio
async def test_operator_cannot_create_or_edit(client):
    res = await client.post("/api/v1/tasks", json={"title": "Algo largo"}, headers=OPERATOR)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
    t = await make(client, assignee_id="u-op")
    res = await client.patch(f"/api/v1/tasks/{t['id']}", json={"title": "Nuevo título"}, headers=OPERATOR)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_validation_envelope(client):
    res = await client.post("/api/v1/tasks", json={"title": " a "}, headers=ADMIN)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_INPUT"
    res = await client.post("/api/v1/tasks", json={"title": "Válido", "priority": "URGENTE"}, headers=ADMIN)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_tenant_isolation(client):
    t = await make(client)
    # La otra organización no la ve ni en lista ni por id, ni puede moverla
    lst = await client.get("/api/v1/tasks", headers=FOREIGN_ADMIN)
    assert lst.json()["items"] == []
    assert (await client.get(f"/api/v1/tasks/{t['id']}", headers=FOREIGN_ADMIN)).status_code == 404
    res = await client.patch(
        f"/api/v1/tasks/{t['id']}/status", json={"status": "IN_PROGRESS"}, headers=FOREIGN_ADMIN
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_assignee_must_belong_to_tenant(client):
    res = await client.post(
        "/api/v1/tasks", json={"title": "Tarea nueva", "assignee_id": "u-x"}, headers=ADMIN
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_operator_sees_only_assigned(client):
    mine = await make(client, assignee_id="u-op")
    await make(client, title="De otro operador", assignee_id="u-op2")
    await make(client, title="Sin asignar")
    items = (await client.get("/api/v1/tasks", headers=OPERATOR)).json()["items"]
    assert [i["id"] for i in items] == [mine["id"]]
    assert items[0]["assignee_name"] == "Op Uno"
    # Y de las demás recibe 404, no 403: no se revela que existen
    all_items = (await client.get("/api/v1/tasks", headers=ADMIN)).json()["items"]
    other = next(i for i in all_items if i["title"] == "De otro operador")
    assert (await client.get(f"/api/v1/tasks/{other['id']}", headers=OPERATOR)).status_code == 404


@pytest.mark.asyncio
async def test_manager_filters(client):
    await make(client, assignee_id="u-op")
    await make(client, title="Sin asignar")
    res = await client.get("/api/v1/tasks?assignee_id=u-op", headers=ADMIN)
    assert len(res.json()["items"]) == 1
    res = await client.get("/api/v1/tasks?status=DONE", headers=ADMIN)
    assert res.json()["items"] == []
    res = await client.get("/api/v1/tasks?status=NOPE", headers=ADMIN)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_happy_path_through_all_states(client):
    t = await make(client, assignee_id="u-op")
    url = f"/api/v1/tasks/{t['id']}/status"
    r = await client.patch(url, json={"status": "IN_PROGRESS"}, headers=OPERATOR)
    assert r.status_code == 200 and r.json()["status"] == "IN_PROGRESS"
    await add_evidence(client, t["id"])
    r = await client.patch(url, json={"status": "IN_REVIEW"}, headers=OPERATOR)
    assert r.json()["status"] == "IN_REVIEW"
    r = await client.patch(url, json={"status": "DONE"}, headers=COMPLIANCE)
    assert r.json()["status"] == "DONE"


@pytest.mark.asyncio
async def test_invalid_transition(client):
    t = await make(client)
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}/status", json={"status": "DONE"}, headers=ADMIN
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "INVALID_TRANSITION"
    assert err["details"]["allowed"] == ["IN_PROGRESS"]


@pytest.mark.asyncio
async def test_operator_cannot_close_or_reopen(client):
    t = await make(client, assignee_id="u-op")
    url = f"/api/v1/tasks/{t['id']}/status"
    await client.patch(url, json={"status": "IN_PROGRESS"}, headers=OPERATOR)
    await add_evidence(client, t["id"])
    await client.patch(url, json={"status": "IN_REVIEW"}, headers=OPERATOR)
    r = await client.patch(url, json={"status": "DONE"}, headers=OPERATOR)
    assert r.status_code == 403
    await client.patch(url, json={"status": "DONE"}, headers=ADMIN)
    r = await client.patch(url, json={"status": "IN_REVIEW"}, headers=OPERATOR)
    assert r.status_code == 403
    r = await client.patch(url, json={"status": "IN_REVIEW"}, headers=ADMIN)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_same_status_is_noop(client):
    t = await make(client)
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}/status", json={"status": "BACKLOG"}, headers=ADMIN
    )
    assert r.status_code == 200 and r.json()["status"] == "BACKLOG"


@pytest.mark.asyncio
async def test_update_partial_and_unassign(client):
    t = await make(client, assignee_id="u-op", due_date="2030-01-15")
    assert t["due_date"].startswith("2030-01-15")
    r = await client.patch(f"/api/v1/tasks/{t['id']}", json={"priority": "BAJA"}, headers=ADMIN)
    out = r.json()
    assert out["priority"] == "BAJA" and out["title"] == t["title"]
    assert out["assignee_id"] == "u-op" and out["due_date"].startswith("2030-01-15")
    r = await client.patch(
        f"/api/v1/tasks/{t['id']}", json={"assignee_id": None, "due_date": None}, headers=ADMIN
    )
    out = r.json()
    assert out["assignee_id"] is None and out["assignee_name"] is None and out["due_date"] is None


@pytest.mark.asyncio
async def test_update_rejects_null_title(client):
    t = await make(client)
    r = await client.patch(f"/api/v1/tasks/{t['id']}", json={"title": None}, headers=ADMIN)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_overdue_flag(client):
    late = await make(client, due_date="2000-01-01")
    future = await make(client, title="A tiempo", due_date="2999-01-01")
    items = {i["id"]: i for i in (await client.get("/api/v1/tasks", headers=ADMIN)).json()["items"]}
    assert items[late["id"]]["overdue"] is True
    assert items[future["id"]]["overdue"] is False
    # Una tarea cerrada ya no está vencida
    url = f"/api/v1/tasks/{late['id']}/status"
    await client.patch(url, json={"status": "IN_PROGRESS"}, headers=ADMIN)
    await add_evidence(client, late["id"], uploader="u-op")
    for s in ("IN_REVIEW", "DONE"):
        await client.patch(url, json={"status": s}, headers=ADMIN)
    assert (await client.get(f"/api/v1/tasks/{late['id']}", headers=ADMIN)).json()["overdue"] is False


@pytest.mark.asyncio
async def test_assignees_list_managers_only(client):
    r = await client.get("/api/v1/tasks/assignees", headers=COMPLIANCE)
    assert r.status_code == 200
    names = [u["full_name"] for u in r.json()["items"]]
    assert "Foráneo" not in names and "Op Uno" in names
    assert (await client.get("/api/v1/tasks/assignees", headers=OPERATOR)).status_code == 403


@pytest.mark.asyncio
async def test_review_requires_evidence(client):
    t = await make(client, assignee_id="u-op")
    url = f"/api/v1/tasks/{t['id']}/status"
    await client.patch(url, json={"status": "IN_PROGRESS"}, headers=OPERATOR)
    r = await client.patch(url, json={"status": "IN_REVIEW"}, headers=OPERATOR)
    assert r.status_code == 409 and r.json()["error"]["code"] == "EVIDENCE_REQUIRED"
    await add_evidence(client, t["id"])
    r = await client.patch(url, json={"status": "IN_REVIEW"}, headers=OPERATOR)
    assert r.status_code == 200
    assert r.json()["evidence_count"] == 1


@pytest.mark.asyncio
async def test_uploader_cannot_approve_own_evidence(client):
    t = await make(client, assignee_id="u-op")
    url = f"/api/v1/tasks/{t['id']}/status"
    await client.patch(url, json={"status": "IN_PROGRESS"}, headers=ADMIN)
    await add_evidence(client, t["id"], uploader="u-admin")
    await client.patch(url, json={"status": "IN_REVIEW"}, headers=ADMIN)
    r = await client.patch(url, json={"status": "DONE"}, headers=ADMIN)
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"
    # Otro oficial sí puede cerrarla
    r = await client.patch(url, json={"status": "DONE"}, headers=COMPLIANCE)
    assert r.status_code == 200 and r.json()["status"] == "DONE"


@pytest.mark.asyncio
async def test_evidence_count_in_list(client):
    t = await make(client, assignee_id="u-op")
    await make(client, title="Otra tarea")
    await add_evidence(client, t["id"])
    items = {i["id"]: i for i in (await client.get("/api/v1/tasks", headers=ADMIN)).json()["items"]}
    assert items[t["id"]]["evidence_count"] == 1
    assert sorted(i["evidence_count"] for i in items.values()) == [0, 1]
