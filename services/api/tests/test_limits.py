"""Límites de uso: freno de login (H-03) y tope de uso de IA (H-04)."""
import pytest

from app.core import limits
from app.core.config import settings
from app.core.security import CurrentUser, Role, create_access_token
from app.rag.guard import FALLBACK_MESSAGE
from app.schemas.rag import QueryResponse
from app.services import assistant_service
from tests import test_assistant, test_auth_flow
from tests.test_auth_flow import login_body

# Se reutilizan las fixtures de las suites existentes
login_client = test_auth_flow.client
ai_client = test_assistant.client

LOGIN = "/api/v1/auth/login"


class Clock:
    """Reloj falso para avanzar el tiempo sin esperar."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(limits, "_now", c)
    return c


def bad(**kw):
    return login_body(password="incorrecta", **kw)


# ------------------------------------------------------------------ login (H-03)
@pytest.mark.asyncio
async def test_login_locks_after_max_failures(login_client, clock):
    for _ in range(settings.login_max_failures):
        res = await login_client.post(LOGIN, json=bad())
        assert res.status_code == 401

    res = await login_client.post(LOGIN, json=bad())
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
    assert int(res.headers["Retry-After"]) >= 1

    # Con la cuenta bloqueada ni la contraseña correcta entra
    res = await login_client.post(LOGIN, json=login_body())
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_login_unlocks_after_window(login_client, clock):
    for _ in range(settings.login_max_failures):
        await login_client.post(LOGIN, json=bad())
    assert (await login_client.post(LOGIN, json=login_body())).status_code == 429

    clock.t += settings.login_window_seconds + 1
    assert (await login_client.post(LOGIN, json=login_body())).status_code == 200


@pytest.mark.asyncio
async def test_successful_login_resets_account_counter(login_client, clock):
    for _ in range(settings.login_max_failures - 1):
        await login_client.post(LOGIN, json=bad())
    assert (await login_client.post(LOGIN, json=login_body())).status_code == 200

    # El contador volvió a cero: se tienen de nuevo todos los intentos
    for _ in range(settings.login_max_failures):
        assert (await login_client.post(LOGIN, json=bad())).status_code == 401
    assert (await login_client.post(LOGIN, json=bad())).status_code == 429


@pytest.mark.asyncio
async def test_lock_is_per_account(login_client, clock):
    for _ in range(settings.login_max_failures):
        await login_client.post(LOGIN, json=bad())
    # Otra cuenta de la misma organización no se ve afectada
    other = login_body(email="operator@demo.lexi")
    assert (await login_client.post(LOGIN, json=other)).status_code == 200


@pytest.mark.asyncio
async def test_unknown_accounts_are_also_counted(login_client, clock):
    """Adivinar correos inexistentes también se frena y no delata si la cuenta existe."""
    ghost = bad(email="nadie@demo.lexi")
    for _ in range(settings.login_max_failures):
        assert (await login_client.post(LOGIN, json=ghost)).status_code == 401
    res = await login_client.post(LOGIN, json=ghost)
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_ip_limit_stops_spraying_many_accounts(login_client, clock, monkeypatch):
    monkeypatch.setattr(settings, "login_ip_max_failures", 4)
    for i in range(4):
        res = await login_client.post(LOGIN, json=bad(email=f"user{i}@demo.lexi"))
        assert res.status_code == 401
    res = await login_client.post(LOGIN, json=bad(email="user99@demo.lexi"))
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_account_key_ignores_case_and_spaces(login_client, clock):
    for _ in range(settings.login_max_failures):
        await login_client.post(LOGIN, json=bad(email="ADMIN@demo.lexi"))
    res = await login_client.post(LOGIN, json=bad(email="admin@demo.lexi"))
    assert res.status_code == 429


# --------------------------------------------------------------------- IA (H-04)
def ask(client, headers=None):
    return client.post(
        "/api/v1/query",
        json={"question": "¿Qué debe contener el aviso de privacidad?"},
        headers=headers or test_assistant.auth(),
    )


@pytest.fixture
def fake_answer(monkeypatch):
    async def fake(tenant_id, question):
        return QueryResponse(answer=FALLBACK_MESSAGE, grounded=False, best_score=0.2)

    monkeypatch.setattr(assistant_service, "_answer", fake)


@pytest.mark.asyncio
async def test_user_hourly_ai_limit(ai_client, fake_answer, clock, monkeypatch):
    monkeypatch.setattr(settings, "ai_user_hourly_limit", 3)
    for _ in range(3):
        assert (await ask(ai_client)).status_code == 200

    res = await ask(ai_client)
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "AI_LIMIT_REACHED"
    assert int(res.headers["Retry-After"]) >= 1

    clock.t += 3601
    assert (await ask(ai_client)).status_code == 200


@pytest.mark.asyncio
async def test_tenant_daily_ai_limit_is_shared_by_its_users(
    ai_client, fake_answer, clock, monkeypatch
):
    monkeypatch.setattr(settings, "ai_tenant_daily_limit", 2)

    def as_user(uid, tenant="t1"):
        token = create_access_token(uid, tenant, Role.OPERATOR)
        return {"Authorization": f"Bearer {token}"}

    assert (await ask(ai_client, as_user("a"))).status_code == 200
    assert (await ask(ai_client, as_user("b"))).status_code == 200
    res = await ask(ai_client, as_user("c"))  # otra persona, misma organización
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "AI_LIMIT_REACHED"

    # Otra organización tiene su propio presupuesto
    assert (await ask(ai_client, as_user("d", tenant="t2"))).status_code == 200


@pytest.mark.asyncio
async def test_rejected_requests_do_not_consume_quota(ai_client, fake_answer, monkeypatch):
    monkeypatch.setattr(settings, "ai_user_hourly_limit", 1)
    # Sin sesión: se rechaza antes de contar
    for _ in range(3):
        res = await ai_client.post("/api/v1/query", json={"question": "hola mundo"})
        assert res.status_code == 401
    assert (await ask(ai_client)).status_code == 200


def test_try_consume_returns_false_instead_of_raising(monkeypatch):
    monkeypatch.setattr(settings, "ai_user_hourly_limit", 1)
    actor = CurrentUser(id="u1", tenant_id="t1", role=Role.OPERATOR)
    assert limits.try_consume_ai(actor) is True
    assert limits.try_consume_ai(actor) is False
