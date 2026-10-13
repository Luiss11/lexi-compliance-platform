from pydantic import BaseModel, Field, field_validator

from app.core.security import Role


class LoginRequest(BaseModel):
    tenant_slug: str = Field(min_length=1, max_length=60)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("tenant_slug", "email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.strip().lower()


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: Role


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    sector: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MeResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
