"""Esquemas de la bitácora de auditoría."""
from datetime import datetime

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str | None
    actor_name: str | None
    details: dict | None
    created_at: datetime


class AuditList(BaseModel):
    items: list[AuditEntryOut]
    total: int
