"""Esquemas del agente de vacíos normativos."""
from datetime import date

from pydantic import BaseModel, Field

from app.models.tables import Priority


class GapSuggestion(BaseModel):
    key: str  # id estable de la sugerencia (para marcarla en la pantalla)
    title: str
    description: str
    priority: Priority
    due_date: date
    reason: str  # por qué es un vacío (no hay tarea que lo cubra)
    # Fundamento: SIEMPRE sale del fragmento recuperado, nunca de lo que escriba el modelo
    document_id: str
    document_title: str
    page: int
    clause: str | None = None
    quote: str  # cita literal del documento, verificada contra el texto


class GapStats(BaseModel):
    documents: int  # documentos indexados de la organización
    passages: int  # fragmentos revisados
    existing_tasks: int
    excluded_internal: int = 0  # fragmentos de políticas internas u otros, que no se analizan
    already_covered: int  # sugerencias descartadas porque ya existe una tarea parecida
    dismissed_before: int = 0  # sugerencias que una persona ya había descartado
    not_obligation: int = 0  # sugerencias cuya cita no contiene un verbo de obligación
    discarded_unverified: int  # sugerencias descartadas porque su cita no aparece en el documento


class GapAnalysis(BaseModel):
    suggestions: list[GapSuggestion]
    stats: GapStats


class GapAcceptItem(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    priority: Priority = Priority.MEDIA
    due_date: date | None = None
    document_id: str | None = None
    citation: str | None = Field(default=None, max_length=300)


class GapAccept(BaseModel):
    items: list[GapAcceptItem] = Field(min_length=1, max_length=20)


class GapDismissItem(BaseModel):
    document_id: str
    page: int
    clause: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=3, max_length=200)


class GapDismiss(BaseModel):
    items: list[GapDismissItem] = Field(min_length=1, max_length=20)


class GapDismissed(BaseModel):
    dismissed: int
