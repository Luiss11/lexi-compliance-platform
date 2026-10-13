"""Asistente: autenticación, validación, aislamiento por tenant y manejo de fallas."""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.routers import query
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.security import Role, create_access_token
from app.rag.guard import FALLBACK_MESSAGE
from app.schemas.rag import Citation, QueryResponse
from app.services import assistant_service


def auth(role: Role = Role.OPERATOR, tenant: str = "t1") -> dict:
    return {"Authorization": f"Bearer {create_access_token('u1', tenant, role)}"}


@pytest_asyncio.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test", raising=False)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(query.router, prefix="/api/v1/query")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def ask(client, question="¿Qué debe contener el aviso de privacidad?", headers=None, **extra):
    return client.post(
        "/api/v1/query", json={"question": question, **extra}, headers=headers or auth()
    )


@pytest.mark.asyncio
async def test_requires_auth(client):
    res = await client.post("/api/v1/query", json={"question": "hola mundo"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_validation(client):
    res = await ask(client, question="a")
    assert res.status_code == 400 and res.json()["error"]["code"] == "INVALID_INPUT"
    res = await ask(client, question="x" * 2001)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_tenant_comes_from_token_not_body(client, monkeypatch):
    seen = {}

    async def fake(tenant_id, question):
        seen["tenant"], seen["q"] = tenant_id, question
        return QueryResponse(answer=FALLBACK_MESSAGE, grounded=False, best_score=0.2)

    monkeypatch.setattr(assistant_service, "_answer", fake)
    res = await ask(client, question="  ¿Plazo para responder?  ", tenant_id="OTRO")
    assert res.status_code == 200
    assert seen == {"tenant": "t1", "q": "¿Plazo para responder?"}


@pytest.mark.asyncio
async def test_grounded_answer_with_citations(client, monkeypatch):
    async def fake(tenant_id, question):
        return QueryResponse(
            answer="Debe incluir la identidad del responsable [1].",
            grounded=True,
            best_score=0.82,
            citations=[Citation(document_id="d1", document_title="LFPDPPP", page=4,
                                clause="Artículo 16", score=0.82, excerpt="El aviso…")],
        )

    monkeypatch.setattr(assistant_service, "_answer", fake)
    body = (await ask(client)).json()
    assert body["grounded"] is True and body["citations"][0]["page"] == 4
    assert body["citations"][0]["clause"] == "Artículo 16"


@pytest.mark.asyncio
async def test_missing_key_is_503(client, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None, raising=False)
    res = await ask(client)
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "EMBEDDINGS_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_infra_failure_is_502(client, monkeypatch):
    async def boom(*_):
        raise RuntimeError("OpenAI 500")

    monkeypatch.setattr(assistant_service, "_answer", boom)
    res = await ask(client)
    assert res.status_code == 502
    assert res.json()["error"]["code"] == "ASSISTANT_UNAVAILABLE"
    assert "OpenAI" not in res.text  # no se filtran detalles internos


@pytest.mark.asyncio
async def test_missing_collection_returns_fallback(client, monkeypatch):
    class UnexpectedResponse(Exception):
        status_code = 404

    async def no_collection(*_):
        raise UnexpectedResponse("Collection not found")

    monkeypatch.setattr(assistant_service, "_answer", no_collection)
    res = await ask(client)
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == FALLBACK_MESSAGE and body["grounded"] is False
