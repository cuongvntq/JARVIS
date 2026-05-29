"""Chat business logic — orchestrates LLM + DB persistence."""

import uuid
from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.llm import orchestrator
from app.llm.prompt import build_system_prompt
from app.models.user import User
from app.repositories import conversation_repo
from app.schemas.chat import (
    ChatSendRequest,
    ChatSendResponse,
    ConversationDetailOut,
    ConversationListResponse,
    ConversationOut,
    ConversationPatchRequest,
    MessageOut,
)
from app.tools.definitions import TOOLS

log = structlog.get_logger()


async def stream_message(
    db: AsyncSession,
    req: ChatSendRequest,
    current_user: User,
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE event dicts for streaming chat."""
    conv = await conversation_repo.get_or_create(db, current_user.id, req.conversation_id)

    prior_msgs, _ = await conversation_repo.get_messages_page(db, conv.id, None, 20)
    history = [{"role": m.role, "content": m.content} for m in prior_msgs]

    user_msg = await conversation_repo.add_message(
        db, conv.id, current_user.id, "user", req.content, 0, 0, {}
    )
    await db.flush()

    if not prior_msgs:
        auto_title = req.content.strip()[:50]
        await conversation_repo.update_title(db, conv.id, auto_title)

    yield {"type": "meta", "conversation_id": str(conv.id), "user_message_id": str(user_msg.id)}

    system_prompt, prompt_version = build_system_prompt(current_user)

    orch_done: dict | None = None

    try:
        async for event in orchestrator.run_stream(
            db=db,
            user_id=current_user.id,
            user_message=req.content,
            system_prompt=system_prompt,
            history=history,
            message_id=user_msg.id,
            all_tools=TOOLS,
            user_tz=current_user.timezone,
        ):
            if event["type"] == "orchestrator_done":
                orch_done = event
            else:
                yield event
    except RuntimeError as e:
        log.error("chat.stream.llm_error", error=str(e), user_id=str(current_user.id))
        yield {"type": "error", "code": "llm_error", "message": "Dịch vụ AI tạm thời không khả dụng, vui lòng thử lại"}
        return

    if orch_done is None:
        yield {"type": "error", "code": "internal_error", "message": "Lỗi nội bộ"}
        return

    assistant_msg = await conversation_repo.add_message(
        db,
        conv.id,
        current_user.id,
        "assistant",
        orch_done["content"],
        orch_done["total_tokens_in"],
        orch_done["total_tokens_out"],
        {
            "model": orch_done["model"],
            "intent": orch_done["route"].intent.value,
            "llm_calls": orch_done["total_llm_calls"],
            "prompt_version": prompt_version,
        },
    )

    await conversation_repo.increment_message_count(db, conv.id)
    await conversation_repo.increment_message_count(db, conv.id)
    await db.commit()

    log.info(
        "chat.stream.sent",
        conversation_id=str(conv.id),
        intent=orch_done["route"].intent.value,
        model=orch_done["model"],
        tokens_in=orch_done["total_tokens_in"],
        tokens_out=orch_done["total_tokens_out"],
        tool_calls=len(orch_done["tool_results"]),
    )

    yield {
        "type": "done",
        "assistant_message_id": str(assistant_msg.id),
        "tokens_in": orch_done["total_tokens_in"],
        "tokens_out": orch_done["total_tokens_out"],
        "model": orch_done["model"],
    }


async def send_message(
    db: AsyncSession,
    req: ChatSendRequest,
    current_user: User,
) -> ChatSendResponse:

    conv = await conversation_repo.get_or_create(db, current_user.id, req.conversation_id)

    # Fetch prior history BEFORE inserting the current user message
    prior_msgs, _ = await conversation_repo.get_messages_page(db, conv.id, None, 20)
    history = [{"role": m.role, "content": m.content} for m in prior_msgs]

    user_msg = await conversation_repo.add_message(
        db, conv.id, current_user.id, "user", req.content, 0, 0, {}
    )
    await db.flush()

    # Auto-title on first message (prior_msgs empty means this is message #1)
    if not prior_msgs:
        auto_title = req.content.strip()[:50]
        await conversation_repo.update_title(db, conv.id, auto_title)

    system_prompt, prompt_version = build_system_prompt(current_user)

    try:
        orch_result = await orchestrator.run(
            db=db,
            user_id=current_user.id,
            user_message=req.content,
            system_prompt=system_prompt,
            history=history,
            message_id=user_msg.id,
            all_tools=TOOLS,
            user_tz=current_user.timezone,
        )
    except RuntimeError as e:
        log.error("chat.llm_error", error=str(e), user_id=str(current_user.id))
        raise JarvisError(
            502, "llm_error", "Dịch vụ AI tạm thời không khả dụng, vui lòng thử lại"
        ) from e

    content = orch_result.final_response.content
    assistant_msg = await conversation_repo.add_message(
        db,
        conv.id,
        current_user.id,
        "assistant",
        content,
        orch_result.total_tokens_in,
        orch_result.total_tokens_out,
        {
            "model": orch_result.final_response.model,
            "intent": orch_result.route.intent.value,
            "llm_calls": orch_result.total_llm_calls,
            "prompt_version": prompt_version,
        },
    )

    await conversation_repo.increment_message_count(db, conv.id)
    await conversation_repo.increment_message_count(db, conv.id)

    log.info(
        "chat.sent",
        conversation_id=str(conv.id),
        intent=orch_result.route.intent.value,
        model=orch_result.final_response.model,
        tokens_in=orch_result.total_tokens_in,
        tokens_out=orch_result.total_tokens_out,
        tool_calls=len(orch_result.tool_results),
    )

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
    items, next_cursor = await conversation_repo.list_conversations(db, user_id, limit, cursor)
    return ConversationListResponse(
        items=[ConversationOut.model_validate(c) for c in items],
        next_cursor=next_cursor,
    )


async def get_conversation_detail(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    before_message_id: uuid.UUID | None,
    limit: int,
) -> ConversationDetailOut:
    conv = await conversation_repo.get_conversation(db, conversation_id, user_id)
    if conv is None:
        raise JarvisError(404, "conversation_not_found", "Cuộc hội thoại không tồn tại")

    messages, has_more = await conversation_repo.get_messages_page(
        db, conversation_id, before_message_id, limit
    )
    return ConversationDetailOut(
        id=conv.id,
        title=conv.title,
        last_message_at=conv.last_message_at,
        message_count=conv.message_count,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in messages],
        has_more=has_more,
    )


async def update_conversation_title(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ConversationPatchRequest,
) -> ConversationDetailOut:
    conv = await conversation_repo.get_conversation(db, conversation_id, user_id)
    if conv is None:
        raise JarvisError(404, "conversation_not_found", "Cuộc hội thoại không tồn tại")

    await conversation_repo.update_title(db, conversation_id, data.title)
    await db.commit()
    return await get_conversation_detail(db, conversation_id, user_id, None, 50)


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    conv = await conversation_repo.get_conversation(db, conversation_id, user_id)
    if conv is None:
        raise JarvisError(404, "conversation_not_found", "Cuộc hội thoại không tồn tại")

    await conversation_repo.soft_delete_conversation(db, conversation_id)
    await db.commit()
