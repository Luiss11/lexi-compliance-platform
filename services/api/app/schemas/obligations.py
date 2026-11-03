"""Esquemas del catálogo de obligaciones y su carga como tareas."""
from pydantic import BaseModel, Field

from app.schemas.tasks import TaskOut
from app.services.obligations_catalog import Obligation


class ObligationItem(Obligation):
    loaded: bool = False  # ya existe una tarea creada desde este punto del catálogo


class ObligationList(BaseModel):
    sector: str | None  # sector reconocido de la organización (None si no hay catálogo propio)
    aviso: str
    items: list[ObligationItem]


class ObligationLoad(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=60)


class ObligationLoadResult(BaseModel):
    created: list[TaskOut]
    skipped: list[str]  # ids que ya tenían tarea y no se repitieron
