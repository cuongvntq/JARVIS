"""Conversation and Message repository — DB queries only."""

import base64
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.models.conversation import Conversation, Message


async def get_or_create(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
) -> Conversation:
    if conversation_id is None:
        conv = Conversation(user_id=user_id)
        db.add(conv)
        await db.flush()
        await db.refresh(conv)
        return conv

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.deleted_at.is_(None),
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise JarvisError(404, "conversation_not_found", "Cuộc hội thoại không tồn tại")
    if conv.user_id != user_id:
        raise JarvisError(403, "forbidden", "Không có quyền truy cập cuộc hội thoại này")
    return conv


async def add_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    content: str,
    tokens_in: int,
    tokens_out: int,
    metadata: dict,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role=role,
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        metadata_=metadata,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def increment_message_count(db: AsyncSession, conversation_id: uuid.UUID) -> None:
    await db.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            message_count=Conversation.message_count + 1,
            last_message_at=datetime.now(UTC),
        )
    )


async def list_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int,
    cursor: str | None,
) -> tuple[list[Conversation], str | None]:
    query = select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.deleted_at.is_(None),
    )

    if cursor:
        try:
            cursor_dt_str = base64.b64decode(cursor).decode()
            cursor_dt = datetime.fromisoformat(cursor_dt_str)
            query = query.where(Conversation.last_message_at < cursor_dt)
        except Exception:
            pass  # invalid cursor → ignore, return from start

    query = query.order_by(Conversation.last_message_at.desc().nullslast()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last_dt = rows[-1].last_message_at
        if last_dt:
            next_cursor = base64.b64encode(last_dt.isoformat().encode()).decode()

    return rows, next_cursor
