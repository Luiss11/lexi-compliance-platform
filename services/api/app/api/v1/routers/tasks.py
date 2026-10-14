from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, Role, get_current_user, require_roles
from app.db.session import get_db
from app.models.tables import TaskStatus
from app.schemas.tasks import TaskCreate, TaskList, TaskOut, TaskStatusChange, TaskUpdate
from app.services import task_service

router = APIRouter()

managers = require_roles(Role.ADMIN, Role.COMPLIANCE)


@router.get("", response_model=TaskList)
async def list_tasks(
    status: TaskStatus | None = None,
    assignee_id: str | None = None,
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    return await task_service.list_tasks(db, actor, status, assignee_id)


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreate,
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    return await task_service.create_task(db, actor, body)


@router.get("/assignees")
async def list_assignees(
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"items": await task_service.list_assignees(db, actor)}


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    return await task_service.get_task(db, actor, task_id)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    return await task_service.update_task(db, actor, task_id, body)


@router.patch("/{task_id}/status", response_model=TaskOut)
async def change_status(
    task_id: str,
    body: TaskStatusChange,
    actor: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskOut:
    return await task_service.change_status(db, actor, task_id, body)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    actor: CurrentUser = Depends(managers),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await task_service.delete_task(db, actor, task_id)
    return Response(status_code=204)
