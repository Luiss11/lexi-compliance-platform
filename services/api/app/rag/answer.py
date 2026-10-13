from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.guard import FALLBACK_MESSAGE, apply_cutoff
from app.rag.retriever import hybrid_search
from app.schemas.rag import Citation, QueryResponse

SYSTEM_PROMPT = (
    "Eres un asistente de cumplimiento legal. Responde SOLO con la información de los "
    "fragmentos dados. Cita cada afirmación con [n] según el número del fragmento. "
    f"Si los fragmentos no responden la pregunta, responde exactamente: '{FALLBACK_MESSAGE}'"
)


async def answer_question(tenant_id: str, question: str) -> QueryResponse:
    hits = await hybrid_search(tenant_id, question)
    best = max((h.dense_score for h in hits), default=0.0)
    grounded = apply_cutoff(hits)
    if not grounded:
        return QueryResponse(answer=FALLBACK_MESSAGE, grounded=False, best_score=best)

    context = "\n\n".join(
        f"[{i}] {h.document_title} · p.{h.page} · {h.clause or 's/c'}\n{h.text}"
        for i, h in enumerate(grounded, start=1)
    )
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    completion = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Fragmentos:\n{context}\n\nPregunta: {question}"},
        ],
    )
    return QueryResponse(
        answer=completion.choices[0].message.content or FALLBACK_MESSAGE,
        grounded=True,
        best_score=best,
        citations=[
            Citation(
                document_id=h.document_id,
                document_title=h.document_title,
                page=h.page,
                clause=h.clause,
                score=round(h.dense_score, 3),
                excerpt=h.text[:400],
            )
            for h in grounded
        ],
    )
