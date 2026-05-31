# Current Sprint

> Sprint history (what each PR built): `memory/project-sprint-status.md` *(external Claude memory, không nằm trong repo)*
> This file covers: current state, design decisions chốt, Sprint 5 plan.

**As of:** 2026-05-31 | **Branch:** `main` (Sprint 4 merged) | **Tests:** 167 passed

---

## Current State

- Sprint 0–4: MERGED vào main ✅
  - Sprint 4: Memory System + RAG + Settings (PR #13–#15, 2026-05-31) — 167 tests
- Sprint 5: **NEXT** — Reminder + Dashboard + Push notification

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
| Soft delete conversations + todos + notes + memories | Audit trail, recovery khả năng |
| Cursor-based pagination (không offset) | Consistent với concurrent inserts |
| `user_tz` thread qua orchestrator → dispatch → executor | Tool executor cần timezone user để filter đúng |
| Atomic `UPDATE...RETURNING` cho refresh token rotation | Tránh race condition 2 request cùng dùng token |
| `streamSucceeded` flag trong ChatInterface.tsx | Chống navigate đến rolled-back conv_id nếu stream error sau meta event |
| `except Exception` (không chỉ RuntimeError) trong stream_message | Mọi unexpected exception đều cần rollback, không chỉ RuntimeError |
| ORM `embedding = sa.JSON` | SQLite compat; Postgres dùng `vector(1536)` via migration DDL |
| RAG call ở `chat_service.py` (không trong orchestrator) | `build_system_prompt()` gọi trước orchestrator — inject memory tại đây |
| `asyncio.create_task()` cho embedding | Tool executors không có FastAPI request context, không inject BackgroundTasks |
| `memory_service.create_committed()` dùng session riêng | Tool executor không được commit shared chat session — gây commit toàn bộ pending writes |
| `MemoryOut` snapshot trước khi session đóng | Tránh `DetachedInstanceError` sau `async with` block |
| `memory_repo.semantic_search()` trả `[]` trên SQLite | `<=>` operator không tồn tại trong SQLite |
| Single-page section navigation (không multi-route) | Sidebar `Section` type + mount component trong `page.tsx` — không tạo route riêng |
| `EditorState` discriminated union cho Memory/Notes | Thay `isCreating + editingItem` bằng `{ mode: "closed"|"create"|"edit" }` — loại bỏ state inconsistency |
| HTTPException handler thống nhất ở `main.py` | FastAPI default `{ detail }` shape gây crash `new ApiException(res.status, body.error)` khi `body.error` là undefined |
| isSaving guard + disable fields trong editor (Memory & Notes) | Tránh overwrite draft khi `mutateAsync` resolve sau khi user đã sửa tiếp |

---

## Sprint 4 — DONE ✅ (merged 2026-05-31)

**Goal:** Memory System + RAG + Settings UI
**Result:** 167 tests pass. Memory CRUD + semantic RAG + Settings endpoint + Memory UI + Settings UI.

| PR | Branch | Tên | Status |
|---|---|---|---|
| #13 | `feat/sprint4-settings` | S4-4: PATCH /auth/me + validation | MERGED |
| #14 | `feat/sprint4-settings-fe` | S4-7: Frontend Settings UI | MERGED |
| #15 | `feat/sprint4-memory-fe` | S4-1→S4-6: Memory DB + API + Tools + RAG + Memory UI + Notes fixes + error envelope | MERGED |

**Thực tế merge order:** S4-1 → S4-2 → S4-3 → S4-5 → S4-4 (PR #13) → S4-7 (PR #14) → S4-6 (PR #15).
S4-8 (stretch: conv summarization) → deferred sang Sprint 5 hoặc Sprint 6.

---

## Sprint 5 Plan — Reminder + Dashboard + Push

**Goal:** Reminder với push notification đúng giờ, dashboard overview hôm nay
**DoD:** Tạo reminder → đúng giờ nhận push notification. Dashboard hiện todo hôm nay + memory count + reminder count.

### PR Breakdown (draft)

| PR | Branch | Thành phần | Depends |
|---|---|---|---|
| S5-1 | `feat/sprint5-reminder-db` | Migration 007 reminders + ORM | main |
| S5-2 | `feat/sprint5-reminder-api` | Schema + Repo + Svc + Router `/v1/reminders` | S5-1 |
| S5-3 | `feat/sprint5-scheduler` | APScheduler job: check remind_at, fire push | S5-2 |
| S5-4 | `feat/sprint5-push` | VAPID setup, `/v1/notifications` subscribe/send | S5-3 |
| S5-5 | `feat/sprint5-dashboard-api` | `GET /v1/dashboard/today` — todos + reminders + summary | S5-2 |
| S5-6 | `feat/sprint5-dashboard-fe` | DashboardPage component, mount in page.tsx | S5-5 |
| S5-7 | `feat/sprint5-reminder-fe` | Types + hooks + ReminderPage (list + create) | S5-2 |
| S5-8 | `feat/sprint5-rate-limit` | SlowAPI rate limiting middleware | main |

### Key design questions (resolve khi bắt đầu sprint)

- Reminder scheduler: dùng APScheduler hay cron job riêng?
- Dashboard data: aggregation query hay multiple service calls?
- Push: store subscription per device hay per user (1 active)?
- Rate limit store: in-memory (dev) vs Redis Upstash (prod)?

---

## Deferred (Sprint 5+)

| Feature | Sprint |
|---|---|
| Conversation summarization | 5 hoặc 6 |
| Rate limiting (429) | 5 (S5-8) |
| 4-tier LLM routing | 6 |
| Eval set automation (10 cases) | 6 |
| E2E Playwright tests | 6 |
| Google OAuth | Post-MVP 1 |
| Idempotency-Key header | Post-MVP 1 |
