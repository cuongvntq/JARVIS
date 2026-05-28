"""
Tiered LLM router — Sprint 2 simplified 2-model version.

Stage 0: rule-based pre-filter (no LLM cost)
Stage 1: Gemini Flash classifier → JSON intent
Stage 2: route to model by intent

Sprint 2 model map (simplified):
  chitchat     → gemini/gemini-2.5-flash   (FREE)
  simple_query → gpt-4o-mini               (defer gpt-5.4-nano to Sprint 4)
  tool_call    → gpt-4o-mini
  complex      → gpt-4o-mini               (defer gpt-5-mini to Sprint 6)
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import StrEnum

import litellm
import structlog

from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()


class Intent(StrEnum):
    CHITCHAT = "chitchat"
    SIMPLE_QUERY = "simple_query"
    TOOL_CALL = "tool_call"
    COMPLEX = "complex"


# Sprint 2: 2-model routing. Nano/mini tiers added Sprint 4/6.
MODEL_MAP: dict[Intent, str] = {
    Intent.CHITCHAT: settings.llm_primary,  # gemini/gemini-2.5-flash (FREE)
    Intent.SIMPLE_QUERY: settings.llm_fallback,  # gpt-4o-mini
    Intent.TOOL_CALL: settings.llm_fallback,  # gpt-4o-mini
    Intent.COMPLEX: settings.llm_fallback,  # gpt-4o-mini
}

# Read-only tools that simple_query may call
_READ_ONLY_TOOLS = frozenset(
    {"list_todos", "list_reminders", "search_notes", "search_memory", "get_today_summary"}
)

# ── Stage 0: Pre-filter ────────────────────────────────────────────────────────

_CHITCHAT_PATTERNS = [
    re.compile(r"^(xin\s+)?chào\b", re.IGNORECASE),
    re.compile(r"^cảm\s*ơn\b", re.IGNORECASE),
    re.compile(r"^(ok|okay|được|vâng|dạ|ừm?)\.?$", re.IGNORECASE),
    re.compile(r"^[\W\s]{1,5}$"),  # only emoji/punctuation, short
]

_TOOL_INTENT_PATTERNS: list[tuple[Intent, re.Pattern]] = [
    (
        Intent.TOOL_CALL,
        re.compile(r"^(thêm|tạo|nhắc|nhớ\s+là|đã\s+xong|hoàn\s+thành|hủy)", re.IGNORECASE),
    ),
    (
        Intent.SIMPLE_QUERY,
        re.compile(
            r"(còn\s+việc|todo\s+còn|hôm\s+nay\s+có|tìm\s+ghi\s+chú|có\s+lời\s+nhắc)", re.IGNORECASE
        ),
    ),
]


def _pre_filter(message: str) -> Intent | None:
    msg = message.strip()
    if len(msg) < 3:
        return Intent.CHITCHAT
    for pat in _CHITCHAT_PATTERNS:
        if pat.match(msg):
            return Intent.CHITCHAT
    for intent, pat in _TOOL_INTENT_PATTERNS:
        if pat.search(msg):
            return intent
    return None


# ── Stage 1: Classifier ────────────────────────────────────────────────────────

_CLASSIFIER_PROMPT = """\
Bạn là classifier. Đọc message user và trả về JSON CHÍNH XÁC theo schema sau, KHÔNG thêm text khác:

{{"intent": "chitchat" | "simple_query" | "tool_call" | "complex", "confidence": 0.0-1.0, "reason": "tối đa 10 chữ"}}

Định nghĩa:
- chitchat: Chào hỏi, cảm ơn, hỏi kiến thức chung.
- simple_query: Đọc/list/search dữ liệu user (todo, note, reminder, memory) — KHÔNG tạo/sửa/xóa.
- tool_call: Tạo/sửa/hoàn thành/xóa todo/note/reminder/memory.
- complex: Tóm tắt, lên kế hoạch, so sánh, reasoning đa bước.

Nếu mơ hồ → "tool_call". Nếu vừa hỏi vừa yêu cầu → ưu tiên action → "tool_call".

User: "{message}"
"""


@dataclass
class RouteResult:
    intent: Intent
    model: str
    confidence: float
    classify_source: str  # "prefilter" | "classifier" | "fallback"
    effective_tools: list[dict]  # filtered tool subset for this intent
    # Populated only when classify_source == "classifier"
    classifier_model: str = field(default="")
    classifier_tokens_in: int = field(default=0)
    classifier_tokens_out: int = field(default=0)
    classifier_duration_ms: int = field(default=0)


async def route(
    user_message: str,
    all_tools: list[dict],
) -> RouteResult:
    """Classify user_message and return routing decision."""
    # Stage 0
    pre = _pre_filter(user_message)
    if pre is not None:
        return _build_result(pre, 1.0, "prefilter", all_tools)

    # Stage 1: Gemini classifier (free, fast, 3s timeout)
    try:
        t0 = time.monotonic()
        resp = await asyncio.wait_for(
            litellm.acompletion(
                model=settings.llm_primary,
                messages=[
                    {
                        "role": "user",
                        "content": _CLASSIFIER_PROMPT.format(message=user_message[:500]),
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=80,
            ),
            timeout=3.0,
        )
        classifier_duration_ms = int((time.monotonic() - t0) * 1000)
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        intent = Intent(data.get("intent", "tool_call"))
        confidence = float(data.get("confidence", 0.8))
        usage = getattr(resp, "usage", None)
        result = _build_result(intent, confidence, "classifier", all_tools)
        result.classifier_model = settings.llm_primary
        result.classifier_tokens_in = getattr(usage, "prompt_tokens", 0) or 0
        result.classifier_tokens_out = getattr(usage, "completion_tokens", 0) or 0
        result.classifier_duration_ms = classifier_duration_ms
        return result
    except Exception as exc:
        log.warning("router.classifier_failed", error=str(exc))
        return _build_result(Intent.TOOL_CALL, 0.5, "fallback", all_tools)


def _build_result(
    intent: Intent,
    confidence: float,
    source: str,
    all_tools: list[dict],
) -> RouteResult:
    model = MODEL_MAP[intent]

    if intent == Intent.CHITCHAT:
        effective_tools = []
    elif intent == Intent.SIMPLE_QUERY:
        effective_tools = [t for t in all_tools if t["function"]["name"] in _READ_ONLY_TOOLS]
    else:
        effective_tools = all_tools

    log.info(
        "router.routed",
        intent=intent.value,
        model=model,
        source=source,
        confidence=confidence,
        tool_count=len(effective_tools),
    )
    return RouteResult(
        intent=intent,
        model=model,
        confidence=confidence,
        classify_source=source,
        effective_tools=effective_tools,
    )
