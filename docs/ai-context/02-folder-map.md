# Folder Map & File Purpose

## Repository Root

```
Javis/
├── backend/                    # FastAPI Python backend
├── frontend/                   # Next.js 15 frontend
├── docs/                       # Technical documentation
│   ├── ai-context/             # AI session context (this folder)
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
│   ├── config.py               # Settings (pydantic-settings), get_settings() lru_cache
│   ├── database.py             # SQLAlchemy engine, AsyncSessionLocal, Base, get_db()
│   │
│   ├── core/
│   │   ├── deps.py             # get_current_user() FastAPI dependency (JWT → User)
│   │   ├── errors.py           # JarvisError, RequestIDMiddleware, exception handlers
│   │   └── security.py         # JWT encode/decode, bcrypt hash/verify, token helpers
│   │
│   ├── models/                 # SQLAlchemy ORM models (table definitions)
│   │   ├── user.py             # User, AuthSession; Sprint 3: +notes relationship
│   │   ├── conversation.py     # Conversation, Message
│   │   ├── todo.py             # Todo
│   │   ├── note.py             # Note — Sprint 3
│   │   └── tool_log.py         # ToolExecutionLog, LLMCallLog
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserOut, RefreshRequest
│   │   ├── chat.py             # ChatSendRequest/Response, ConversationOut/Detail/List, MessageOut
│   │   ├── todo.py             # TodoCreate, TodoReplace, TodoPartialUpdate, TodoOut, TodoListOut
│   │   └── note.py             # NoteCreate, NoteUpdate, NotePatch, NoteOut, NoteListOut — Sprint 3
│   │
│   ├── routers/                # FastAPI route handlers (thin: validate → service → return)
│   │   ├── auth.py             # /auth/register, login, refresh, logout, me
│   │   ├── chat.py             # /v1/chat/send, conversations CRUD
│   │   ├── todos.py            # /v1/todos CRUD
│   │   ├── notes.py            # /v1/notes CRUD + pin/unpin — Sprint 3
│   │   └── health.py           # /health, /health/ready
│   │
│   ├── services/               # Business logic
│   │   ├── auth_service.py     # register, login, refresh_tokens, logout, _issue_tokens
│   │   ├── chat_service.py     # send_message, list_conversations, get_conversation_detail, update/delete; Sprint 3: auto-title first message
│   │   ├── todo_service.py     # create, get, list, replace, patch, complete, uncomplete, delete
│   │   └── note_service.py     # create, get, list, update, patch (internal), pin, unpin, delete — Sprint 3
│   │
│   ├── repositories/           # DB queries (SQLAlchemy 2.0, no business logic)
│   │   ├── user_repo.py        # get_by_email, get_by_id, create, update_last_login
│   │   ├── auth_repo.py        # create_session, get_session_by_hash, revoke_session, atomic_revoke_session
│   │   ├── conversation_repo.py # get_or_create, add_message, list_conversations, get_conversation, get_messages_page, update_title, soft_delete_conversation
│   │   ├── todo_repo.py        # get_by_id, list_todos, create, update_fields, complete, uncomplete, soft_delete + _today_range_utc()
│   │   ├── note_repo.py        # get_by_id, list_notes (pinned/q/cursor), create, update_fields, soft_delete — Sprint 3
│   │   ├── tool_log_repo.py    # log_execution()
│   │   └── llm_call_log_repo.py # log_call() + _calc_cost()
│   │
│   ├── llm/                    # LLM layer
│   │   ├── client.py           # chat_completion() — LiteLLM wrapper, primary→fallback chain
│   │   ├── models.py           # LLMResponse dataclass, ToolCall dataclass
│   │   ├── router.py           # route() — Stage 0 pre-filter + Stage 1 Gemini classifier, RouteResult, Intent enum
│   │   ├── orchestrator.py     # run() — full tool loop, OrchestratorResult, _execute_tool()
│   │   └── prompt.py           # build_system_prompt() → (str, PROMPT_VERSION)
│   │
│   ├── tools/                  # Tool system
│   │   ├── definitions.py      # TOOLS list (5 schemas: 3 todo + create_note + search_notes), TOOL_MAP dict
│   │   └── executors.py        # execute_create/list/update_todo + execute_create/search_notes + dispatch() — Sprint 3
│   │
│   └── utils/
│       └── datetime_parser.py  # parse_datetime() — ISO fast path → dict replace → regex → LLM fallback
│
├── vi_time_dict.json           # ~40 Vietnamese time expression mappings
│
├── migrations/
│   ├── env.py                  # Alembic env config
│   └── versions/
│       ├── 001_init_extensions.py       # uuid-ossp, pgcrypto, pg_trgm, vector
│       ├── 002_create_core_tables.py    # users, auth_sessions, conversations, messages + ENUM message_role
│       ├── 003_sprint2_todos_tool_logs.py # todos, tool_execution_logs, llm_call_logs + ENUMs
│       └── 004_sprint3_notes.py         # notes table — Sprint 3
│
└── tests/
    ├── conftest.py             # SQLite in-memory engine, fixtures: async_client, auth_headers, mock_llm
    ├── test_auth.py            # Auth endpoint tests
    ├── test_chat.py            # Chat endpoint + conversation CRUD tests
    ├── test_todos.py           # Todo CRUD + _today_range_utc unit tests + today filter integration
    ├── test_notes.py           # Note CRUD + pin/unpin + search + ownership (19 tests) — Sprint 3
    ├── test_orchestrator.py    # Orchestrator unit tests (26 tests) + router tests + fallback chain regression
    ├── test_datetime_parser.py # Datetime parser tests (12 tests)
    └── test_health.py          # Health endpoint tests
```

---

## Frontend: `frontend/src/`

```
frontend/src/
├── app/
│   ├── layout.tsx              # Root layout: QueryProvider + AuthGuard
│   ├── page.tsx                # Main page: manages conversationId state, wires Sidebar↔ChatInterface
│   └── auth/
│       ├── layout.tsx          # Auth pages layout (no sidebar)
│       ├── login/page.tsx      # Login form
│       └── register/page.tsx   # Register form
│
├── components/
│   ├── auth/
│   │   └── AuthGuard.tsx       # Redirect if not logged in; calls api.me() to restore session
│   ├── chat/
│   │   ├── ChatInterface.tsx   # Message list, loads history, calls useChatMutation
│   │   ├── ChatInput.tsx       # Textarea + send button
│   │   └── MessageBubble.tsx   # User/assistant message rendering
│   └── layout/
│       └── Sidebar.tsx         # Conversation list + NEW CHAT button (useConversations hook)
│
├── hooks/
│   ├── useChatMutation.ts      # Tanstack useMutation → api.sendMessage()
│   └── useConversations.ts     # Tanstack useQuery for list + detail; invalidates on send
│
├── lib/
│   ├── api.ts                  # ApiClient class (singleton `api`); auto-refresh on 401
│   ├── queryClient.ts          # Tanstack QueryClient singleton
│   └── types/api.ts            # TypeScript types: UserOut, TokenResponse, MessageOut, ChatSendResponse, ConversationOut/Detail/List, ApiException
│
├── providers/
│   └── QueryProvider.tsx       # QueryClientProvider wrapper
│
└── stores/
    └── authStore.ts            # Zustand: { user, accessToken, setAuth, clearAuth }
```

---

## Key Config Files

| File | Purpose |
|---|---|
| `backend/pyproject.toml` | Python deps, ruff config, pytest config |
| `backend/alembic.ini` | Alembic migration settings |
| `frontend/package.json` | Node deps |
| `frontend/biome.json` | Biome lint/format config |
| `.env.example` | All env var templates |
| `.gitignore` | Excludes .env, .venv, node_modules, __pycache__ |
