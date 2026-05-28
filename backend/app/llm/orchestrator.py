"""
Tool-call orchestrator for JARVIS chat.

Flow per request:
  1. Route message (classify intent → choose model + tool subset)
  2. Call LLM with system prompt + history + tools
  3. If response has tool_calls → execute → feed results → loop (max 5 total calls)
  4. Return final LLMResponse + metadata

Safety limits (per rules/04_ai_llm.md):
  - Hard cap: 5 tool calls per turn
  - Loop detection: same tool called 3x in a row → abort
  - Per-tool retry: handled naturally by LLM seeing failure result in context
"""

import time
import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm.client import chat_completion
from app.llm.models import LLMResponse, ToolCall
from app.llm.router import RouteResult, route
from app.repositories import llm_call_log_repo, tool_log_repo
from app.tools.executors import dispatch

log = structlog.get_logger()
settings = get_settings()

_MAX_TOOL_CALLS = 5


@dataclass
class OrchestratorResult:
    final_response: LLMResponse
    route: RouteResult
    tool_results: list[dict] = field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_llm_calls: int = 0


async def run(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    user_message: str,
    system_prompt: str,
    history: list[dict],
    message_id: uuid.UUID | None = None,
    all_tools: list[dict],
    user_tz: str = "UTC",
) -> OrchestratorResult:
    """
    Full orchestration loop: route → LLM → [tool → LLM]* → final response.

    Args:
        db:            Active async session (caller owns commit).
        user_id:       Current user UUID (for tool auth + logging).
        user_message:  Raw user message text.
        system_prompt: Rendered system prompt string.
        history:       Prior messages in OpenAI format (role/content dicts).
        message_id:    DB message_id for tool log FK (may be None before flush).
        all_tools:     Full list of available tool schemas.
        user_tz:       User's IANA timezone string for date-sensitive tool filters.

    Returns:
        OrchestratorResult with final response and metadata.
    """
    # ── Stage 0+1: Route ────────────────────────────────────────────────────────
    route_result = await route(user_message, all_tools)

    # Log classifier LLM call when it actually hit the API
    if route_result.classify_source == "classifier" and route_result.classifier_tokens_in > 0:
        try:
            await llm_call_log_repo.log_call(
                db,
                user_id=user_id,
                message_id=message_id,
                intent=route_result.intent.value,
                classify_source="classifier",
                model_used=route_result.classifier_model,
                tokens_in=route_result.classifier_tokens_in,
                tokens_out=route_result.classifier_tokens_out,
                duration_ms=route_result.classifier_duration_ms,
                success=True,
            )
        except Exception:
            log.warning("orchestrator.classifier_log_failed")

    # ── Build initial message list ──────────────────────────────────────────────
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    tools_to_send = route_result.effective_tools or None

    # Pass None for primary model to enable the primary→fallback chain in client.py.
    # When routing to fallback model directly (tool_call, etc.), pin it — no tertiary.
    call_model = None if route_result.model == settings.llm_primary else route_result.model

    total_tokens_in = 0
    total_tokens_out = 0
    total_llm_calls = 0
    tool_results: list[dict] = []
    tool_call_count = 0

    # Track last 3 tool names for loop detection
    recent_tool_names: list[str] = []

    llm_response: LLMResponse | None = None

    while True:
        total_llm_calls += 1
        t0 = time.monotonic()
        try:
            llm_response = await chat_completion(
                messages=messages,
                model=call_model,
                tools=tools_to_send,
            )
            call_duration_ms = int((time.monotonic() - t0) * 1000)
            total_tokens_in += llm_response.tokens_in
            total_tokens_out += llm_response.tokens_out

            # Log each individual LLM call (classifier logged separately above)
            try:
                await llm_call_log_repo.log_call(
                    db,
                    user_id=user_id,
                    message_id=message_id,
                    intent=route_result.intent.value,
                    classify_source="orchestrator",
                    model_used=llm_response.model,
                    tokens_in=llm_response.tokens_in,
                    tokens_out=llm_response.tokens_out,
                    duration_ms=call_duration_ms,
                    success=True,
                )
            except Exception:
                log.warning("orchestrator.llm_log_failed")

        except RuntimeError:
            call_duration_ms = int((time.monotonic() - t0) * 1000)
            try:
                await llm_call_log_repo.log_call(
                    db,
                    user_id=user_id,
                    message_id=message_id,
                    intent=route_result.intent.value,
                    classify_source="orchestrator",
                    model_used=route_result.model,
                    tokens_in=0,
                    tokens_out=0,
                    duration_ms=call_duration_ms,
                    success=False,
                    error_code="llm_error",
                )
            except Exception:
                log.warning("orchestrator.llm_log_failed")
            raise

        if not llm_response.has_tool_calls:
            # Terminal: plain text response
            break

        # ── Execute tool calls ──────────────────────────────────────────────────
        # Add assistant message with tool_calls to history
        assistant_msg: dict = {"role": "assistant", "content": llm_response.content}
        if llm_response.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": _dumps(tc.arguments)},
                }
                for tc in llm_response.tool_calls
            ]
        messages.append(assistant_msg)

        for tc in llm_response.tool_calls:
            # Hard cap checked per-execution so a batch of >5 tools never all run
            if tool_call_count >= _MAX_TOOL_CALLS:
                log.warning(
                    "orchestrator.tool_cap_exceeded",
                    user_id=str(user_id),
                    tool_call_count=tool_call_count,
                )
                llm_response = LLMResponse(
                    content="Xin lỗi, tôi đã thực hiện quá nhiều hành động trong lượt này. Bạn hãy thử chia nhỏ yêu cầu.",
                    model=llm_response.model,
                    tokens_in=0,
                    tokens_out=0,
                )
                tool_call_count = _MAX_TOOL_CALLS + 1
                break

            tool_call_count += 1

            # Loop detection: same tool 3x in a row
            recent_tool_names.append(tc.name)
            if len(recent_tool_names) > 3:
                recent_tool_names.pop(0)
            if len(recent_tool_names) == 3 and len(set(recent_tool_names)) == 1:
                log.warning(
                    "orchestrator.loop_detected",
                    tool=tc.name,
                    user_id=str(user_id),
                )
                messages.append(
                    _tool_result_msg(
                        tc,
                        {
                            "success": False,
                            "error": {
                                "code": "loop_detected",
                                "message": "Phát hiện vòng lặp tool.",
                            },
                            "data": None,
                        },
                    )
                )
                llm_response = LLMResponse(
                    content="Có vẻ tôi đang bị lặp. Bạn có thể nói rõ hơn yêu cầu không?",
                    model=llm_response.model,
                    tokens_in=0,
                    tokens_out=0,
                )
                # Signal outer while to break
                tool_call_count = _MAX_TOOL_CALLS + 1
                break

            # Execute tool — DB errors propagate as RuntimeError to abort the turn
            result = await _execute_tool(db, user_id, tc, message_id, user_tz)
            tool_results.append({"tool": tc.name, "result": result})
            messages.append(_tool_result_msg(tc, result))

        # Check if we broke out of the inner loop due to cap / loop detection
        if tool_call_count > _MAX_TOOL_CALLS:
            break

        # Continue loop — LLM will synthesize based on tool results

    assert llm_response is not None
    return OrchestratorResult(
        final_response=llm_response,
        route=route_result,
        tool_results=tool_results,
        total_tokens_in=total_tokens_in,
        total_tokens_out=total_tokens_out,
        total_llm_calls=total_llm_calls,
    )


async def _execute_tool(
    db: AsyncSession,
    user_id: uuid.UUID,
    tc: ToolCall,
    message_id: uuid.UUID | None,
    user_tz: str = "UTC",
) -> dict:
    """Execute a tool call and log the result.

    SQLAlchemy errors propagate from dispatch() and are re-raised as RuntimeError
    so the outer session is not left in a dirty state for subsequent logging.
    """
    t0 = time.monotonic()

    try:
        result = await dispatch(tc.name, tc.arguments, db, user_id, user_tz)
    except SQLAlchemyError as e:
        # DB error escaped the executor — session may be dirty; abort the turn
        # so we never attempt further DB writes on a broken session.
        log.exception("orchestrator.tool_db_error", tool=tc.name)
        raise RuntimeError(f"DB error in tool '{tc.name}': {e}") from e

    duration_ms = int((time.monotonic() - t0) * 1000)
    success = result.get("success", False)

    try:
        await tool_log_repo.log_execution(
            db,
            user_id=user_id,
            tool_name=tc.name,
            input=tc.arguments,
            output=result,
            status="success" if success else "failed",
            duration_ms=duration_ms,
            message_id=message_id,
            error_message=result.get("error", {}).get("message") if not success else None,
        )
    except Exception as log_exc:
        log.warning("orchestrator.tool_log_failed", error=str(log_exc))

    return result


def _tool_result_msg(tc: ToolCall, result: dict) -> dict:
    """Build the tool-result message to feed back to the LLM."""
    import json as _json

    return {
        "role": "tool",
        "tool_call_id": tc.id,
        "content": _json.dumps(result, ensure_ascii=False, default=str),
    }


def _dumps(obj: dict) -> str:
    import json as _json

    return _json.dumps(obj, ensure_ascii=False)
