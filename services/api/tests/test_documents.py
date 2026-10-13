"""Documentos: subida con SHA-256, estados, duplicados, aislamiento y reintento de indexación."""
import hashlib
import io

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import documents
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.security import Role, create_access_token
from app.db.session import get_db
from app.models.tables import Base, Tenant, User
from app.services import document_service


def auth(user_id: str, tenant_id: str, role: Role) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id, tenant_id, role)}"}


ADMIN = auth("u-admin", "t1", Role.ADMIN)
OPERATOR = auth("u-op", "t1", Role.OPERATOR)
FOREIGN = auth("u-x", "t2", Role.ADMIN)


def make_pdf(text: str | None = "Artículo 16. El aviso de privacidad deberá contener...") -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def files(data: bytes, name: str = "ley_datos.pdf"):
    return {"file": (name, io.BytesIO(data), "application/pdf")}


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path), raising=False)
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)

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
                User(id="u-admin", tenant_id="t1", name="Admin Demo", email="a@x", password_hash="x", role="ADMIN"),
                User(id="u-op", tenant_id="t1", name="Op", email="o@x", password_hash="x", role="OPERATOR"),
                User(id="u-x", tenant_id="t2", name="Foráneo", email="f@x", password_hash="x", role="ADMIN"),
            ]
        )
        await s.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(documents.router, prefix="/api/v1/documents")

    async def override_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await engine.dispose()


async def upload(client, data=None, headers=ADMIN, category="Ley", **extra):
    data = make_pdf() if data is None else data
    return await client.post(
        "/api/v1/documents", files=files(data), data={"category": category, **extra}, headers=headers
    )


@pytest.mark.asyncio
async def test_requires_auth_and_role(client):
    assert (await client.get("/api/v1/documents")).status_code == 401
    res = await upload(client, headers=OPERATOR)
    assert res.status_code == 403
    assert (await client.get("/api/v1/documents", headers=OPERATOR)).status_code == 403


@pytest.mark.asyncio
async def test_upload_seals_sha256_and_stays_uploaded_without_key(client, tmp_path):
    data = make_pdf()
    res = await upload(client, data)
    assert res.status_code == 201, res.text
    doc = res.json()
    assert doc["sha256"] == hashlib.sha256(data).hexdigest()
    assert doc["status"] == "UPLOADED"  # sin OPENAI_API_KEY no se indexa
    assert doc["pages"] == 1
    assert doc["title"] == "ley datos"
    assert doc["category"] == "Ley"
    assert doc["uploaded_by_name"] == "Admin Demo"
    # El archivo quedó en disco bajo la carpeta del tenant, intacto
    stored = tmp_path / "t1" / "documents" / f"{doc['id']}.pdf"
    assert stored.read_bytes() == data


@pytest.mark.asyncio
async def test_custom_title(client):
    res = await upload(client, title="  LFPDPPP completa  ")
    assert res.json()["title"] == "LFPDPPP completa"


@pytest.mark.asyncio
async def test_rejects_non_pdf_empty_and_corrupt(client):
    res = await client.post(
        "/api/v1/documents", files=files(b"hola mundo", "x.pdf"), data={"category": "Ley"}, headers=ADMIN
    )
    assert res.status_code == 415 and res.json()["error"]["code"] == "UNSUPPORTED_FILE"
    res = await client.post(
        "/api/v1/documents", files=files(b"", "x.pdf"), data={"category": "Ley"}, headers=ADMIN
    )
    assert res.status_code == 400
    res = await client.post(
        "/api/v1/documents", files=files(b"%PDF-1.7 basura", "x.pdf"), data={"category": "Ley"}, headers=ADMIN
    )
    assert res.status_code == 415
    assert (await client.get("/api/v1/documents", headers=ADMIN)).json()["items"] == []


@pytest.mark.asyncio
async def test_rejects_too_large(client, monkeypatch):
    monkeypatch.setattr(document_service, "MAX_BYTES", 10)
    monkeypatch.setattr(documents, "MAX_BYTES", 10)
    res = await upload(client, b"%PDF-" + b"0" * 50)
    assert res.status_code == 413 and res.json()["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_requires_category(client):
    res = await client.post("/api/v1/documents", files=files(make_pdf()), headers=ADMIN)
    assert res.status_code == 400 and res.json()["error"]["code"] == "INVALID_INPUT"
    res = await upload(client, category="   ")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_duplicate_per_tenant_only(client):
    data = make_pdf()
    first = (await upload(client, data)).json()
    res = await upload(client, data)
    assert res.status_code == 409
    err = res.json()["error"]
    assert err["code"] == "DUPLICATE_DOCUMENT" and err["details"]["document_id"] == first["id"]
    # Otra organización sí puede subir el mismo PDF
    assert (await upload(client, data, headers=FOREIGN)).status_code == 201


@pytest.mark.asyncio
async def test_scanned_pdf_needs_review(client):
    res = await upload(client, make_pdf(text=None))
    assert res.status_code == 201
    assert res.json()["status"] == "NEEDS_REVIEW"
    r = await client.post(f"/api/v1/documents/{res.json()['id']}/index", headers=ADMIN)
    assert r.status_code == 409 and r.json()["error"]["code"] == "NEEDS_REVIEW"


@pytest.mark.asyncio
async def test_list_and_isolation(client):
    a = (await upload(client, make_pdf("Artículo 1"))).json()
    await upload(client, make_pdf("Otro texto"), headers=FOREIGN)
    items = (await client.get("/api/v1/documents", headers=ADMIN)).json()["items"]
    assert [i["id"] for i in items] == [a["id"]]
    assert (await client.get(f"/api/v1/documents/{a['id']}", headers=FOREIGN)).status_code == 404
    assert (await client.get(f"/api/v1/documents/{a['id']}", headers=ADMIN)).status_code == 200
    r = await client.post(f"/api/v1/documents/{a['id']}/index", headers=FOREIGN)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_index_without_key_is_409(client):
    doc = (await upload(client)).json()
    r = await client.post(f"/api/v1/documents/{doc['id']}/index", headers=ADMIN)
    assert r.status_code == 409 and r.json()["error"]["code"] == "EMBEDDINGS_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_indexing_success_on_upload(client, monkeypatch):
    calls = []

    async def fake_ingest(tenant_id, doc_id, title, path):
        calls.append((tenant_id, doc_id, title))
        return 7

    monkeypatch.setattr(document_service, "_embeddings_ready", lambda: True)
    monkeypatch.setattr(document_service, "_ingest", fake_ingest)
    doc = (await upload(client)).json()
    assert doc["status"] == "INDEXED" and doc["chunks"] == 7
    assert calls == [("t1", doc["id"], "ley datos")]
    # Indexar de nuevo no duplica fragmentos
    r = await client.post(f"/api/v1/documents/{doc['id']}/index", headers=ADMIN)
    assert r.status_code == 200 and len(calls) == 1


@pytest.mark.asyncio
async def test_indexing_failure_then_retry(client, monkeypatch):
    state = {"fail": True}

    async def flaky_ingest(*_):
        if state["fail"]:
            raise RuntimeError("OpenAI caído")
        return 3

    monkeypatch.setattr(document_service, "_embeddings_ready", lambda: True)
    monkeypatch.setattr(document_service, "_ingest", flaky_ingest)
    doc = (await upload(client)).json()
    assert doc["status"] == "ERROR"  # el archivo sí quedó guardado y sellado
    assert doc["sha256"]

    state["fail"] = False
    r = await client.post(f"/api/v1/documents/{doc['id']}/index", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] == "INDEXED" and r.json()["chunks"] == 3


@pytest.mark.asyncio
async def test_no_chunks_means_needs_review(client, monkeypatch):
    async def empty_ingest(*_):
        return 0

    monkeypatch.setattr(document_service, "_embeddings_ready", lambda: True)
    monkeypatch.setattr(document_service, "_ingest", empty_ingest)
    assert (await upload(client)).json()["status"] == "NEEDS_REVIEW"
