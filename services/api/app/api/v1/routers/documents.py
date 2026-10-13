from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser, Role, require_roles
from app.db.session import get_db
from app.schemas.documents import DocumentList, DocumentOut
from app.services import document_service
from app.services.document_service import MAX_BYTES

router = APIRouter()

managers = require_roles(Role.ADMIN, Role.COMPLIANCE)


@router.get("", response_model=DocumentList)
async def list_documents(
    actor: CurrentUser = Depends(managers), db: AsyncSession = Depends(get_db)
) -> DocumentList:
    return await document_service.list_documents(db, actor)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    title: str | None = Form(default=None),
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    # Se lee un byte de más para detectar archivos que exceden el límite sin cargarlos enteros
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "El PDF supera el límite de 20 MB.")
    return await document_service.upload_document(db, actor, data, file.filename, category, title)


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: str, actor: CurrentUser = Depends(managers), db: AsyncSession = Depends(get_db)
) -> DocumentOut:
    return await document_service.get_document(db, actor, doc_id)


@router.post("/{doc_id}/index", response_model=DocumentOut)
async def reindex_document(
    doc_id: str, actor: CurrentUser = Depends(managers), db: AsyncSession = Depends(get_db)
) -> DocumentOut:
    return await document_service.reindex_document(db, actor, doc_id)
