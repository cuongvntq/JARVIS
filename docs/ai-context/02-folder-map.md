# Folder Map & File Purpose

## Repository Root

```
Javis/
├── backend/                    # FastAPI Python backend
├── frontend/                   # Next.js 15 frontend + Tauri desktop wrapper
├── docs/                       # Technical documentation
│   ├── ai-context/             # AI session context (this folder)
│   ├── migration-desktop-app.md # Tauri desktop migration plan + lessons learned
│   ├── 01_Database_Schema_ERD.md
│   ├── 02_API_Specification.md
│   ├── 03_AI_Tool_Schemas.md
│   ├── 04_System_Prompt.md
│   ├── 05_Tech_Stack_Decision.md
│   ├── 05c_Tiered_Routing_Strategy.md
│   └── 06_Updated_Execution_Plan.md
├── .claude/rules/              # Claude Code rules per layer
├── .env.example                # Env var template
├── CLAUDE.md                   # Main instructions for Claude Code
└── MEMORY.md                   # (in ~/.claude/projects/.../memory/)
```

---

## Backend: `backend/`

```
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, middleware, routers registration
│   │                           # Sprint 5: + lifespan (APScheduler start/stop) + SlowAPI state + rate_limit exception handler
│   ├── config.py               # Settings (pydantic-settings), get_settings() lru_cache
│   │                           # Sprint 4: + embedding_model, embedding_dim
│   │                           # Sprint 5: + backend_port; Phase 4: removed vapid_* fields
│   ├── database.py             # SQLAlchemy engine, AsyncSessionLocal, Base, get_db()
│   │
│   ├── core/
│   │   ├── deps.py             # get_current_user() FastAPI dependency (JWT → User)
│   │   ├── errors.py           # JarvisError, RequestIDMiddleware, exception handlers; Sprint 4: + http_exception_handler (unified HTTPException → { error: ... })
│   │   └── security.py         # JWT encode/decode, bcrypt hash/verify, token helpers
│   │
│   ├── middleware/
│   │   └── rate_limit.py       # SlowAPI limiter setup, in-memory store; Sprint 5 (S5-5)
│   │
│   ├── models/                 # SQLAlchemy ORM models (table definitions)
│   │   ├── user.py             # User, AuthSession; +notes relationship; Sprint 4: +memories relationship; Sprint 5: +reminders relationship
│   │   ├── conversation.py     # Conversation, Message; Sprint 4 stretch: +summary column
│   │   ├── todo.py             # Todo
│   │   ├── note.py             # Note
│   │   ├── memory.py           # Memory — embedding=sa.JSON (SQLite compat)
│   │   ├── reminder.py         # Reminder — status ENUM (pending|sending|sent|failed|cancelled); Sprint 5
│   │   └── tool_log.py         # ToolExecutionLog, LLMCallLog
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserOut, RefreshRequest
│   │   │                       # Sprint 4: + UserUpdateRequest (for PATCH /auth/me)
│   │   ├── chat.py             # ChatSendRequest/Response, ConversationOut/Detail/List, MessageOut
│   │   ├── todo.py             # TodoCreate, TodoReplace, TodoPartialUpdate, TodoOut, TodoListOut
│   │   ├── note.py             # NoteCreate, NoteUpdate, NotePatch, NoteOut, NoteListOut
│   │   │                       # Sprint 5: NoteUpdate + field_validator reject explicit null (→422 not 500)
│   │   ├── memory.py           # MemoryCreate, MemoryUpdate, MemoryOut, MemoryListOut
│   │   └── reminder.py         # ReminderCreate, ReminderUpdate, ReminderOut, ReminderListOut, ReminderStatus; Sprint 5
│   │                           # ReminderUpdate: reject null on title+remind_at; description nullable (can be set to null)
│   │
│   ├── routers/                # FastAPI route handlers (thin: validate → service → return)
│   │   ├── auth.py             # /auth/register, login, refresh, logout, me; Sprint 4: + PATCH /auth/me
│   │   ├── chat.py             # /v1/chat/send (non-stream + SSE stream), conversations CRUD
│   │   │                       # Sprint 5: @limiter.limit("20/minute") on /v1/chat/send
│   │   ├── todos.py            # /v1/todos CRUD
│   │   ├── notes.py            # /v1/notes CRUD + pin/unpin
│   │   ├── memories.py         # /v1/memories CRUD + /search
│   │   ├── reminders.py        # /v1/reminders CRUD + /cancel + /due + /{id}/ack; Sprint 5; Phase 4: +due/ack
│   │   ├── dashboard.py        # /v1/dashboard/today; Sprint 5
│   │   └── health.py           # /health, /health/ready
│   │
│   ├── services/               # Business logic
│   │   ├── auth_service.py     # register, login, refresh_tokens, logout; Sprint 4: + update_profile()
│   │   ├── chat_service.py     # send_message (non-stream + stream_message generator);
│   │   │                       # Sprint 4: + RAG call (search_semantic) before build_system_prompt
│   │   │                       # Sprint 6: + _bg_tasks set + _schedule_summarize() (strong ref, RUF006)
│   │   ├── todo_service.py     # create, get, list, replace, patch, complete, uncomplete, delete
│   │   ├── note_service.py     # create, get, list, update, patch, pin, unpin, delete
│   │   ├── embedding_service.py # embed_text(text) → list[float] via LiteLLM aembedding
│   │   ├── memory_service.py   # create (+async embed task), create_committed (tool path), search_semantic, get, list, update, forget
│   │   ├── reminder_service.py # create (validate remind_at future), get, list, update, cancel, delete; Sprint 5
│   │   ├── scheduler_service.py # APScheduler (max_instances=1, coalesce=True), check_reminders() job 60s; Sprint 5
│   │   │                        # Phase 4: marks pending→due (no push), frontend polls /due + acks /ack
│   │   └── dashboard_service.py # get_today_dashboard(db, user_id, user_tz) → DashboardOut; Sprint 5
│   │
│   ├── repositories/           # DB queries (SQLAlchemy 2.0, no business logic)
│   │   ├── user_repo.py        # get_by_email, get_by_id, create, update_last_login; Sprint 4: + update_fields()
│   │   ├── auth_repo.py        # create_session, get_session_by_hash, revoke_session, atomic_revoke_session
│   │   ├── conversation_repo.py # get_or_create, add_message, list, get_conversation, get_messages_page,
│   │   │                        # update_title, soft_delete; Sprint 4 stretch: + update_summary()
│   │   ├── todo_repo.py        # get_by_id, list_todos, create, update_fields, complete, uncomplete, soft_delete, _today_range_utc()
│   │   ├── note_repo.py        # get_by_id, list_notes (pinned/q/cursor), create, update_fields, soft_delete
│   │   ├── memory_repo.py      # create, get_by_id, list_memories, update_fields, update_embedding,
│   │   │                       # soft_delete, _build_semantic_search_stmt(), semantic_search (SQLite→[])
│   │   ├── reminder_repo.py    # get_by_id, list_reminders, create, update_fields, cancel, soft_delete,
│   │   │                       # get_pending_due(before_utc), claim_pending_due() — atomic UPDATE...RETURNING; Sprint 5
│   │   ├── tool_log_repo.py    # log_execution()
│   │   └── llm_call_log_repo.py # log_call() + _calc_cost()
│   │
│   ├── llm/                    # LLM layer
│   │   ├── client.py           # chat_completion() — LiteLLM wrapper, primary→fallback chain
│   │   ├── models.py           # LLMResponse dataclass, ToolCall dataclass
│   │   ├── router.py           # route() — Stage 0 pre-filter + Stage 1 Gemini classifier, RouteResult, Intent enum
│   │   ├── orchestrator.py     # run() — full tool loop, OrchestratorResult, _execute_tool()
│   │   └── prompt.py           # build_system_prompt(user, memories?, summary?) → (str, PROMPT_VERSION)
│   │                           # Sprint 4: _PART_C updated (+3 memory tools), PROMPT_VERSION="1.0.0-sprint4"
│   │                           # Sprint 5: PROMPT_VERSION unchanged — no prompt schema changes in Sprint 5
│   │
│   ├── tools/                  # Tool system
│   │   ├── definitions.py      # TOOLS list; Sprint 3: 5 schemas; Sprint 4: 8 schemas; Sprint 5: 10 schemas (+create_reminder, list_reminders)
│   │   └── executors.py        # dispatch(); Sprint 3: 5 executors; Sprint 4: +3 memory; Sprint 5: +2 reminder executors
│   │
│   └── utils/
│       └── datetime_parser.py  # parse_datetime() — ISO fast path → dict replace → regex → LLM fallback
│
├── vi_time_dict.json           # ~40 Vietnamese time expression mappings
├── jarvis_server.py            # PyInstaller entry point — reads .env từ exe dir, start uvicorn
├── jarvis_server.spec          # PyInstaller build spec — collect_all(litellm+tiktoken), hiddenimports, onefile
│
├── migrations/
│   ├── env.py                  # Alembic env config
│   └── versions/
│       ├── 001_init_extensions.py          # uuid-ossp, pgcrypto, pg_trgm, vector
│       ├── 002_create_core_tables.py       # users, auth_sessions, conversations, messages + ENUM message_role
│       ├── 003_sprint2_todos_tool_logs.py  # todos, tool_execution_logs, llm_call_logs + ENUMs
│       ├── 004_sprint3_notes.py            # notes table
│       ├── 005_sprint4_memories.py         # memories + ENUM memory_type + HNSW index
│       ├── 006_sprint5_reminders.py        # reminders + ENUM reminder_status (pending|due|sent|failed|cancelled); Sprint 5
│       └── 007_add_summary_to_conversations.py # ADD COLUMN summary TEXT to conversations; Sprint 6
│
└── tests/
    ├── conftest.py             # SQLite in-memory, fixtures: async_client, auth_headers, mock_llm,
    │                           # mock_llm_stream, mock_llm_stream_error,
    │                           # mock_embedding, mock_semantic_search, auth_headers_user_b
    ├── eval/                   # Prompt eval set — chỉ chạy khi RUN_EVAL=1; Sprint 6
    │   ├── __init__.py
    │   ├── eval_cases.py       # 10 eval cases (E-01 to E-10)
    │   └── test_prompt_eval.py # pytest -m eval — gọi real LLM, ghi kết quả vào eval_results/
    ├── test_auth.py            # Auth endpoint tests (23 tests)
    ├── test_chat.py            # Chat + conversation CRUD + streaming + RAG tests (18 tests)
    ├── test_todos.py           # Todo CRUD + filter + ownership (26 collected)
    ├── test_notes.py           # Note CRUD + pin/unpin + search + ownership (19 tests)
    ├── test_memories.py        # Memory CRUD + search + ownership + query structure (22 tests)
    ├── test_reminders.py       # Reminder CRUD + cancel + due/ack endpoints + ownership (214 lines); Sprint 5; Phase 4: +9 tests
    ├── test_dashboard.py       # Dashboard today summary tests (5 collected); Sprint 5
    ├── test_rate_limit.py      # SlowAPI 429 response format (3 collected); Sprint 5
    ├── test_orchestrator.py    # Orchestrator + router + fallback chain + memory tools (28 collected)
    ├── test_tool_executors.py  # Tool executor unit tests: todo/note/memory/summary (17 collected)
    ├── test_datetime_parser.py # Datetime parser tests (12 collected)
    └── test_health.py          # Health endpoint tests (2 collected)
```

**Total: ~214 tests collected** (`pytest --collect-only`; some functions expand via `@pytest.mark.parametrize`)
Per-file breakdown: auth=23, chat=18, todos=26, notes=19, memories=22, reminders=~39, dashboard=5, rate_limit=3, orchestrator=28, tool_executors=17, datetime_parser=12, health=2

---

## Tauri: `frontend/src-tauri/`

```
frontend/src-tauri/
├── src/
│   ├── main.rs                 # Entry point (calls lib::run)
│   └── lib.rs                  # Sidecar spawn (#[cfg(not(debug_assertions))]) + kill on Destroyed
│                               # BackendProcess(Mutex<Option<CommandChild>>) managed state
├── capabilities/
│   └── default.json            # core:default only — sidecar spawn là Rust-side, không cần JS shell permission
├── binaries/
│   └── jarvis-server-x86_64-pc-windows-msvc.exe  # PyInstaller onefile (~106MB, NOT committed to git)
├── icons/                      # App icons (32x32, 128x128, icns, ico)
├── gen/schemas/                # Auto-generated Tauri capability schemas
├── Cargo.toml                  # tauri, tauri-plugin-shell, tauri-plugin-log deps
└── tauri.conf.json             # productName=JARVIS, externalBin=binaries/jarvis-server, security.csp=null
```

> **Quan trọng:** `binaries/*.exe` (~106MB) KHÔNG commit vào git. Trước khi `tauri build`: chạy `cd backend && uv sync --extra dev` rồi `.\scripts\build-sidecar.ps1` từ repo root (tự build + copy đúng tên target triple).

---

## Frontend: `frontend/src/`

```
frontend/src/
├── instrumentation.ts          # Sentry server/edge init (Next.js App Router hook); Sprint 6
│
├── app/
│   ├── layout.tsx              # Root layout: QueryProvider + AuthGuard
│   ├── page.tsx                # Single-page section nav (Dashboard|Chat|Todo|Reminders|Notes|Memory|Settings);
│   │                           # Sprint 5: Dashboard is default section; mount RemindersPage + DashboardPage
│   ├── global-error.tsx        # React render error boundary — captureException to Sentry; Sprint 6
│   └── auth/
│       ├── layout.tsx          # Auth pages layout (no sidebar)
│       ├── login/page.tsx      # Login form
│       └── register/page.tsx   # Register form
│
├── components/
│   ├── auth/
│   │   └── AuthGuard.tsx       # Redirect if not logged in; calls api.me() to restore session
│   ├── chat/
│   │   ├── ChatInterface.tsx   # Message list, history; for-await SSE loop; streamSucceeded guard
│   │   ├── ChatInput.tsx       # Textarea + send button
│   │   └── MessageBubble.tsx   # User/assistant message rendering; streaming/toolStatus props
│   ├── dashboard/              # Sprint 5
│   │   ├── DashboardPage.tsx   # Section root; grid layout; refetchInterval 5min
│   │   ├── TodayStats.tsx      # Count cards (today / overdue / upcoming todos)
│   │   ├── UpcomingReminders.tsx # Next 5 reminders + countdown to remind_at
│   │   └── MemoryCount.tsx     # Memory count chip
│   ├── memories/
│   │   ├── MemoryCard.tsx      # Type badge (6 types), content, importance dots, edit/delete on hover
│   │   ├── MemoryList.tsx      # Filter chips by type, grid list, empty state; isSaving prop → disable actions
│   │   ├── MemoryEditor.tsx    # content textarea, type select, importance slider; validationError state; disable fields + close when isSaving
│   │   └── MemoryPage.tsx      # Section root; EditorState discriminated union { mode: closed|create|edit }
│   ├── reminders/              # Sprint 5
│   │   ├── RemindersPage.tsx   # Section root; filter tabs upcoming/sent/all; EditorState pattern
│   │   ├── ReminderCard.tsx    # Status badge, countdown to remind_at, cancel/delete actions
│   │   └── CreateReminderDialog.tsx # Modal dialog: title + datetime input + submit
│   ├── settings/
│   │   └── SettingsPage.tsx    # Form: name, assistant_name, timezone select (11 IANA), locale select (vi-VN/en-US)
│   ├── todos/
│   │   ├── TodoPage.tsx        # Section root; filter tabs; empty state
│   │   ├── TodoCard.tsx        # Status checkbox, title, due_at, priority badge, delete
│   │   └── CreateTodoDialog.tsx # Modal dialog: title + due_at + priority + submit
│   ├── notes/
│   │   ├── NoteEditor.tsx      # title/content/tags inputs; validationError state; disable fields + close when isSaving
│   │   ├── NoteList.tsx        # Search, pinned/all sections; isSaving prop → disable select/pin/delete
│   │   └── NotesPage.tsx       # isSaving guards on all navigation handlers; MỚI button disabled when isSaving
│   └── layout/
│       └── Sidebar.tsx         # Conversation list + NEW CHAT + nav links (Dashboard|Chat|Todos|Reminders|Notes|Memory|Settings)
│
├── hooks/
│   ├── useChatMutation.ts      # Tanstack useMutation → api.sendMessage()
│   ├── useConversations.ts     # useQuery list + detail; invalidates on send
│   ├── useDashboard.ts         # useQuery GET /v1/dashboard/today, refetchInterval 5min; Sprint 5
│   ├── useMemories.ts          # useInfiniteQuery (cursor), useCreateMemory, useUpdateMemory, useDeleteMemory
│   ├── useNotes.ts             # useInfiniteQuery (cursor), useCreateNote, useUpdateNote, usePinNote, useDeleteNote
│   ├── useReminderPolling.ts   # polls GET /v1/reminders/due (60s), shows toast (manual dismiss → ack), POSTs /ack; Phase 4
│   ├── useReminders.ts         # useInfiniteQuery (cursor), useCreateReminder, useCancelReminder, useDeleteReminder; Sprint 5
│   ├── useSettings.ts          # useMutation → PATCH /auth/me + setAuth to update authStore
│   └── useTodos.ts             # useInfiniteQuery (cursor), useCreateTodo, useCompleteTodo, useDeleteTodo
│
├── lib/
│   ├── api.ts                  # ApiClient; Sprint 5: + reminder/dashboard/notification methods;
│   │                           # clearAuth() + _accessToken=null on silentRefresh fail (review fix)
│   ├── queryClient.ts          # Tanstack QueryClient singleton
│   ├── utils.ts                # Utility helpers (cn() classname merge)
│   └── types/api.ts            # TypeScript types: all API response/request types including Sprint 5
│                               # (ReminderOut, ReminderCreate, ReminderUpdate, ReminderListOut, DashboardOut, SSEEvent)
│
├── providers/
│   └── QueryProvider.tsx       # QueryClientProvider wrapper
│
└── stores/
    └── authStore.ts            # Zustand: { user, accessToken, setAuth, clearAuth }
```

**Phase 4 frontend additions:** `hooks/useReminderPolling.ts` (replaces Web Push — polls `/due` every 60s, shows toast with infinite duration, acks on manual dismiss)

**Sprint 6 frontend additions:**
- `src/instrumentation.ts` — Sentry server/edge init hook
- `src/app/global-error.tsx` — React render error boundary
- `e2e/` — Playwright E2E test suite (4 spec files + fixtures + globalSetup)
- `playwright.config.ts` — 2 webServers (BE + FE), globalSetup, retries: 1 in CI

---

## E2E Tests: `frontend/e2e/`

```
frontend/e2e/
├── global-setup.ts     # Pre-fetch /auth/login + / để warm up Next.js JIT trước khi tests chạy
├── fixtures.ts         # registerAndLogin() helper — POST /auth/register rồi login via UI
├── auth.spec.ts        # Login → redirect dashboard; wrong password → error
├── chat.spec.ts        # Send "Xin chào" (MOCK_LLM=1), verify response bubble or input cleared (1 test)
├── reminder.spec.ts    # Create reminder via UI form → appears in reminders section
└── dashboard.spec.ts   # Dashboard loads with stats cards
```

---

## Key Config Files

| File | Purpose |
|---|---|
| `backend/pyproject.toml` | Python deps (+ slowapi S5; + redis, sentry-sdk S6; + pyinstaller Phase 4 dev), ruff config, mypy strict, pytest config |
| `backend/alembic.ini` | Alembic migration settings |
| `backend/jarvis_server.py` | PyInstaller entry point; resolves .env: %APPDATA%\JARVIS\.env → next to exe |
| `backend/jarvis_server.spec` | PyInstaller build spec — collect_all(litellm+tiktoken), dynamic path resolution |
| `scripts/build-sidecar.ps1` | Build PyInstaller exe + stage to `frontend/src-tauri/binaries/` with correct triple |
| `frontend/package.json` | Node deps; `check` script dùng `biome check .` (no --write, CI-safe) |
| `frontend/next.config.ts` | `typedRoutes: true`; `withSentryConfig` + `deleteSourcemapsAfterUpload: true` |
| `frontend/biome.json` | Biome lint/format; ignore: `.next, node_modules, test-results, playwright-report` |
| `frontend/playwright.config.ts` | E2E config: globalSetup, 2 webServers, retries=1 CI |
| `.env.example` | Env var template: local Postgres + LLM keys + JWT + Google OAuth; no VAPID (removed Phase 4) |
| `.gitignore` | Excludes .env, .venv, node_modules, __pycache__, test-results/, playwright-report/ |
| `.github/workflows/ci.yml` | GitHub Actions: backend-test + migration-smoke + frontend-check + desktop-build (Windows/Tauri) |
