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
│   │   ├── errors.py           # JarvisError, RequestIDMiddleware, exception handlers; Sprint 4: + http_exception_handler (unified HTTPException → { error: ... })
│   │   └── security.py         # JWT encode/decode, bcrypt hash/verify, token helpers
│   │
│   ├── models/                 # SQLAlchemy ORM models (table definitions)
│   │   ├── user.py             # User, AuthSession; +notes relationship; Sprint 4: +memories relationship
│   │   ├── conversation.py     # Conversation, Message; Sprint 4 stretch: +summary column
│   │   ├── todo.py             # Todo
│   │   ├── note.py             # Note
│   │   ├── memory.py           # Memory — embedding=sa.JSON (SQLite compat)
│   │   └── tool_log.py         # ToolExecutionLog, LLMCallLog
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse, UserOut, RefreshRequest
│   │   │                       # Sprint 4: + UserUpdateRequest (for PATCH /auth/me)
│   │   ├── chat.py             # ChatSendRequest/Response, ConversationOut/Detail/List, MessageOut
│   │   ├── todo.py             # TodoCreate, TodoReplace, TodoPartialUpdate, TodoOut, TodoListOut
│   │   ├── note.py             # NoteCreate, NoteUpdate, NotePatch, NoteOut, NoteListOut
│   │   └── memory.py           # MemoryCreate, MemoryUpdate, MemoryOut, MemoryListOut
│   │
│   ├── routers/                # FastAPI route handlers (thin: validate → service → return)
│   │   ├── auth.py             # /auth/register, login, refresh, logout, me; Sprint 4: + PATCH /auth/me
│   │   ├── chat.py             # /v1/chat/send (non-stream + SSE stream), conversations CRUD
│   │   ├── todos.py            # /v1/todos CRUD
│   │   ├── notes.py            # /v1/notes CRUD + pin/unpin
│   │   ├── memories.py         # /v1/memories CRUD + /search
│   │   └── health.py           # /health, /health/ready
│   │
│   ├── services/               # Business logic
│   │   ├── auth_service.py     # register, login, refresh_tokens, logout; Sprint 4: + update_profile()
│   │   ├── chat_service.py     # send_message (non-stream + stream_message generator);
│   │   │                       # Sprint 4: + RAG call (search_semantic) before build_system_prompt
│   │   ├── todo_service.py     # create, get, list, replace, patch, complete, uncomplete, delete
│   │   ├── note_service.py     # create, get, list, update, patch, pin, unpin, delete
│   │   ├── embedding_service.py # embed_text(text) → list[float] via LiteLLM aembedding
│   │   └── memory_service.py   # create (+async embed task), create_committed (tool path), search_semantic, get, list, update, forget
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
│       ├── 005_sprint4_memories.py         # memories + ENUM memory_type + HNSW index
│       └── 006_sprint4_conv_summary.py     # ADD COLUMN conversations.summary — deferred (not yet applied)
│
└── tests/
    ├── conftest.py             # SQLite in-memory, fixtures: async_client, auth_headers, mock_llm,
    │                           # mock_llm_stream, mock_llm_stream_error,
    │                           # mock_embedding, mock_semantic_search, auth_headers_user_b
    ├── test_auth.py            # Auth endpoint tests (23 tests)
    ├── test_chat.py            # Chat + conversation CRUD + streaming + RAG tests (18 tests)
    ├── test_todos.py           # Todo CRUD + filter + ownership (26 tests)
    ├── test_notes.py           # Note CRUD + pin/unpin + search + ownership (19 tests)
    ├── test_memories.py        # Memory CRUD + search + ownership + query structure (22 tests)
    ├── test_orchestrator.py    # Orchestrator + router + fallback chain + memory tools (28 tests)
    ├── test_tool_executors.py  # Tool executor unit tests: todo/note/memory/summary (17 tests)
    ├── test_datetime_parser.py # Datetime parser tests (12 tests)
    └── test_health.py          # Health endpoint tests (2 tests)
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
│   ├── memories/
│   │   ├── MemoryCard.tsx      # Type badge (6 types), content, importance dots, edit/delete on hover
│   │   ├── MemoryList.tsx      # Filter chips by type, grid list, empty state; isSaving prop → disable actions
│   │   ├── MemoryEditor.tsx    # content textarea, type select, importance slider; validationError state; disable fields + close when isSaving
│   │   └── MemoryPage.tsx      # Section root; EditorState discriminated union { mode: closed|create|edit }
│   ├── settings/
│   │   └── SettingsPage.tsx    # Form: name, assistant_name, timezone select (11 IANA), locale select (vi-VN/en-US); inputs disabled when isPending
│   ├── notes/
│   │   ├── NoteEditor.tsx      # title/content/tags inputs; validationError state; disable fields + close when isSaving
│   │   ├── NoteList.tsx        # Search, pinned/all sections; isSaving prop → disable select/pin/delete
│   │   └── NotesPage.tsx       # isSaving guards on all navigation handlers; MỚI button disabled when isSaving
│   └── layout/
│       └── Sidebar.tsx         # Conversation list + NEW CHAT + nav links (Chat|Todos|Notes|Memory|Settings)
│
├── hooks/
│   ├── useChatMutation.ts      # Tanstack useMutation → api.sendMessage()
│   ├── useConversations.ts     # useQuery list + detail; invalidates on send
│   ├── useMemories.ts          # useInfiniteQuery (cursor), useCreateMemory, useUpdateMemory, useDeleteMemory
│   ├── useNotes.ts             # useInfiniteQuery (cursor), useCreateNote, useUpdateNote, usePinNote, useDeleteNote
│   └── useSettings.ts          # useMutation → PATCH /auth/me + setAuth to update authStore
│
├── lib/
│   ├── api.ts                  # ApiClient; error normalization: body.error ?? { body.detail fallback }; memory + PATCH /auth/me methods
│   ├── queryClient.ts          # Tanstack QueryClient singleton
│   └── types/api.ts            # TypeScript types: MemoryOut, MemoryCreate, MemoryUpdate, MemoryListOut, MemorySearchRequest, UserUpdateRequest
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

