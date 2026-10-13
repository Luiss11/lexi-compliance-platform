"""Esquemas del Panel de cumplimiento y del Expediente de auditoría."""
from datetime import date, datetime

from pydantic import BaseModel


class StatusCounts(BaseModel):
    backlog: int = 0
    in_progress: int = 0
    in_review: int = 0
    done: int = 0


class Alert(BaseModel):
    kind: str  # OVERDUE | DONE_WITHOUT_EVIDENCE | HIGH_PRIORITY_PENDING | AWAITING_REVIEW | UNASSIGNED | DOCUMENT_ISSUE
    severity: str  # high | medium | info
    message: str
    task_id: str | None = None
    task_code: str | None = None


class Upcoming(BaseModel):
    task_id: str
    code: str
    title: str
    due_date: date
    days_left: int
    priority: str
    status: str
    assignee_name: str | None = None


class DashboardOut(BaseModel):
    scope: str  # "tenant" (admin/oficial) | "mine" (operador: solo sus tareas)
    score: int
    score_label: str
    total_tasks: int
    counts: StatusCounts
    overdue: int
    due_soon: int
    evidence_files: int
    evidence_coverage: int | None  # % de tareas en revisión/cumplidas con evidencia; None si no hay
    documents_total: int | None
    documents_indexed: int | None
    alerts: list[Alert]
    upcoming: list[Upcoming]


class DossierEvidence(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    uploaded_by_name: str | None
    uploaded_at: datetime
    integrity: str  # OK | TAMPERED | MISSING


class DossierTask(BaseModel):
    code: str
    title: str
    description: str | None
    status: str
    priority: str
    due_date: date | None
    overdue: bool
    assignee_name: str | None
    citation: str | None
    document_title: str | None
    evidence: list[DossierEvidence]


class DossierDocument(BaseModel):
    title: str
    category: str
    status: str
    pages: int | None
    sha256: str
    uploaded_at: datetime


class DossierSummary(BaseModel):
    score: int
    score_label: str
    total_tasks: int
    done: int
    overdue: int
    evidence_files: int
    integrity_failures: int


class DossierOut(BaseModel):
    tenant_name: str
    generated_at: datetime
    generated_by: str | None
    summary: DossierSummary
    documents: list[DossierDocument]
    tasks: list[DossierTask]
    seal: str  # SHA-256 del contenido canónico (todo lo anterior)
