# API Contract — Implemented Endpoints

> Full planned spec (including future endpoints): `docs/02_API_Specification.md`
> This file covers what's **currently implemented and working** + what's planned for the active sprint.

Base URL: `http://localhost:8000` (dev)
Auth: `Authorization: Bearer <access_token>`
Error format: `{ "error": { "code", "message", "details", "request_id" } }`

---

## Not yet implemented (in docs/02 but not built)

- `POST /auth/google` — Google OAuth (removed from MVP 1 scope)
- `PATCH /auth/me` — profile update **(Sprint 4 S4-4)**
- `/v1/memories/*` — **(Sprint 4 S4-2)**
- `/v1/reminders/*` — Sprint 5
- `/v1/dashboard/*` — Sprint 5
- Idempotency-Key header — post-MVP 1
- Rate limiting (429) — Sprint 5

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

**MessageOut:** `{ id, role, content, tokens_in, tokens_out, created_at }`
Errors: `404 conversation_not_found`, `502 llm_error`

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
### PATCH /v1/notes/{id}/pin → 200
### PATCH /v1/notes/{id}/unpin → 200
### DELETE /v1/notes/{id} → 204 (soft delete)

**NoteOut:** `{ id, user_id, title, content, tags, pinned, source, created_at, updated_at }`

---

## Memories (`/v1/memories`) — Sprint 4

### GET /v1/memories
Query: `type?` (fact|preference|rule|relation|goal|other), `limit=20`, `cursor?`
Response: `{ "items": [MemoryOut], "next_cursor": "base64|null" }`

### POST /v1/memories → 201
```json
{ "memory_type": "fact", "content": "(3-500 chars)", "importance": 5 }
```
Note: embedding generated async via `asyncio.create_task()` — may be null briefly after create.

### POST /v1/memories/search
Request: `{ "query": "...", "limit": 5, "min_similarity": 0.7 }`
Response: `{ "items": [MemoryOut], "count": N }`

### GET /v1/memories/{id} → 200 MemoryOut | 404
### PATCH /v1/memories/{id} → 200 (partial: content?, importance?, memory_type?)
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
| `invalid_status` | 400 | Unknown status query param |
| `invalid_filter` | 400 | Unknown filter query param |
| `invalid_timezone` | 422 | PATCH /auth/me with invalid IANA timezone *(Sprint 4)* |
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
