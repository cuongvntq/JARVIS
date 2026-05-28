# Architecture

## Layered Architecture (Backend)

```
HTTP Request
    │
    ▼
[Router] app/routers/*.py
  - Validate request (Pydantic)
  - Auth via Depends(get_current_user)
  - Call service function
  - Return response schema
    │
    ▼
[Service] app/services/*.py
  - Business logic & orchestration
  - No HTTP objects (Request/Response)
  - Calls repositories for DB
  - Raises JarvisError for domain errors
    │
    ▼
[Repository] app/repositories/*.py
  - SQLAlchemy 2.0 queries ONLY
  - No business logic
  - Returns ORM objects
    │
    ▼
[Database] PostgreSQL via SQLAlchemy async
```

**Rule:** Never query DB in router. Never import FastAPI in service.

---

## Chat Request Flow (Sprint 2)

```
POST /v1/chat/send
    │
    ├─ chat_service.send_message()
    │     ├─ get_or_create conversation
    │     ├─ fetch prior history (last 20 msgs)
    │     ├─ add user Message to DB (flush)
    │     ├─ build_system_prompt(user) → (prompt, version)
    │     └─ orchestrator.run(...)
    │           ├─ router.route(user_message, all_tools)
    │           │     ├─ Stage 0: pre-filter regex
    │           │     └─ Stage 1: Gemini classifier (if no pre-filter match)
    │           │
    │           ├─ chat_completion(model=call_model, messages, tools)
    │           │     └─ LiteLLM → Gemini or gpt-4o-mini
    │           │
    │           └─ [tool loop, max 5 calls]
    │                 ├─ dispatch(tool_name, params, db, user_id, user_tz)
    │                 ├─ tool_log_repo.log_execution()
    │                 └─ feed result → next LLM call
    │
    ├─ add assistant Message to DB
    ├─ increment_message_count x2
    └─ return ChatSendResponse
```

---

## Auth Flow

```
POST /auth/register | /auth/login
    │
    ├─ auth_service.register() / login()
    │     ├─ validate password strength
    │     ├─ hash password (bcrypt)
    │     ├─ user_repo.create() | verify_password()
    │     ├─ create_access_token (JWT HS256, 15min)
    │     ├─ create_refresh_token (urlsafe_48, stored as SHA-256 hash)
    │     └─ auth_repo.create_session()
    │
    └─ set_refresh_cookie (HttpOnly, SameSite=lax, path=/auth)
       return TokenResponse { access_token, expires_in, user }

Refresh token rotation (atomic):
    UPDATE auth_sessions SET revoked_at=now WHERE hash=? AND revoked_at IS NULL
    RETURNING user_id, user_agent, ip_address
    → issue new pair
```

---

## Key Patterns

### Error Handling
```python
raise JarvisError(404, "todo_not_found", "Todo không tồn tại")
# → { "error": { "code", "message", "details", "request_id" } }
```

### DB Session
- `get_db()` dependency → `AsyncSession` via `async_sessionmaker`
- Service calls `flush()` for intermediate results, repository never commits
- Service commits after all writes: `await db.commit()`
- Tool executors use `commit=False` (orchestrator owns the commit via chat_service)

### Soft Delete
- Tables with `deleted_at`: `conversations`, `todos`
- All queries filter `WHERE deleted_at IS NULL`
- Never hard-delete via API handler

### Datetime
- Always UTC in DB (`TIMESTAMPTZ`)
- Use `datetime.now(UTC)`, never `datetime.utcnow()`
- Convert to user timezone at application layer using `zoneinfo.ZoneInfo`
- `user_tz` string flows: `chat_service` → `orchestrator.run()` → `dispatch()` → executor → `todo_service.list_todos()` → `todo_repo.list_todos()`

### Pagination
- Cursor-based: encode last item's `created_at` as base64
- `before_message_id` for chat history: anchor query MUST filter by `conversation_id` to prevent cross-conversation cursor leak

### Logging
```python
log = structlog.get_logger()
log.info("todo.created", todo_id=str(todo.id), user_id=str(user_id))
# Never log tokens, passwords, API keys
```

---

## System Prompt Architecture (4 parts)

```
Part A: Core Persona (static)
        JARVIS identity, role, language, tone

Part B: User Context (dynamic per request)
        user_id, name, timezone, now_utc, now_local, locale
        + Relevant Memories (Sprint 4: top-5 by similarity ≥0.7)
        + Conversation summary (Sprint 4: when >10 messages)

Part C: Tool Usage Rules (static)
        When to call tools, datetime parsing rules,
        reminder vs todo distinction, missing info behavior

Part D: Safety + Style (static)
        Prompt injection resistance, crisis response,
        response length/tone rules
```

`PROMPT_VERSION = "1.0.0-sprint2"` logged to `messages.metadata`.

---

## Frontend Architecture

```
app/layout.tsx              → QueryProvider + AuthGuard (wraps all pages)
app/page.tsx                → main page: manages conversationId state
app/auth/login/page.tsx     → login form
app/auth/register/page.tsx  → register form

components/
  auth/AuthGuard.tsx        → redirect if not logged in, silent token refresh
  chat/ChatInterface.tsx    → message list + useChatMutation
  chat/ChatInput.tsx        → textarea + send button
  chat/MessageBubble.tsx    → renders user/assistant messages
  layout/Sidebar.tsx        → conversation list + NEW CHAT button

hooks/
  useChatMutation.ts        → Tanstack mutation for POST /v1/chat/send
  useConversations.ts       → Tanstack query for GET /v1/chat/conversations + detail

lib/
  api.ts                    → ApiClient class (singleton `api`)
  types/api.ts              → TypeScript types matching backend schemas
  queryClient.ts            → Tanstack QueryClient singleton

stores/authStore.ts         → Zustand: user, accessToken, setAuth, clearAuth
providers/QueryProvider.tsx → wraps app with QueryClientProvider
```
