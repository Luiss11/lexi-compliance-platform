"""AssistantService: consulta al motor RAG con manejo de fallas (RF-AI-01).

El motor (app/rag) ya aplica el corte de similitud coseno y devuelve el mensaje fijo
"No se encontró documento de soporte…" cuando no hay evidencia suficiente. Este servicio
solo traduce las fallas de infraestructura (clave ausente, Qdrant u OpenAI caídos) a errores
claros con el envelope estándar, en lugar de un 500 genérico.
"""
import logging

from app.core.config import settings
from app.core.errors import AppError
from app.rag.guard import FALLBACK_MESSAGE
from app.schemas.rag import QueryResponse

log = logging.getLogger(__name__)


async def _answer(tenant_id: str, question: str) -> QueryResponse:
    # Import tardío: el motor carga clientes de Qdrant y OpenAI al importarse
    from app.rag.answer import answer_question

    return await answer_question(tenant_id, question)


def _is_missing_collection(exc: Exception) -> bool:
    # Qdrant responde 404 si todavía no se indexó ningún documento (la colección no existe)
    return type(exc).__name__ == "UnexpectedResponse" and getattr(exc, "status_code", None) == 404


async def ask(tenant_id: str, question: str) -> QueryResponse:
    if not settings.openai_api_key:
        raise AppError(
            503, "EMBEDDINGS_NOT_CONFIGURED",
            "El asistente aún no está configurado (falta la clave de OpenAI).",
        )
    try:
        return await _answer(tenant_id, question.strip())
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        if _is_missing_collection(exc):
            return QueryResponse(answer=FALLBACK_MESSAGE, grounded=False, best_score=0.0)
        log.exception("Falló la consulta al asistente")
        raise AppError(
            502, "ASSISTANT_UNAVAILABLE",
            "El asistente no está disponible por ahora. Intenta de nuevo en un momento.",
        ) from exc
