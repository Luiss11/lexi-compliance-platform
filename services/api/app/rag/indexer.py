"""Indexación en Qdrant con aislamiento por tenant_id (TASK-09)."""
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from app.core.config import settings
from app.rag.chunker import Chunk
from app.rag.embeddings import embed

VECTOR_SIZE = 1536  # text-embedding-3-small

client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


async def ensure_collection() -> None:
    names = {c.name for c in (await client.get_collections()).collections}
    if settings.qdrant_collection not in names:
        await client.create_collection(
            settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        await client.create_payload_index(
            settings.qdrant_collection, "tenant_id", PayloadSchemaType.KEYWORD
        )


async def index_chunks(tenant_id: str, document_id: str, title: str, chunks: list[Chunk]) -> int:
    await ensure_collection()
    vectors = await embed([c.text for c in chunks])
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "tenant_id": tenant_id,
                "document_id": document_id,
                "document_title": title,
                "page": c.page,
                "clause": c.clause,
                "text": c.text,
            },
        )
        for c, vec in zip(chunks, vectors, strict=True)
    ]
    await client.upsert(settings.qdrant_collection, points=points)
    return len(points)
