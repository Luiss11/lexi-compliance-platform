"""Carga del catálogo como tareas: permisos, aislamiento, sin duplicados y bitácora."""
import pytest

from app.models.tables import AuditLog
from app.services import obligations_catalog as oc
from tests import test_tasks
from tests.test_tasks import ADMIN, COMPLIANCE, FOREIGN_ADMIN, OPERATOR

# Reutiliza la base de test_tasks: t1 es «clinica» y t2 es «retail» (comercio)
client = test_tasks.client

LIST = "/api/v1/compliance/obligations"
LOAD = "/api/v1/compliance/obligations/load"


@pytest.fixture
def app_client(client):
    """test_tasks solo monta /tasks: se añade el router de cumplimiento a la misma app."""
    from app.api.v1.routers import compliance

    transport_app = client._transport.app
    transport_app.include_router(compliance.router, prefix="/api/v1/compliance")
    return client


@pytest.mark.asyncio
async def test_list_returns_sector_and_common_items(app_client):
    res = await app_client.get(LIST, headers=ADMIN)
    assert res.status_code == 200
    data = res.json()
    assert data["sector"] == "clinica"
    ids = {i["id"] for i in data["items"]}
    assert "CLI-01" in ids and "INC-06" in ids and "COM-01" not in ids
    assert all(i["loaded"] is False for i in data["items"])
    assert data["aviso"]


@pytest.mark.asyncio
async def test_other_tenant_sees_its_own_sector(app_client):
    res = await app_client.get(LIST, headers=FOREIGN_ADMIN)
    ids = {i["id"] for i in res.json()["items"]}
    assert res.json()["sector"] == "comercio"
    assert "COM-01" in ids and "CLI-01" not in ids


@pytest.mark.asyncio
async def test_operator_cannot_list_or_load(app_client):
    assert (await app_client.get(LIST, headers=OPERATOR)).status_code == 403
    res = await app_client.post(LOAD, json={"ids": ["INC-01"]}, headers=OPERATOR)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_load_creates_tasks_with_citation_and_source(app_client):
    res = await app_client.post(LOAD, json={"ids": ["CLI-01", "INC-04"]}, headers=COMPLIANCE)
    assert res.status_code == 201
    created = res.json()["created"]
    assert [t["code"] for t in created] == ["TSK-001", "TSK-002"]
    first = created[0]
    assert first["title"] == "Integrar y conservar el expediente clínico"
    assert first["citation"] == "NOM-004-SSA3-2012, 5.1 y 5.4"
    assert first["status"] == "BACKLOG" and first["suggested_by_ai"] is False
    assert "Código del catálogo: CLI-01" in first["description"]
    assert "Evidencia sugerida" in first["description"]


@pytest.mark.asyncio
async def test_loading_twice_does_not_duplicate(app_client):
    await app_client.post(LOAD, json={"ids": ["INC-01", "INC-02"]}, headers=ADMIN)
    res = await app_client.post(LOAD, json={"ids": ["INC-02", "INC-03"]}, headers=ADMIN)
    assert res.status_code == 201
    body = res.json()
    assert body["skipped"] == ["INC-02"]
    assert len(body["created"]) == 1

    items = (await app_client.get(LIST, headers=ADMIN)).json()["items"]
    loaded = {i["id"] for i in items if i["loaded"]}
    assert loaded == {"INC-01", "INC-02", "INC-03"}
    tasks = (await app_client.get("/api/v1/tasks", headers=ADMIN)).json()["items"]
    assert len(tasks) == 3


@pytest.mark.asyncio
async def test_duplicate_ids_in_one_request_create_one_task(app_client):
    res = await app_client.post(LOAD, json={"ids": ["INC-01", "INC-01"]}, headers=ADMIN)
    assert len(res.json()["created"]) == 1


@pytest.mark.asyncio
async def test_ids_from_another_sector_are_rejected(app_client):
    res = await app_client.post(LOAD, json={"ids": ["COM-01"]}, headers=ADMIN)  # t1 es clínica
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_INPUT"
    res = await app_client.post(LOAD, json={"ids": ["NOPE-99"]}, headers=ADMIN)
    assert res.status_code == 400
    tasks = (await app_client.get("/api/v1/tasks", headers=ADMIN)).json()["items"]
    assert tasks == []  # nada se creó a medias


@pytest.mark.asyncio
async def test_empty_or_oversized_requests_are_invalid(app_client):
    assert (await app_client.post(LOAD, json={"ids": []}, headers=ADMIN)).status_code == 400
    many = [f"INC-{i:02d}" for i in range(61)]
    assert (await app_client.post(LOAD, json={"ids": many}, headers=ADMIN)).status_code == 400


@pytest.mark.asyncio
async def test_each_tenant_loads_independently(app_client):
    await app_client.post(LOAD, json={"ids": ["INC-01"]}, headers=ADMIN)
    items = (await app_client.get(LIST, headers=FOREIGN_ADMIN)).json()["items"]
    assert all(i["loaded"] is False for i in items)  # lo cargado por t1 no cuenta para t2
    res = await app_client.post(LOAD, json={"ids": ["INC-01"]}, headers=FOREIGN_ADMIN)
    assert res.json()["created"][0]["code"] == "TSK-001"


@pytest.mark.asyncio
async def test_unverified_items_warn_in_description(app_client):
    res = await app_client.post(LOAD, json={"ids": ["CLI-14"]}, headers=ADMIN)
    description = res.json()["created"][0]["description"]
    assert "aún no se confirma en fuente oficial" in description


@pytest.mark.asyncio
async def test_event_items_have_no_due_date_and_periodic_ones_do(app_client):
    res = await app_client.post(LOAD, json={"ids": ["DAT-03", "INC-06"]}, headers=ADMIN)
    by_title = {t["title"]: t for t in res.json()["created"]}
    assert by_title["Responder solicitudes ARCO en 20 días hábiles"]["due_date"] is None
    assert by_title["Revisión mensual de extintores"]["due_date"] is not None


@pytest.mark.asyncio
async def test_load_is_recorded_in_audit_log(app_client):
    await app_client.post(LOAD, json={"ids": ["INC-01"]}, headers=ADMIN)
    from sqlalchemy import select

    async with app_client.session_factory() as s:
        query = select(AuditLog).where(AuditLog.action == "OBLIGATIONS_LOADED")
        rows = (await s.execute(query)).scalars().all()
    assert len(rows) == 1 and rows[0].tenant_id == "t1"
    assert rows[0].details["created"] == ["TSK-001"]


def test_every_catalog_id_matches_the_marker_format():
    from app.services.obligations_service import _MARKER_RE, MARKER

    for o in oc.load_catalog().obligaciones:
        assert _MARKER_RE.search(f"{MARKER} {o.id}"), o.id
