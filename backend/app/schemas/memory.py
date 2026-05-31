"""Memory request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal["fact", "preference", "rule", "relation", "goal", "other"]


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    memory_type: MemoryType = "fact"
    importance: int = Field(default=5, ge=1, le=10)


class MemoryUpdate(BaseModel):
    """REST PATCH /memories/{id} — all fields optional."""

    content: str | None = Field(default=None, min_length=1, max_length=2000)
    memory_type: MemoryType | None = None
    importance: int | None = Field(default=None, ge=1, le=10)
    is_active: bool | None = None


class MemoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    memory_type: str
    content: str
    importance: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MemoryListOut(BaseModel):
    items: list[MemoryOut]
    next_cursor: str | None


class MemorySearchOut(BaseModel):
    items: list[MemoryOut]
    count: int


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)
