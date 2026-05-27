"""Chat endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.schemas.chat import ChatSendRequest, ChatSendResponse, ConversationListResponse
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
