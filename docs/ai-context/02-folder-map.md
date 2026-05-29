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
│   │                           # Sprint 4: + embedding_model, embedding_dim
│   ├── database.py             # SQLAlchemy engine, AsyncSessionLocal, Base, get_db()
│   │
│   ├── core/
│   │   ├── deps.py             # get_current_user() FastAPI dependency (JWT → User)
│   │   ├── errors.py           # JarvisError, RequestIDMiddleware, exception handlers
│   │   └── security.py         # JWT encode/decode, bcrypt hash/verify, token helpers
│   │
│   ├── models/                 # SQLAlchemy ORM models (table definitions)
│   │   ├── user.py             # User, AuthSession; +notes relationship; Sprint 4: +memories relationship
│   │   ├── conversation.py     # Conversation, Message; Sprint 4 stretch: +summary column
│   │   ├── todo.py             # Todo
│   │   ├── note.py             # Note
│   │   ├── memory.py           # Memory — embedding=sa.JSON (SQLite compat) — SPRINT 4 [CREATE]
│   │   └── tool_log.py         # ToolExecutionLog, LLMCallLog
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserOut, RefreshRequest
│   │   │                       # Sprint 4: + UserUpdateRequest (for PATCH /auth/me)
│   │   ├── chat.py             # ChatSendRequest/Response, ConversationOut/Detail/List, MessageOut
│   │   ├── todo.py             # TodoCreate, TodoReplace, TodoPartialUpdate, TodoOut, TodoListOut
│   │   ├── note.py             # NoteCreate, NoteUpdate, NotePatch, NoteOut, NoteListOut
│   │   └── memory.py           # MemoryCreate, MemoryUpdate, MemoryOut, MemoryListOut — SPRINT 4 [CREATE]
│   │
│   ├── routers/                # FastAPI route handlers (thin: validate → service → return)
│   │   ├── auth.py             # /auth/register, login, refresh, logout, me; Sprint 4: + PATCH /auth/me
│   │   ├── chat.py             # /v1/chat/send (non-stream + SSE stream), conversations CRUD
│   │   ├── todos.py            # /v1/todos CRUD
│   │   ├── notes.py            # /v1/notes CRUD + pin/unpin
│   │   ├── memories.py         # /v1/memories CRUD + /search — SPRINT 4 [CREATE]
│   │   └── health.py           # /health, /health/ready
│   │
│   ├── services/               # Business logic
│   │   ├── auth_service.py     # register, login, refresh_tokens, logout; Sprint 4: + update_profile()
│   │   ├── chat_service.py     # send_message (non-stream + stream_message generator);
│   │   │                       # Sprint 4: + RAG call (search_semantic) before build_system_prompt
│   │   ├── todo_service.py     # create, get, list, replace, patch, complete, uncomplete, delete
│   │   ├── note_service.py     # create, get, list, update, patch, pin, unpin, delete
│   │   ├── embedding_service.py # embed_text(text) → list[float] via LiteLLM aembedding — SPRINT 4 [CREATE]
│   │   └── memory_service.py   # create (+async embed task), search_semantic, get, list, update, forget — SPRINT 4 [CREATE]
│   │
│   ├── repositories/           # DB queries (SQLAlchemy 2.0, no business logic)
│   │   ├── user_repo.py        # get_by_email, get_by_id, create, update_last_login; Sprint 4: + update_fields()
│   │   ├── auth_repo.py        # create_session, get_session_by_hash, revoke_session, atomic_revoke_session
│   │   ├── conversation_repo.py # get_or_create, add_message, list, get_conversation, get_messages_page,
│   │   │                        # update_title, soft_delete; Sprint 4 stretch: + update_summary()
│   │   ├── todo_repo.py        # get_by_id, list_todos, create, update_fields, complete, uncomplete, soft_delete, _today_range_utc()
│   │   ├── note_repo.py        # get_by_id, list_notes (pinned/q/cursor), create, update_fields, soft_delete
│   │   ├── memory_repo.py      # create, get_by_id, list_memories, update_fields, update_embedding,
│   │   │                       # soft_delete, semantic_search (SQLite→[]) — SPRINT 4 [CREATE]
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
│   │
│   ├── tools/                  # Tool system
│   │   ├── definitions.py      # TOOLS list; Sprint 3: 5 schemas; Sprint 4: 8 schemas (+save/search/forget_memory)
│   │   └── executors.py        # dispatch(); Sprint 3: 5 executors; Sprint 4: +3 memory executors
│   │
│   └── utils/
│       └── datetime_parser.py  # parse_datetime() — ISO fast path → dict replace → regex → LLM fallback
│
├── vi_time_dict.json           # ~40 Vietnamese time expression mappings
│
├── migrations/
│   ├── env.py                  # Alembic env config
│   └── versions/
│       ├── 001_init_extensions.py          # uuid-ossp, pgcrypto, pg_trgm, vector
│       ├── 002_create_core_tables.py       # users, auth_sessions, conversations, messages + ENUM message_role
│       ├── 003_sprint2_todos_tool_logs.py  # todos, tool_execution_logs, llm_call_logs + ENUMs
│       ├── 004_sprint3_notes.py            # notes table
│       ├── 005_sprint4_memories.py         # memories + ENUM memory_type + HNSW index — SPRINT 4 [CREATE]
│       └── 006_sprint4_conv_summary.py     # ADD COLUMN conversations.summary — SPRINT 4 stretch [CREATE]
│
└── tests/
    ├── conftest.py             # SQLite in-memory, fixtures: async_client, auth_headers, mock_llm,
    │                           # mock_llm_stream, mock_llm_stream_error;
    │                           # Sprint 4: + mock_embedding, mock_semantic_search
    ├── test_auth.py            # Auth endpoint tests (16 tests)
    ├── test_chat.py            # Chat + conversation CRUD + streaming tests (15 tests)
    ├── test_todos.py           # Todo CRUD + filter + ownership (21 tests)
    ├── test_notes.py           # Note CRUD + pin/unpin + search + ownership (19 tests)
    ├── test_memories.py        # Memory CRUD + search + ownership — SPRINT 4 [CREATE] (~13 tests)
    ├── test_orchestrator.py    # Orchestrator + router + fallback chain (26 tests);
    │                           # Sprint 4: + RAG integration test
    ├── test_datetime_parser.py # Datetime parser tests (12 tests)
    └── test_health.py          # Health endpoint tests
```

---

## Frontend: `frontend/src/`

```
frontend/src/
├── app/
│   ├── layout.tsx              # Root layout: QueryProvider + AuthGuard
│   ├── page.tsx                # Single-page section nav (Chat|Todo|Notes|Memory|Settings);
│   │                           # Sprint 4: mount MemoryPage + SettingsPage sections
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
│   ├── memories/               # SPRINT 4 [CREATE folder]
│   │   ├── MemoryCard.tsx      # Type badge, content, importance bar, edit/delete actions
│   │   ├── MemoryList.tsx      # Filter chips by type, list of cards, empty state
│   │   ├── MemoryEditor.tsx    # Dialog: content textarea, type select, importance slider (1-10)
│   │   └── MemoryPage.tsx      # Section root: wire MemoryList + MemoryEditor — SPRINT 4 [CREATE]
│   ├── settings/               # SPRINT 4 [CREATE folder]
│   │   └── SettingsPage.tsx    # Form: name, assistant_name, timezone select, locale select — SPRINT 4 [CREATE]
│   └── layout/
│       └── Sidebar.tsx         # Conversation list + NEW CHAT + nav links;
│                               # Sprint 4: add "settings" to Section type + Settings nav link
│
├── hooks/
│   ├── useChatMutation.ts      # Tanstack useMutation → api.sendMessage()
│   ├── useConversations.ts     # useQuery list + detail; invalidates on send
│   ├── useMemories.ts          # useMemories, useCreateMemory, useUpdateMemory, useDeleteMemory — SPRINT 4 [CREATE]
│   └── useSettings.ts          # useMutation → PATCH /auth/me + update authStore — SPRINT 4 [CREATE]
│
├── lib/
│   ├── api.ts                  # ApiClient; Sprint 4: + memory methods + PATCH /auth/me
│   ├── queryClient.ts          # Tanstack QueryClient singleton
│   └── types/api.ts            # TypeScript types; Sprint 4: + MemoryOut, MemoryCreate, MemoryUpdate,
│                               #   MemoryListOut, MemorySearchRequest, UserUpdateRequest
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

---

## Sprint 4 — Files chính cần tạo/sửa

**Tạo mới:**
```
backend/app/models/memory.py
backend/app/schemas/memory.py
backend/app/repositories/memory_repo.py        # incl. _build_semantic_search_stmt() testable fn
backend/app/services/embedding_service.py
backend/app/services/memory_service.py
backend/app/routers/memories.py
backend/migrations/versions/005_sprint4_memories.py
backend/tests/test_memories.py
frontend/src/hooks/useMemories.ts
frontend/src/hooks/useSettings.ts
frontend/src/components/memories/MemoryCard.tsx
frontend/src/components/memories/MemoryList.tsx
frontend/src/components/memories/MemoryEditor.tsx
frontend/src/components/memories/MemoryPage.tsx  # section root (NOT a Next.js route)
frontend/src/components/settings/SettingsPage.tsx # section root (NOT a Next.js route)
```

**Sửa:**
```
backend/app/config.py              (verify existing embedding_model, embedding_dim — no change needed)
backend/app/main.py                (+import Memory, register memories router)
backend/app/models/user.py         (+memories relationship)
backend/app/schemas/auth.py        (+UserUpdateRequest)
backend/app/repositories/user_repo.py (+update_fields)
backend/app/services/auth_service.py  (+update_profile)
backend/app/services/chat_service.py  (+_build_prompt_with_rag() helper; replace build_system_prompt in both send_message + stream_message)
backend/app/routers/auth.py        (+PATCH /auth/me)
backend/app/tools/definitions.py   (+3 memory tool schemas → 8 total)
backend/app/tools/executors.py     (+3 memory executors, update dispatch)
backend/app/llm/prompt.py          (+memory tools in _PART_C, bump PROMPT_VERSION)
backend/tests/conftest.py          (+mock_embedding, mock_semantic_search fixtures)
backend/tests/test_orchestrator.py (+RAG integration test)
frontend/src/lib/api.ts            (+memory API methods, +PATCH /auth/me)
frontend/src/lib/types/api.ts      (+Memory types, +UserUpdateRequest)
frontend/src/components/layout/Sidebar.tsx (+settings to Section type + Settings nav link)
frontend/src/app/page.tsx          (+memory + settings sections, replace ComingSoon for memory)
```
