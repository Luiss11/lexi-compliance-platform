"""DocumentService: subida, sello SHA-256 e indexación de documentos (RF-DOC-01).

Flujo de estados:
  UPLOADED      guardado y sellado, aún sin indexar (p. ej. todavía no hay OPENAI_API_KEY)
  PROCESSING    indexando
  INDEXED       listo para consultas del asistente
  NEEDS_REVIEW  PDF escaneado sin texto: requiere OCR o revisión humana
  ERROR         falló la indexación; se puede reintentar con POST /documents/{id}/index

El tenant sale siempre del token. Los archivos viven en STORAGE_DIR/<tenant>/documents/.
"""
import asyncio
import logging
import os
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import CurrentUser
from app.models.tables import Document, DocumentStatus, User
from app.schemas.documents import DocumentList, DocumentOut
from app.services.hashing import sha256_bytes

log = logging.getLogger(__name__)

MAX_BYTES = 20 * 1024 * 1024  # 20 MB
S = DocumentStatus


# --- Piezas que tocan el mundo exterior (se sustituyen en las pruebas) -----------------------


def _inspect_pdf(path: str) -> tuple[int, bool]:
    """Páginas y si tiene capa de texto. Lanza excepción si el archivo no es un PDF legible."""
    import fitz  # PyMuPDF

    with fitz.open(path) as doc:
        pages = doc.page_count
        has_text = any(page.get_text().strip() for page in doc)
    return pages, has_text


def _embeddings_ready() -> bool:
    return bool(settings.openai_api_key)


async def _ingest(tenant_id: str, doc_id: str, title: str, path: str) -> int:
    """Parte el PDF en fragmentos con página y cláusula y los indexa en Qdrant."""
    from app.rag.chunker import chunk_blocks
    from app.rag.indexer import index_chunks
    from app.rag.parser import parse_pdf

    blocks = await asyncio.to_thread(parse_pdf, path)
    chunks = chunk_blocks(blocks)
    if not chunks:
        return 0
    return await index_chunks(tenant_id, doc_id, title, chunks)


# --- Utilidades ----------------------------------------------------------------------------


def _write_file(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def _remove_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _title_from(filename: str | None, title: str | None) -> str:
    if title and title.strip():
        return title.strip()[:200]
    name = os.path.basename(filename or "documento.pdf")
    stem = name[:-4] if name.lower().endswith(".pdf") else name
    return (stem.replace("_", " ").strip() or "Documento")[:200]


def _out(doc: Document, uploader_name: str | None) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.uploaded_by_name = uploader_name
    return out


async def _get(db: AsyncSession, actor: CurrentUser, doc_id: str) -> tuple[Document, str | None]:
    row = (
        await db.execute(
            select(Document, User.name)
            .outerjoin(User, Document.uploaded_by == User.id)
            .where(Document.id == doc_id, Document.tenant_id == actor.tenant_id)
        )
    ).first()
    if row is None:
        raise AppError(404, "NOT_FOUND", "El documento no existe.")
    return row[0], row[1]


async def _run_indexing(db: AsyncSession, doc: Document) -> None:
    doc.status = S.PROCESSING
    await db.commit()
    try:
        n = await _ingest(doc.tenant_id, doc.id, doc.title, doc.storage_path)
    except Exception:  # noqa: BLE001 - cualquier fallo (red, OpenAI, Qdrant) deja el doc en ERROR
        log.exception("Falló la indexación del documento %s", doc.id)
        doc.status = S.ERROR
    else:
        doc.chunks = n
        doc.status = S.INDEXED if n > 0 else S.NEEDS_REVIEW
    await db.commit()
    await db.refresh(doc)


# --- Casos de uso --------------------------------------------------------------------------


async def list_documents(db: AsyncSession, actor: CurrentUser) -> DocumentList:
    rows = (
        await db.execute(
            select(Document, User.name)
            .outerjoin(User, Document.uploaded_by == User.id)
            .where(Document.tenant_id == actor.tenant_id)
            .order_by(Document.created_at.desc(), Document.id)
        )
    ).all()
    return DocumentList(items=[_out(d, name) for d, name in rows])


async def get_document(db: AsyncSession, actor: CurrentUser, doc_id: str) -> DocumentOut:
    doc, name = await _get(db, actor, doc_id)
    return _out(doc, name)


async def upload_document(
    db: AsyncSession,
    actor: CurrentUser,
    data: bytes,
    filename: str | None,
    category: str,
    title: str | None,
) -> DocumentOut:
    category = category.strip()
    if not category or len(category) > 60:
        raise AppError(
            400, "INVALID_INPUT", "Indica una categoría (máximo 60 caracteres).",
            {"fields": [{"loc": ["category"], "msg": "Categoría no válida."}]},
        )
    if not data:
        raise AppError(400, "INVALID_INPUT", "El archivo está vacío.")
    if len(data) > MAX_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "El PDF supera el límite de 20 MB.")
    if not data.startswith(b"%PDF-"):
        raise AppError(415, "UNSUPPORTED_FILE", "Solo se aceptan archivos PDF.")

    digest = sha256_bytes(data)
    duplicate = (
        await db.execute(
            select(Document.id, Document.title).where(
                Document.tenant_id == actor.tenant_id, Document.sha256 == digest
            )
        )
    ).first()
    if duplicate:
        raise AppError(
            409, "DUPLICATE_DOCUMENT",
            f"Este PDF ya está cargado como «{duplicate.title}».",
            {"document_id": duplicate.id},
        )

    doc_id = str(uuid4())
    path = os.path.join(settings.storage_dir, actor.tenant_id, "documents", f"{doc_id}.pdf")
    await asyncio.to_thread(_write_file, path, data)

    try:
        pages, has_text = await asyncio.to_thread(_inspect_pdf, path)
    except Exception as exc:  # noqa: BLE001 - PDF corrupto o protegido
        await asyncio.to_thread(_remove_file, path)
        raise AppError(415, "UNSUPPORTED_FILE", "No se pudo leer el PDF. ¿Está dañado o protegido?") from exc

    doc = Document(
        id=doc_id,
        tenant_id=actor.tenant_id,
        title=_title_from(filename, title),
        category=category,
        status=S.UPLOADED if has_text else S.NEEDS_REVIEW,
        pages=pages,
        chunks=None,
        sha256=digest,
        storage_path=path,
        uploaded_by=actor.id,
    )
    db.add(doc)
    await db.commit()

    if has_text and _embeddings_ready():
        await _run_indexing(db, doc)
    await db.refresh(doc)

    name = (await db.execute(select(User.name).where(User.id == actor.id))).scalar_one_or_none()
    return _out(doc, name)


async def reindex_document(db: AsyncSession, actor: CurrentUser, doc_id: str) -> DocumentOut:
    doc, name = await _get(db, actor, doc_id)

    if doc.status == S.INDEXED:
        return _out(doc, name)  # ya está listo; reindexar duplicaría los fragmentos
    if doc.status == S.PROCESSING:
        raise AppError(409, "ALREADY_PROCESSING", "El documento se está indexando.")
    if doc.status == S.NEEDS_REVIEW:
        raise AppError(
            409, "NEEDS_REVIEW",
            "Este PDF no tiene texto (parece escaneado). Sube una versión con texto o aplica OCR.",
        )
    if not _embeddings_ready():
        raise AppError(
            409, "EMBEDDINGS_NOT_CONFIGURED",
            "Falta configurar la clave de embeddings (OPENAI_API_KEY) para indexar.",
        )

    await _run_indexing(db, doc)
    return _out(doc, name)
