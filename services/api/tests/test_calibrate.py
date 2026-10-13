"""La herramienta de calibración: sugerencia de corte e informe, sin Qdrant ni OpenAI."""
from types import SimpleNamespace

import pytest

from app.tools.calibrate import Result, evaluate, format_report, suggest_cutoff


def hit(score, page, text="texto"):
    return SimpleNamespace(dense_score=score, page=page, clause="10.1", text=text)


def res(kind, best, expected, found):
    return Result(kind, "q", expected, best, 1, found, [])


def test_suggests_midpoint_between_trap_and_good():
    results = [res("good", 0.52, {22}, True), res("good", 0.61, {20}, True), res("trap", 0.18, set(), False)]
    cutoff, why = suggest_cutoff(results)
    assert cutoff == 0.35
    assert "0.35" in why


def test_not_separable_when_trap_scores_higher():
    results = [res("good", 0.40, {22}, True), res("trap", 0.45, set(), False)]
    cutoff, why = suggest_cutoff(results)
    assert cutoff is None and "No se pueden separar" in why


def test_good_questions_that_missed_their_page_are_ignored():
    # Una buena con similitud alta pero en la página equivocada no debe inflar el corte
    results = [res("good", 0.30, {22}, False), res("good", 0.55, {20}, True), res("trap", 0.20, set(), False)]
    cutoff, _ = suggest_cutoff(results)
    assert cutoff == 0.38


def test_no_good_found_means_search_problem():
    cutoff, why = suggest_cutoff([res("good", 0.5, {22}, False), res("trap", 0.1, set(), False)])
    assert cutoff is None and "la búsqueda" in why


@pytest.mark.asyncio
async def test_evaluate_and_report():
    async def search(q):
        if "pozole" in q:
            return [hit(0.12, 3)]
        return [hit(0.55, 22), hit(0.31, 5)]

    cases = [("good", "¿Intentos de login?", {22}), ("trap", "receta del pozole", set())]
    results = await evaluate(cases, search)
    assert results[0].best == 0.55 and results[0].best_page == 22 and results[0].found_expected
    assert results[1].best == 0.12 and not results[1].found_expected
    report = format_report(results, verbose=True)
    assert "0.55" in report and "RAG_COSINE_CUTOFF=0.34" in report and "p.22" in report
