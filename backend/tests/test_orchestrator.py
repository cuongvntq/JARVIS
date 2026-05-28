"""Tests for LLM orchestrator and router (Sprint 2 PR C)."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.models import LLMResponse, ToolCall
from app.llm.router import Intent, RouteResult, _pre_filter, route

# ─── Pre-filter unit tests ─────────────────────────────────────────────────────


class TestPreFilter:
    def test_greeting_vi(self):
        assert _pre_filter("Xin chào") == Intent.CHITCHAT

    def test_thanks_vi(self):
        assert _pre_filter("Cảm ơn") == Intent.CHITCHAT

    def test_ok_vi(self):
        assert _pre_filter("ok") == Intent.CHITCHAT

    def test_vang_vi(self):
        assert _pre_filter("vâng") == Intent.CHITCHAT

    def test_too_short(self):
        assert _pre_filter("a") == Intent.CHITCHAT

    def test_create_todo_intent(self):
        assert _pre_filter("Thêm việc mua sữa chiều nay") == Intent.TOOL_CALL

    def test_done_intent(self):
        assert _pre_filter("Đã xong việc gọi mẹ rồi") == Intent.TOOL_CALL

    def test_create_remind_intent(self):
        assert _pre_filter("Nhắc tôi uống thuốc") == Intent.TOOL_CALL

    def test_remember_intent(self):
        assert _pre_filter("Nhớ là tôi dị ứng tôm") == Intent.TOOL_CALL

    def test_simple_query_intent(self):
        assert _pre_filter("Tôi còn việc gì hôm nay") == Intent.SIMPLE_QUERY

    def test_unknown_returns_none(self):
        assert _pre_filter("AI là gì vậy bạn?") is None

    def test_unknown_question_returns_none(self):
        assert _pre_filter("Hôm nay thời tiết thế nào?") is None


# ─── Router tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_route_prefilter_chitchat_empty_tools():
    result = await route("Xin chào", [])
    assert result.intent == Intent.CHITCHAT
    assert result.classify_source == "prefilter"
    assert result.effective_tools == []


@pytest.mark.asyncio
async def test_route_prefilter_tool_call_passes_all_tools():
    fake_tools = [{"type": "function", "function": {"name": "create_todo"}}]
    result = await route("Thêm việc mua sữa", fake_tools)
    assert result.intent == Intent.TOOL_CALL
    assert result.effective_tools == fake_tools


@pytest.mark.asyncio
async def test_route_classifier_called_for_unknown():
    mock_resp = MagicMock()
    mock_resp.choices[
        0
    ].message.content = '{"intent": "tool_call", "confidence": 0.9, "reason": "create action"}'
    # Message that does NOT match pre-filter (no leading action keywords)
    with patch(
        "app.llm.router.litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp
    ):
        result = await route("Bỏ deadline của việc mua sữa đi", [])

    assert result.intent == Intent.TOOL_CALL
    assert result.classify_source == "classifier"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_route_classifier_failure_defaults_to_tool_call():
    with patch("app.llm.router.litellm.acompletion", side_effect=RuntimeError("network error")):
        result = await route("Câu gì đó mơ hồ", [])
    assert result.intent == Intent.TOOL_CALL
    assert result.classify_source == "fallback"


@pytest.mark.asyncio
async def test_route_simple_query_filters_write_tools():
    all_tools = [
        {"type": "function", "function": {"name": "list_todos"}},
        {"type": "function", "function": {"name": "create_todo"}},
        {"type": "function", "function": {"name": "search_memory"}},
    ]
    mock_resp = MagicMock()
    mock_resp.choices[
        0
    ].message.content = '{"intent": "simple_query", "confidence": 0.85, "reason": "list query"}'
    with patch(
        "app.llm.router.litellm.acompletion", new_callable=AsyncMock, return_value=mock_resp
    ):
        result = await route("Tôi còn bao nhiêu việc?", all_tools)

    names = {t["function"]["name"] for t in result.effective_tools}
    assert "list_todos" in names
    assert "search_memory" in names
    assert "create_todo" not in names  # write tool excluded


@pytest.mark.asyncio
async def test_route_chitchat_has_no_tools():
    all_tools = [{"type": "function", "function": {"name": "create_todo"}}]
    result = await route("Cảm ơn bạn nhiều lắm", all_tools)
    assert result.intent == Intent.CHITCHAT
    assert result.effective_tools == []


# ─── Orchestrator tests ────────────────────────────────────────────────────────


def _make_route_result(intent: Intent = Intent.CHITCHAT, tools: list | None = None) -> RouteResult:
    from app.llm.router import MODEL_MAP

    return RouteResult(
        intent=intent,
        model=MODEL_MAP[intent],
        confidence=1.0,
        classify_source="prefilter",
        effective_tools=tools or [],
    )


@pytest.mark.asyncio
async def test_orchestrator_plain_text_no_tool_calls():
    """No tool calls → single LLM call, return response directly."""
    from app.llm import orchestrator

    llm_resp = LLMResponse(content="Xin chào!", model="gemini-mock", tokens_in=10, tokens_out=5)
    db = AsyncMock()

    with (
        patch(
            "app.llm.orchestrator.route", new_callable=AsyncMock, return_value=_make_route_result()
        ),
        patch(
            "app.llm.orchestrator.chat_completion", new_callable=AsyncMock, return_value=llm_resp
        ),
        patch("app.llm.orchestrator.llm_call_log_repo.log_call", new_callable=AsyncMock),
    ):
        result = await orchestrator.run(
            db=db,
            user_id=uuid.uuid4(),
            user_message="Xin chào",
            system_prompt="You are JARVIS.",
            history=[],
            all_tools=[],
        )

    assert result.final_response.content == "Xin chào!"
    assert result.tool_results == []
    assert result.total_llm_calls == 1
    assert result.total_tokens_in == 10
    assert result.total_tokens_out == 5


@pytest.mark.asyncio
async def test_orchestrator_single_tool_call_then_synthesis():
    """LLM makes one tool call → execute → LLM synthesizes final answer."""
    from app.llm import orchestrator

    tc = ToolCall(id="call_1", name="create_todo", arguments={"title": "mua sữa"})
    first_resp = LLMResponse(
        content="", model="gpt-4o-mini", tokens_in=50, tokens_out=30, tool_calls=[tc]
    )
    second_resp = LLMResponse(
        content="Đã thêm việc mua sữa!", model="gpt-4o-mini", tokens_in=80, tokens_out=15
    )
    tool_result = {
        "success": True,
        "data": {"id": str(uuid.uuid4()), "title": "mua sữa"},
        "summary": "Đã thêm việc 'mua sữa'.",
        "warnings": [],
    }
    db = AsyncMock()

    with (
        patch(
            "app.llm.orchestrator.route",
            new_callable=AsyncMock,
            return_value=_make_route_result(Intent.TOOL_CALL),
        ),
        patch(
            "app.llm.orchestrator.chat_completion",
            new_callable=AsyncMock,
            side_effect=[first_resp, second_resp],
        ),
        patch("app.llm.orchestrator.dispatch", new_callable=AsyncMock, return_value=tool_result),
        patch("app.llm.orchestrator.tool_log_repo.log_execution", new_callable=AsyncMock),
        patch("app.llm.orchestrator.llm_call_log_repo.log_call", new_callable=AsyncMock),
    ):
        result = await orchestrator.run(
            db=db,
            user_id=uuid.uuid4(),
            user_message="Thêm việc mua sữa",
            system_prompt="You are JARVIS.",
            history=[],
            all_tools=[{"type": "function", "function": {"name": "create_todo"}}],
        )

    assert result.final_response.content == "Đã thêm việc mua sữa!"
    assert len(result.tool_results) == 1
    assert result.tool_results[0]["tool"] == "create_todo"
    assert result.total_llm_calls == 2


@pytest.mark.asyncio
async def test_orchestrator_hard_cap_5_tool_calls():
    """After 5 tool calls, orchestrator stops with friendly error."""
    from app.llm import orchestrator

    # Alternate 2 tools to avoid triggering loop detection (needs 3 same in a row)
    tc_a = ToolCall(id="call_a", name="list_todos", arguments={})
    tc_b = ToolCall(id="call_b", name="create_todo", arguments={"title": "x"})
    tool_call_responses = [
        LLMResponse(
            content="",
            model="gpt-4o-mini",
            tokens_in=50,
            tokens_out=10,
            tool_calls=[tc_a if i % 2 == 0 else tc_b],
        )
        for i in range(7)  # far more than the cap — only 6 consumed
    ]
    tool_result = {"success": True, "data": {}, "summary": "OK", "warnings": []}
    db = AsyncMock()

    with (
        patch(
            "app.llm.orchestrator.route",
            new_callable=AsyncMock,
            return_value=_make_route_result(Intent.TOOL_CALL),
        ),
        patch(
            "app.llm.orchestrator.chat_completion",
            new_callable=AsyncMock,
            side_effect=tool_call_responses,
        ),
        patch("app.llm.orchestrator.dispatch", new_callable=AsyncMock, return_value=tool_result),
        patch("app.llm.orchestrator.tool_log_repo.log_execution", new_callable=AsyncMock),
        patch("app.llm.orchestrator.llm_call_log_repo.log_call", new_callable=AsyncMock),
    ):
        result = await orchestrator.run(
            db=db,
            user_id=uuid.uuid4(),
            user_message="Làm thật nhiều việc",
            system_prompt="You are JARVIS.",
            history=[],
            all_tools=[],
        )

    assert len(result.tool_results) == 5  # exactly 5 tool calls executed
    assert (
        "quá nhiều" in result.final_response.content or "thử lại" in result.final_response.content
    )


@pytest.mark.asyncio
async def test_orchestrator_loop_detection_3_consecutive_same_tool():
    """Same tool 3x in a row triggers loop detection before 5-cap."""
    from app.llm import orchestrator

    tc = ToolCall(id="call_loop", name="list_todos", arguments={})
    tool_resp = LLMResponse(
        content="", model="gpt-4o-mini", tokens_in=50, tokens_out=10, tool_calls=[tc]
    )
    tool_result = {"success": True, "data": {}, "summary": "OK", "warnings": []}
    db = AsyncMock()
    mock_dispatch = AsyncMock(return_value=tool_result)
    mock_log = AsyncMock()

    with (
        patch(
            "app.llm.orchestrator.route",
            new_callable=AsyncMock,
            return_value=_make_route_result(Intent.TOOL_CALL),
        ),
        patch(
            "app.llm.orchestrator.chat_completion", new_callable=AsyncMock, return_value=tool_resp
        ),
        patch("app.llm.orchestrator.dispatch", mock_dispatch),
        patch("app.llm.orchestrator.tool_log_repo.log_execution", mock_log),
        patch("app.llm.orchestrator.llm_call_log_repo.log_call", new_callable=AsyncMock),
    ):
        result = await orchestrator.run(
            db=db,
            user_id=uuid.uuid4(),
            user_message="Làm gì đó",
            system_prompt="You are JARVIS.",
            history=[],
            all_tools=[],
        )

    # Loop detected at 3rd call → only 2 executions happen
    assert mock_dispatch.call_count == 2
    assert "lặp" in result.final_response.content or "rõ hơn" in result.final_response.content


@pytest.mark.asyncio
async def test_orchestrator_tool_failure_fed_back_to_model():
    """Failed tool result is returned to LLM; model synthesizes final answer without retry."""
    from app.llm import orchestrator

    tc = ToolCall(id="call_retry", name="create_todo", arguments={"title": "x"})
    llm_first = LLMResponse(
        content="", model="gpt-4o-mini", tokens_in=50, tokens_out=10, tool_calls=[tc]
    )
    llm_final = LLMResponse(
        content="Xin lỗi, có lỗi xảy ra.", model="gpt-4o-mini", tokens_in=80, tokens_out=15
    )
    fail_result = {
        "success": False,
        "error": {"code": "db_error", "message": "DB error"},
        "data": None,
    }
    db = AsyncMock()

    with (
        patch(
            "app.llm.orchestrator.route",
            new_callable=AsyncMock,
            return_value=_make_route_result(Intent.TOOL_CALL),
        ),
        patch(
            "app.llm.orchestrator.chat_completion",
            new_callable=AsyncMock,
            side_effect=[llm_first, llm_final],
        ),
        patch("app.llm.orchestrator.dispatch", new_callable=AsyncMock, return_value=fail_result),
        patch(
            "app.llm.orchestrator.tool_log_repo.log_execution", new_callable=AsyncMock
        ) as mock_log,
        patch("app.llm.orchestrator.llm_call_log_repo.log_call", new_callable=AsyncMock),
    ):
        result = await orchestrator.run(
            db=db,
            user_id=uuid.uuid4(),
            user_message="Thêm việc",
            system_prompt="You are JARVIS.",
            history=[],
            all_tools=[{"type": "function", "function": {"name": "create_todo"}}],
        )

    # dispatch called once — failure is fed back to LLM which synthesizes the final response
    assert mock_log.call_count == 1
    assert result.final_response.content == "Xin lỗi, có lỗi xảy ra."


# ─── LLMCallLogRepo cost calculation ─────────────────────────────────────────


def test_calc_cost_free_model():
    from app.repositories.llm_call_log_repo import _calc_cost

    assert _calc_cost("gemini/gemini-2.5-flash", 1_000_000, 1_000_000) == Decimal("0.000000")


def test_calc_cost_gpt4o_mini():
    from app.repositories.llm_call_log_repo import _calc_cost

    # 1000 in @ 0.15/M + 500 out @ 0.60/M = 0.00015 + 0.0003 = 0.00045
    result = _calc_cost("gpt-4o-mini", 1000, 500)
    assert result == Decimal("0.000450")


def test_calc_cost_unknown_model_is_zero():
    from app.repositories.llm_call_log_repo import _calc_cost

    assert _calc_cost("unknown-future-model", 1000, 500) == Decimal("0.000000")
