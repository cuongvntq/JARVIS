"""Chat endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.schemas.chat import (
    ChatSendRequest,
    ChatSendResponse,
    ConversationDetailOut,
    ConversationListResponse,
    ConversationPatchRequest,
)
from app.services import chat_service

router = APIRouter()


@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    req: ChatSendRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.send_message(db, req, current_user)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.list_conversations(db, current_user.id, limit, cursor)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    before: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.get_conversation_detail(
        db, conversation_id, current_user.id, before, limit
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def update_conversation(
    conversation_id: uuid.UUID,
    data: ConversationPatchRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.update_conversation_title(
        db, conversation_id, current_user.id, data
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await chat_service.delete_conversation(db, conversation_id, current_user.id)
    return Response(status_code=204)
