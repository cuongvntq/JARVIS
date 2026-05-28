# Database Schema — Current State

> Full SQL DDL: `docs/01_Database_Schema_ERD.md`
> This file covers: migration state, what's implemented vs planned, SQLite compat notes, ORM→file map.

---

## Migration State

| # | File | Tables created | Status |
|---|---|---|---|
| 001 | `001_init_extensions.py` | — (extensions only) | Applied |
| 002 | `002_create_core_tables.py` | users, auth_sessions, conversations, messages + ENUM message_role | Applied |
| 003 | `003_sprint2_todos_tool_logs.py` | todos, tool_execution_logs, llm_call_logs + ENUMs todo_status, todo_priority, tool_status | Applied |
| 004 | `004_sprint3_notes.py` | notes | Sprint 3 (pending apply) |

**Not yet created (future sprints):** memories (S4), reminders (S5), notifications (S5)

---

## ENUMs (implemented)

```
message_role:  user | assistant | system | tool
todo_status:   pending | in_progress | completed | cancelled
todo_priority: low | medium | high | urgent
tool_status:   success | failed | timeout
```

---

## Tables with soft delete

| Table | soft delete? | Notes |
|---|---|---|
| users | NO | Hard delete only (admin) |
| auth_sessions | NO | `revoked_at` marks as inactive |
| conversations | YES (`deleted_at`) | |
| messages | NO | Retention policy only |
| todos | YES (`deleted_at`) | |
| notes | YES (`deleted_at`) | Sprint 3 |
| tool_execution_logs | NO | |
| llm_call_logs | NO | |

---

## ORM Models → File Map

| Model class | File | Relationships |
|---|---|---|
| `User` | `models/user.py` | → sessions, conversations, todos, notes |
| `AuthSession` | `models/user.py` | → user |
| `Conversation` | `models/conversation.py` | → user, messages |
| `Message` | `models/conversation.py` | → conversation |
| `Todo` | `models/todo.py` | → user |
| `Note` | `models/note.py` | → user — Sprint 3 |
| `ToolExecutionLog` | `models/tool_log.py` | → user |
| `LLMCallLog` | `models/tool_log.py` | → user |

---

## SQLite Compatibility (test env only)

Tests use `sqlite+aiosqlite:///:memory:`. These diverge from Postgres:

| Postgres type | SQLite workaround | Affected files |
|---|---|---|
| `postgresql.UUID` | `sa.Uuid` | All models |
| `JSONB` | `sa.JSON` | All models |
| `ENUM` (pre-defined) | `sa.Enum(..., create_type=False)` | Models with ENUMs |
| `TEXT[]` arrays | `sa.JSON` (same in both envs now) | `models/todo.py` |
| `pool_size`/`max_overflow` | Omitted for SQLite | `database.py` |
| `server_default="true"` for BOOLEAN | Must also set `default=True` in Python | `models/user.py` |

**Reason for last point:** `server_default` stores TEXT `"true"` in SQLite, which fails `.is_(True)` filter.

---

## LLMCallLog Cost Rates (USD per 1M tokens)

Defined in `repositories/llm_call_log_repo.py` → `_COST_PER_M`:

| Model | $/M in | $/M out |
|---|---|---|
| gemini/gemini-2.5-flash | $0 | $0 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-5.4-nano | $0.075 | $0.30 |
| gpt-5-mini | $0.25 | $2.00 |
