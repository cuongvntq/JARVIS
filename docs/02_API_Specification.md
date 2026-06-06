# TÀI LIỆU 2: API SPECIFICATION
## J.A.R.V.I.S Personal AI Assistant — MVP 1

**Phiên bản:** 1.0
**Base URL:** `https://api.jarvis.local/v1`
**Content-Type:** `application/json` (mặc định, UTF-8)
**Auth:** Bearer JWT (header `Authorization: Bearer <access_token>`)

---

## 1. NGUYÊN TẮC API

1. **REST + JSON**, version trong URL (`/v1`).
2. **Mọi datetime** ISO 8601 UTC (`2026-05-18T10:30:00Z`). Client convert sang timezone.
3. **Pagination chuẩn:** `?limit=20&cursor=<base64>` (cursor-based), trả về `next_cursor`.
4. **Error format đồng nhất** (xem §3).
5. **Idempotency** cho POST quan trọng bằng header `Idempotency-Key: <uuid>` (TTL 24h).
6. **Rate limit:** 60 req/phút/user cho endpoint thường, 20 req/phút cho `/chat/send`.
7. **CORS** chỉ allow origin của FE.
8. **JWT access token** TTL 15 phút, refresh token TTL 30 ngày (rotating).

---

## 2. AUTHENTICATION

> **Cookie flow (browser):** `/auth/register` và `/auth/login` set `refresh_token` qua
> `Set-Cookie: refresh_token=...; HttpOnly; SameSite=Lax; Path=/auth`.
> Browser tự gửi cookie này khi gọi `/auth/refresh` hoặc `/auth/logout` (không cần body).
> API/test clients có thể gửi `{ "refresh_token": "..." }` trong body thay thế.
>
> **Production cross-site** (Vercel → Railway): set `COOKIE_SAMESITE=none` và `COOKIE_SECURE=true` trong env.
> Email tự động normalize về lowercase.

### `POST /auth/register`
Đăng ký bằng email/password.
```json
// Request
{ "email": "user@example.com", "password": "Strong@123", "name": "Nguyễn Văn A" }

// 201 Created — refresh_token KHÔNG có trong body; được set qua HttpOnly cookie
{ "access_token": "eyJ...", "expires_in": 900,
  "user": { "id": "uuid", "email": "user@example.com", "name": "Nguyễn Văn A",
            "timezone": "Asia/Ho_Chi_Minh", "assistant_name": "JARVIS", "locale": "vi-VN" } }
// Header: Set-Cookie: refresh_token=<raw>; HttpOnly; SameSite=Lax; Path=/auth; Max-Age=2592000
```
**Errors:** `409` email_taken · `422` weak_password (min 8, có chữ + số).

### `POST /auth/login`
```json
// Request
{ "email": "user@example.com", "password": "Strong@123" }

// 200 OK — cùng shape với /auth/register
{ "access_token": "eyJ...", "expires_in": 900, "user": { ... } }
// Header: Set-Cookie: refresh_token=...; HttpOnly; ...
```
**Errors:** `401` invalid_credentials · `423` account_disabled.

### `POST /auth/google`
```json
{ "id_token": "<google-id-token>" }
// 200 OK: same shape as /auth/login
```

### `POST /auth/refresh`
Browser gửi tự động qua cookie. API clients dùng body fallback.
```json
// Request (optional body — chỉ cần nếu không có cookie)
{ "refresh_token": "..." }

// 200 OK — token mới (rotation); cookie mới được set
{ "access_token": "eyJ...", "expires_in": 900, "user": { ... } }
```
**Errors:** `401` invalid_refresh_token.

### `POST /auth/logout`
Browser gửi cookie tự động, không cần body. **204 No Content**.
Cookie `refresh_token` bị xóa. Token đã dùng bị revoke.

### `GET /auth/me`
Trả về profile hiện tại. **200 OK** kèm user object.

### `PATCH /auth/me`
Cập nhật profile.
```json
{ "name": "...", "timezone": "Asia/Ho_Chi_Minh", "assistant_name": "JARVIS", "locale": "vi-VN" }
```

---

## 3. ERROR FORMAT

Mọi lỗi đều theo format dưới đây với HTTP status code phù hợp.
```json
{
  "error": {
    "code": "todo_not_found",
    "message": "Todo with id 'abc' does not exist or has been deleted.",
    "details": { "todo_id": "abc" },
    "request_id": "req_01HXYZ..."
  }
}
```

**Bảng mã lỗi:**

| HTTP | code | Ý nghĩa |
|------|------|---------|
| 400 | `bad_request`, `invalid_param` | Body/param sai định dạng |
| 401 | `unauthenticated`, `token_expired`, `invalid_token` | Thiếu/sai JWT |
| 403 | `forbidden` | Không có quyền (FK đến user khác) |
| 404 | `not_found`, `todo_not_found`, `memory_not_found`, ... | Resource không tồn tại |
| 409 | `conflict`, `email_taken`, `idempotency_conflict` | Xung đột state |
| 422 | `validation_error`, `weak_password`, `missing_remind_at` | Logic validation |
| 429 | `rate_limited` | Quá rate (kèm header `Retry-After`) |
| 500 | `internal_error`, `llm_error`, `db_error` | Server bug |
| 502 | `upstream_error` | LLM provider lỗi |
| 503 | `service_unavailable` | Maintenance |
| 504 | `timeout`, `llm_timeout` | LLM không trả lời trong SLA |

---

## 4. CHAT API

### `POST /chat/send`
Gửi message → trả về assistant response (có thể stream).
```json
// Request
{
  "conversation_id": "uuid|null",   // null = tạo mới
  "content": "Thêm việc mua sữa chiều nay",
  "stream": false                    // true để nhận SSE
}

// 200 OK (non-stream)
{
  "conversation_id": "uuid",
  "user_message": { "id": "...", "role": "user", "content": "...", "created_at": "..." },
  "assistant_message": {
    "id": "...", "role": "assistant",
    "content": "Đã thêm việc 'mua sữa' lúc 18:00 hôm nay.",
    "tool_calls": [
      { "tool": "create_todo", "input": {...}, "output": {...}, "status": "success" }
    ],
    "tokens": { "in": 540, "out": 80 },
    "created_at": "..."
  }
}
```
**Stream mode** (`stream=true`) trả về SSE với các event: `message_start`, `content_delta`, `tool_call`, `tool_result`, `message_end`.

**Errors:** `422` empty_content · `429` rate_limited · `504` llm_timeout · `502` llm_error.

### `GET /chat/conversations`
```
?limit=20&cursor=<...>
```
```json
// 200 OK
{
  "items": [
    { "id": "uuid", "title": "...", "last_message_at": "...", "message_count": 12 }
  ],
  "next_cursor": "..." | null
}
```

### `GET /chat/conversations/{id}`
```json
// 200 OK
{
  "id": "uuid", "title": "...", "created_at": "...",
  "messages": [
    { "id": "...", "role": "user", "content": "...", "created_at": "..." },
    { "id": "...", "role": "assistant", "content": "...", "tool_calls": [...] }
  ],
  "next_cursor": null
}
```
Query: `?before=<message_id>&limit=50` để phân trang ngược (load older).

### `PATCH /chat/conversations/{id}`
Đổi title. Body: `{ "title": "..." }`. **200 OK**.

### `DELETE /chat/conversations/{id}`
Soft delete. **204 No Content**.

---

## 5. TODO API

### `GET /todos`
```
?status=pending|in_progress|completed|cancelled|overdue
&filter=today|upcoming|overdue|all     (high-level filter, ưu tiên hơn status nếu cùng truyền)
&q=<search text>
&limit=20&cursor=...
```
```json
// 200 OK
{
  "items": [
    { "id": "uuid", "title": "Mua sữa", "status": "pending", "priority": "medium",
      "due_at": "2026-05-18T11:00:00Z", "tags": [], "created_at": "..." }
  ],
  "next_cursor": null,
  "total": 12
}
```

### `POST /todos`
```json
// Request
{ "title": "Mua sữa", "description": null, "priority": "medium",
  "due_at": "2026-05-18T11:00:00Z", "tags": ["mua sắm"] }

// 201 Created → todo object
```
**Errors:** `422` invalid_priority, `422` invalid_due_at (in past > 1 day cảnh báo).

### `GET /todos/{id}` → todo object.

### `PUT /todos/{id}`
Update tất cả field cho phép. Trả về todo mới.

### `PATCH /todos/{id}/complete`
Set status=completed, completed_at=NOW(). **200 OK**.

### `PATCH /todos/{id}/uncomplete`
Set status=pending, completed_at=NULL. **200 OK**.

### `DELETE /todos/{id}` → soft delete. **204**.

---

## 6. NOTES API

### `GET /notes`
```
?q=<search>&tag=<tag>&pinned=true|false&limit=20&cursor=...
```

### `POST /notes`
```json
{ "title": "Ý tưởng app", "content": "...", "tags": ["idea"], "pinned": false }
// 201 Created
```

### `GET /notes/{id}` · `PUT /notes/{id}` · `DELETE /notes/{id}` (soft).

### `POST /notes/search`
Full-text + tag combo.
```json
// Request
{ "query": "tiếng nhật", "tags": ["learning"], "limit": 10 }
// 200 OK: { "items": [...] }
```

---

## 7. REMINDERS API

### `GET /reminders`
```
?status=scheduled|sent|cancelled&from=<iso>&to=<iso>&limit=20&cursor=...
```

### `POST /reminders`
```json
{ "title": "Uống thuốc", "description": null, "remind_at": "2026-05-18T13:00:00Z" }
// 201 Created
```
**Errors:** `422` missing_remind_at · `422` remind_at_in_past.

### `PUT /reminders/{id}` — sửa khi status='scheduled'. **409** nếu đã sent.

### `DELETE /reminders/{id}` — soft delete (đồng thời set status='cancelled'). **204**.

---

## 8. MEMORY API

### `GET /memories`
```
?type=fact|preference|rule|relation|goal|other
&is_active=true|false
&limit=20&cursor=...
```

### `POST /memories`
```json
{ "memory_type": "preference", "content": "Tôi thích cà phê đen không đường", "importance": 7 }
// 201 Created (server auto-embed)
```

### `PUT /memories/{id}` — sửa content/importance/is_active.

### `DELETE /memories/{id}` — soft delete. **204**.

### `POST /memories/search`
Semantic search (vector).
```json
// Request
{ "query": "tôi uống gì buổi sáng", "limit": 5, "min_similarity": 0.7 }
// 200 OK
{ "items": [ { "id": "...", "content": "...", "memory_type": "preference", "similarity": 0.84 } ] }
```

---

## 9. DASHBOARD API

### `GET /dashboard/today`
```json
// 200 OK
{
  "date": "2026-05-18",
  "timezone": "Asia/Ho_Chi_Minh",
  "todos_today":   [ /* todo objects */ ],
  "todos_overdue": [ /* todo objects */ ],
  "reminders_today": [ /* reminder objects */ ],
  "counts": { "todos_today": 5, "completed_today": 2, "overdue": 1, "reminders_today": 3 }
}
```

### `GET /dashboard/briefing`
Tóm tắt tự nhiên do AI sinh (cache 1h).
```json
{
  "briefing": "Chào buổi sáng! Hôm nay bạn có 3 việc, đáng chú ý nhất là...",
  "generated_at": "2026-05-18T01:00:00Z"
}
```

---

## 10. REMINDER POLLING ENDPOINTS (Phase 4 — replaces Web Push)

### `GET /v1/reminders/due`
Returns reminders with `status=due` for the current user (scheduler has already transitioned them from `pending`).

**Response 200:**
```json
{ "items": [ReminderOut], "next_cursor": null }
```

### `POST /v1/reminders/{id}/ack`
Frontend calls this after displaying the in-app toast. Transitions status `due → sent`.

- **204** on success
- **409** if reminder is not in `due` status (already acked or cancelled)
- **404** if reminder not found or belongs to another user

---

## 11. SETTINGS API

### `GET /settings` → user settings (timezone, assistant_name, locale, notification prefs).

### `PUT /settings` → cập nhật.

### `POST /settings/export-data`
Xuất toàn bộ data của user dạng ZIP (todos, notes, memories, conversations) — GDPR-style.

### `DELETE /settings/account`
Xóa hard toàn bộ account (cần password confirm trong body). **204**.

---

## 12. HEALTH & META

| Endpoint | Mục đích |
|----------|---------|
| `GET /health` | Liveness, không cần auth. `{ "status": "ok" }` |
| `GET /health/ready` | Readiness (check DB + LLM). |
| `GET /meta/version` | Build version, commit SHA. |

---

## 13. RATE LIMIT HEADERS

Mọi response trả kèm:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1747562400
```

---

## 14. STREAM EVENT (Chat SSE)

```
event: message_start
data: {"message_id":"...","conversation_id":"..."}

event: content_delta
data: {"delta":"Đã thêm "}

event: content_delta
data: {"delta":"việc 'mua sữa'..."}

event: tool_call
data: {"tool":"create_todo","input":{...}}

event: tool_result
data: {"tool":"create_todo","output":{...},"status":"success"}

event: message_end
data: {"tokens":{"in":540,"out":80}}
```

---

## 15. CHECKLIST IMPLEMENT API

- [ ] Middleware: auth (JWT verify), CORS, rate-limit, request_id, error formatter.
- [ ] Validation: dùng Pydantic (FastAPI) hoặc Zod (Next.js).
- [ ] OpenAPI tự sinh từ code (FastAPI có sẵn, Next.js dùng `zod-to-openapi`).
- [ ] Test integration cho mọi endpoint (happy + 1 error path mỗi cái).
- [ ] Postman collection / Bruno collection để QA test tay.
