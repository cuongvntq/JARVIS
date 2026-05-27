# Sprint 2 — Tool Router + 3 Todo Tools

**Mục tiêu:** AI gọi được tool nội bộ, lưu todo vào DB.  
**DoD:** Gõ "Thêm việc mua sữa chiều nay" → todo lưu DB → user nhận xác nhận tiếng Việt. Eval E-01, E-02 passed.

**Nhánh:** `feat/sprint2-tool-router`  
**PR đề xuất:** 4 PR nhỏ (A → B → C → D)

---

## PR A — Database, Todo CRUD, Chat History Endpoint

### Phase 1 — Database & Models

| # | Task | File(s) | Ghi chú |
|---|------|---------|---------|
| B1a | Migration 003 — ENUM types | `migrations/versions/003_*.py` | `todo_status`, `todo_priority`, `tool_status` |
| B1b | Migration 003 — bảng `todos` + indexes | cùng file | Partial index `WHERE deleted_at IS NULL` |
| B1c | Migration 003 — bảng `tool_execution_logs` + indexes | cùng file | |
| B1d | Migration 003 — bảng `llm_call_logs` + indexes | cùng file | Schema đầy đủ: xem §Schema llm_call_logs bên dưới |

**ORM Models:**

| # | Task | File(s) |
|---|------|---------|
| B2a | ORM model `Todo` | `app/models/todo.py` |
| B2b | ORM model `ToolExecutionLog` + `LLMCallLog` | `app/models/tool_log.py` |

### Phase 2 — Todo CRUD

**Contract Todo API** (theo docs/02, bắt buộc bám spec):

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/v1/todos` | List với `?status=`, `?filter=today\|upcoming\|overdue\|all`, `?q=`, `?limit=`, `?cursor=` |
| POST | `/v1/todos` | Tạo mới |
| GET | `/v1/todos/{id}` | Chi tiết |
| PUT | `/v1/todos/{id}` | Update tất cả field cho phép |
| PATCH | `/v1/todos/{id}/complete` | Set status=completed, completed_at=NOW() |
| PATCH | `/v1/todos/{id}/uncomplete` | Set status=pending, completed_at=NULL |
| DELETE | `/v1/todos/{id}` | Soft delete — 204 |

**Schemas (tách rõ 2 use case):**
- `TodoCreate` — tạo mới (title required)
- `TodoReplace` — dùng cho `PUT /todos/{id}`: title required, các field còn lại optional (giữ giá trị cũ nếu không truyền)
- `TodoPartialUpdate` — **chỉ dùng nội bộ** cho tool executor: tất cả field optional, chỉ update field nào được truyền. **Không expose qua REST.**
- `TodoOut` — response shape

| # | Task | File(s) |
|---|------|---------|
| B3a | Pydantic schemas | `app/schemas/todo.py` — `TodoCreate`, `TodoReplace`, `TodoPartialUpdate` (internal), `TodoOut` |
| B4a | TodoRepository — read ops | `app/repositories/todo_repo.py` — `get_by_id`, `list` (5 filter: today/upcoming/overdue/completed/all) |
| B4b | TodoRepository — write ops | `create`, `update_fields(id, **kwargs)` (partial — dùng cho cả PUT và tool), `complete`, `uncomplete`, soft delete |
| B5a | TodoService | `app/services/todo_service.py` — `replace(id, TodoReplace)` cho PUT, `patch_fields(id, TodoPartialUpdate)` cho tool, complete, uncomplete, delete |
| B5b | TodoRouter — read endpoints | `app/routers/todos.py` — `GET /v1/todos`, `GET /v1/todos/{id}` |
| B5c | TodoRouter — write endpoints | `POST /v1/todos`, `PUT /v1/todos/{id}`, `PATCH /v1/todos/{id}/complete`, `PATCH /v1/todos/{id}/uncomplete`, `DELETE /v1/todos/{id}` |
| B5d | Register router | `app/main.py` — thêm `app.include_router(todos_router, prefix="/v1")` |
| B5e | Tests todo API | `tests/test_todos.py` — happy path + error path mỗi endpoint |

### Phase 2b — Chat History Endpoint (backend cho F2a)

**Contract** (theo docs/02):
- `GET /v1/chat/conversations/{id}` — trả conversation + messages, `?before=<message_id>&limit=50`
- `PATCH /v1/chat/conversations/{id}` — đổi title
- `DELETE /v1/chat/conversations/{id}` — soft delete, 204

| # | Task | File(s) |
|---|------|---------|
| B5f | ChatRouter — conversation detail + PATCH + DELETE | `app/routers/chat.py` — 3 endpoint mới |
| B5g | ConversationRepository — get with messages, update title, soft delete | `app/repositories/conversation_repo.py` |

---

## PR B — Vietnamese Datetime Parser + Tool System

### Phase 3 — Vietnamese Datetime Parser

**Contract:**
```python
def parse_datetime(text: str, now: datetime, timezone: str) -> datetime:
    """
    Input:  text (tiếng Việt), now (UTC-aware, caller truyền — dễ freeze trong test), timezone (vd "Asia/Ho_Chi_Minh")
    Output: UTC-aware datetime
    Raises: ParseDatetimeError nếu không parse được sau cả 2 bước
    """
```
> **Quan trọng:** Test phải truyền `now` tường minh — không gọi `datetime.now()` bên trong hàm. Tránh flaky test.

**Step 1 xử lý deterministic (không dùng thư viện ngoài):**
1. ISO 8601 string → `datetime.fromisoformat()` trực tiếp
2. Pattern `HH:mm` → hôm nay lúc giờ đó (regex `^\d{1,2}:\d{2}$`)
3. Dict replace (vi_time_dict.json) → resolve thành `(base_day, hour, minute)` relative to `now`
4. Regex cho dạng `"(mai|ngày mai)\s+(\d{1,2})h(\d{2})?"` → ngày mai lúc giờ đó
5. Regex cho `"thứ (hai|ba|bốn|năm|sáu|bảy|CN)\s*(tới|này)?"` → tính weekday tiếp theo từ `now`

Nếu không khớp rule nào → Step 2 (LLM fallback).

| # | Task | File(s) | Ghi chú |
|---|------|---------|---------|
| B6a | `vi_time_dict.json` | `app/vi_time_dict.json` | ~20 cụm: "chiều nay"→(today,15,0), "tối nay"→(today,20,0), "sáng mai"→(tomorrow,8,0), "sáng nay"→(today,8,0), "cuối tuần"→(next_sat,9,0), ... |
| B6b | Datetime parser — step 1 | `app/utils/datetime_parser.py` | ISO detect → HH:mm regex → dict replace → "mai Xh" regex → weekday regex. Output: UTC-aware datetime |
| B6c | Datetime parser — step 2 | Cùng file | LLM fallback sub-call (chỉ khi step 1 fail) → parse ISO 8601. Raise `ParseDatetimeError` nếu vẫn fail |
| B6d | Tests datetime parser | `tests/test_datetime_parser.py` | 12 case — freeze `now`: ISO input, HH:mm, cụm VN từ dict, "mai 7h", "thứ hai tới", LLM fallback trigger, invalid |

### Phase 4 — Tool System

| # | Task | File(s) |
|---|------|---------|
| B7a | Tool definitions | `app/tools/definitions.py` — 3 JSON schema theo docs/03: `create_todo`, `list_todos`, `update_todo` |
| B8a | Executor `create_todo` | `app/tools/executors/todo.py` — gọi todo_service, trả `{success, data, summary, warnings}` |
| B8b | Executor `list_todos` | Cùng file — filter + format response |
| B8c | Executor `update_todo` | Cùng file — lookup todo trước, rồi update |
| B9a | `ToolExecutionLogRepo` | `app/repositories/tool_log_repo.py` — `log_execution()`, log cả khi fail |

---

## PR C — LLM Client Update + Orchestrator + Tiered Routing

### Phase 4b — LLM Client Response Model

`chat_completion()` hiện tại chỉ trả `(content, model, tokens_in, tokens_out)` — mất `tool_calls`. Orchestrator cần raw response.

| # | Task | File(s) | Ghi chú |
|---|------|---------|---------|
| B9b | `LLMResponse` dataclass | `app/llm/models.py` | Fields: `content: str \| None`, `tool_calls: list \| None`, `model: str`, `tokens_in: int`, `tokens_out: int` |
| B9c | Cập nhật `chat_completion()` | `app/llm/client.py` | Trả `LLMResponse` thay tuple. Update `chat_service.py` để không bị break |

### Phase 5 — Tool Orchestrator

| # | Task | File(s) |
|---|------|---------|
| B10a | Orchestrator — dispatch loop | `app/llm/orchestrator.py` — detect `tool_calls` → execute → feed result → re-call LLM |
| B10b | Orchestrator — safety guards | Hard cap 5 calls/turn, max 2 retry/tool |
| B10c | Orchestrator — loop detection | Cùng tool gọi 3 lần với input gần giống → ngắt, thông báo user |
| B10d | Tests orchestrator | `tests/test_orchestrator.py` — mock LLM: tool flow, cap hit, loop detection |

### Phase 6 — Tiered Routing v1

| # | Task | File(s) |
|---|------|---------|
| B11a | Pre-filter Stage 0 | `app/llm/router.py` — chitchat patterns bypass classifier |
| B11b | Classifier Stage 1 | Gemini sub-call → parse intent JSON → `ClassifyResult` |
| B11c | Route by intent | chitchat→Gemini Flash, tool_call→gpt-4o-mini, fallback khi classifier fail → TOOL_CALL |
| B11d | `LLMCallLogRepo` + log | `app/repositories/llm_log_repo.py` — log mỗi LLM call vào `llm_call_logs` |

---

## PR D — Chat Integration + Frontend

### Phase 7 — Chat Service Update

| # | Task | File(s) |
|---|------|---------|
| B12a | System prompt builder | `app/llm/prompt.py` — inject `user_name`, `timezone`, `now_utc` (memory inject Sprint 4) |
| B12b | Update `chat_service.py` | Dùng orchestrator + router thay `chat_completion` trực tiếp |

### Phase 8 — Frontend (minimal)

| # | Task | File(s) |
|---|------|---------|
| F1a | Hook `useConversations` | `src/hooks/useConversations.ts` — `GET /v1/chat/conversations` với Tanstack Query |
| F1b | Sidebar conversation list | `src/components/layout/Sidebar.tsx` — render list, click để switch |
| F2a | Load conversation history | `src/components/chat/ChatInterface.tsx` — call `GET /v1/chat/conversations/{id}`, load messages khi `conversationId` thay đổi |

---

## Schema llm_call_logs (reference cho B1d)

```sql
CREATE TABLE llm_call_logs (
    id               UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id       UUID          REFERENCES messages(id) ON DELETE SET NULL,
    intent           VARCHAR(32)   NOT NULL,
    classify_source  VARCHAR(16)   NOT NULL,   -- prefilter|classifier|fallback
    model_used       VARCHAR(64)   NOT NULL,
    tokens_in        INTEGER       NOT NULL,
    tokens_out       INTEGER       NOT NULL,
    cost_usd         NUMERIC(10,6) NOT NULL,
    duration_ms      INTEGER       NOT NULL,
    success          BOOLEAN       NOT NULL,
    error_code       VARCHAR(64),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_llm_log_user_created ON llm_call_logs(user_id, created_at DESC);
CREATE INDEX idx_llm_log_model        ON llm_call_logs(model_used, created_at DESC);
```

---

## Quyết định thiết kế đã chốt

- **Bỏ `dateparser` library** — dict replace + LLM fallback (2 bước, không thêm dependency)
- **Bỏ Google OAuth** khỏi toàn bộ MVP 1
- **Tiered routing v1 = 2 tier:** Gemini Flash (chitchat) + gpt-4o-mini (tool_call). Mở rộng Sprint 6
- **Todo API bám spec docs/02:** `PUT /todos/{id}` (full update) + `PATCH /todos/{id}/complete|uncomplete` (chuyên biệt), không dùng generic `PATCH /todos/{id}`
- **LLM client trả `LLMResponse`** thay tuple — orchestrator cần `tool_calls`
- `sa.JSON` (không phải `JSONB`) để tương thích SQLite test

## Những gì KHÔNG làm Sprint 2

- Google OAuth
- SSE streaming
- Rate limiting (Sprint 6)
- Memory / RAG (Sprint 4)
- Todo UI đầy đủ (Sprint 3)
- Notes, Reminders (Sprint 3, 5)

---

## Tổng: 35 tasks, 4 PR
