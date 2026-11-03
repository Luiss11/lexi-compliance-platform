import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://lexi:lexi_dev@localhost:5432/lexi"

    vector_backend: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "lexi_chunks"

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    rag_cosine_cutoff: float = 0.75
    rag_top_k: int = 8

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    # Solo para desarrollo local: permite arrancar con un secreto débil o de ejemplo (H-01)
    allow_insecure_jwt_secret: bool = False

    # Freno a intentos fallidos de login (H-03): por cuenta y por IP, en una ventana deslizante
    login_max_failures: int = 5
    login_ip_max_failures: int = 20
    login_window_seconds: int = 900
    # Tope de uso de IA (H-04): por usuario cada hora y por organización cada día
    ai_user_hourly_limit: int = 30
    ai_tenant_daily_limit: int = 200

    storage_dir: str = "./storage"
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def async_database_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Valores públicos: están en el repositorio, así que cualquiera podría firmar tokens con ellos
INSECURE_JWT_SECRETS = {"dev-secret-change-me", "cambia-esto-por-un-secreto-largo"}
MIN_JWT_SECRET_LENGTH = 32


def jwt_secret_problem(secret: str) -> str | None:
    """Motivo por el que el secreto no sirve, o None si es aceptable."""
    if secret in INSECURE_JWT_SECRETS:
        return "es un valor de ejemplo que está en el repositorio"
    if len(secret) < MIN_JWT_SECRET_LENGTH:
        return f"tiene menos de {MIN_JWT_SECRET_LENGTH} caracteres"
    return None


def check_jwt_secret(current: Settings | None = None) -> None:
    """Se llama al arrancar la API: sin un JWT_SECRET propio, cualquiera puede fabricar tokens.

    Para desarrollo local se puede saltar con ALLOW_INSECURE_JWT_SECRET=true.
    """
    cfg = current or settings
    problem = jwt_secret_problem(cfg.jwt_secret)
    if problem is None:
        return
    if cfg.allow_insecure_jwt_secret:
        log.warning("JWT_SECRET inseguro permitido por ALLOW_INSECURE_JWT_SECRET: %s", problem)
        return
    raise RuntimeError(
        f"JWT_SECRET no es seguro: {problem}. Define uno aleatorio de al menos "
        f"{MIN_JWT_SECRET_LENGTH} caracteres en el archivo .env "
        "(por ejemplo: python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
    )
