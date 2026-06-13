# JARVIS Backend

FastAPI backend cho J.A.R.V.I.S Personal AI Assistant. Backend hiện đã hoàn thành MVP 1: auth, chat AI, todo, notes, memories/RAG, reminders, dashboard, scheduler, rate limit và observability.

---

## Stack

- FastAPI + Uvicorn
- SQLAlchemy 2.0 async + PostgreSQL
- Alembic migrations
- pgvector cho semantic memory search
- LiteLLM cho Gemini/OpenAI routing
- APScheduler cho reminder jobs
- JWT access token + refresh token HttpOnly cookie
- SlowAPI rate limiting, optional Upstash Redis
- Sentry FastAPI/SQLAlchemy integration
- pytest, ruff, mypy strict

---

## Setup

Chạy từ thư mục `backend/`:

```powershell
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend:

- API: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/health/ready

---

## Environment

Backend đọc env mặc định từ `../.env`. Khi chạy PyInstaller sidecar, `jarvis_server.py` có thể override bằng `ENV_FILE_PATH`, ưu tiên `%APPDATA%\JARVIS\.env`.

Các biến chính:

```env
DATABASE_URL=postgresql+asyncpg://jarvis_user:local_pass@localhost:5432/jarvis
DATABASE_URL_DIRECT=postgresql://jarvis_user:local_pass@localhost:5432/jarvis

GEMINI_API_KEY=...
OPENAI_API_KEY=...
JWT_SECRET=your-random-secret-at-least-32-chars

BACKEND_CORS_ORIGINS=http://localhost:3000,http://tauri.localhost,https://tauri.localhost,tauri://localhost

SENTRY_DSN=
UPSTASH_REDIS_URL=
APP_ENV=development
```

---

## Modules

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, middleware, handlers, routers
│   ├── config.py                # Pydantic settings
│   ├── database.py              # Async engine/session
│   ├── core/                    # Auth deps, security, error envelope
│   ├── middleware/              # Rate limiting
│   ├── routers/                 # HTTP endpoints
│   ├── services/                # Business logic
│   ├── repositories/            # SQLAlchemy queries
│   ├── models/                  # ORM models
│   ├── schemas/                 # Pydantic schemas
│   ├── llm/                     # LiteLLM client, router, orchestrator, prompt
│   ├── tools/                   # AI tool schemas and executors
│   └── utils/                   # Vietnamese datetime parser
├── migrations/                  # Alembic migrations
├── tests/                       # pytest suite
├── jarvis_server.py             # PyInstaller sidecar entry
├── jarvis_server.spec           # PyInstaller spec
├── pyproject.toml
└── alembic.ini
```

---

## API Surface

| Area | Routes |
|---|---|
| Health | `GET /health`, `GET /health/ready`, `GET /health/sentry-test` |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET/PATCH /auth/me` |
| Chat | `POST /v1/chat/send`, `GET /v1/chat/conversations`, `GET/PATCH/DELETE /v1/chat/conversations/{id}` |
| Todos | `GET/POST /v1/todos`, `GET/PUT/DELETE /v1/todos/{id}`, `PATCH /complete`, `PATCH /uncomplete` |
| Notes | `GET/POST /v1/notes`, `GET/PATCH/DELETE /v1/notes/{id}`, `PATCH /pin`, `PATCH /unpin` |
| Memories | `GET/POST /v1/memories`, `POST /v1/memories/search`, `GET/PATCH/DELETE /v1/memories/{id}` |
| Reminders | `GET/POST /v1/reminders`, `GET /v1/reminders/due`, `POST /v1/reminders/{id}/ack`, `GET/PATCH/DELETE /v1/reminders/{id}`, `PATCH /cancel` |
| Dashboard | `GET /v1/dashboard/today` |

---

## AI Tools

LLM có thể gọi các tool sau qua orchestrator:

- `create_todo`, `list_todos`, `update_todo`
- `create_note`, `search_notes`
- `save_memory`, `search_memory`, `forget_memory`
- `create_reminder`, `list_reminders`

Tool execution được log qua `tool_logs`. Chat service giữ transaction chính; tool executors không tự commit shared chat session.

---

## Commands

```powershell
# Lint
ruff check .

# Auto-fix + format
ruff check . --fix
ruff format .

# Type check
mypy app/

# Test
pytest
pytest --cov=app

# Prompt eval, cần real LLM keys
$env:RUN_EVAL="1"
pytest -m eval

# Migration mới
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

---

## Build Sidecar

Desktop release dùng PyInstaller sidecar. Từ repo root:

```powershell
.\scripts\build-sidecar.ps1
```

Script chạy `uv run --extra dev pyinstaller jarvis_server.spec --noconfirm` và copy binary sang:

```text
frontend/src-tauri/binaries/jarvis-server-<target-triple>.exe
```

---

## Notes

- Scheduler không gửi web push nữa. Nó chỉ chuyển reminder đến hạn sang `due`; frontend poll `/v1/reminders/due` và ack qua `/ack`.
- Google OAuth chưa nằm trong MVP 1.
- SQLite auto `create_all` chỉ bật trong test env, không dùng để mutate schema ở dev/prod.
- Local desktop build hiện giả định máy có PostgreSQL + pgvector.
