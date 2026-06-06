# API Contract — Implemented Endpoints

> Full planned spec (including future endpoints): `docs/02_API_Specification.md`
> This file covers what's **currently implemented and working** + what's planned for the active sprint.

Base URL: `http://localhost:8000` (dev)
Auth: `Authorization: Bearer <access_token>`
Error format: `{ "error": { "code", "message", "details", "request_id" } }`
Note: ALL exceptions (including FastAPI `HTTPException`) now return the unified envelope — `http_exception_handler` registered in `main.py` (Sprint 4 review fix).

---

## Not yet implemented (planned Sprint 6+)

- `POST /auth/google` — Google OAuth (removed from MVP 1 scope)
- Idempotency-Key header — post-MVP 1
- Conversation summarization — Sprint 6

---

## Rate Limiting — Sprint 5

- General endpoints: **60 req/min/user** (SlowAPI in-memory store)
- `/v1/chat/send`: **20 req/min/user**
- Error: `429` + `Retry-After` header, body: `{ "error": { "code": "rate_limit_exceeded", "message": "..." } }`

---

## Health

```
GET /health        → { "status": "ok" }
GET /health/ready  → { "status": "ready", "db": "ok" } | { "status": "degraded", "db": "<error_msg>" }
```
Note: `/health/ready` không set 503 khi DB lỗi — trả 200 với `status: "degraded"`.

---

## Auth (`/auth/`)

### POST /auth/register
Request: `{ "email", "password", "name" }`
Response 201: `{ "access_token", "expires_in": 900, "user": UserOut }`
Set-Cookie: `refresh_token=<raw>; HttpOnly; SameSite=lax; Path=/auth`
Errors: `409 email_taken`, `422 weak_password`

### POST /auth/login
Request: `{ "email", "password" }`
Response 200: same shape as register
Errors: `401 invalid_credentials`, `423 account_disabled`

### POST /auth/refresh
Cookie: `refresh_token` (or body `{ "refresh_token": "..." }` for API/test clients)
Response 200: `{ "access_token", "expires_in", "user" }` + new cookie (rotation)
Errors: `401 invalid_refresh_token`, `403 forbidden` (CSRF origin mismatch)

### POST /auth/logout → 204
### GET /auth/me → 200 UserOut

### PATCH /auth/me → 200 UserOut *(Sprint 4)*
Request: `{ "name"?, "timezone"?, "locale"?, "assistant_name"? }`
Errors: `422 invalid_timezone` (if timezone not a valid IANA string)

**UserOut:** `{ id, email, name, timezone, assistant_name, locale, avatar_url }`

---

## Chat (`/v1/chat/`)

### POST /v1/chat/send
```json
{ "conversation_id": "uuid|null", "content": "...(1-4000 chars)", "stream": false|true }
```
**Non-streaming** (`stream: false`) Response 200:
```json
{ "conversation_id": "uuid", "user_message": MessageOut, "assistant_message": MessageOut }
```
**Streaming** (`stream: true`) Response 200 `text/event-stream`:
```
data: {"type":"meta","conversation_id":"uuid","message_id":"uuid"}\n\n
data: {"type":"delta","content":"X"}\n\n   (multiple)
data: {"type":"done","content":"full text","model":"gemini-*","tokens_in":N,"tokens_out":N}\n\n
```
Error event: `{"type":"error","code":"llm_error","message":"..."}`

Note: stream error after `meta` event → backend rolls back DB, `conversation_id` becomes invalid.
Use `streamSucceeded` flag on FE to guard `onConversationCreated()` call.

**Rate limit:** 20 req/min/user.

**MessageOut:** `{ id, role, content, tokens_in, tokens_out, created_at }`
Errors: `404 conversation_not_found`, `502 llm_error`, `429 rate_limit_exceeded`

### GET /v1/chat/conversations?limit=20&cursor=
Response: `{ "items": [ConversationOut], "next_cursor": "base64|null" }`
**ConversationOut:** `{ id, title, last_message_at, message_count, created_at }`

### GET /v1/chat/conversations/{id}?before=<uuid>&limit=50
Response: `{ id, title, last_message_at, message_count, created_at, messages: [MessageOut], has_more: bool }`
- `before` = load messages older than this message_id (scroll-up pagination)
- `before` from a different conversation → ignored, returns from start
Errors: `404 conversation_not_found`

### PATCH /v1/chat/conversations/{id}
Request: `{ "title": "..." (1-255 chars) }`
Response 200: ConversationDetailOut

### DELETE /v1/chat/conversations/{id} → 204

---

## Todos (`/v1/todos`)

### GET /v1/todos
Query: `status?`, `filter?`, `q?`, `limit=20`, `cursor?`
- `filter`: `today | upcoming | overdue | completed | all`
- `today` filter: due_at in `[start_of_local_day_utc, end_of_local_day_utc)` AND status IN (pending, in_progress), uses JWT user's timezone
Errors: `400 invalid_status`, `400 invalid_filter`

### POST /v1/todos → 201
```json
{ "title": "(required, 1-500)", "description": null, "priority": "medium", "due_at": "ISO UTC|null", "tags": [], "source": "ui" }
```

### GET /v1/todos/{id} → 200 TodoOut | 404
### PUT /v1/todos/{id} → 200 (full replace, title required)
### PATCH /v1/todos/{id}/complete → 200 (sets status=completed, completed_at=now)
### PATCH /v1/todos/{id}/uncomplete → 200 (sets status=pending, completed_at=null)
### DELETE /v1/todos/{id} → 204 (soft delete)

**TodoOut:** `{ id, user_id, title, description, status, priority, due_at, completed_at, tags, source, created_at, updated_at }`

---

## Notes (`/v1/notes`)

### GET /v1/notes
Query: `pinned?` (bool), `q?`, `limit=20`, `cursor?`
- Pinned notes luôn đứng trước (order: pinned DESC, created_at DESC)

### POST /v1/notes → 201
```json
{ "title": "(required, 1-500)", "content": "", "tags": [], "pinned": false, "source": "ui" }
```

### GET /v1/notes/{id} → 200 NoteOut | 404
### PATCH /v1/notes/{id} → 200 (partial update — all fields optional)
```json
{ "title"?, "content"?, "tags"?, "pinned"? }
```
Note: all fields reject explicit null (422) — omit field to leave unchanged. (Sprint 5 review fix)

### PATCH /v1/notes/{id}/pin → 200
### PATCH /v1/notes/{id}/unpin → 200
### DELETE /v1/notes/{id} → 204 (soft delete)

**NoteOut:** `{ id, user_id, title, content, tags, pinned, source, created_at, updated_at }`

---

## Reminders (`/v1/reminders`) — Sprint 5

### GET /v1/reminders
Query: `status?` (pending|sending|sent|failed|cancelled), `limit=20`, `cursor?`
Response: `{ "items": [ReminderOut], "next_cursor": "base64|null" }`

### POST /v1/reminders → 201
```json
{ "title": "(required, 1-500)", "remind_at": "ISO UTC (required, must be future)", "description": null, "source": "ui" }
```
Errors: `422` if `remind_at` is in the past or missing

### GET /v1/reminders/{id} → 200 ReminderOut | 404
### PATCH /v1/reminders/{id} → 200 (partial update)
```json
{ "title"?, "remind_at"?, "description"? }
```
Note: `title` and `remind_at` reject explicit null (422). `description` accepts null (nullable DB column).

### PATCH /v1/reminders/{id}/cancel → 200 (sets status=cancelled)
### DELETE /v1/reminders/{id} → 204 (soft delete)

**ReminderOut:** `{ id, user_id, title, description, remind_at, status, source, created_at, updated_at }`
**ReminderStatus:** `pending | sending | sent | failed | cancelled`
Error codes: `reminder_not_found` (404)

---

## Dashboard (`/v1/dashboard`) — Sprint 5

### GET /v1/dashboard/today → 200
```json
{
  "todos_today":        [ TodoOut ],
  "todos_count":        { "today": N, "overdue": N, "upcoming": N },
  "reminders_upcoming": [ ReminderOut ],
  "memories_count":     N,
  "as_of":              "ISO UTC"
}
```
- `todos_today`: due today (user timezone), status IN (pending, in_progress)
- `reminders_upcoming`: top 5, status IN (pending, sending), remind_at >= now, ORDER BY remind_at ASC
- `memories_count`: count where is_active=true AND deleted_at IS NULL

---

## Memories (`/v1/memories`) — Sprint 4

### GET /v1/memories
Query: `memory_type?` (fact|preference|rule|relation|goal|other), `limit=20`, `cursor?`
Response: `{ "items": [MemoryOut], "next_cursor": "base64|null" }`

### POST /v1/memories → 201
```json
{ "memory_type": "fact", "content": "(1-2000 chars)", "importance": 5 }
```
Note: embedding generated async (background task) — may be null briefly after create.

### POST /v1/memories/search
Request: `{ "query": "...", "limit": 5, "min_similarity": 0.7 }`
Response: `{ "items": [MemoryOut], "count": N }` — no cursor (bounded by limit, no pagination)

### GET /v1/memories/{id} → 200 MemoryOut | 404
### PATCH /v1/memories/{id} → 200 (partial: content?, importance?, memory_type? — explicit null rejected with 422)
### DELETE /v1/memories/{id} → 204 (soft delete: sets is_active=false, deleted_at=now)

**MemoryOut:** `{ id, memory_type, content, importance, is_active, created_at, updated_at }`
Error codes: `memory_not_found` (404)

---

## AI Tools (called by LLM internally, not by HTTP client)

### create_todo
Params: `{ title* (1-500), description?, due_at? (ISO UTC), priority?, tags? }`

### list_todos
Params: `{ filter?: today|upcoming|overdue|completed|all, limit?: 1-50, q?: string }`

### update_todo
Params: `{ todo_id* (uuid), title?, description?, due_at?, priority?, status?, add_tags?, remove_tags? }`

### create_note
Params: `{ content* (1+), title?, tags?, pinned? }`

### search_notes
Params: `{ query* (1+), tag?, limit? (1-20) }`

### save_memory *(Sprint 4)*
Params: `{ memory_type* (enum), content* (3-500), importance? (1-10, default 5) }`

### search_memory *(Sprint 4)*
Params: `{ query* (1+), memory_type? (enum|null), limit? (1-10), min_similarity? (0-1, default 0.7) }`
Note: called by orchestrator automatically before each LLM turn (RAG).

### forget_memory *(Sprint 4)*
Params: `{ memory_id* (uuid) }`

### create_reminder *(Sprint 5)*
Params: `{ title* (1-500), remind_at* (ISO UTC, must be future), description?, source? }`
Note: executor validates remind_at is future; if past → `{ success: false, error: { code: "invalid_remind_at" } }`

### list_reminders *(Sprint 5)*
Params: `{ status?: pending|sending|sent|failed|cancelled, limit?: 1-20 }`

All tool responses: `{ success, data, summary, warnings }` or `{ success: false, error: {code, message}, data: null }`

---

## Error Codes (implemented)

| Code | HTTP | Condition |
|---|---|---|
| `email_taken` | 409 | Duplicate email on register |
| `weak_password` | 422 | <8 chars, missing letter or digit |
| `invalid_credentials` | 401 | Wrong email/password |
| `account_disabled` | 423 | user.is_active = false |
| `invalid_refresh_token` | 401 | Expired, revoked, or not found |
| `forbidden` | 403 | CSRF origin check failed |
| `conversation_not_found` | 404 | Conversation missing or belongs to other user |
| `todo_not_found` | 404 | Todo missing or belongs to other user |
| `note_not_found` | 404 | Note missing or belongs to other user |
| `memory_not_found` | 404 | Memory missing or belongs to other user *(Sprint 4)* |
| `reminder_not_found` | 404 | Reminder missing or belongs to other user *(Sprint 5)* |
| `invalid_status` | 400 | Unknown status query param |
| `invalid_filter` | 400 | Unknown filter query param |
| `invalid_timezone` | 422 | PATCH /auth/me with invalid IANA timezone *(Sprint 4)* |
| `rate_limit_exceeded` | 429 | Too many requests *(Sprint 5)* |
| `llm_error` | 502 | All LLM providers failed |
| `validation_error` | 422 | Pydantic schema failure |

---

## Pagination

All list endpoints use cursor-based pagination (base64-encoded `created_at`):
```
GET /v1/todos?limit=20               → first page, next_cursor: "eyJ..."
GET /v1/todos?limit=20&cursor=eyJ... → next page
next_cursor == null                  → last page
```
