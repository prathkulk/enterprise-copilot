from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthRegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("tenant_name", "full_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty.")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Email must be valid.")
        return normalized


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError("Email must be valid.")
        return normalized


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse
    tenant: TenantResponse
