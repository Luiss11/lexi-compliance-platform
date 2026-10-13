"""Sello SHA-256 de evidencias (TASK-14)."""
import hashlib
from collections.abc import AsyncIterator

CHUNK = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def sha256_stream(chunks: AsyncIterator[bytes]) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    async for part in chunks:
        h.update(part)
        size += len(part)
    return h.hexdigest(), size
