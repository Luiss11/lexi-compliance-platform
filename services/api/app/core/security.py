"""Contraseñas (bcrypt), JWT y Guardián RBAC (TASK-13).

El JWT va FIRMADO (HS256), no cifrado: solo lleva sub, tid, role y exp.
Nunca se pone correo ni nombre dentro del token.
"""
from datetime import UTC, datetime, timedelta
from enum import Enum

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import forbidden, unauthenticated

# auto_error=False: si falta el header respondemos nosotros con el envelope 401
bearer = HTTPBearer(auto_error=False)

# bcrypt solo considera los primeros 72 bytes de la contraseña
_MAX_BYTES = 72

# Hash válido de una contraseña cualquiera. Se compara cuando el usuario no existe
# para que el login tarde lo mismo y no revele qué correos están registrados.
DUMMY_HASH = "$2b$12$A0iur7RnpwQJ5XNIVJlJrO8qrGkoXLif62LBQfUwDvM4C.iNDtucS"


class Role(str, Enum):
    ADMIN = "ADMIN"
    COMPLIANCE = "COMPLIANCE"
    OPERATOR = "OPERATOR"


class CurrentUser(BaseModel):
    id: str
    tenant_id: str
    role: Role


def hash_password(plain: str, rounds: int = 12) -> str:
    raw = plain.encode("utf-8")[:_MAX_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_MAX_BYTES], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, tenant_id: str, role: Role) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": user_id, "tid": tenant_id, "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> CurrentUser:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return CurrentUser(id=data["sub"], tenant_id=data["tid"], role=Role(data["role"]))
    except (JWTError, KeyError, ValueError) as exc:
        raise unauthenticated() from exc


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if creds is None or not creds.credentials:
        raise unauthenticated()
    return decode_access_token(creds.credentials)


def require_roles(*roles: Role):
    """Uso: Depends(require_roles(Role.ADMIN, Role.COMPLIANCE))."""

    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise forbidden()
        return user

    return checker
