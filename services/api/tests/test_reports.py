"""Panel de cumplimiento y Expediente de auditoría."""
import os
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.v1.routers import evidence, reports, tasks
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.security import Role, create_access_token
from app.db.session import get_db
from app.models.tables import (
    Base, Document, DocumentStatus, Priority, Task, TaskStatus, Tenant, User,
)
from app.services.report_service import compute_score, score_label, seal_of


def auth(user_id, tenant_id, role):
    return {"Authorization": f"Bearer {create_access_token(user_id, tenant_id, role)}"}


ADMIN = auth("u-admin", "t1", Role.ADMIN)
COMPLIANCE = auth("u-comp", "t1", Role.COMPLIANCE)
OPERATOR = auth("u-op", "t1", Role.OPERATOR)
FOREIGN = auth("u-x", "t2", Role.ADMIN)
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64 + b"fotografia"

NOW = datetime.now(UTC).replace(tzinfo=None)


def T(id, code, status, priority, assignee="u-op", due=None):
    return Task(id=id, code=code, tenant_id="t1", title=f"Tarea {code}", status=status,
                priority=priority, assignee_id=assignee, due_date=due)


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path), raising=False)
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    S = TaskStatus
    async with Session() as s:
        s.add_all(
            [
                Tenant(id="t1", name="Clínica Sonrisa", slug="c", sector="clinica"),
                Tenant(id="t2", name="Otro", slug="o", sector="retail"),
                User(id="u-admin", tenant_id="t1", name="Admin", email="a@x", password_hash="x", role="ADMIN"),
                User(id="u-comp", tenant_id="t1", name="Comp", email="c@x", password_hash="x", role="COMPLIANCE"),
                User(id="u-op", tenant_id="t1", name="Op Uno", email="o@x", password_hash="x", role="OPERATOR"),
                User(id="u-x", tenant_id="t2", name="Foráneo", email="f@x", password_hash="x", role="ADMIN"),
                T("k-prog", "TSK-001", S.IN_PROGRESS, Priority.ALTA, due=NOW + timedelta(days=5)),
                T("k-done-noev", "TSK-002", S.DONE, Priority.MEDIA),
                T("k-late", "TSK-003", S.IN_PROGRESS, Priority.MEDIA, assignee="u-comp",
                  due=NOW - timedelta(days=3)),
                T("k-back", "TSK-004", S.BACKLOG, Priority.ALTA, assignee=None),
                T("k-review", "TSK-005", S.IN_REVIEW, Priority.BAJA),
                Document(id="d1", tenant_id="t1", title="LFPDPPP", category="LEY",
                         status=DocumentStatus.INDEXED, sha256="a" * 64, storage_path="x"),
                Document(id="d2", tenant_id="t1", title="Escaneado", category="LEY",
                         status=DocumentStatus.NEEDS_REVIEW, sha256="b" * 64, storage_path="y"),
            ]
        )
        await s.commit()

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(tasks.router, prefix="/api/v1/tasks")
    app.include_router(evidence.tasks_router, prefix="/api/v1/tasks")
    app.include_router(evidence.router, prefix="/api/v1/evidence")
    app.include_router(reports.dashboard_router, prefix="/api/v1/dashboard")
    app.include_router(reports.router, prefix="/api/v1/reports")

    async def override_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        c.storage = tmp_path
        yield c
    await engine.dispose()


async def upload(client, task_id="k-prog", headers=OPERATOR, data=JPEG):
    r = await client.post(
        f"/api/v1/tasks/{task_id}/evidence", headers=headers,
        files={"evidence_file": ("foto.jpg", data, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------- índice ----------

def _t(status, priority):
    return Task(id="x", code="X", tenant_id="t", title="x", status=status, priority=priority)


def test_score_weights_and_done_without_evidence():
    S, P = TaskStatus, Priority
    assert compute_score([]) == 0
    assert compute_score([(_t(S.DONE, P.ALTA), 1)]) == 100
    assert compute_score([(_t(S.DONE, P.ALTA), 0)]) == 50  # cumplida sin evidencia: la mitad
    assert compute_score([(_t(S.BACKLOG, P.ALTA), 0)]) == 0
    # ALTA(3) cumplida + BAJA(1) pendiente = 3/4
    assert compute_score([(_t(S.DONE, P.ALTA), 2), (_t(S.BACKLOG, P.BAJA), 0)]) == 75


def test_score_labels():
    assert score_label(0, 0) == "Sin tareas"
    assert score_label(85, 4) == "Sólido"
    assert score_label(60, 4) == "En progreso"
    assert score_label(20, 4) == "Crítico"


# ---------- panel ----------

async def test_dashboard_manager_view(client):
    r = await client.get("/api/v1/dashboard", headers=COMPLIANCE)
    assert r.status_code == 200
    d = r.json()
    assert d["scope"] == "tenant"
    assert d["total_tasks"] == 5
    assert d["counts"] == {"backlog": 1, "in_progress": 2, "in_review": 1, "done": 1}
    assert d["overdue"] == 1
    assert d["documents_total"] == 2 and d["documents_indexed"] == 1
    assert d["evidence_files"] == 0
    assert d["evidence_coverage"] == 0  # revisión + cumplida, ninguna con evidencia
    kinds = {a["kind"] for a in d["alerts"]}
    assert {"OVERDUE", "DONE_WITHOUT_EVIDENCE", "HIGH_PRIORITY_PENDING",
            "AWAITING_REVIEW", "UNASSIGNED", "DOCUMENT_ISSUE"} <= kinds
    # las alertas graves van primero
    assert d["alerts"][0]["severity"] == "high"
    # próximos vencimientos: la vencida va antes que la de 5 días
    assert [u["code"] for u in d["upcoming"]] == ["TSK-003", "TSK-001"]
    assert d["upcoming"][0]["days_left"] < 0


async def test_dashboard_improves_with_evidence(client):
    before = (await client.get("/api/v1/dashboard", headers=ADMIN)).json()
    await upload(client, "k-prog")
    after = (await client.get("/api/v1/dashboard", headers=ADMIN)).json()
    assert after["evidence_files"] == 1
    assert after["score"] == before["score"]  # tener evidencia en curso no cambia el avance
    # enviar a revisión sí sube el índice (0.25 -> 0.6)
    r = await client.patch("/api/v1/tasks/k-prog/status", headers=OPERATOR, json={"status": "IN_REVIEW"})
    assert r.status_code == 200
    final = (await client.get("/api/v1/dashboard", headers=ADMIN)).json()
    assert final["score"] > after["score"]
    assert final["evidence_coverage"] == 33  # 1 de 3 (dos en revisión + una cumplida)


async def test_dashboard_operator_sees_only_own(client):
    d = (await client.get("/api/v1/dashboard", headers=OPERATOR)).json()
    assert d["scope"] == "mine"
    assert d["total_tasks"] == 3  # TSK-003 es de comp, TSK-004 sin responsable
    assert d["documents_total"] is None and d["documents_indexed"] is None
    kinds = {a["kind"] for a in d["alerts"]}
    assert "UNASSIGNED" not in kinds and "AWAITING_REVIEW" not in kinds and "DOCUMENT_ISSUE" not in kinds


async def test_dashboard_tenant_isolation_and_empty(client):
    d = (await client.get("/api/v1/dashboard", headers=FOREIGN)).json()
    assert d["total_tasks"] == 0 and d["score"] == 0 and d["score_label"] == "Sin tareas"
    assert d["evidence_coverage"] is None and d["alerts"] == [] and d["documents_total"] == 0


async def test_dashboard_requires_auth(client):
    assert (await client.get("/api/v1/dashboard")).status_code == 401


# ---------- expediente ----------

async def test_dossier_only_managers(client):
    assert (await client.get("/api/v1/reports/dossier", headers=OPERATOR)).status_code == 403
    assert (await client.get("/api/v1/reports/dossier")).status_code == 401
    assert (await client.get("/api/v1/reports/dossier", headers=COMPLIANCE)).status_code == 200


async def test_dossier_content_and_seal(client):
    ev = await upload(client, "k-prog")
    d = (await client.get("/api/v1/reports/dossier", headers=COMPLIANCE)).json()
    assert d["tenant_name"] == "Clínica Sonrisa"
    assert d["summary"]["total_tasks"] == 5
    assert d["summary"]["evidence_files"] == 1 and d["summary"]["integrity_failures"] == 0
    task = next(t for t in d["tasks"] if t["code"] == "TSK-001")
    assert task["evidence"][0]["sha256"] == ev["sha256"]
    assert task["evidence"][0]["integrity"] == "OK"
    assert task["evidence"][0]["uploaded_by_name"] == "Op Uno"
    assert len(d["documents"]) == 2
    # el sello se puede recalcular sin la API: SHA-256 del JSON canónico sin el campo seal
    body = {k: v for k, v in d.items() if k != "seal"}
    assert seal_of(body) == d["seal"]
    # y cambiar cualquier dato lo invalida
    body["summary"]["score"] += 1
    assert seal_of(body) != d["seal"]


async def test_dossier_detects_tampered_and_missing_files(client):
    a = await upload(client, "k-prog")
    b = await upload(client, "k-prog", data=JPEG + b"otra")
    files = sorted(
        os.path.join(root, f) for root, _, fs in os.walk(client.storage) for f in fs
    )
    assert len(files) == 2
    with open(files[0], "ab") as fh:  # alterar un archivo guardado
        fh.write(b"manipulado")
    os.remove(files[1])  # y borrar el otro

    d = (await client.get("/api/v1/reports/dossier", headers=ADMIN)).json()
    states = sorted(e["integrity"] for t in d["tasks"] for e in t["evidence"])
    assert states == ["MISSING", "TAMPERED"]
    assert d["summary"]["integrity_failures"] == 2
    assert {a["id"], b["id"]} == {e["id"] for t in d["tasks"] for e in t["evidence"]}


async def test_dossier_tenant_isolation(client):
    await upload(client, "k-prog")
    d = (await client.get("/api/v1/reports/dossier", headers=FOREIGN)).json()
    assert d["tenant_name"] == "Otro"
    assert d["tasks"] == [] and d["documents"] == [] and d["summary"]["evidence_files"] == 0


async def test_standalone_verifier_matches_api_seal(client, tmp_path):
    import json

    from app.tools.verify_dossier import main, verify

    await upload(client, "k-prog")
    raw = (await client.get("/api/v1/reports/dossier", headers=ADMIN)).text
    path = tmp_path / "exp.json"
    path.write_text(raw, encoding="utf-8")
    assert verify(json.loads(raw))
    assert main(["x", str(path)]) == 0

    data = json.loads(raw)
    data["tasks"][0]["title"] = "Editado a mano"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert main(["x", str(path)]) == 1
