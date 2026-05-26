"""Chat business logic — orchestrates LLM + DB persistence."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import JarvisError
from app.llm.client import chat_completion
from app.models.user import User
from app.repositories import conversation_repo
from app.schemas.chat import ChatSendRequest, ChatSendResponse, ConversationListResponse, MessageOut

log = structlog.get_logger()
settings = get_settings()

_SYSTEM_PROMPT_TEMPLATE = (
    "Bạn là {assistant_name}, trợ lý cá nhân AI của người dùng.\n"
    "Luôn giao tiếp bằng tiếng Việt tự nhiên, thân thiện, ngắn gọn (1-3 câu trừ khi cần giải thích dài).\n"
    "Hôm nay là {now_local}. Múi giờ: {timezone}."
)


async def send_message(
    db: AsyncSession,
    req: ChatSendRequest,
    current_user: User,
) -> ChatSendResponse:
    if req.stream:
        raise JarvisError(422, "stream_not_supported", "Streaming sẽ được hỗ trợ ở Sprint 2")

    conv = await conversation_repo.get_or_create(db, current_user.id, req.conversation_id)

    user_msg = await conversation_repo.add_message(
        db, conv.id, current_user.id, "user", req.content, 0, 0, {}
    )
    await db.flush()

    try:
        user_tz = ZoneInfo(current_user.timezone)
    except ZoneInfoNotFoundError:
        user_tz = ZoneInfo(settings.timezone_default)
    now_local = datetime.now(user_tz).strftime("%H:%M %d/%m/%Y")
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        assistant_name=current_user.assistant_name,
        now_local=now_local,
        timezone=current_user.timezone,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.content},
    ]

    try:
        content, model_name, tokens_in, tokens_out = await chat_completion(messages)
    except RuntimeError as e:
        log.error("chat.llm_error", error=str(e), user_id=str(current_user.id))
        raise JarvisError(502, "llm_error", "Dịch vụ AI tạm thời không khả dụng, vui lòng thử lại")

    assistant_msg = await conversation_repo.add_message(
        db, conv.id, current_user.id, "assistant", content,
        tokens_in, tokens_out, {"model": model_name},
    )

    await conversation_repo.increment_message_count(db, conv.id)
    await conversation_repo.increment_message_count(db, conv.id)

    log.info("chat.sent", conversation_id=str(conv.id), tokens_in=tokens_in, tokens_out=tokens_out)

    return ChatSendResponse(
        conversation_id=conv.id,
        user_message=MessageOut.model_validate(user_msg),
        assistant_message=MessageOut.model_validate(assistant_msg),
    )


async def list_conversations(
    db: AsyncSession,
    user_id,
    limit: int,
    cursor: str | None,
) -> ConversationListResponse:
    from app.schemas.chat import ConversationOut

    items, next_cursor = await conversation_repo.list_conversations(db, user_id, limit, cursor)
    return ConversationListResponse(
        items=[ConversationOut.model_validate(c) for c in items],
        next_cursor=next_cursor,
    )
