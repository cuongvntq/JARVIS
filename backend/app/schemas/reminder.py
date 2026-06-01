"""Reminder request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    remind_at: datetime
    description: str | None = None
    source: str = Field(default="ui", pattern="^(ui|chat)$")


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    remind_at: datetime | None = None
    description: str | None = None


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
