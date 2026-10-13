"""TaskService: tablero de cumplimiento (RF-TSK-01, SDD §4.2 y §7.2).

Reglas:
- El tenant sale siempre del token (CurrentUser), nunca del cuerpo de la petición.
- ADMIN y COMPLIANCE crean, editan, reasignan y pueden mover a cualquier estado.
- OPERATOR solo ve y mueve las tareas que tiene asignadas, y no puede marcarlas DONE:
  la tarea termina en IN_REVIEW y el oficial de cumplimiento la cierra.
"""
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.errors import AppError, forbidden
from app.core.security import CurrentUser, Role
from app.models.tables import EvidenceFile, Task, TaskStatus, User
from app.schemas.tasks import TaskCreate, TaskList, TaskOut, TaskStatusChange, TaskUpdate

S = TaskStatus

# Movimientos permitidos: avanzar un paso, o regresar un paso (corregir un error de tablero)
TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    S.BACKLOG: {S.IN_PROGRESS},
    S.IN_PROGRESS: {S.BACKLOG, S.IN_REVIEW},
    S.IN_REVIEW: {S.IN_PROGRESS, S.DONE},
    S.DONE: {S.IN_REVIEW},
}

MANAGERS = (Role.ADMIN, Role.COMPLIANCE)


def _is_manager(actor: CurrentUser) -> bool:
    return actor.role in MANAGERS


def _to_naive_utc(d: date | None) -> datetime | None:
    # Prisma guarda timestamp sin zona: se guarda como medianoche UTC sin tzinfo
    if d is None:
        return None
    return datetime(d.year, d.month, d.day)


def _out(task: Task, assignee_name: str | None, evidence_count: int = 0) -> TaskOut:
    overdue = (
        task.due_date is not None
        and task.status != S.DONE
        and task.due_date < datetime.now(UTC).replace(tzinfo=None)
    )
    out = TaskOut.model_validate(task)
    out.assignee_name = assignee_name
    out.overdue = overdue
    out.evidence_count = evidence_count
    return out


async def _evidence_counts(db: AsyncSession, task_ids: list[str]) -> dict[str, int]:
    if not task_ids:
        return {}
    rows = await db.execute(
        select(EvidenceFile.task_id, func.count())
        .where(EvidenceFile.task_id.in_(task_ids))
        .group_by(EvidenceFile.task_id)
    )
    return {tid: n for tid, n in rows.all()}


async def load_task(db: AsyncSession, actor: CurrentUser, task_id: str) -> Task:
    """Tarea visible para el actor (mismo tenant; el operador solo ve las suyas) o 404."""
    task, _ = await _get_task(db, actor, task_id)
    return task


async def _get_task(db: AsyncSession, actor: CurrentUser, task_id: str) -> tuple[Task, str | None]:
    # Filtrar por tenant: una tarea de otra organización responde 404, no 403
    result = await db.execute(
        select(Task, User.name)
        .outerjoin(User, Task.assignee_id == User.id)
        .where(Task.id == task_id, Task.tenant_id == actor.tenant_id)
    )
    row = result.first()
    if row is None:
        raise AppError(404, "NOT_FOUND", "La tarea no existe.")
    task, name = row
    if actor.role == Role.OPERATOR and task.assignee_id != actor.id:
        raise AppError(404, "NOT_FOUND", "La tarea no existe.")
    return task, name


async def _check_assignee(db: AsyncSession, actor: CurrentUser, assignee_id: str) -> str:
    result = await db.execute(
        select(User.name).where(User.id == assignee_id, User.tenant_id == actor.tenant_id)
    )
    name = result.scalar_one_or_none()
    if name is None:
        raise AppError(
            400, "INVALID_INPUT", "El responsable no pertenece a tu organización.",
            {"fields": [{"loc": ["assignee_id"], "msg": "Responsable no válido."}]},
        )
    return name


async def _next_code(db: AsyncSession, tenant_id: str) -> str:
    total = (
        await db.execute(select(func.count()).select_from(Task).where(Task.tenant_id == tenant_id))
    ).scalar_one()
    return f"TSK-{total + 1:03d}"


async def list_tasks(
    db: AsyncSession,
    actor: CurrentUser,
    status: TaskStatus | None = None,
    assignee_id: str | None = None,
) -> TaskList:
    query = (
        select(Task, User.name)
        .outerjoin(User, Task.assignee_id == User.id)
        .where(Task.tenant_id == actor.tenant_id)
        .order_by(Task.created_at, Task.code)
    )
    if actor.role == Role.OPERATOR:
        query = query.where(Task.assignee_id == actor.id)
    elif assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if status:
        query = query.where(Task.status == status)
    rows = (await db.execute(query)).all()
    counts = await _evidence_counts(db, [t.id for t, _ in rows])
    return TaskList(items=[_out(t, name, counts.get(t.id, 0)) for t, name in rows])


async def get_task(db: AsyncSession, actor: CurrentUser, task_id: str) -> TaskOut:
    task, name = await _get_task(db, actor, task_id)
    counts = await _evidence_counts(db, [task.id])
    return _out(task, name, counts.get(task.id, 0))


async def create_task(db: AsyncSession, actor: CurrentUser, body: TaskCreate) -> TaskOut:
    assignee_name = None
    if body.assignee_id:
        assignee_name = await _check_assignee(db, actor, body.assignee_id)

    # El código es único por organización; si dos peticiones chocan, se reintenta una vez
    for attempt in range(2):
        task = Task(
            id=uuid4().hex,
            code=await _next_code(db, actor.tenant_id),
            tenant_id=actor.tenant_id,
            title=body.title,
            description=body.description,
            priority=body.priority,
            status=S.BACKLOG,
            due_date=_to_naive_utc(body.due_date),
            assignee_id=body.assignee_id,
            document_id=body.document_id,
            citation=body.citation,
            suggested_by_ai=False,
        )
        db.add(task)
        try:
            await db.commit()
            break
        except IntegrityError:
            await db.rollback()
            if attempt == 1:
                raise AppError(409, "CONFLICT", "No se pudo crear la tarea. Intenta de nuevo.")
    await db.refresh(task)
    return _out(task, assignee_name)


async def update_task(
    db: AsyncSession, actor: CurrentUser, task_id: str, body: TaskUpdate
) -> TaskOut:
    task, name = await _get_task(db, actor, task_id)
    changes = body.model_dump(exclude_unset=True)

    if "title" in changes and changes["title"] is None:
        raise AppError(400, "INVALID_INPUT", "El título no puede quedar vacío.")
    if "priority" in changes and changes["priority"] is None:
        raise AppError(400, "INVALID_INPUT", "La prioridad no puede quedar vacía.")

    if "assignee_id" in changes:
        aid = changes.pop("assignee_id")
        name = await _check_assignee(db, actor, aid) if aid else None
        task.assignee_id = aid
    if "due_date" in changes:
        task.due_date = _to_naive_utc(changes.pop("due_date"))
    for field, value in changes.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    counts = await _evidence_counts(db, [task.id])
    return _out(task, name, counts.get(task.id, 0))


async def change_status(
    db: AsyncSession, actor: CurrentUser, task_id: str, body: TaskStatusChange
) -> TaskOut:
    task, name = await _get_task(db, actor, task_id)
    target = body.status

    counts = await _evidence_counts(db, [task.id])
    n_evidence = counts.get(task.id, 0)

    if target == task.status:
        return _out(task, name, n_evidence)

    if not _is_manager(actor) and target == S.DONE:
        raise forbidden("Solo un oficial de cumplimiento puede cerrar una tarea.")
    if not _is_manager(actor) and task.status == S.DONE:
        raise forbidden("Solo un oficial de cumplimiento puede reabrir una tarea.")

    if target not in TRANSITIONS[task.status]:
        raise AppError(
            409,
            "INVALID_TRANSITION",
            f"No se puede pasar de {task.status.value} a {target.value}.",
            {"from": task.status.value, "to": target.value,
             "allowed": sorted(s.value for s in TRANSITIONS[task.status])},
        )

    # SDD §5.3: para pasar a revisión hace falta al menos una evidencia sellada
    if target == S.IN_REVIEW and task.status == S.IN_PROGRESS and n_evidence == 0:
        raise AppError(
            409, "EVIDENCE_REQUIRED",
            "Sube al menos una evidencia antes de enviar la tarea a revisión.",
        )

    # SDD §5.3: quien revisa no puede ser quien subió la evidencia (separación de funciones)
    if target == S.DONE:
        own = (
            await db.execute(
                select(func.count()).select_from(EvidenceFile).where(
                    EvidenceFile.task_id == task.id, EvidenceFile.uploaded_by_id == actor.id
                )
            )
        ).scalar_one()
        if own:
            raise forbidden("No puedes aprobar una tarea con evidencia que subiste tú.")

    task.status = target
    await db.commit()
    await db.refresh(task)
    return _out(task, name, n_evidence)


async def list_assignees(db: AsyncSession, actor: CurrentUser) -> list[dict]:
    """Usuarios de la organización que pueden recibir tareas (para el selector del tablero)."""
    if not _is_manager(actor):
        raise forbidden()
    rows = await db.execute(
        select(User.id, User.name, User.role)
        .where(User.tenant_id == actor.tenant_id)
        .order_by(User.name)
    )
    return [{"id": i, "full_name": n, "role": r} for i, n, r in rows.all()]
