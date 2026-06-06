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
| 004 | `004_sprint3_notes.py` | notes | Applied |
| 005 | `005_sprint4_memories.py` | memories + ENUM memory_type + HNSW index | Applied (Sprint 4 done) |
| 006 | `006_sprint5_reminders.py` | reminders + ENUM reminder_status (pending\|sending\|sent\|failed\|cancelled) | Applied (Sprint 5 done) |
| 008 | `008_desktop_reminders.py` | ADD `due` to reminder_status ENUM; DROP TABLE push_subscriptions | Applied (Phase 4) |

**Not yet created:** conversations.summary (deferred Sprint 6)

---

## ENUMs (implemented + planned)

```
message_role:     user | assistant | system | tool
todo_status:      pending | in_progress | completed | cancelled
todo_priority:    low | medium | high | urgent
tool_status:      success | failed | timeout
memory_type:      fact | preference | rule | relation | goal | other
reminder_status:  pending | sending | sent | failed | cancelled | due   (Sprint 5; +due Phase 4)
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
| notes | YES (`deleted_at`) | |
| memories | YES (`deleted_at` + `is_active`) | also has `is_active` flag for RAG filter |
| reminders | YES (`deleted_at`) | Sprint 5 |
| tool_execution_logs | NO | |
| llm_call_logs | NO | |

---

## ORM Models → File Map

| Model class | File | Relationships |
|---|---|---|
| `User` | `models/user.py` | → sessions, conversations, todos, notes, memories |
| `AuthSession` | `models/user.py` | → user |
| `Conversation` | `models/conversation.py` | → user, messages |
| `Message` | `models/conversation.py` | → conversation |
| `Todo` | `models/todo.py` | → user |
| `Note` | `models/note.py` | → user |
| `Memory` | `models/memory.py` | → user |
| `Reminder` | `models/reminder.py` | → user; Sprint 5 |
| `ToolExecutionLog` | `models/tool_log.py` | → user |
| `LLMCallLog` | `models/tool_log.py` | → user |

---

## Memory Table

```sql
CREATE TABLE memories (
    id           UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_type  memory_type   NOT NULL DEFAULT 'fact',
    content      TEXT          NOT NULL,
    embedding    vector(1536),              -- NULL until background embed task runs
    importance   INTEGER       NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    deleted_at   TIMESTAMPTZ
);
-- idx_memories_user_active: (user_id) WHERE is_active=TRUE AND deleted_at IS NULL
-- idx_memories_type: (user_id, memory_type) WHERE is_active=TRUE AND deleted_at IS NULL
-- idx_memories_hnsw: USING hnsw(embedding vector_cosine_ops) WHERE embedding IS NOT NULL AND deleted_at IS NULL AND is_active=TRUE
-- trg_memory_updated_at: BEFORE UPDATE EXECUTE FUNCTION set_updated_at()
```

**ORM `embedding` column:** `Column(sa.JSON, nullable=True)` — SQLite stores as JSON list; Postgres stores actual `vector(1536)` via migration DDL (Alembic controls the column type in production).

**Semantic search query (Postgres only):**
```sql
SELECT * FROM memories
WHERE user_id = :uid AND is_active = TRUE AND deleted_at IS NULL
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> :query_vec) >= :min_similarity
ORDER BY embedding <=> :query_vec
LIMIT :k
```
→ `memory_repo.semantic_search()` detects SQLite dialect → returns `[]` (mocked in tests).

---

## SQLite Compatibility (test env only)

Tests use `sqlite+aiosqlite:///:memory:`. These diverge from Postgres:

| Postgres type | SQLite workaround | Affected files |
|---|---|---|
| `postgresql.UUID` | `sa.Uuid` | All models |
| `JSONB` | `sa.JSON` | All models |
| `ENUM` (pre-defined) | `sa.Enum(..., create_type=False)` | All models with ENUMs (incl. reminder_status) |
| `TEXT[]` arrays | `sa.JSON` | `models/todo.py` |
| `vector(1536)` | `sa.JSON` (store as float list) | `models/memory.py` |
| `pool_size`/`max_overflow` | Omitted for SQLite | `database.py` |
| `server_default="true"` for BOOLEAN | Must also set `default=True` in Python | `models/user.py`, `models/memory.py` |

**Note on vector:** HNSW index and `<=>` operator not available in SQLite. `semantic_search()` short-circuits on SQLite. Tests mock `embedding_service.embed_text()` and `memory_repo.semantic_search()`.

---

## LLMCallLog Cost Rates (USD per 1M tokens)

Defined in `repositories/llm_call_log_repo.py` → `_COST_PER_M`:

| Model | $/M in | $/M out |
|---|---|---|
| gemini/gemini-2.5-flash | $0 | $0 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-5.4-nano | $0.075 | $0.30 |
| gpt-5-mini | $0.25 | $2.00 |
| text-embedding-3-small | $0.02 | — |
