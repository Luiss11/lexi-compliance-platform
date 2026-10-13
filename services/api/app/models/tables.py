"""Mapeo SQLAlchemy de las tablas creadas por Prisma (ADR-0002).

Prisma es el dueño del esquema: aquí NUNCA se crean ni alteran tablas en producción.
Las columnas de Prisma están en camelCase, por eso el nombre explícito en mapped_column.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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
    tenant_id: Mapped[str] = mapped_column("tenantId", ForeignKey("tenants.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    priority: Mapped[str] = mapped_column(String)
    due_date: Mapped[datetime | None] = mapped_column("dueDate", DateTime)
    citation: Mapped[str | None] = mapped_column(String)
