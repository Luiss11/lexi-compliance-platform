import os

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import settings
from app.core.security import CurrentUser, get_current_user
from app.schemas.tasks import EvidenceReceipt
from app.services.hashing import sha256_bytes

router = APIRouter()
ALLOWED = {"image/jpeg", "image/png", "application/pdf"}


@router.post("/{task_id}", response_model=EvidenceReceipt, status_code=201)
async def upload_evidence(
    task_id: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
) -> EvidenceReceipt:
    data = await file.read()
    digest = sha256_bytes(data)
    folder = os.path.join(settings.storage_dir, user.tenant_id, "evidence", task_id)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{digest}-{file.filename}"), "wb") as fh:
        fh.write(data)
    # TODO(Yosvanni): guardar en evidence_files y pedir review_evidence() al agente
    return EvidenceReceipt(task_id=task_id, filename=file.filename or "evidencia",
                           sha256=digest, size_bytes=len(data))
