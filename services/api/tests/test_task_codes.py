"""Códigos de tarea (hallazgo H-05): no se repiten aunque se borre una tarea intermedia."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.tables import Priority, Task, TaskStatus
from tests import test_tasks
from tests.test_tasks import ADMIN, FOREIGN_ADMIN, make

# Se reutiliza la fixture de test_tasks (base SQLite con usuarios de dos organizaciones)
client = test_tasks.client


@pytest.mark.asyncio
async def test_code_not_reused_after_deleting_a_middle_task(client):
    first = await make(client, title="Primera tarea")
    second = await make(client, title="Segunda tarea")
    third = await make(client, title="Tercera tarea")
    assert [first["code"], second["code"], third["code"]] == ["TSK-001", "TSK-002", "TSK-003"]

    res = await client.delete(f"/api/v1/tasks/{first['id']}", headers=ADMIN)
    assert res.status_code == 204

    fourth = await make(client, title="Cuarta tarea")
    assert fourth["code"] == "TSK-004"  # antes repetía TSK-003

    res = await client.get("/api/v1/tasks", headers=ADMIN)
    codes = [t["code"] for t in res.json()["items"]]
    assert len(codes) == len(set(codes)) == 3


@pytest.mark.asyncio
async def test_code_of_deleted_last_task_can_be_reused(client):
    await make(client, title="Primera tarea")
    last = await make(client, title="Segunda tarea")
    assert (await client.delete(f"/api/v1/tasks/{last['id']}", headers=ADMIN)).status_code == 204

    again = await make(client, title="Otra tarea")
    assert again["code"] == "TSK-002"


@pytest.mark.asyncio
async def test_codes_are_per_tenant_and_ignore_unknown_formats(client):
    async with client.session_factory() as s:
        s.add(Task(id="legacy", code="LEGACY-9", tenant_id="t1", title="Tarea heredada",
                   status=TaskStatus.BACKLOG, priority=Priority.MEDIA))
        await s.commit()

    mine = await make(client, title="Tarea de t1")
    assert mine["code"] == "TSK-001"  # el formato desconocido no rompe la numeración

    foreign = await make(client, headers=FOREIGN_ADMIN, title="Tarea de t2")
    assert foreign["code"] == "TSK-001"  # cada organización numera por separado


@pytest.mark.asyncio
async def test_database_rejects_duplicate_code_in_same_tenant(client):
    """La base de pruebas ya refleja @@unique([tenantId, code]) de Prisma."""
    await make(client, title="Primera tarea")
    async with client.session_factory() as s:
        s.add(Task(id="dup", code="TSK-001", tenant_id="t1", title="Duplicada",
                   status=TaskStatus.BACKLOG, priority=Priority.MEDIA))
        with pytest.raises(IntegrityError):
            await s.commit()
