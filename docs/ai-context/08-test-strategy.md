# Test Strategy

## Overview

**Backend:** pytest + pytest-asyncio, SQLite in-memory (real DB, no mocks for DB layer)
**Frontend:** vitest (unit), Playwright (E2E) — 4 E2E specs (auth/chat/reminder/dashboard)
**Test count (Sprint 6):** 211 backend tests collected, all passing + Playwright E2E (retries=1 in CI)

---

## Backend Test Setup

### Test Database
```python
# tests/conftest.py
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # single shared connection for all test coroutines
)
```

- Tables created once per session (`scope="session"`)
- All rows wiped between tests (autouse fixture `clean_tables`)
- `get_db` dependency overridden with `_override_get_db` (test session)

### Key Fixtures

| Fixture | Scope | What it does |
|---|---|---|
| `create_tables` | session | `Base.metadata.create_all` once |
| `clean_tables` | function (autouse) | DELETE all rows between tests |
| `async_client` | function | `AsyncClient` via `ASGITransport` |
| `auth_headers` | function | Register TEST_USER, return `{"Authorization": "Bearer ..."}` |
| `mock_llm` | function | Patch `orchestrator.run` to return fixed OrchestratorResult |
| `mock_llm_stream` | function | Patch `stream_message` generator (Sprint 3) |
| `mock_llm_stream_error` | function | Patch stream generator to raise (Sprint 3) |
| `mock_embedding` | function | Patch `embed_text` → `[0.1] * 1536` (Sprint 4) |
| `mock_semantic_search` | function | Patch `memory_repo.semantic_search` → `[]` (Sprint 4) |
| `auth_headers_user_b` | function | Second test user for ownership isolation (Sprint 4) |

### TEST_USER
```python
TEST_USER = {"email": "test@jarvis.dev", "password": "Test1234!", "name": "Test User"}
```

### CSRF in Tests
All cookie-based endpoints check Origin header. Tests using cookies must include:
```python
headers={"Origin": "http://test"}
```
`BACKEND_CORS_ORIGINS = "http://test"` set in conftest before app import.

### mock_llm Fixture Details
```python
_orch = OrchestratorResult(
    final_response=LLMResponse(
        content="Xin chào! Tôi là JARVIS.",
        model="gemini-mock",
        tokens_in=10,
        tokens_out=20,
    ),
    route=RouteResult(intent=Intent.CHITCHAT, model="gemini-mock", ...),
    total_tokens_in=10, total_tokens_out=20, total_llm_calls=1,
)
# Patches: app.llm.orchestrator.run
```

---

## Test Files & Coverage

### `tests/test_auth.py` (23 tests — Sprint 4 added 7)
- register happy path
- duplicate email → 409
- weak password → 422
- login happy path
- wrong password → 401
- refresh token rotation
- logout
- `/auth/me` with/without token
- CSRF origin rejection
- **Sprint 4:** PATCH /auth/me (name, timezone, locale, assistant_name)
- **Sprint 4:** invalid timezone → 422, locale too long → 422, unknown field → 422

### `tests/test_chat.py` (18 tests — Sprint 4 added 3 RAG tests)
- send message authenticated
- creates conversation when `conversation_id=null`
- resumes existing conversation
- unauthenticated → 401
- list conversations
- ownership isolation → 404 (not 403)
- GET conversation detail (messages, has_more)
- GET conversation not found
- GET conversation ownership
- PATCH conversation title
- PATCH not found
- DELETE conversation
- DELETE not found
- **Regression:** `test_before_from_other_conversation_is_ignored` — cross-conversation anchor returns all messages

### `tests/test_todos.py` (26 collected)
- POST /todos happy path (all fields)
- POST missing title → 422
- POST empty title → 422
- POST unauthenticated → 401
- GET todo by id
- GET not found → 404
- GET ownership isolation → 404
- GET list (own todos only)
- GET list unauthenticated → 401
- GET list filter=completed
- GET list invalid filter → 400
- GET list search q
- PUT todo (replace)
- PUT not found
- PATCH /complete
- PATCH /uncomplete
- PATCH complete not found
- DELETE soft delete (then 404 on GET)
- DELETE not found
- Deleted todo excluded from list
- **Unit:** `TestTodayRangeUtc` (4 tests)
  - span is exactly 1 day
  - start is local midnight
  - HCM = 17:00 UTC (UTC+7, no DST)
  - invalid TZ falls back to UTC
- **Regression:** today filter includes current moment, excludes far future

### `tests/test_orchestrator.py` (28 collected — Sprint 4 added memory tool + RAG tests)
- route pre-filter: chitchat patterns (empty tools list)
- route pre-filter: tool intent patterns (full tools list)
- route classifier (mocked LiteLLM)
- route classifier failure → fallback to TOOL_CALL
- route simple query filters write tools
- route chitchat has no tools
- orchestrator: plain text (no tool calls)
- orchestrator: tool call (create_todo) then synthesis
- orchestrator: hard cap at 5 tool calls
- orchestrator: loop detection (same tool 3x)
- orchestrator: tool failure result fed back to LLM (not RuntimeError)
- calc_cost: free model, gpt-4o-mini, unknown model
- **Regression:** `test_orchestrator_primary_intent_passes_none_to_chat_completion`
  - CHITCHAT route → `chat_completion(model=None, ...)`
- **Regression:** `test_orchestrator_fallback_intent_pins_model_string`
  - TOOL_CALL route → `chat_completion(model=settings.llm_fallback, ...)`

### `tests/test_datetime_parser.py` (12 tests)
- ISO 8601 fast path
- "chiều nay", "sáng mai", "tối nay" dict replace
- "X h Y" (hour notation)
- weekday references
- DD/MM date parsing
- time only (future resolve)
- LLM fallback (mocked)
- `ParseDatetimeError` when all fail

### `tests/test_reminders.py` (30 collected) — Sprint 5
- POST /reminders happy path (all fields)
- POST missing title/remind_at → 422
- POST remind_at in past → 422
- POST unauthenticated → 401
- GET /reminders/{id} happy path
- GET not found → 404, ownership isolation → 404
- GET /reminders list, filter by status
- PATCH /reminders/{id} update title/remind_at/description
- PATCH reject explicit null on title/remind_at → 422; description accepts null
- PATCH /cancel → status=cancelled
- DELETE soft delete
- **Sprint 5 tool executors:** execute_create_reminder, execute_list_reminders (Vietnamese datetime, past time → error)
- **Unit:** claim_pending_due — transitions status to `due`, ignores non-pending/deleted

### `tests/test_dashboard.py` (5 collected) — Sprint 5
- GET /dashboard/today authenticated
- todos_today count, overdue count
- reminders_upcoming ordering
- memories_count active only
- unauthenticated → 401

### `tests/test_reminders.py` — due/ack endpoints (Phase 4, added 9 tests)
- GET /v1/reminders/due → 200 `[]` when no due reminders
- GET /v1/reminders/due → 200 array containing only `status=due` items (pending excluded)
- GET /v1/reminders/due ownership isolation — user B's due reminders not returned to user A
- GET /v1/reminders/due unauthenticated → 401
- POST /v1/reminders/{id}/ack happy path → 200 `ReminderOut` with `status="sent"`
- POST /v1/reminders/{id}/ack non-due reminder → 409 `reminder_not_due`
- POST /v1/reminders/{id}/ack not found → 404 `reminder_not_found`
- POST /v1/reminders/{id}/ack ownership isolation → 404 (not 403)
- POST /v1/reminders/{id}/ack unauthenticated → 401

### `tests/test_rate_limit.py` (3 collected) — Sprint 5
- 429 response has correct format `{ "error": { "code": "rate_limit_exceeded", ... } }`
- Retry-After header present
- Rate limit applies to authenticated users

### `tests/test_memories.py` (22 collected) — Sprint 4
- POST /memories happy path (all fields)
- POST missing content → 422
- POST unauthenticated → 401
- GET /memories/{id} happy path
- GET not found → 404, ownership isolation → 404
- GET /memories list, filter by memory_type
- PATCH /memories/{id} update content/importance/type
- PATCH not found → 404
- DELETE soft delete (then 404 on GET)
- DELETE ownership isolation
- POST /memories/search (mocked semantic_search)
- **Unit:** `test_semantic_search_query_structure` — SQL builder correctness without DB

### `tests/test_tool_executors.py` (17 collected) — Sprint 4
- execute_create_todo, execute_list_todos, execute_update_todo
- execute_create_note, execute_search_notes
- execute_save_memory, execute_search_memory, execute_forget_memory
- Error paths: not found, ownership

### `tests/test_notes.py` (19 tests) — Sprint 3
- POST /notes happy path (all fields)
- POST missing title → 422, empty title → 422
- POST unauthenticated → 401
- GET /notes/{id} happy path
- GET not found → 404
- GET ownership isolation → 404
- GET /notes list empty, list returns created
- GET filter pinned=true
- GET search by q
- PATCH /notes/{id} update title+content
- PATCH not found → 404
- PATCH /pin → pinned=true; PATCH /unpin → pinned=false
- DELETE soft delete (then 404 on GET)
- DELETE not found → 404
- DELETE ownership (other user gets 404, original still exists)
- Pinned notes appear first in list

### `tests/test_health.py`
- GET /health → 200
- GET /health/ready → 200

---

## Running Tests

```powershell
cd backend

# All tests
pytest -v

# Specific file
pytest tests/test_todos.py -v

# Specific test
pytest tests/test_orchestrator.py::test_orchestrator_primary_intent_passes_none_to_chat_completion -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## Lint Before Tests

```powershell
ruff check . --fix    # auto-fix import sorting and style
ruff format .         # format all files
pytest                # then run tests
```

**Common ruff failures:**
- E401: import block with blank lines inside a function → `ruff check . --fix` fixes automatically
- E501: line too long → manually wrap

---

## Adding New Tests

### Pattern for new endpoint
```python
@pytest.mark.asyncio
async def test_create_note_happy_path(async_client, auth_headers):
    resp = await async_client.post("/v1/notes", json={"title": "Test", "content": "..."}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_note_unauthenticated(async_client):
    resp = await async_client.post("/v1/notes", json={"title": "Test"})
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_get_note_ownership(async_client, auth_headers):
    # Create as user A, try to GET as user B → 404
    ...
```

### Pattern for tool executor test
```python
@pytest.mark.asyncio
async def test_execute_create_note_happy_path():
    async with get_test_session() as db:
        user_id = uuid.uuid4()
        result = await execute_create_note(db, user_id, {"title": "Test"})
        assert result["success"] is True
        assert result["data"]["title"] == "Test"
```

### Pattern for LLM/orchestrator test
```python
@pytest.mark.asyncio
async def test_something_with_llm(async_client, auth_headers, mock_llm):
    # mock_llm fixture patches orchestrator.run
    resp = await async_client.post("/v1/chat/send", json={...}, headers=auth_headers)
    assert resp.status_code == 200
```

---

## E2E Tests (Playwright) — Sprint 6

```
frontend/e2e/
├── global-setup.ts     # Pre-warm Next.js JIT: fetch /auth/login + /
├── fixtures.ts         # registerAndLogin() — POST /auth/register + login via UI + waitForURL
├── auth.spec.ts        # Login → dashboard; wrong password → error (2 tests)
├── chat.spec.ts        # Send "Xin chào" (MOCK_LLM=1), verify response bubble or input cleared (1 test)
├── reminder.spec.ts    # Create via UI form → appears in reminders (1 test)
└── dashboard.spec.ts   # Dashboard stats cards visible (1 test)
```

**Key patterns:**
- `registerAndLogin()`: register via API, login via UI with `waitForResponse` + `waitForURL`
- `globalSetup`: fetch both routes before tests → eliminates cold-start flakiness
- `MOCK_LLM=1`: backend orchestrator returns deterministic response without calling real LLM
- `retries: 1` in CI only — local runs no retry

## Prompt Eval Set — Sprint 6

```
backend/tests/eval/
├── __init__.py
├── eval_cases.py       # 10 cases: E-01 to E-10
└── test_prompt_eval.py # pytest -m eval — calls real LLM, writes eval_results/YYYYMMDD_HHMM.json
```

- Only runs when `RUN_EVAL=1` env var set
- `addopts = "-v --tb=short -m 'not eval'"` in `pyproject.toml` — excluded from normal CI
- Target: ≥9/10 pass before any prompt/tool schema change

## What's NOT Tested Yet

- Frontend vitest unit tests (components, hooks)
- RAG end-to-end on real Postgres (SQLite tests mock semantic_search → `[]`) — manual test only
- In-app reminder polling end-to-end (scheduler marks due, frontend polls /due, acks /ack) — manual only; scheduler job runs every 60s, cannot simulate in SQLite unit tests
- Token refresh race condition
- LLM actual API calls (all mocked in tests)
- Alembic migration smoke test runs in CI (GitHub Actions `backend-migration-smoke` job with pgvector/pg16)
