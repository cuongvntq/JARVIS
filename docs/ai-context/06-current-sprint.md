# Current Sprint

> Sprint history (what each PR built): `memory/project-sprint-status.md` *(external Claude memory, không nằm trong repo)*
> This file covers: current state, design decisions chốt, Sprint 3 plan.

**As of:** 2026-05-28 | **Branch:** `feat/sprint3-todo-ui` (in progress) | **Tests:** 117 passed

---

## Current State

- Sprint 0–2: MERGED vào main
- Sprint 3: IN PROGRESS (`feat/sprint3-todo-ui`)
  - Backend B3-1→B3-9: **DONE** (117 tests pass)
  - Frontend F3-1→F3-7: **TODO**

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
| Soft delete conversations + todos | Audit trail, recovery khả năng |
| Cursor-based pagination (không offset) | Consistent với concurrent inserts |
| `user_tz` thread qua orchestrator → dispatch → executor | Tool executor cần timezone user để filter đúng |
| Atomic `UPDATE...RETURNING` cho refresh token rotation | Tránh race condition 2 request cùng dùng token |

---

## Sprint 3 Plan — Todo UI + Note module

**Goal:** CRUD todo/note trên UI + chat integration
**DoD:** User có thể tạo/xem/xóa todo từ UI; chat "thêm ghi chú X" → lưu DB → hiện trong danh sách

### Backend ✅ DONE (2026-05-28)

**Note module:**
- [x] Migration 004: bảng `notes` (id, user_id, title, content TEXT, tags JSON, pinned BOOL, created_at, updated_at, deleted_at)
- [x] `models/note.py` — Note ORM; thêm `notes` relationship vào User
- [x] `schemas/note.py` — NoteCreate, NoteUpdate, NotePatch (internal), NoteOut, NoteListOut
- [x] `repositories/note_repo.py` — get_by_id, list_notes (filter: pinned, q, cursor, pinned-first order), create, update_fields, soft_delete
- [x] `services/note_service.py` — create, get, list, update, patch, pin, unpin, delete
- [x] `routers/notes.py` — `/v1/notes` CRUD + pin/unpin, đã register trong main.py
- [x] `tools/definitions.py` — thêm `create_note`, `search_notes` tool schemas
- [x] `tools/executors.py` — thêm executors + update dispatch()

**Chat improvement:**
- [x] Auto-title conversation từ first message (truncate 50 chars, `chat_service.py`)

### Frontend — TODO (F3-1 → F3-7)

**F3-1: Sidebar + routing**
- Navigation: Chat | Todos | Notes với active state per route
- Tạo `app/todos/page.tsx`, `app/notes/page.tsx` (placeholder)

**F3-2: Todo API types + hooks**
- `lib/types/api.ts` — thêm TodoOut, TodoCreate, TodoListOut
- `hooks/useTodos.ts` — useQuery list + useMutation create/complete/delete

**F3-3: TodoCard component**
- `components/todos/TodoCard.tsx` — title, status badge, priority, due_at, tags, complete/delete inline

**F3-4: Todo page đầy đủ**
- `app/todos/page.tsx` — filter tabs (Today | Upcoming | Overdue | Completed | All), list TodoCards
- Invalidate `['todos']` khi chat tạo todo mới

**F3-5: Create Todo dialog**
- `components/todos/CreateTodoDialog.tsx` — react-hook-form + zod, dialog/drawer

**F3-6: Note API types + hooks**
- `lib/types/api.ts` — thêm NoteOut, NoteCreate, NoteListOut
- `hooks/useNotes.ts` — list + create/update/delete/pin/unpin mutations

**F3-7: Note UI**
- `components/notes/NoteList.tsx` — list, pinned section trên đầu, search input
- `components/notes/NoteEditor.tsx` — textarea markdown, title field
- `app/notes/page.tsx` — wires NoteList + NoteEditor

---

## Deferred (không làm Sprint 3)

| Feature | Sprint |
|---|---|
| SSE streaming chat | 3 (stretch — có thể trượt sang 4) |
| Rate limiting | 5 |
| Memory + RAG | 4 |
| Reminder + push notification | 5 |
| 4-tier LLM routing | 6 |
| Eval set automation (10 cases) | 6 |
| Google OAuth | Post-MVP 1 (removed) |
