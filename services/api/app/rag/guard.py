"""Guardafuegos de alucinación: corte por similitud coseno >= 0.75."""
from app.core.config import settings

FALLBACK_MESSAGE = "No se encontró documento de soporte autorizado en la base de conocimiento."


def apply_cutoff(hits: list, cutoff: float | None = None) -> list:
    """Conserva solo fragmentos cuya similitud densa alcanza el umbral.

    El corte se aplica sobre el score coseno (no el híbrido) para que BM25 no
    pueda "rescatar" un fragmento semánticamente irrelevante.
    """
    threshold = settings.rag_cosine_cutoff if cutoff is None else cutoff
    return [h for h in hits if h.dense_score >= threshold]
