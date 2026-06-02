"""Prompt eval tests — run with: pytest -m eval -v (set RUN_EVAL=1).

These tests call the real LLM and verify tool-call behavior.
They are excluded from normal CI via addopts = '-m not eval' in pyproject.toml.

Usage:
  RUN_EVAL=1 pytest tests/eval/test_prompt_eval.py -m eval -v
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.eval.eval_cases import EVAL_CASES, EvalCase

# ── Skip entire module if RUN_EVAL is not set ──────────────────────────────────
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_EVAL"),
    reason="Set RUN_EVAL=1 to run prompt eval tests",
)


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def llm_client():
    """Real LiteLLM client configured from env."""
    import os

    from app.llm.client import chat_completion

    if not os.getenv("GEMINI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No LLM API key configured — set GEMINI_API_KEY or OPENAI_API_KEY")
    return chat_completion


# ── Helpers ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Bạn là JARVIS, trợ lý cá nhân của người dùng.
Hãy trả lời bằng tiếng Việt, ngắn gọn, tự nhiên.
Khi cần thực hiện hành động, gọi tool phù hợp.
"""

# Minimal tool schema for eval — use real tool definitions
from app.tools.definitions import TOOLS  # noqa: E402


def _get_tool_calls_from_response(response) -> list[str]:
    """Extract list of tool names from LLMResponse."""
    return [tc.name for tc in response.tool_calls]


def _passes(case: EvalCase, response) -> tuple[bool, str]:
    """Return (passed, reason) for an eval case."""
    called_tools = _get_tool_calls_from_response(response)

    if case.assert_tool is not None and case.assert_tool not in called_tools:
        return False, f"Expected tool '{case.assert_tool}' but got {called_tools}"

    for forbidden in case.assert_no_tool:
        if forbidden in called_tools:
            return False, f"Forbidden tool '{forbidden}' was called"

    if (
        case.assert_content_contains
        and case.assert_content_contains.lower() not in response.content.lower()
    ):
        return False, (
            f"Expected content to contain '{case.assert_content_contains}' "
            f"but got: {response.content[:200]}"
        )

    return True, "OK"


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.eval
@pytest.mark.parametrize("case", EVAL_CASES, ids=[c.id for c in EVAL_CASES])
async def test_eval_case(case: EvalCase, llm_client) -> None:
    """Run a single eval case against the real LLM."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": case.input},
    ]

    response = await llm_client(messages=messages, tools=TOOLS)

    passed, reason = _passes(case, response)

    # Record result for the summary fixture
    _RESULTS.append(
        {
            "id": case.id,
            "description": case.description,
            "input": case.input,
            "passed": passed,
            "reason": reason,
            "tool_calls": _get_tool_calls_from_response(response),
            "content_preview": response.content[:150],
        }
    )

    assert passed, f"[{case.id}] {case.description} — FAILED: {reason}"


# ── Session-level result writing ───────────────────────────────────────────────

_RESULTS: list[dict] = []


@pytest.fixture(scope="session", autouse=True)
def write_eval_results():
    """Write eval results to eval_results/YYYYMMDD_HHMM.json after session ends."""
    yield  # wait for all tests
    if not _RESULTS:
        return
    out_dir = Path(__file__).parents[3] / "eval_results"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M")
    out_path = out_dir / f"{ts}.json"
    passed = sum(1 for r in _RESULTS if r["passed"])
    summary = {
        "timestamp": ts,
        "total": len(_RESULTS),
        "passed": passed,
        "failed": len(_RESULTS) - passed,
        "pass_rate": f"{passed}/{len(_RESULTS)}",
        "results": _RESULTS,
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nEval results written to {out_path} — {passed}/{len(_RESULTS)} passed")
