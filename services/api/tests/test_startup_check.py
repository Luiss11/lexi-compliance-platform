"""Revisión de arranque: en producción la API no inicia si falta algo crítico."""
import pytest

from app.core.config import Settings, check_startup, production_problems

DEV_DB = "postgresql://lexi:lexi_dev@postgres:5432/lexi"
STRONG = "k8Jx2mQ9vLw4RtYb7NcPz3HsEd6GfUa1XoIq5VnBy0MuTe8Wr"


def prod(tmp_path, **kw) -> Settings:
    """Configuración de producción válida; cada prueba rompe una sola cosa."""
    base = dict(
        app_env="production",
        jwt_secret=STRONG,
        database_url="postgresql://lexi:Zq81vXk2Lm@postgres:5432/lexi",
        llm_provider="openai",
        openai_api_key="sk-test",
        storage_dir=str(tmp_path / "storage"),
    )
    base.update(kw)
    return Settings(_env_file=None, **base)


def test_valid_production_config_starts(tmp_path):
    check_startup(prod(tmp_path))
    assert (tmp_path / "storage").is_dir()  # crea la carpeta de evidencias si falta


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"jwt_secret": "dev-secret-change-me"}, "JWT_SECRET"),
        ({"allow_insecure_jwt_secret": True}, "ALLOW_INSECURE_JWT_SECRET"),
        ({"database_url": DEV_DB}, "contraseña de desarrollo"),
        ({"database_url": "postgresql://lexi@postgres:5432/lexi"}, "contraseña de desarrollo"),
        ({"database_url": "postgresql://lexi:Zq81vXk2Lm@localhost:5432/lexi"}, "localhost"),
        ({"openai_api_key": None}, "OPENAI_API_KEY"),
        ({"llm_provider": "gpt"}, "LLM_PROVIDER"),
        ({"qdrant_url": ""}, "QDRANT_URL"),
    ],
)
def test_each_critical_problem_blocks_production(tmp_path, override, expected):
    with pytest.raises(RuntimeError, match=expected):
        check_startup(prod(tmp_path, **override))


def test_all_problems_are_reported_at_once(tmp_path):
    cfg = prod(tmp_path, openai_api_key=None, database_url="postgresql://lexi:lexi_dev@postgres/lexi")
    with pytest.raises(RuntimeError) as exc:
        check_startup(cfg)
    assert "OPENAI_API_KEY" in str(exc.value) and "DATABASE_URL" in str(exc.value)
    assert ".env.prod" in str(exc.value)


def test_ollama_does_not_need_an_openai_key(tmp_path):
    assert production_problems(prod(tmp_path, llm_provider="ollama", openai_api_key=None)) == []


def test_unwritable_storage_blocks_production(tmp_path):
    blocker = tmp_path / "archivo"
    blocker.write_text("no soy carpeta")
    with pytest.raises(RuntimeError, match="STORAGE_DIR"):
        check_startup(prod(tmp_path, storage_dir=str(blocker / "storage")))


def test_typo_in_app_env_is_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="APP_ENV"):
        check_startup(prod(tmp_path, app_env="prod"))


def test_development_only_checks_the_jwt_secret(tmp_path):
    # Sin clave de IA y con la base de desarrollo: normal en tu equipo
    check_startup(prod(tmp_path, app_env="development", openai_api_key=None,
                       database_url="postgresql://lexi:lexi_dev@localhost:5432/lexi"))
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_startup(prod(tmp_path, app_env="development", jwt_secret="corto"))
