"""Auth request/response schemas."""

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()


class RefreshRequest(BaseModel):
    refresh_token: str | None = None  # optional — can come from httponly cookie instead


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = None
    assistant_name: str | None = Field(default=None, min_length=1, max_length=50)
    locale: str | None = None

    @field_validator("timezone", mode="after")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, KeyError):
            raise ValueError(f"Timezone không hợp lệ: {v!r}") from None
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    timezone: str
    assistant_name: str
    locale: str
    avatar_url: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None  # not returned in body; browser gets token via httponly cookie
    expires_in: int
    user: UserOut
