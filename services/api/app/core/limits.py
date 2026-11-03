"""Límites de uso (hallazgos H-03 y H-04).

H-03: freno a los intentos fallidos de login (por cuenta y por IP) contra adivinar contraseñas.
H-04: tope de llamadas a la IA (por usuario y por organización) para controlar el gasto.

Los contadores viven en memoria del proceso: sirven con una sola instancia de la API (como en
docker-compose). Si algún día hay varias réplicas, hay que moverlos a Redis o a la base.
"""
import time
from collections import defaultdict, deque

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import CurrentUser

# Reloj inyectable: las pruebas lo reemplazan para no esperar minutos reales
_now = time.monotonic


class SlidingWindow:
    """Cuenta eventos recientes por clave dentro de una ventana deslizante."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, window: float) -> deque[float]:
        events = self._events[key]
        limit = _now() - window
        while events and events[0] <= limit:
            events.popleft()
        if not events:
            self._events.pop(key, None)
            return deque()
        return events

    def count(self, key: str, window: float) -> int:
        return len(self._prune(key, window))

    def add(self, key: str) -> None:
        self._events[key].append(_now())

    def retry_after(self, key: str, window: float) -> int:
        """Segundos hasta que el evento más antiguo salga de la ventana (mínimo 1)."""
        events = self._prune(key, window)
        if not events:
            return 1
        return max(1, int(events[0] + window - _now()) + 1)

    def clear(self, key: str) -> None:
        self._events.pop(key, None)

    def reset(self) -> None:
        self._events.clear()


_login_failures = SlidingWindow()
_ai_calls = SlidingWindow()

_HOUR = 3600
_DAY = 86400


def reset_all() -> None:
    """Para pruebas: borra todos los contadores."""
    _login_failures.reset()
    _ai_calls.reset()


def _too_many(status_code: int, code: str, message: str, retry_after: int) -> AppError:
    return AppError(
        status_code, code, message, {"retry_after_seconds": retry_after},
        headers={"Retry-After": str(retry_after)},
    )


# ---------------------------------------------------------------- login (H-03)
def _account_key(tenant_slug: str, email: str) -> str:
    return f"acct:{tenant_slug.strip().lower()}:{email.strip().lower()}"


def _ip_key(ip: str | None) -> str:
    return f"ip:{ip or 'desconocida'}"


def check_login_allowed(tenant_slug: str, email: str, ip: str | None) -> None:
    """Se llama ANTES de verificar la contraseña: una cuenta bloqueada no gasta bcrypt."""
    window = settings.login_window_seconds
    for key, maximum in (
        (_account_key(tenant_slug, email), settings.login_max_failures),
        (_ip_key(ip), settings.login_ip_max_failures),
    ):
        if _login_failures.count(key, window) >= maximum:
            raise _too_many(
                429,
                "TOO_MANY_ATTEMPTS",
                "Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.",
                _login_failures.retry_after(key, window),
            )


def register_login_failure(tenant_slug: str, email: str, ip: str | None) -> None:
    _login_failures.add(_account_key(tenant_slug, email))
    _login_failures.add(_ip_key(ip))


def register_login_success(tenant_slug: str, email: str) -> None:
    """Un acceso correcto reinicia la cuenta (la IP conserva su historial)."""
    _login_failures.clear(_account_key(tenant_slug, email))


# ------------------------------------------------------------------- IA (H-04)
def _ai_keys(actor: CurrentUser) -> tuple[tuple[str, int, int, str], ...]:
    return (
        (f"u:{actor.id}", _HOUR, settings.ai_user_hourly_limit,
         "Llegaste al límite de consultas de IA por hora."),
        (f"t:{actor.tenant_id}", _DAY, settings.ai_tenant_daily_limit,
         "Tu organización llegó al límite diario de uso de IA."),
    )


def _violation(actor: CurrentUser) -> AppError | None:
    for key, window, maximum, message in _ai_keys(actor):
        if _ai_calls.count(key, window) >= maximum:
            return _too_many(
                429, "AI_LIMIT_REACHED", f"{message} Inténtalo más tarde.",
                _ai_calls.retry_after(key, window),
            )
    return None


def _record(actor: CurrentUser) -> None:
    for key, _window, _maximum, _message in _ai_keys(actor):
        _ai_calls.add(key)


def consume_ai(actor: CurrentUser) -> None:
    """Cuenta una llamada a la IA o lanza 429 si el usuario u organización llegó a su tope."""
    error = _violation(actor)
    if error is not None:
        raise error
    _record(actor)


def try_consume_ai(actor: CurrentUser) -> bool:
    """Igual que consume_ai pero sin lanzar error: para funciones de mejor esfuerzo."""
    if _violation(actor) is not None:
        return False
    _record(actor)
    return True
