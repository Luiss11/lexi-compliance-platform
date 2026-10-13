"""Evidencias: sello SHA-256, inmutabilidad, tipos válidos, verificación y permisos."""
import hashlib
import io
import os

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import evidence, tasks
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.security import Role, create_access_token
from app.db.session import get_db
from app.models.tables import Base, Task, TaskStatus, Tenant, User, Priority


def auth(user_id, tenant_id, role):
    return {"Authorization": f"Bearer {create_access_token(user_id, tenant_id, role)}"}


ADMIN = auth("u-admin", "t1", Role.ADMIN)
COMPLIANCE = auth("u-comp", "t1", Role.COMPLIANCE)
OPERATOR = auth("u-op", "t1", Role.OPERATOR)
OTHER_OP = auth("u-op2", "t1", Role.OPERATOR)
FOREIGN = auth("u-x", "t2", Role.ADMIN)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"fotografia"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"contenido de prueba"


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path), raising=False)
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
                Task(id="task-prog", code="TSK-001", tenant_id="t1", title="En curso", status=TaskStatus.IN_PROGRESS,
                     priority=Priority.ALTA, assignee_id="u-op"),
                Task(id="task-backlog", code="TSK-002", tenant_id="t1", title="Pendiente", status=TaskStatus.BACKLOG,
                     priority=Priority.MEDIA, assignee_id="u-op"),
                Task(id="task-done", code="TSK-003", tenant_id="t1", title="Cerrada", status=TaskStatus.DONE,
                     priority=Priority.BAJA, assignee_id="u-op"),
            ]
        )
        await s.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(tasks.router, prefix="/api/v1/tasks")
    app.include_router(evidence.tasks_router, prefix="/api/v1/tasks")
    app.include_router(evidence.router, prefix="/api/v1/evidence")

    async def override_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.storage = tmp_path
        yield c
    await engine.dispose()


async def upload(client, data=JPEG, task="task-prog", headers=OPERATOR, name="foto.jpg"):
    return await client.post(
        f"/api/v1/tasks/{task}/evidence",
        files={"evidence_file": (name, io.BytesIO(data), "application/octet-stream")},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_upload_seals_hash_of_received_bytes(client):
    res = await upload(client)
    assert res.status_code == 201, res.text
    ev = res.json()
    assert ev["sha256"] == hashlib.sha256(JPEG).hexdigest()
    assert ev["size_bytes"] == len(JPEG) and ev["mime_type"] == "image/jpeg"
    assert ev["ai_verdict"] == "NOT_REVIEWED" and ev["uploaded_by_name"] == "Op Uno"
    stored = client.storage / "t1" / "evidence" / f"{ev['id']}.jpg"
    assert stored.read_bytes() == JPEG


@pytest.mark.asyncio
async def test_type_is_detected_from_bytes_not_from_client(client):
    assert (await upload(client, PNG, name="x.jpg")).json()["mime_type"] == "image/png"
    assert (await upload(client, PDF, name="x.png")).json()["mime_type"] == "application/pdf"
    res = await upload(client, b"MZ\x90\x00 ejecutable", name="foto.jpg")
    assert res.status_code == 415 and res.json()["error"]["code"] == "UNSUPPORTED_FILE"


@pytest.mark.asyncio
async def test_empty_and_oversized(client, monkeypatch):
    res = await upload(client, b"")
    assert res.status_code == 400
    monkeypatch.setattr("app.services.evidence_service.MAX_BYTES", 20)
    monkeypatch.setattr(evidence, "MAX_BYTES", 20)
    res = await upload(client, JPEG)
    assert res.status_code == 413 and res.json()["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_each_upload_is_a_new_immutable_row(client):
    a = (await upload(client, JPEG)).json()
    b = (await upload(client, JPEG)).json()  # mismo contenido: otra fila, otro archivo
    assert a["id"] != b["id"] and a["sha256"] == b["sha256"]
    items = (await client.get("/api/v1/tasks/task-prog/evidence", headers=OPERATOR)).json()["items"]
    assert len(items) == 2
    files = os.listdir(client.storage / "t1" / "evidence")
    assert len(files) == 2


@pytest.mark.asyncio
async def test_only_open_tasks_accept_evidence(client):
    for task in ("task-backlog", "task-done"):
        res = await upload(client, task=task, headers=ADMIN)
        assert res.status_code == 409 and res.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_permissions_and_isolation(client):
    assert (await client.get("/api/v1/tasks/task-prog/evidence")).status_code == 401
    # Operador sin esa tarea asignada: 404
    assert (await upload(client, headers=OTHER_OP)).status_code == 404
    # Otra organización: 404
    assert (await upload(client, headers=FOREIGN)).status_code == 404
    ev = (await upload(client)).json()
    assert (await client.get(f"/api/v1/evidence/{ev['id']}/file", headers=FOREIGN)).status_code == 404
    assert (await client.get(f"/api/v1/evidence/{ev['id']}/file", headers=OTHER_OP)).status_code == 404
    assert (await client.get("/api/v1/tasks/task-prog/evidence", headers=FOREIGN)).status_code == 404
    # Un oficial sí puede subir y ver
    assert (await upload(client, headers=COMPLIANCE)).status_code == 201


@pytest.mark.asyncio
async def test_file_download_is_authenticated_and_exact(client):
    ev = (await upload(client, PDF, name="acta.pdf")).json()
    res = await client.get(f"/api/v1/evidence/{ev['id']}/file", headers=COMPLIANCE)
    assert res.status_code == 200 and res.content == PDF
    assert res.headers["content-type"] == "application/pdf"
    assert "inline" in res.headers["content-disposition"]
    assert (await client.get(f"/api/v1/evidence/{ev['id']}/file")).status_code == 401


@pytest.mark.asyncio
async def test_verify_ok_and_tampered_and_missing(client):
    ev = (await upload(client)).json()
    url = f"/api/v1/evidence/{ev['id']}/verify"

    ok = (await client.post(url, headers=COMPLIANCE)).json()
    assert ok["ok"] is True and ok["tampered"] is False
    assert ok["computed_sha256"] == ok["stored_sha256"] == ev["sha256"]

    path = client.storage / "t1" / "evidence" / f"{ev['id']}.jpg"
    path.write_bytes(JPEG + b"alterado")
    bad = (await client.post(url, headers=COMPLIANCE)).json()
    assert bad["tampered"] is True and bad["ok"] is False
    assert bad["computed_sha256"] != bad["stored_sha256"] and "no coincide" in bad["reason"]

    path.unlink()
    gone = (await client.post(url, headers=ADMIN)).json()
    assert gone["tampered"] is True and gone["computed_sha256"] is None


@pytest.mark.asyncio
async def test_verify_is_for_managers_only(client):
    ev = (await upload(client)).json()
    url = f"/api/v1/evidence/{ev['id']}/verify"
    assert (await client.post(url, headers=OPERATOR)).status_code == 403
    assert (await client.post(url, headers=FOREIGN)).status_code == 404
    assert (await client.post("/api/v1/evidence/nope/verify", headers=ADMIN)).status_code == 404


@pytest.mark.asyncio
async def test_filename_is_sanitized(client):
    ev = (await upload(client, name="..\\..\\etc/passwd\x00.jpg")).json()
    assert "/" not in ev["filename"] and "\\" not in ev["filename"] and "\x00" not in ev["filename"]
    # La ruta en disco se deriva del id, nunca del nombre que mandó el cliente
    assert os.listdir(client.storage / "t1" / "evidence") == [f"{ev['id']}.jpg"]
