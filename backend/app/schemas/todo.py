"""Todo request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    due_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="ui", pattern="^(ui|chat)$")


class TodoReplace(BaseModel):
    """Used for PUT /todos/{id} — full replacement (title required)."""

    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    due_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class TodoPartialUpdate(BaseModel):
    """Internal only — used by tool executor for partial update. NOT exposed via REST."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")
    status: str | None = Field(default=None, pattern="^(pending|in_progress|completed|cancelled)$")
    due_at: datetime | None = None
    tags: list[str] | None = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: str
    due_at: datetime | None
    completed_at: datetime | None
    tags: list[str]
    source: str
    created_at: datetime
    updated_at: datetime


class TodoListOut(BaseModel):
    items: list[TodoOut]
    next_cursor: str | None
