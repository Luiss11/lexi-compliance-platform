"""Búsqueda híbrida: vectores densos (coseno) + BM25 léxico, filtrada por tenant (TASK-09)."""
from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.rag.embeddings import embed
from app.rag.indexer import client


@dataclass
class Hit:
    document_id: str
    document_title: str
    page: int
    clause: str | None
    text: str
    dense_score: float
    hybrid_score: float = 0.0


def _tokens(text: str) -> list[str]:
    return [t for t in text.lower().split() if len(t) > 2]


async def hybrid_search(tenant_id: str, question: str, top_k: int | None = None,
                        alpha: float = 0.7) -> list[Hit]:
    top_k = top_k or settings.rag_top_k
    [qvec] = await embed([question])
    tenant_filter = Filter(must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))])
    results = await client.search(
        settings.qdrant_collection, query_vector=qvec, query_filter=tenant_filter, limit=top_k * 3
    )
    hits = [
        Hit(
            document_id=r.payload["document_id"],
            document_title=r.payload["document_title"],
            page=r.payload["page"],
            clause=r.payload.get("clause"),
            text=r.payload["text"],
            dense_score=float(r.score),
        )
        for r in results
    ]
    if not hits:
        return []
    bm25 = BM25Okapi([_tokens(h.text) for h in hits])
    lex = bm25.get_scores(_tokens(question))
    max_lex = max(lex) or 1.0
    for h, s in zip(hits, lex, strict=True):
        h.hybrid_score = alpha * h.dense_score + (1 - alpha) * (s / max_lex)
    hits.sort(key=lambda h: h.hybrid_score, reverse=True)
    return hits[:top_k]
