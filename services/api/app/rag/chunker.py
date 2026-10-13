from dataclasses import dataclass

from app.rag.parser import PageBlock


@dataclass
class Chunk:
    page: int
    clause: str | None
    text: str


def chunk_blocks(blocks: list[PageBlock], max_chars: int = 1200) -> list[Chunk]:
    """Agrupa bloques sin cruzar de página ni de cláusula, para que cada cita sea exacta."""
    chunks: list[Chunk] = []
    buf: list[str] = []
    key: tuple[int, str | None] | None = None
    for b in blocks:
        k = (b.page, b.clause)
        if key is not None and (k != key or sum(map(len, buf)) + len(b.text) > max_chars):
            chunks.append(Chunk(page=key[0], clause=key[1], text="\n".join(buf)))
            buf = []
        key = k
        buf.append(b.text)
    if buf and key is not None:
        chunks.append(Chunk(page=key[0], clause=key[1], text="\n".join(buf)))
    return chunks
