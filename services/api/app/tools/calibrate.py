"""Calibración del corte coseno (SDD §9.2, paso 5): mide qué similitud obtiene cada pregunta.

Uso (con la pila levantada y el SDD V1.1 indexado):
    docker compose exec api python -m app.tools.calibrate
    docker compose exec api python -m app.tools.calibrate --verbose
    docker compose exec api python -m app.tools.calibrate --slug clinica-sonrisa

No llama al LLM: solo embebe cada pregunta y consulta Qdrant (cuesta centavos de dólar).
Para cada pregunta imprime la similitud coseno máxima, en qué página quedó el mejor
fragmento y si la página correcta apareció entre los resultados. Al final sugiere un
corte que separa las preguntas con respuesta ("good") de las trampa ("trap").
"""
import argparse
import asyncio
from dataclasses import dataclass

# (tipo, pregunta, páginas del PDF donde está la respuesta; vacío = no debe haber soporte)
CASES: list[tuple[str, str, set[int]]] = [
    ("good", "¿Cuántos intentos fallidos de login bloquean la cuenta y por cuánto tiempo?", {22}),
    ("good", "How many failed logins lock the account and for how long?", {22}),
    ("good", "¿Cuál es el umbral de similitud coseno y qué pasa si no se alcanza?", {19, 20, 29}),
    ("good", "What is the cosine cutoff and what happens below it?", {19, 20, 29}),
    ("good", "¿Cuál es el tamaño máximo de un PDF?", {9, 18, 27}),
    ("good", "What is the maximum PDF size?", {9, 18, 27}),
    ("good", "¿Qué roles pueden aprobar o rechazar tareas?", {9, 23}),
    ("good", "Which roles can approve or reject tasks?", {9, 23}),
    ("good", "¿Cuántos endpoints tiene la API?", {15}),
    ("good", "How many endpoints does the API expose?", {15}),
    ("good", "¿Cuánto dura el token de acceso y dónde se guarda?", {22}),
    ("good", "How long does the access token live and where is it stored?", {22}),
    ("good", "¿Quién es responsable del riesgo de PDFs escaneados?", {30}),
    ("trap", "¿Cuál es la receta del pozole?", set()),
    ("trap", "¿Cuánto cuesta el plan mensual de Lexi?", set()),
    ("trap", "¿Qué dice la LFPDPPP sobre el plazo para derechos ARCO?", set()),
]


@dataclass
class Result:
    kind: str
    question: str
    expected: set[int]
    best: float
    best_page: int | None
    found_expected: bool
    hits: list  # los fragmentos devueltos, para --verbose


async def evaluate(cases, search) -> list[Result]:
    """`search(question)` devuelve los Hit del motor RAG (se inyecta para poder probarlo)."""
    results = []
    for kind, question, expected in cases:
        hits = await search(question)
        top = max(hits, key=lambda h: h.dense_score, default=None)
        results.append(
            Result(
                kind=kind,
                question=question,
                expected=expected,
                best=top.dense_score if top else 0.0,
                best_page=top.page if top else None,
                found_expected=bool(expected & {h.page for h in hits}),
                hits=hits,
            )
        )
    return results


def suggest_cutoff(results: list[Result]) -> tuple[float | None, str]:
    """Devuelve (corte sugerido, explicación). Solo cuenta las buenas cuya página sí apareció."""
    good = [r.best for r in results if r.kind == "good" and r.found_expected]
    traps = [r.best for r in results if r.kind == "trap"]
    if not good:
        return None, "Ninguna pregunta buena encontró su página: el problema no es el corte, es la búsqueda."
    low_good, high_trap = min(good), max(traps, default=0.0)
    if low_good <= high_trap:
        return None, (
            f"No se pueden separar: la trampa más alta ({high_trap:.2f}) iguala o supera a la "
            f"pregunta buena más baja ({low_good:.2f})."
        )
    cutoff = round((low_good + high_trap) / 2, 2)
    return cutoff, (
        f"Buena más baja {low_good:.2f} · trampa más alta {high_trap:.2f} → "
        f"RAG_COSINE_CUTOFF={cutoff}"
    )


def format_report(results: list[Result], verbose: bool = False) -> str:
    lines = [f"{'tipo':<5} {'sim.':>5} {'pág.mejor':>9} {'pág.correcta':>12}  pregunta"]
    for r in results:
        if r.kind == "trap":
            check = "(sin soporte)"
        else:
            check = "sí" if r.found_expected else "NO"
        page = "-" if r.best_page is None else str(r.best_page)
        lines.append(f"{r.kind:<5} {r.best:5.2f} {page:>9} {check:>12}  {r.question}")
        if verbose:
            for h in sorted(r.hits, key=lambda h: h.dense_score, reverse=True)[:3]:
                snippet = h.text.replace("\n", " ")[:110]
                lines.append(f"        {h.dense_score:.2f} p.{h.page} {h.clause or '-'} | {snippet}")
    cutoff, why = suggest_cutoff(results)
    lines += ["", why]
    if cutoff is None:
        lines.append("Corte actual: 0.75 (variable RAG_COSINE_CUTOFF).")
    return "\n".join(lines)


async def _main(slug: str, verbose: bool) -> None:
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.tables import Tenant
    from app.rag.retriever import hybrid_search

    async with SessionLocal() as db:
        tenant_id = (await db.execute(select(Tenant.id).where(Tenant.slug == slug))).scalar_one_or_none()
    if tenant_id is None:
        raise SystemExit(f"No existe la organización '{slug}'.")

    async def search(question: str):
        return await hybrid_search(tenant_id, question)

    print(format_report(await evaluate(CASES, search), verbose))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--slug", default="clinica-sonrisa")
    parser.add_argument("--verbose", action="store_true", help="muestra los 3 mejores fragmentos")
    args = parser.parse_args()
    asyncio.run(_main(args.slug, args.verbose))
