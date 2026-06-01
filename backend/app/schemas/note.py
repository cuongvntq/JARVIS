"""Note request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    pinned: bool = False
    source: str = Field(default="ui", pattern="^(ui|chat)$")


class NotePatch(BaseModel):
    """Internal only — used by tool executor for partial update. NOT exposed via REST."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    tags: list[str] | None = None
    pinned: bool | None = None


class NoteUpdate(BaseModel):
    """REST PATCH /notes/{id} — all fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    tags: list[str] | None = None
    pinned: bool | None = None

    @field_validator("title", "content", "tags", "pinned", mode="before")
    @classmethod
    def _reject_explicit_null(cls, v: object) -> object:
        if v is None:
            raise ValueError("cannot be set to null; omit the field to leave it unchanged")
        return v


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    content: str
    tags: list
    pinned: bool
    source: str
    created_at: datetime
    updated_at: datetime


class NoteListOut(BaseModel):
    items: list[NoteOut]
    next_cursor: str | None
