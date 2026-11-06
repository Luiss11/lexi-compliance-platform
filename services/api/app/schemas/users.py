"""Esquemas de usuarios, contraseñas y alta de organizaciones."""
import re

from pydantic import BaseModel, Field, field_validator

from app.core.security import Role

MIN_PASSWORD = 10
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def check_password_strength(value: str) -> str:
    """Mínimo 10 caracteres, con al menos una letra y un número."""
    if len(value) < MIN_PASSWORD:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", value) or not re.search(r"\d", value):
        raise ValueError("La contraseña debe incluir letras y números.")
    return value


class UserAdminOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: Role
    active: bool


class UserList(BaseModel):
    items: list[UserAdminOut]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    role: Role = Role.OPERATOR
    password: str = Field(max_length=200)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Escribe el nombre completo.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Escribe un correo válido.")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return check_password_strength(v)


class UserUpdate(BaseModel):
    """PATCH parcial: solo se cambia lo que viene en el cuerpo."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: Role | None = None
    active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Escribe el nombre completo.")
        return v


class PasswordReset(BaseModel):
    new_password: str = Field(max_length=200)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return check_password_strength(v)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(max_length=200)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return check_password_strength(v)
