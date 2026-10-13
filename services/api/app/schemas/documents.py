"""Esquemas de documentos normativos (SDD §5.2)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.tables import DocumentStatus


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    status: DocumentStatus
    pages: int | None
    chunks: int | None
    sha256: str
    uploaded_by_name: str | None = None
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentOut]
