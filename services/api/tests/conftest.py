import pytest

from app.core import limits


@pytest.fixture(autouse=True)
def _reset_limits():
    """Los contadores de límites viven en memoria: cada prueba empieza con ceros."""
    limits.reset_all()
    yield
    limits.reset_all()
