# PHỤ LỤC 5C: TIERED ROUTING STRATEGY
## Tối ưu chi phí LLM bằng cách dùng model rẻ/free cho task đơn giản

**Phiên bản:** 1.0
**Ngày:** 18/05/2026
**Áp dụng cho:** J.A.R.V.I.S Personal AI Assistant — MVP 1

---

## 1. TRIẾT LÝ

Mỗi câu hỏi không cần dùng cùng 1 model. Pattern này gọi là **LLM Routing / Triage / Model Cascading**. Nguyên tắc:

1. **Câu đơn giản** (chào hỏi, list query) → model FREE / rẻ nhất.
2. **Câu cần tool calling** (tạo todo, reminder) → model có function calling reliability cao.
3. **Câu phức tạp** (briefing, reasoning) → model mạnh hơn.
4. **Mỗi lần routing sai tốn ít hơn 1 cent** → đáng để tối ưu.

→ Tiết kiệm 50-80% cost so với "1 model cho tất cả".

---

## 2. KIẾN TRÚC CHI TIẾT

```
┌─────────────────────────────────────────────────────────────┐
│ User message: "Thêm việc mua sữa chiều nay"                  │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 0: Pre-filter (rule-based, code thuần — KHÔNG LLM)     │
│                                                                │
│ - len(message) < 3                  → reject                  │
│ - Pure emoji / "ok" / "cảm ơn"      → bypass (echo response) │
│ - Slash command "/help", "/clear"   → handler riêng          │
│ - Keyword match strong intent       → skip classifier        │
│   (xem §4 keyword whitelist)                                  │
└─────────────────────────────────┬───────────────────────────┘
                                  │ (chỉ ~70% message tới đây)
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: Classifier (FREE model)                              │
│                                                                │
│ Model: Gemini 2.5 Flash hoặc gpt-5.4-nano                     │
│ Prompt: phân loại trong 4 nhóm + trả JSON                     │
│ Output schema:                                                 │
│  { "intent": "chitchat|simple_query|tool_call|complex",      │
│    "confidence": 0.0-1.0,                                     │
│    "reason": "ngắn" }                                          │
│ Timeout: 3s                                                    │
│ Fallback nếu fail: route mặc định = "tool_call"               │
└─────────────────────────────────┬───────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
   ┌─────────┐  ┌──────────────┐  ┌─────────┐  ┌──────────────┐
   │chitchat │  │ simple_query │  │tool_call│  │   complex    │
   └────┬────┘  └──────┬───────┘  └────┬────┘  └──────┬───────┘
        │              │                │              │
        ▼              ▼                ▼              ▼
   Gemini 2.5     gpt-5.4-nano    gpt-4o-mini    gpt-5-mini
   Flash (FREE)   $0.075/$0.30   $0.15/$0.60    $0.25/$2.00
                                                
   Trả lời       List/search    Function call    Reasoning,
   không tool    đơn giản       tin cậy cao      briefing
```

---

## 3. ĐỊNH NGHĨA 4 INTENT

### 3.1 `chitchat`
**Đặc điểm:** Không cần tool, không cần data user. Chỉ trao đổi xã giao hoặc kiến thức chung.

**Ví dụ:**
- "Xin chào"
- "Cảm ơn bạn"
- "Bạn là ai?"
- "Hôm nay thời tiết Sài Gòn thế nào?" (nếu chưa có integration weather)
- "Giải thích cho tôi về AI"

**Model:** Gemini 2.5 Flash (FREE)
**Tool array:** [] (không truyền tool)
**Tokens:** Input ~1000 (no tool def), Output ~150

### 3.2 `simple_query`
**Đặc điểm:** Cần đọc data user (list todo, search note, list memory) nhưng không sửa/tạo gì.

**Ví dụ:**
- "Tôi còn việc gì chưa làm?"
- "Tìm ghi chú về tiếng Nhật"
- "Có lời nhắc nào sắp tới không?"
- "Tôi đã lưu memory về sở thích cà phê chưa?"

**Tool có thể gọi:** `list_todos`, `list_reminders`, `search_notes`, `search_memory`, `get_today_summary`

**Model:** `gpt-5.4-nano`
**Tool array:** Chỉ subset 5 read-only tool
**Tokens:** Input ~1500, Output ~200

### 3.3 `tool_call`
**Đặc điểm:** Cần TẠO/SỬA/XÓA data — đòi hỏi tool call reliable cao.

**Ví dụ:**
- "Thêm việc mua sữa chiều nay"
- "Nhắc tôi 8h sáng mai uống thuốc"
- "Nhớ là tôi dị ứng tôm"
- "Đã hoàn thành việc gọi mẹ"
- "Quên đi việc đặt vé máy bay"

**Tool có thể gọi:** Full 11 tool (write tool: create/update/forget).

**Model:** `gpt-4o-mini`
**Tool array:** Full 11 tool
**Tokens:** Input ~2500 (full tool def), Output ~150

### 3.4 `complex`
**Đặc điểm:** Cần reasoning, tổng hợp nhiều data, sinh nội dung dài.

**Ví dụ:**
- "Tóm tắt tình hình tuần này của tôi"
- "Lên kế hoạch cho ngày mai dựa trên todo và lịch"
- "So sánh 2 note này và rút ra điểm chung"
- Daily briefing (background job)
- Conversation summarization (background job)

**Model:** `gpt-5-mini`
**Tool array:** Full + có thể chain
**Tokens:** Input ~3000, Output ~500-1000

---

## 4. PRE-FILTER WHITELIST (Stage 0)

Một số pattern có thể bypass classifier để tiết kiệm 1 LLM call:

```python
CHITCHAT_PATTERNS = [
    r'^(xin\s+)?chào\b',
    r'^cảm\s*ơn\b',
    r'^(ok|okay|được|vâng|dạ|ừm?)\.?$',
    r'^(👍|🙏|❤️|😊)$',
]

CLEAR_TOOL_INTENT_PATTERNS = {
    'create_todo':    [r'^(thêm|tạo)\s+(việc|task)', r'^cần\s+làm\s+gì'],
    'create_reminder': [r'^nhắc\s+tôi\s+.*\s+(lúc|vào)\s+\d'],
    'list_todos':     [r'^(việc|todo)\s+(hôm\s+nay|còn|chưa)'],
    'today_summary':  [r'hôm\s+nay\s+(có\s+gì|làm\s+gì|tình\s+hình)'],
}
```

Khi match → route thẳng tới Stage 2 model, skip classifier. Tiết kiệm ~30% LLM call.

---

## 5. CLASSIFIER PROMPT

```
Bạn là classifier. Đọc message user và trả về JSON CHỈNH XÁC theo schema sau, KHÔNG thêm text khác:

{
  "intent": "chitchat" | "simple_query" | "tool_call" | "complex",
  "confidence": 0.0 đến 1.0,
  "reason": "tối đa 10 chữ"
}

Định nghĩa:
- chitchat: Chào hỏi, cảm ơn, hỏi kiến thức chung, trò chuyện không cần data user.
- simple_query: Đọc/list/search dữ liệu user (todo, note, reminder, memory) — KHÔNG tạo mới/sửa/xóa.
- tool_call: Tạo, sửa, hoàn thành, xóa todo/note/reminder/memory.
- complex: Tóm tắt, lên kế hoạch, so sánh, reasoning đa bước.

Nếu mơ hồ → chọn "tool_call" (an toàn nhất).
Nếu user vừa hỏi vừa yêu cầu (hybrid) → ưu tiên action → "tool_call".

User message: "{{user_message}}"
```

**Token cost:** ~150 input + 30 output / classifier call.
- Gemini Flash: $0 (free tier)
- gpt-5.4-nano fallback: 0.0001¢/call

---

## 6. ROUTER CODE (Python)

```python
"""
jarvis/llm/router.py
Tiered LLM router with classifier + per-intent model + fallback.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import litellm
from litellm.exceptions import (
    RateLimitError, Timeout, ServiceUnavailableError, BadRequestError
)

log = logging.getLogger(__name__)


class Intent(str, Enum):
    CHITCHAT = "chitchat"
    SIMPLE_QUERY = "simple_query"
    TOOL_CALL = "tool_call"
    COMPLEX = "complex"


# Model assignment per intent
MODEL_MAP = {
    Intent.CHITCHAT:     "gemini/gemini-2.5-flash",   # FREE
    Intent.SIMPLE_QUERY: "gpt-5.4-nano",              # $0.075/$0.30
    Intent.TOOL_CALL:    "gpt-4o-mini",               # $0.15/$0.60
    Intent.COMPLEX:      "gpt-5-mini",                # $0.25/$2.00
}

# Fallback chain when primary model fails
FALLBACK_MAP = {
    Intent.CHITCHAT:     ["gpt-5.4-nano", "gpt-4o-mini"],
    Intent.SIMPLE_QUERY: ["gpt-4o-mini"],
    Intent.TOOL_CALL:    ["claude-haiku-4-5"],
    Intent.COMPLEX:      ["claude-haiku-4-5"],
}


# ============= STAGE 0: Pre-filter =============

CHITCHAT_PATTERNS = [
    re.compile(r'^(xin\s+)?chào\b', re.IGNORECASE),
    re.compile(r'^cảm\s*ơn\b', re.IGNORECASE),
    re.compile(r'^(ok|okay|được|vâng|dạ|ừm?)\.?$', re.IGNORECASE),
    re.compile(r'^[\W\s]{1,5}$'),  # chỉ emoji/punctuation ngắn
]

TOOL_INTENT_PATTERNS = [
    (Intent.TOOL_CALL,    re.compile(r'^(thêm|tạo|nhắc|nhớ\s+là|đã\s+xong|hoàn\s+thành|hủy)', re.IGNORECASE)),
    (Intent.SIMPLE_QUERY, re.compile(r'^(còn\s+việc|todo\s+còn|hôm\s+nay\s+có|tìm\s+ghi\s+chú|có\s+lời\s+nhắc)', re.IGNORECASE)),
]


def pre_filter(message: str) -> Optional[Intent]:
    """Return intent if pre-filter matches, else None to fall through to classifier."""
    msg = message.strip()
    if len(msg) < 3:
        return Intent.CHITCHAT
    for pat in CHITCHAT_PATTERNS:
        if pat.match(msg):
            return Intent.CHITCHAT
    for intent, pat in TOOL_INTENT_PATTERNS:
        if pat.search(msg):
            return intent
    return None


# ============= STAGE 1: Classifier =============

CLASSIFIER_PROMPT = """\
Bạn là classifier. Đọc message user và trả về JSON CHÍNH XÁC theo schema sau, KHÔNG thêm text khác:

{{"intent": "chitchat" | "simple_query" | "tool_call" | "complex", "confidence": 0.0-1.0, "reason": "tối đa 10 chữ"}}

Định nghĩa:
- chitchat: Chào hỏi, cảm ơn, hỏi kiến thức chung.
- simple_query: Đọc/list/search dữ liệu user (todo, note, reminder, memory).
- tool_call: Tạo/sửa/hoàn thành/xóa todo/note/reminder/memory.
- complex: Tóm tắt, lên kế hoạch, so sánh, reasoning đa bước.

Nếu mơ hồ → "tool_call".

User: "{message}"
"""


@dataclass
class ClassifyResult:
    intent: Intent
    confidence: float
    reason: str
    source: str  # "prefilter" | "classifier" | "fallback"


async def classify(message: str) -> ClassifyResult:
    # Stage 0
    pre = pre_filter(message)
    if pre:
        return ClassifyResult(pre, 1.0, "pre-filter match", "prefilter")

    # Stage 1: Gemini Free classifier
    try:
        resp = await asyncio.wait_for(
            litellm.acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{
                    "role": "user",
                    "content": CLASSIFIER_PROMPT.format(message=message[:500])
                }],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=80,
            ),
            timeout=3.0
        )
        import json
        data = json.loads(resp.choices[0].message.content)
        return ClassifyResult(
            intent=Intent(data["intent"]),
            confidence=float(data.get("confidence", 0.8)),
            reason=data.get("reason", ""),
            source="classifier"
        )
    except Exception as e:
        log.warning(f"Classifier failed: {e}. Falling back to TOOL_CALL.")
        return ClassifyResult(Intent.TOOL_CALL, 0.5, "classifier-error", "fallback")


# ============= STAGE 2: Main LLM call with fallback =============

async def chat_with_fallback(
    intent: Intent,
    messages: list,
    tools: list = None,
    stream: bool = False,
    max_retries: int = 1,
):
    """Try primary model for intent, fall back to next models if it fails."""
    chain = [MODEL_MAP[intent]] + FALLBACK_MAP[intent]
    last_error = None

    for attempt, model in enumerate(chain):
        try:
            log.info(f"Calling model={model} intent={intent.value} attempt={attempt}")
            resp = await litellm.acompletion(
                model=model,
                messages=messages,
                tools=tools if intent != Intent.CHITCHAT else None,
                stream=stream,
                timeout=30,
            )
            # Validate tool call schema if tool_call intent
            if intent == Intent.TOOL_CALL and tools:
                tc = resp.choices[0].message.tool_calls
                if tc and not _validate_tool_calls(tc, tools):
                    raise ValueError(f"Invalid tool call shape from {model}")
            return resp, model
        except (RateLimitError, Timeout, ServiceUnavailableError) as e:
            log.warning(f"Model {model} transient error: {e}, trying next.")
            last_error = e
            continue
        except (BadRequestError, ValueError) as e:
            log.error(f"Model {model} hard error: {e}, trying next.")
            last_error = e
            continue
    raise RuntimeError(f"All models failed for intent={intent.value}: {last_error}")


def _validate_tool_calls(tool_calls, tools) -> bool:
    """Basic JSON Schema sanity check on tool calls."""
    tool_names = {t["function"]["name"] for t in tools}
    for tc in tool_calls:
        if tc.function.name not in tool_names:
            return False
        try:
            import json
            json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            return False
    return True


# ============= MAIN ENTRY POINT =============

async def route_and_chat(
    user_message: str,
    system_prompt: str,
    history: list,
    tools: list,
):
    """Top-level entry: classify intent → choose model → call → return."""
    classify_result = await classify(user_message)
    log.info(f"Routed: intent={classify_result.intent.value} "
             f"source={classify_result.source} "
             f"confidence={classify_result.confidence}")

    # Filter tool set per intent (chitchat = no tools, simple_query = read-only)
    intent = classify_result.intent
    if intent == Intent.CHITCHAT:
        effective_tools = None
    elif intent == Intent.SIMPLE_QUERY:
        READ_ONLY = {"list_todos", "list_reminders", "search_notes",
                     "search_memory", "get_today_summary"}
        effective_tools = [t for t in tools if t["function"]["name"] in READ_ONLY]
    else:
        effective_tools = tools

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": user_message},
    ]

    response, model_used = await chat_with_fallback(
        intent=intent,
        messages=messages,
        tools=effective_tools,
    )

    return {
        "response": response,
        "model_used": model_used,
        "intent": intent.value,
        "classify_source": classify_result.source,
        "classify_confidence": classify_result.confidence,
    }
```

---

## 7. MONITORING & COST TRACKING

Lưu thêm cột vào `tool_execution_logs` (hoặc bảng mới `llm_call_logs`):

```sql
CREATE TABLE llm_call_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id    UUID REFERENCES messages(id) ON DELETE SET NULL,
    intent        VARCHAR(32) NOT NULL,
    classify_source VARCHAR(16) NOT NULL,   -- prefilter|classifier|fallback
    model_used    VARCHAR(64) NOT NULL,
    tokens_in     INTEGER NOT NULL,
    tokens_out    INTEGER NOT NULL,
    cost_usd      NUMERIC(10, 6) NOT NULL,
    duration_ms   INTEGER NOT NULL,
    success       BOOLEAN NOT NULL,
    error_code    VARCHAR(64),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_llm_log_user_created ON llm_call_logs(user_id, created_at DESC);
CREATE INDEX idx_llm_log_model        ON llm_call_logs(model_used, created_at DESC);
```

Sau mỗi `route_and_chat`, insert log. Có thể build dashboard:
- $/ngày theo user
- Phân phối intent (% chitchat vs tool vs ...)
- Tỷ lệ fallback (alarm nếu > 10%)
- Latency p50/p95 theo model

**Cost mapping (cho LiteLLM):**

```python
COST_PER_M_TOKENS = {
    "gemini/gemini-2.5-flash":   (0.0,    0.0),   # free tier
    "gpt-5.4-nano":              (0.075,  0.30),
    "gpt-5-nano":                (0.05,   0.40),
    "gpt-4o-mini":               (0.15,   0.60),
    "gpt-5-mini":                (0.25,   2.00),
    "claude-haiku-4-5":          (1.00,   5.00),
}

def calc_cost(model, in_tokens, out_tokens):
    in_rate, out_rate = COST_PER_M_TOKENS.get(model, (0, 0))
    return (in_tokens * in_rate + out_tokens * out_rate) / 1_000_000
```

---

## 8. EVAL CHO ROUTER

Trước khi deploy, test 30 case (mỗi intent 7-8 case):

```python
EVAL_CASES = [
    # chitchat
    ("Xin chào", Intent.CHITCHAT),
    ("Cảm ơn nhé", Intent.CHITCHAT),
    ("AI là gì?", Intent.CHITCHAT),
    # simple_query
    ("Tôi còn việc gì?", Intent.SIMPLE_QUERY),
    ("Tìm ghi chú về Python", Intent.SIMPLE_QUERY),
    ("Có lời nhắc gì hôm nay?", Intent.SIMPLE_QUERY),
    # tool_call
    ("Thêm việc mua sữa chiều nay", Intent.TOOL_CALL),
    ("Nhắc tôi 8h sáng mai uống thuốc", Intent.TOOL_CALL),
    ("Nhớ là tôi không thích cà phê sữa", Intent.TOOL_CALL),
    ("Đã hoàn thành việc gọi mẹ", Intent.TOOL_CALL),
    # complex
    ("Tóm tắt tình hình tuần này", Intent.COMPLEX),
    ("Lên kế hoạch cho ngày mai dựa trên todo", Intent.COMPLEX),
]
```

Pass criteria: ≥ 90% match intent đúng. Nếu fail → tinh chỉnh classifier prompt hoặc tăng confidence threshold để route mặc định.

---

## 9. EDGE CASES

| Tình huống | Xử lý |
|-----------|------|
| Classifier trả JSON malformed | Fallback Intent.TOOL_CALL |
| Gemini free quota hết (1500/ngày) | LiteLLM tự fallback gpt-5.4-nano (~$0.0001/call) |
| Tool call schema invalid từ model rẻ | Fallback chain auto retry model mạnh hơn |
| User message chứa nhiều intent | Classifier prompt yêu cầu "ưu tiên action" |
| Long conversation (>4000 tokens history) | Force route Intent.COMPLEX để dùng gpt-5-mini |
| Streaming + tool ở model khác nhau | Chỉ stream khi Intent.CHITCHAT hoặc COMPLEX |

---

## 10. COST PROJECTION

Giả định 1 user, 30 message/ngày, phân phối thực tế:

| Intent | % | Số msg | Model | $/msg | $/ngày |
|--------|---|--------|-------|-------|--------|
| chitchat | 40% | 12 | Gemini Free | $0 | $0 |
| simple_query | 25% | 7-8 | gpt-5.4-nano | $0.0003 | $0.002 |
| tool_call | 30% | 9 | gpt-4o-mini | $0.0008 | $0.007 |
| complex | 5% | 1-2 | gpt-5-mini | $0.003 | $0.005 |
| **Tổng** | 100% | 30 | | | **$0.014** |
| Classifier overhead | | 30 calls × $0 (Gemini free) | | | $0 |
| **Tổng/ngày** | | | | | **$0.014** |
| **Tổng/tháng** | | | | | **$0.42** |

So sánh với non-routing (chỉ gpt-4o-mini):
- $0.55-0.80/tháng → **tiết kiệm ~40-50%**.

Nếu Gemini free quota dùng hết và phải fallback gpt-5.4-nano cho chitchat:
- chitchat 12 × $0.0001 = $0.0012/ngày = $0.036/tháng
- Vẫn tổng dưới $0.50/tháng.

---

## 11. LỢI ÍCH PHỤ NGOÀI COST

1. **Privacy partial:** Câu chitchat (40%) gửi qua Gemini không chứa tool definition + memory → ít data nhạy cảm rời server.
2. **Resilience:** Khi 1 provider down, fallback auto chuyển provider khác. Uptime gần 99.9%+.
3. **Performance:** Chitchat qua Gemini Flash thường < 1s (nhanh hơn chỉ dùng gpt-4o-mini ~1.5s).
4. **Learning:** Log giúp biết user dùng JARVIS để làm gì nhiều nhất → tối ưu UX về sau.

---

## 12. NHỮNG GÌ KHÔNG NÊN OVER-ENGINEER

| Đừng làm | Lý do |
|----------|------|
| Tier 6+ với 6 model khác nhau | Quá phức tạp, debug khó, tiết kiệm thêm chỉ ~10% |
| Train classifier riêng | Quá tốn công, model FREE đã ~90% accuracy |
| Cache classifier result | User message hiếm lặp lại exact |
| Route per-tool (mỗi tool 1 model) | Phá vỡ multi-tool chain, model bị confused |

---

## 13. ROADMAP TRIỂN KHAI

- **Sprint 2:** Implement Stage 0 pre-filter + Stage 1 classifier với 2 model (Gemini + gpt-4o-mini fallback). Skip nano/mini tier — đơn giản nhất.
- **Sprint 4:** Thêm gpt-5.4-nano cho simple_query khi memory system xong.
- **Sprint 6 (polish):** Thêm gpt-5-mini cho complex, dashboard monitoring.

→ Không cần làm full Tier 4 ngay từ Sprint 1. Tăng tier dần khi có data thực.

---

## 14. CHECKLIST IMPLEMENT

- [ ] Thêm `gemini-api-key` vào env, đăng ký https://aistudio.google.com/apikey (free, không cần card).
- [ ] Cập nhật `pyproject.toml`: `litellm[google]` hoặc `litellm` + `google-generativeai`.
- [ ] Implement `router.py` (~150 dòng theo §6).
- [ ] Tạo migration cho `llm_call_logs`.
- [ ] Viết 30 eval case classifier (xem §8).
- [ ] Dashboard `/admin/llm-usage` đơn giản (chart $/ngày, top intent, fallback rate).
- [ ] Alert: fallback rate > 10% trong 1 giờ → log.warning.
- [ ] Alert: $/ngày vượt $0.20 → log.warning (cao bất thường cho 1 user).

---

## Sources

- [LiteLLM Gemini Integration](https://docs.litellm.ai/docs/providers/gemini)
- [Gemini Free Tier 2026](https://tokenmix.ai/blog/gemini-api-free-tier-limits)
- [OpenAI Cheapest Model 2026](https://tokenmix.ai/blog/openai-api-cheapest-model)
- [LLM Routing Patterns — Anyscale](https://www.anyscale.com/blog/llm-routing)
