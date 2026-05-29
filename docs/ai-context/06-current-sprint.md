# Current Sprint

> Sprint history (what each PR built): `memory/project-sprint-status.md` *(external Claude memory, không nằm trong repo)*
> This file covers: current state, design decisions chốt, Sprint 4 plan.

**As of:** 2026-05-29 | **Branch:** `feat/sprint4-*` (mỗi PR là 1 branch) | **Tests:** 119 passed (main, after SSE PR #7 merge)

---

## Current State

- Sprint 0–3: MERGED vào main ✅
  - Sprint 3 backend (PR #5), SSE streaming (PR #7 squash `aaa7023`, 2 tests added), frontend TodoUI/NoteUI (PR #6), workflow cleanup (PR #8) — ALL DONE
  - Total: 119 tests pass on main
- Sprint 4: **IN PROGRESS**

**RAG injection point (S4-3):** Cả `chat_service.stream_message()` lẫn `send_message()` hiện gọi `build_system_prompt(current_user)` không có memories. Sprint 4 thêm `search_semantic()` call trước BUILD PROMPT trong **cả hai** functions.

---

## Design Decisions (chốt, không reopen)

| Decision | Why |
|---|---|
| `call_model = None` khi route to primary (Gemini) | `client.py` chỉ kích hoạt primary→fallback chain khi `model=None`; pinning model string bỏ qua fallback |
| Bỏ `dateparser` lib, dùng dict+LLM | Tránh dependency, dict đủ cho 95% case tiếng Việt |
| `_today_range_utc(user_tz)` thay vì `cast(due_at, Date) == today` | `cast` dùng UTC date, sai timezone user |
| Anchor query scope to `conversation_id` trong pagination | Anchor từ conversation khác có thể xóa toàn bộ messages của conversation đúng |
| Bỏ Google OAuth khỏi MVP 1 | Scope reduction |
| Trả 404 thay 403 khi ownership fail | Không leak sự tồn tại của resource |
| Soft delete conversations + todos + notes | Audit trail, recovery khả năng |
| Cursor-based pagination (không offset) | Consistent với concurrent inserts |
| `user_tz` thread qua orchestrator → dispatch → executor | Tool executor cần timezone user để filter đúng |
| Atomic `UPDATE...RETURNING` cho refresh token rotation | Tránh race condition 2 request cùng dùng token |
| `streamSucceeded` flag trong ChatInterface.tsx | Chống navigate đến rolled-back conv_id nếu stream error sau meta event |
| `except Exception` (không chỉ RuntimeError) trong stream_message | Mọi unexpected exception đều cần rollback, không chỉ RuntimeError |
| ORM `embedding = sa.JSON` | SQLite compat; Postgres dùng `vector(1536)` via migration DDL (Sprint 4) |
| RAG call ở `chat_service.py` (không trong orchestrator) | `build_system_prompt()` gọi trước orchestrator — inject memory tại đây |
| `asyncio.create_task()` cho embedding | Tool executors không có FastAPI request context, không inject BackgroundTasks |

---

## Sprint 4 Plan — Memory System + Memory Screen

**Goal:** Semantic memory end-to-end: save → embed → RAG → inject vào chat context
**DoD:** `"Nhớ là tôi dị ứng tôm"` → memory saved + embed. `"Tôi có dị ứng gì?"` → retrieved + đúng. Eval E-04 passed.

### PR Breakdown

| PR | Nhánh | Thành phần | Depends |
|---|---|---|---|
| S4-1 | `feat/sprint4-memory-db` | Migration 005 + ORM model | main |
| S4-2 | `feat/sprint4-memory-api` | embedding_service + Schema + Repo + Svc + Router | S4-1 |
| S4-3 | `feat/sprint4-memory-tools-rag` | Tool executors + RAG in chat_service | S4-2 |
| S4-4 | `feat/sprint4-settings` | PATCH /auth/me | main (parallel) |
| S4-5 | `feat/sprint4-backend-tests` | test_memories + conftest + chat RAG tests | S4-1→4 |
| S4-6 | `feat/sprint4-memory-fe` | Types + hooks + MemoryCard/List/Editor + page | S4-3 |
| S4-7 | `feat/sprint4-settings-fe` | Types + hook + settings page + sidebar | S4-4 |
| S4-8 *(stretch)* | `feat/sprint4-conv-summary` | Migration 006 + conv summarization | S4-2 |

---

### PR S4-1 — Memory DB

**Files:**
- `migrations/versions/005_sprint4_memories.py` (tạo mới)
- `app/models/memory.py` (tạo mới)
- update `app/models/user.py` — thêm memories relationship
- update `app/models/__init__.py` — thêm `Memory` vào imports + `__all__` (Alembic đọc file này, KHÔNG update main.py ở PR này)

**Migration 005 (Postgres):**
```sql
CREATE TYPE memory_type AS ENUM ('fact','preference','rule','relation','goal','other');
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    memory_type memory_type NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL,
    embedding vector(1536),   -- nullable, populated by background task
    importance INTEGER NOT NULL DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
-- Partial indexes:
CREATE INDEX idx_memories_user_active ON memories (user_id) WHERE is_active = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_memories_type ON memories (user_id, memory_type) WHERE is_active = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_memories_hnsw ON memories USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL AND deleted_at IS NULL AND is_active = TRUE;
-- updated_at auto-trigger (reuse existing set_updated_at() function):
CREATE TRIGGER trg_memory_updated_at BEFORE UPDATE ON memories FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

**ORM (`models/memory.py`):**
- `embedding = Column(sa.JSON, nullable=True)` — SQLite stores as JSON list; Postgres stores as vector(1536) via DDL
- `memory_type = Column(sa.Enum(..., create_type=False), ...)` — same pattern as todos

**DoD:** `alembic upgrade head` sạch. SQLite `create_all` không crash. `pytest` green.

---

### PR S4-2 — Embedding Service + Memory CRUD API

**Files:**
- `app/services/embedding_service.py` (tạo mới) — `embed_text(text) → list[float]` via LiteLLM aembedding. Cần ở đây vì `search_semantic` gọi `embed_text` để embed query trước khi search.
- `app/schemas/memory.py` (tạo mới) — MemoryCreate, MemoryUpdate, MemoryOut, MemoryListOut
- `app/repositories/memory_repo.py` (tạo mới) — create, get_by_id, list_memories (cursor), update_fields, update_embedding, soft_delete, `_build_semantic_search_stmt()` (testable), semantic_search (SQLite→[])
- `app/services/memory_service.py` (tạo mới) — `create` (REST), `create_committed` (tool executor, session riêng), `search_semantic`, `get`, `list`, `update`, `forget`
- `app/routers/memories.py` (tạo mới) — 6 endpoints
- update `app/main.py` — register memories router (đây là lần duy nhất S4 update main.py)

**Hai code path tạo memory — tránh commit shared chat session:**

`create()` — dùng cho REST `POST /v1/memories` (router quản lý commit):
```python
async def create(db: AsyncSession, user_id: UUID, data: MemoryCreate) -> Memory:
    """REST path — session do router quản lý, commit ngoài."""
    return await memory_repo.create(db, user_id, data)
```
Router sau đó: `await db.commit(); await db.refresh(memory); asyncio.create_task(_embed_and_update(...))`

`create_committed()` — dùng cho tool executor (không nhận chat session):
```python
async def create_committed(user_id: UUID, data: MemoryCreate) -> MemoryOut:
    """Tool executor path — mở session riêng, trả MemoryOut (không trả ORM object sau khi session đóng)."""
    async with AsyncSessionLocal() as db:
        memory = await memory_repo.create(db, user_id, data)
        await db.commit()
        await db.refresh(memory)   # load tất cả fields trước khi session close
        out = MemoryOut.model_validate(memory)  # snapshot thành Pydantic — tránh detached instance error
    asyncio.create_task(_embed_and_update(out.id, out.content))
    return out
```
**Lý do trả `MemoryOut` thay vì ORM object:** sau khi `async with` block đóng, SQLAlchemy expire object (trừ khi `expire_on_commit=False`). Truy cập attribute sau đó có thể raise `DetachedInstanceError`. Snapshot ra Pydantic ngay trong session scope là an toàn nhất.

**Lý do split:** tool executor dùng cùng `AsyncSession` với chat turn. Nếu gọi `db.commit()` trên session đó, sẽ commit toàn bộ pending writes: user message, conversation title, tool logs từ các turn trước. Chat turn fail sau đó không thể rollback những gì đã committed. `create_committed()` dùng session riêng → chỉ memory commit → chat transaction không bị ảnh hưởng.

**Endpoints `/v1/memories`:**
| Method | Path | Action |
|---|---|---|
| GET | `/v1/memories` | list (query: `type?`, `limit=20`, `cursor?`) |
| POST | `/v1/memories` | create — 201 |
| POST | `/v1/memories/search` | semantic search (body: `{query, limit?, min_similarity?}`) |
| GET | `/v1/memories/{id}` | get one |
| PATCH | `/v1/memories/{id}` | update content/importance/type |
| DELETE | `/v1/memories/{id}` | forget (soft delete) — 204 |

**Semantic search fallback:** `memory_repo.semantic_search()` detect dialect SQLite → return `[]`. Tests mock hàm này.

**`_embed_and_update()` — background task, định nghĩa trong `memory_service.py`:**
```python
async def _embed_and_update(memory_id: uuid.UUID, content: str) -> None:
    """Background task: embed content và update DB. Mở session riêng, không dùng request session."""
    async with AsyncSessionLocal() as db:
        try:
            vec = await embed_text(content)
            await memory_repo.update_embedding(db, memory_id, vec)
            await db.commit()
        except Exception as e:
            await db.rollback()
            log.error("embedding.bg_task.failed", memory_id=str(memory_id), error=str(e))
            # Không raise — task thất bại im lặng; embedding=None, RAG sẽ skip record này
```

`asyncio.create_task(_embed_and_update(memory.id, content))` — gọi sau khi memory đã commit thành công (trong `create_committed()` ngay sau `db.commit()`; trong REST router ngay sau `await db.commit()`).

**DoD:** CRUD endpoints hoạt động. `pytest` green (với mock_embedding).

---

### PR S4-3 — Memory Tools + RAG in chat_service

**Files:**
- `app/services/embedding_service.py` — **đã tạo ở S4-2**, không tạo lại
- `app/services/memory_service.py` — **đã tạo ở S4-2** (`create`, `create_committed`, `_embed_and_update`); S4-3 chỉ dùng lại
- `app/config.py` — **verify existing** `embedding_model` và `embedding_dim` (line 44-45 đã có, không cần thêm)
- update `app/tools/executors.py` — thêm execute_save_memory, execute_search_memory, execute_forget_memory; update dispatch()
- update `app/tools/definitions.py` — thêm 3 tool schemas (từ docs/03); TOOLS: 5 → 8
- update `app/services/chat_service.py` — extract helper `_build_prompt_with_rag()` dùng chung cho cả hai functions:

```python
async def _build_prompt_with_rag(
    db: AsyncSession, user: User, content: str
) -> tuple[str, str]:
    """Fetch relevant memories → build system prompt. Used by both send_message and stream_message."""
    relevant_memories = await memory_service.search_semantic(
        db, user.id, content, limit=5, min_similarity=0.7
    )
    return build_system_prompt(user, memories=relevant_memories)

# Trong send_message() và stream_message() — thay dòng build_system_prompt cũ:
system_prompt, prompt_version = await _build_prompt_with_rag(db, current_user, req.content)
```

- update `app/llm/prompt.py` — `_PART_C` thêm save_memory/search_memory/forget_memory vào AVAILABLE TOOLS; bump `PROMPT_VERSION = "1.0.0-sprint4"`

**DoD (S4-3 merge gate — bắt buộc):**
- [ ] `"Nhớ là tôi dị ứng tôm"` → `save_memory` tool called → memory record committed (check DB)
- [ ] Hỏi follow-up `"Tôi có dị ứng gì?"` → memory retrieved → LLM trả lời đúng
- [ ] **Manual integration test trên Postgres thật** (local với `.env` real DB) — SQLite test trả `[]` nên KHÔNG đủ chứng minh RAG hoạt động
- [ ] Eval E-04 passed
- [ ] `pytest` green (unit tests với mock)

---

### PR S4-4 — Settings Endpoint

**Files:**
- update `app/schemas/auth.py` — thêm `UserUpdateRequest(name?, timezone?, locale?, assistant_name?)`
- update `app/repositories/user_repo.py` — thêm `update_fields(db, user_id, **kwargs)`
- update `app/services/auth_service.py` — thêm `update_profile(db, user_id, data)`
- update `app/routers/auth.py` — thêm `PATCH /auth/me → UserOut`

**Validation:** `@field_validator("timezone")` dùng `ZoneInfo(v)` để reject invalid timezone.

**DoD:** `PATCH /auth/me {"timezone": "America/New_York"}` cập nhật đúng. Invalid tz → 422.

---

### PR S4-5 — Backend Tests

**Files:**
- `tests/test_memories.py` (tạo mới) — 13 tests: CRUD, search, ownership isolation
- update `tests/conftest.py` — thêm `mock_embedding`, `mock_semantic_search`, và `auth_headers_user_b` fixtures
- update `tests/test_chat.py` — thêm RAG tests (xem dưới); **không phải test_orchestrator.py** vì `_build_prompt_with_rag` thuộc `chat_service`, orchestrator không biết về RAG

**Fixtures mới trong conftest.py:**
```python
@pytest.fixture
def mock_embedding():
    """Patch embed_text → không gọi OpenAI."""
    fake_vec = [0.1] * 1536
    with patch("app.services.embedding_service.embed_text",
               new_callable=AsyncMock, return_value=fake_vec):
        yield fake_vec

@pytest.fixture
def mock_semantic_search():
    """Patch semantic_search → SQLite không hỗ trợ <=> operator."""
    with patch("app.repositories.memory_repo.semantic_search",
               new_callable=AsyncMock, return_value=[]) as m:
        yield m
```

**Unit test cho semantic_search SQL query builder (không cần real Postgres):**

`memory_repo.semantic_search()` cần được tách thành hai phần: (1) dialect guard + query builder, (2) DB execution. Test sẽ cover query builder bằng cách kiểm tra SQL string được sinh ra:

```python
# tests/test_memories.py
def test_semantic_search_query_structure():
    """Query builder sinh đúng filter: cosine distance + ownership + soft-delete."""
    stmt = memory_repo._build_semantic_search_stmt(
        user_id=TEST_UUID, query_vec=[0.1] * 1536, limit=5, min_similarity=0.7
    )
    sql_str = str(stmt.compile(dialect=postgresql.dialect()))
    assert "embedding <=> " in sql_str
    assert "user_id" in sql_str          # ownership — bắt buộc
    assert "deleted_at IS NULL" in sql_str
    assert "is_active" in sql_str
    assert "embedding IS NOT NULL" in sql_str

async def test_semantic_search_ownership_isolation(async_client, auth_headers_user_b):
    """User B không thể search ra memory của user A qua semantic search."""
    # Tạo memory cho user A (dùng auth_headers thường)
    # Gọi search với user B auth → results phải empty
    resp = await async_client.post("/v1/memories/search",
        json={"query": "dị ứng tôm", "limit": 5}, headers=auth_headers_user_b)
    assert resp.status_code == 200
    assert resp.json()["items"] == []
# Note (implement): auth_headers_user_b chưa có trong conftest.py.
# Khi implement: thêm fixture hoặc inline register/login user B trong test này.
```

→ `_build_semantic_search_stmt()` tách ra khỏi session call → testable mà không cần DB.

**RAG tests trong `test_chat.py` (patch search_semantic, verify gọi đúng):**
```python
async def test_send_message_calls_rag(async_client, auth_headers, mock_llm, mock_semantic_search):
    """Non-stream: _build_prompt_with_rag được gọi với user content."""
    resp = await async_client.post("/v1/chat/send",
        json={"content": "test", "stream": False}, headers=auth_headers)
    assert resp.status_code == 200
    mock_semantic_search.assert_called_once()  # search_semantic được gọi

async def test_stream_message_calls_rag(async_client, auth_headers, mock_llm_stream, mock_semantic_search):
    """Stream: _build_prompt_with_rag được gọi với user content."""
    async with async_client.stream("POST", "/v1/chat/send",
        json={"content": "test", "stream": True}, headers=auth_headers) as r:
        _ = [line async for line in r.aiter_lines()]
    mock_semantic_search.assert_called_once()
```

**Lưu ý:** DoD "retrieved + đúng" cho RAG end-to-end verify bằng manual integration test trên Postgres thật — xem S4-3 DoD checklist.

---

### PR S4-6 — Frontend Memory UI

**Routing pattern:** App dùng single-page section navigation (không phải Next.js multi-route). Sidebar.tsx quản lý `Section` type; `app/page.tsx` render component theo section. **Không tạo `app/memories/page.tsx`** — thay vào đó tạo `components/memories/MemoryPage.tsx` và mount trong `page.tsx`.

`Section` type trong Sidebar.tsx hiện có: `"chat" | "todo" | "notes" | "reminders" | "memory" | "dashboard"` — `"memory"` đã có sẵn.

**Files:**
- update `lib/types/api.ts` — MemoryOut, MemoryCreate, MemoryUpdate, MemoryListOut, MemorySearchRequest
- update `lib/api.ts` — thêm listMemories, createMemory, updateMemory, deleteMemory, searchMemories
- `hooks/useMemories.ts` — useMemories, useCreateMemory, useUpdateMemory, useDeleteMemory
- `components/memories/MemoryCard.tsx` — type badge, content, importance, edit/delete actions
- `components/memories/MemoryList.tsx` — filter chips by type, list, empty state
- `components/memories/MemoryEditor.tsx` — form: content textarea, type select, importance slider (1-10)
- `components/memories/MemoryPage.tsx` — wire MemoryList + MemoryEditor (section root component)
- update `app/page.tsx` — thêm `{section === "memory" && <MemoryPage />}` (thay `<ComingSoon>`)

**Empty state text:** "Chưa có memory nào. Chat với JARVIS để tự động ghi nhớ thông tin quan trọng của bạn."

---

### PR S4-7 — Frontend Settings UI

**Routing pattern:** Tương tự S4-6 — thêm `"settings"` vào `Section` type, tạo `components/settings/SettingsPage.tsx`, mount trong `page.tsx`. **Không tạo `app/settings/page.tsx`**.

**Files:**
- update `lib/types/api.ts` — UserUpdateRequest type
- `hooks/useSettings.ts` — useMutation → PATCH /auth/me + update authStore
- `components/settings/SettingsPage.tsx` — form: name, assistant_name, timezone select, locale select
- update `components/layout/Sidebar.tsx` — thêm `"settings"` vào `Section` type + nav link
- update `app/page.tsx` — thêm `{section === "settings" && <SettingsPage />}`

**Sidebar nav sau Sprint 4:** Chat | Todos | Notes | Memories | Settings (Dashboard deferred S5)

---

### PR S4-8 (Stretch) — Conversation Summarization

**Files:**
- `migrations/versions/006_sprint4_conv_summary.py` — ADD COLUMN `summary TEXT` to conversations
- update `app/models/conversation.py` — thêm `summary = Column(sa.Text, nullable=True)`
- update `app/repositories/conversation_repo.py` — thêm `update_summary()`
- update `app/services/chat_service.py` — trigger `_summarize_conversation()` khi message_count == 20

**Điều kiện làm:** còn thời gian. Không block Sprint 4 DoD.

---

## Deferred (không làm Sprint 4)

| Feature | Sprint |
|---|---|
| Rate limiting (429) | 5 |
| Reminder + push notification | 5 |
| Dashboard | 5 |
| 4-tier LLM routing | 6 |
| Eval set automation (10 cases) | 6 |
| E2E Playwright tests | 6 |
