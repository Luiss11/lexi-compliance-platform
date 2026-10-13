from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import CurrentUser, Role, get_current_user, require_roles
from app.db.session import get_db
from app.schemas.evidence import EvidenceList, EvidenceOut, VerifyResult
from app.services import evidence_service
from app.services.evidence_service import MAX_BYTES

# /tasks/{id}/evidence: se monta bajo /tasks en api/v1/router.py
tasks_router = APIRouter()
# /evidence/{id}/...: se monta bajo /evidence
router = APIRouter()

managers = require_roles(Role.ADMIN, Role.COMPLIANCE)


@tasks_router.post("/{task_id}/evidence", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    task_id: str,
    evidence_file: UploadFile = File(...),
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvidenceOut:
    # Se lee un byte de más para detectar exceso de tamaño sin cargar archivos enormes
    data = await evidence_file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "La evidencia supera el límite de 10 MB.")
    return await evidence_service.upload_evidence(db, actor, task_id, data, evidence_file.filename)


@tasks_router.get("/{task_id}/evidence", response_model=EvidenceList)
async def list_evidence(
    task_id: str,
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvidenceList:
    return await evidence_service.list_evidence(db, actor, task_id)


@router.post("/{evidence_id}/verify", response_model=VerifyResult)
async def verify_evidence(
    evidence_id: str,
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> VerifyResult:
    return await evidence_service.verify_evidence(db, actor, evidence_id)


@router.get("/{evidence_id}/file")
async def evidence_file(
    evidence_id: str,
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    path, mime, filename = await evidence_service.get_file(db, actor, evidence_id)
    return FileResponse(path, media_type=mime, filename=filename, content_disposition_type="inline")
