"""Esquemas de evidencias con sello SHA-256 (SDD §5.4, RF-TSK-02)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    ai_verdict: str | None
    uploaded_by_name: str | None = None
    ai_summary: str | None = None
    ai_issues: list[str] = Field(default_factory=list)
    created_at: datetime


class EvidenceList(BaseModel):
    items: list[EvidenceOut]


class VerifyResult(BaseModel):
    evidence_id: str
    ok: bool
    tampered: bool
    stored_sha256: str
    computed_sha256: str | None
    reason: str | None = None
