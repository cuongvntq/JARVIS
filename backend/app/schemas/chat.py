"""Chat request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatSendRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    content: str = Field(min_length=1, max_length=4000)
    stream: bool = False


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    tokens_in: int = 0
    tokens_out: int = 0
    created_at: datetime


class ChatSendResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message: MessageOut
    assistant_message: MessageOut


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    last_message_at: datetime | None
    message_count: int
    created_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationOut]
    next_cursor: str | None
