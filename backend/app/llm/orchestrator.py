"""
Tool-call orchestrator for JARVIS chat.

Flow per request:
  1. Route message (classify intent → choose model + tool subset)
  2. Call LLM with system prompt + history + tools
  3. If response has tool_calls → execute → feed results → loop (max 5 total calls)
  4. Return final LLMResponse + metadata

Safety limits (per rules/04_ai_llm.md):
  - Hard cap: 5 tool calls per turn
  - Per-tool retry: max 2 retries when executor returns success=False
  - Loop detection: same tool called 3x in a row → abort
"""

import time
import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import chat_completion
from app.llm.models import LLMResponse, ToolCall
from app.llm.router import RouteResult, route
from app.repositories import tool_log_repo
from app.tools.executors import dispatch

log = structlog.get_logger()

_MAX_TOOL_CALLS = 5
_MAX_RETRIES_PER_TOOL = 2


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

    Returns:
        OrchestratorResult with final response and metadata.
    """
    # ── Stage 0+1: Route ────────────────────────────────────────────────────────
    route_result = await route(user_message, all_tools)

    # ── Build initial message list ──────────────────────────────────────────────
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    tools_to_send = route_result.effective_tools or None

    total_tokens_in = 0
    total_tokens_out = 0
    total_llm_calls = 0
    tool_results: list[dict] = []
    tool_call_count = 0

    # Track last 3 tool names for loop detection
    recent_tool_names: list[str] = []
    # Track per-tool retry count
    retry_counts: dict[str, int] = {}

    llm_response: LLMResponse | None = None

    while True:
        total_llm_calls += 1
        llm_response = await chat_completion(
            messages=messages,
            model=route_result.model,
            tools=tools_to_send,
        )
        total_tokens_in += llm_response.tokens_in
        total_tokens_out += llm_response.tokens_out

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

            # Execute with retry
            result = await _execute_with_retry(db, user_id, tc, message_id, retry_counts)
            tool_results.append({"tool": tc.name, "result": result})
            messages.append(_tool_result_msg(tc, result))

        # Check if we broke out of the inner loop due to loop detection
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


async def _execute_with_retry(
    db: AsyncSession,
    user_id: uuid.UUID,
    tc: ToolCall,
    message_id: uuid.UUID | None,
    retry_counts: dict[str, int],
) -> dict:
    """Execute a tool call, retrying up to _MAX_RETRIES_PER_TOOL times on failure."""
    retries = retry_counts.get(tc.name, 0)

    t0 = time.monotonic()
    result = await dispatch(tc.name, tc.arguments, db, user_id)
    duration_ms = int((time.monotonic() - t0) * 1000)

    success = result.get("success", False)
    status = "success" if success else "failed"

    await tool_log_repo.log_execution(
        db,
        user_id=user_id,
        tool_name=tc.name,
        input=tc.arguments,
        output=result,
        status=status,
        duration_ms=duration_ms,
        message_id=message_id,
        error_message=result.get("error", {}).get("message") if not success else None,
    )

    if not success and retries < _MAX_RETRIES_PER_TOOL:
        retry_counts[tc.name] = retries + 1
        log.warning(
            "orchestrator.tool_retry",
            tool=tc.name,
            retry=retries + 1,
            error=result.get("error"),
        )
        # Re-execute on retry
        t0 = time.monotonic()
        result = await dispatch(tc.name, tc.arguments, db, user_id)
        duration_ms = int((time.monotonic() - t0) * 1000)
        success = result.get("success", False)
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
