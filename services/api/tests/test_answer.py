"""Motor de respuesta: corte, negativa del modelo y constructor de citas (sin OpenAI ni Qdrant)."""
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.rag import answer as answer_mod
from app.rag.answer import build_citations, is_fallback
from app.rag.guard import FALLBACK_MESSAGE
from app.rag.retriever import Hit


def hit(score, page, text="Fragmento", clause="10.1", title="SDD"):
    return Hit(document_id="d1", document_title=title, page=page, clause=clause,
               text=text, dense_score=score)


def fake_openai(reply, calls):
    class Completions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=reply))])

    class Client:
        def __init__(self, **_):
            self.chat = SimpleNamespace(completions=Completions())

    return Client


@pytest.fixture(autouse=True)
def _cutoff(monkeypatch):
    monkeypatch.setattr(settings, "rag_cosine_cutoff", 0.30, raising=False)
    monkeypatch.setattr(settings, "openai_model", "test-model", raising=False)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test", raising=False)


def patch(monkeypatch, hits, reply="", calls=None):
    async def fake_search(tenant_id, question):
        return hits

    monkeypatch.setattr(answer_mod, "hybrid_search", fake_search)
    monkeypatch.setattr(answer_mod, "AsyncOpenAI", fake_openai(reply, [] if calls is None else calls))


@pytest.mark.asyncio
async def test_below_cutoff_never_calls_llm(monkeypatch):
    calls = []
    patch(monkeypatch, [hit(0.17, 21)], "no debería usarse", calls)
    res = await answer_mod.answer_question("t1", "¿receta del pozole?")
    assert res.answer == FALLBACK_MESSAGE and res.grounded is False
    assert res.best_score == 0.17 and res.citations == [] and calls == []


@pytest.mark.asyncio
async def test_only_chunks_above_cutoff_reach_the_llm(monkeypatch):
    calls = []
    patch(monkeypatch, [hit(0.50, 22, "TEXTO BUENO"), hit(0.10, 3, "TEXTO IRRELEVANTE")],
          "Respuesta [1]", calls)
    await answer_mod.answer_question("t1", "pregunta")
    prompt = calls[0]["messages"][1]["content"]
    assert "TEXTO BUENO" in prompt and "TEXTO IRRELEVANTE" not in prompt
    assert "<pregunta>" in prompt and calls[0]["temperature"] == 0 and calls[0]["max_tokens"] == 600


@pytest.mark.asyncio
async def test_model_refusal_becomes_ungrounded_fallback(monkeypatch):
    patch(monkeypatch, [hit(0.40, 24)], f'"{FALLBACK_MESSAGE}"')
    res = await answer_mod.answer_question("t1", "¿cuánto cuesta el plan?")
    assert res.grounded is False and res.citations == []
    assert res.answer == FALLBACK_MESSAGE and res.best_score == 0.40


@pytest.mark.asyncio
async def test_grounded_answer_keeps_only_cited_sources(monkeypatch):
    hits = [hit(0.60, 22, clause="10.1"), hit(0.50, 20, clause="9.2"), hit(0.45, 15, clause="7.2")]
    patch(monkeypatch, hits, "El token dura 60 minutos [3] y se guarda en cookie [1].")
    res = await answer_mod.answer_question("t1", "¿token?")
    assert res.grounded is True
    # Orden de primera aparición: el fragmento 3 pasa a ser [1] y el 1 pasa a ser [2]
    assert res.answer == "El token dura 60 minutos [1] y se guarda en cookie [2]."
    assert [c.page for c in res.citations] == [15, 22]


def test_invalid_markers_are_removed():
    chunks = [hit(0.5, 1), hit(0.5, 2)]
    text, used = build_citations("Dato [1] y otro dato [9].", chunks)
    assert text == "Dato [1] y otro dato ." and [h.page for h in used] == [1]


def test_no_markers_returns_all_consulted_sources():
    chunks = [hit(0.5, 1), hit(0.5, 2)]
    text, used = build_citations("Respuesta sin citas.", chunks)
    assert text == "Respuesta sin citas." and len(used) == 2


def test_is_fallback_ignores_quotes_and_case():
    assert is_fallback(f'"{FALLBACK_MESSAGE.upper()}"')
    assert not is_fallback("El plazo es de 20 días [1].")
