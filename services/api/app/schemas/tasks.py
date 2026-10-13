"""Esquemas de tareas (SDD §5.3)."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.tables import Priority, TaskStatus


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: Priority = Priority.MEDIA
    due_date: date | None = None
    assignee_id: str | None = None
    document_id: str | None = None
    citation: str | None = Field(default=None, max_length=300)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("El título debe tener al menos 3 caracteres.")
        return v

    @field_validator("description", "citation")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return _clean(v)


class TaskUpdate(BaseModel):
    """PATCH parcial: solo se cambia lo que viene en el cuerpo."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: Priority | None = None
    due_date: date | None = None
    assignee_id: str | None = None
    citation: str | None = Field(default=None, max_length=300)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3:
            raise ValueError("El título debe tener al menos 3 caracteres.")
        return v


class TaskStatusChange(BaseModel):
    status: TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    due_date: datetime | None
    assignee_id: str | None
    assignee_name: str | None = None
    document_id: str | None
    citation: str | None
    suggested_by_ai: bool
    overdue: bool = False
    created_at: datetime


class TaskList(BaseModel):
    items: list[TaskOut]


# --- Modelos del arranque original: los usan el agente (supervisor) y el router de evidencias ---


class TaskSuggestion(BaseModel):
    title: str
    priority: str  # ALTA | MEDIA | BAJA
    due_date: date | None = None
    citation: str
    role: str  # ADMIN | COMPLIANCE | OPERATOR


class EvidenceReceipt(BaseModel):
    task_id: str
    filename: str
    sha256: str
    size_bytes: int
    ai_verdict: str | None = None
