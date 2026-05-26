# JARVIS Backend

FastAPI + SQLAlchemy + LiteLLM backend for J.A.R.V.I.S Personal AI Assistant.

## Setup

```powershell
# 1. Tạo venv với uv
uv venv

# 2. Activate
.venv\Scripts\activate           # Windows PowerShell
# source .venv/bin/activate      # Mac/Linux

# 3. Install dependencies
uv pip install -e ".[dev]"

# 4. Run migrations
alembic upgrade head

# 5. Run dev server
uvicorn app.main:app --reload --port 8000
```

→ Backend: http://localhost:8000
→ Docs: http://localhost:8000/docs

## Cấu trúc

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry
│   ├── config.py            # Settings (env vars)
│   ├── database.py          # Async SQLAlchemy
│   ├── llm/
│   │   ├── client.py        # 2-tier fallback (Gemini → gpt-4o-mini)
│   ├── models/              # ORM models (Sprint 1+)
│   ├── routers/
│   │   ├── health.py
│   │   └── chat.py
│   └── schemas/             # Pydantic schemas (Sprint 1+)
├── migrations/              # Alembic
├── tests/
├── pyproject.toml
└── alembic.ini
```

## Commands

```powershell
# Lint + format
ruff check . --fix
ruff format .

# Type check
mypy app/

# Test
pytest
pytest --cov=app

# Migration mới
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Reset DB
alembic downgrade base
alembic upgrade head
```

## Troubleshooting

- **`asyncpg` install fail trên Windows:** cần Microsoft C++ Build Tools, hoặc dùng `pip install asyncpg --only-binary :all:`.
- **DB connection refused:** check `DATABASE_URL` trong `.env`, đảm bảo dùng `?sslmode=require` nếu Supabase.
- **LLM call timeout:** check Gemini key + quota tại https://aistudio.google.com.
