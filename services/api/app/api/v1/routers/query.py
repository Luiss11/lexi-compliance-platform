from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.schemas.rag import QueryRequest, QueryResponse
from app.services import assistant_service

router = APIRouter()


@router.post("", response_model=QueryResponse)
async def query(body: QueryRequest, user: CurrentUser = Depends(get_current_user)) -> QueryResponse:
    # tenant_id sale del token, nunca del body: evita fugas entre organizaciones.
    return await assistant_service.ask(user.tenant_id, body.question)
