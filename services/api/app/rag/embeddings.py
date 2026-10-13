from openai import AsyncOpenAI

from app.core.config import settings

_client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None


async def embed(texts: list[str]) -> list[list[float]]:
    if _client is None:
        raise RuntimeError("Configura OPENAI_API_KEY para generar embeddings")
    res = await _client.embeddings.create(model=settings.embedding_model, input=texts)
    return [d.embedding for d in res.data]
