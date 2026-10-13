from datetime import date

from pydantic import BaseModel


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
