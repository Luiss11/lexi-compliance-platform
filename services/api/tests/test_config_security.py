"""JWT_SECRET (hallazgo H-01): la API no arranca con un secreto de ejemplo o muy corto."""
import pytest

from app.core.config import (
    INSECURE_JWT_SECRETS,
    MIN_JWT_SECRET_LENGTH,
    Settings,
    check_jwt_secret,
    jwt_secret_problem,
)

STRONG = "k8Jx2mQ9vLw4RtYb7NcPz3HsEd6GfUa1XoIq5VnBy0MuTe8Wr"


def cfg(**kw) -> Settings:
    # _env_file=None: el .env real de quien corre las pruebas no debe influir
    return Settings(_env_file=None, **kw)


@pytest.mark.parametrize("secret", sorted(INSECURE_JWT_SECRETS))
def test_example_secrets_are_rejected(secret):
    assert jwt_secret_problem(secret) is not None
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_jwt_secret(cfg(jwt_secret=secret))


def test_short_secret_is_rejected():
    short = "a" * (MIN_JWT_SECRET_LENGTH - 1)
    assert "menos de" in jwt_secret_problem(short)
    with pytest.raises(RuntimeError):
        check_jwt_secret(cfg(jwt_secret=short))


def test_strong_secret_is_accepted():
    assert len(STRONG) >= MIN_JWT_SECRET_LENGTH
    assert jwt_secret_problem(STRONG) is None
    check_jwt_secret(cfg(jwt_secret=STRONG))  # no lanza


def test_default_settings_do_not_start_without_a_real_secret():
    with pytest.raises(RuntimeError):
        check_jwt_secret(cfg())


def test_weak_secret_allowed_only_with_explicit_flag(caplog):
    with caplog.at_level("WARNING"):
        check_jwt_secret(cfg(allow_insecure_jwt_secret=True))
    assert "JWT_SECRET inseguro" in caplog.text


def test_error_message_explains_how_to_fix_it():
    with pytest.raises(RuntimeError) as exc:
        check_jwt_secret(cfg())
    assert ".env" in str(exc.value)
    assert "secrets.token_urlsafe" in str(exc.value)
