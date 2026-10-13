"""Mapeo SQLAlchemy de las tablas creadas por Prisma (ADR-0002).

Prisma es el dueño del esquema: aquí NUNCA se crean ni alteran tablas en producción.
Las columnas de Prisma están en camelCase, por eso el nombre explícito en mapped_column.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TaskStatus(str, enum.Enum):
    """Mismos valores que el enum TaskStatus de Prisma."""

    BACKLOG = "BACKLOG"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class Priority(str, enum.Enum):
    """Mismos valores que el enum Priority de Prisma."""

    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True)
    sector: Mapped[str] = mapped_column(String)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column("tenantId", ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column("passwordHash", String)
    # En PostgreSQL es el enum "Role"; asyncpg lo entrega como str
    role: Mapped[str] = mapped_column(String)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column("tenantId", ForeignKey("tenants.id"))
    title: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    pages: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column("storagePath", String)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String)
    tenant_id: Mapped[str] = mapped_column("tenantId", ForeignKey("tenants.id"))
    document_id: Mapped[str | None] = mapped_column("documentId", ForeignKey("documents.id"))
    assignee_id: Mapped[str | None] = mapped_column("assigneeId", ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    # Enums nativos de Postgres creados por Prisma: create_type=False evita que SQLAlchemy los cree
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="TaskStatus", create_type=False), default=TaskStatus.BACKLOG
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="Priority", create_type=False), default=Priority.MEDIA
    )
    due_date: Mapped[datetime | None] = mapped_column("dueDate", DateTime)
    citation: Mapped[str | None] = mapped_column(String)
    suggested_by_ai: Mapped[bool] = mapped_column("suggestedByAi", Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime, server_default=func.now()
    )
