"""Reminder request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _require_aware(v: datetime) -> datetime:
    if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
        raise ValueError("remind_at must be timezone-aware (include UTC offset or 'Z')")
    return v


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    remind_at: datetime
    description: str | None = None
    source: str = Field(default="ui", pattern="^(ui|chat)$")

    @field_validator("remind_at")
    @classmethod
    def remind_at_must_be_aware(cls, v: datetime) -> datetime:
        return _require_aware(v)


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    remind_at: datetime | None = None
    description: str | None = None

    @field_validator("title", "remind_at", mode="before")
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("cannot be set to null; omit the field to leave it unchanged")
        return v

    @field_validator("remind_at")
    @classmethod
    def remind_at_must_be_aware(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return _require_aware(v)


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    remind_at: datetime
    status: str
    source: str
    created_at: datetime
    updated_at: datetime


class ReminderListOut(BaseModel):
    items: list[ReminderOut]
    next_cursor: str | None


ReminderStatus = Literal["pending", "sending", "sent", "failed", "cancelled"]
