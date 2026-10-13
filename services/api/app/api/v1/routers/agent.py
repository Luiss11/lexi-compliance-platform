from fastapi import APIRouter, Depends

from app.agents.supervisor import audit_gaps
from app.core.security import CurrentUser, Role, require_roles

router = APIRouter()


@router.post("/audit")
async def run_audit(
    sector: str,
    document_titles: list[str],
    user: CurrentUser = Depends(require_roles(Role.ADMIN, Role.COMPLIANCE)),
) -> list[dict]:
    # TODO(Yubel): leer títulos desde la BD del tenant en lugar del body
    return [g.__dict__ for g in audit_gaps(sector, document_titles)]
