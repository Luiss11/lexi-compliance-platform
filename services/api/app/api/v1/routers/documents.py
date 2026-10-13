import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.security import CurrentUser, Role, require_roles
from app.rag.chunker import chunk_blocks
from app.rag.indexer import index_chunks
from app.rag.parser import has_text_layer, parse_pdf
from app.services.hashing import sha256_bytes

router = APIRouter()


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    user: CurrentUser = Depends(require_roles(Role.ADMIN, Role.COMPLIANCE)),
) -> dict:
    if file.content_type != "application/pdf":
        raise HTTPException(415, "Solo se aceptan archivos PDF")
    data = await file.read()
    doc_id = str(uuid.uuid4())
    folder = os.path.join(settings.storage_dir, user.tenant_id, "documents")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{doc_id}.pdf")
    with open(path, "wb") as fh:
        fh.write(data)

    if not has_text_layer(path):
        return {"id": doc_id, "status": "ERROR", "detail": "PDF escaneado: requiere OCR"}

    chunks = chunk_blocks(parse_pdf(path))
    n = await index_chunks(user.tenant_id, doc_id, file.filename or "documento.pdf", chunks)
    # TODO(Yosvanni): persistir fila en documents con status INDEXED y sha256
    return {"id": doc_id, "status": "INDEXED", "chunks": n, "sha256": sha256_bytes(data),
            "category": category}
