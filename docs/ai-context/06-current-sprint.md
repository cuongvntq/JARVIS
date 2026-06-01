# Current Sprint

> Sprint history (what each PR built): `memory/project-sprint-status.md` *(external Claude memory, không nằm trong repo)*
> This file covers: current state, design decisions chốt, Sprint 6 plan.

**As of:** 2026-06-02 | **Branch:** `main` (Sprint 5 merged) | **Tests:** 211 collected (196 functions)

---

## Current State

- Sprint 0–5: MERGED vào main ✅
  - Sprint 5: Reminder + Dashboard + Push Notification (PR #16–#25, 2026-06-01, 211 tests)
- Sprint 6: **NEXT** — QA + polish + beta deploy

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
| APScheduler `max_instances=1, coalesce=True` in-process | MVP1, single Railway instance; max_instances=1 ngăn job overlap khi chạy lâu hơn interval |
| Atomic `UPDATE...RETURNING` cho scheduler claim | Idempotent: nếu pod restart giữa chừng, row ở trạng thái `sending` không bị fire lại |
| Stuck-sending recovery: `sending → failed` sau 5 phút | Tránh reminder kẹt `sending` mãi nếu app crash sau claim nhưng trước khi update sent/failed |
| `push_subscriptions` tách riêng khỏi `reminders` | Delivery state thuộc `reminders.status`; subscription keys là concern khác |
| 1 active push subscription per user (overwrite khi re-subscribe) | Đơn giản hơn per-device; mở rộng ở Sprint 6+ |
| SlowAPI in-memory rate limit store | Không cần Redis cho MVP1; swap sang Upstash Redis ở Sprint 6 |
| Dashboard dùng multiple service calls (không raw SQL aggregation) | Dễ maintain hơn |
| `NoteUpdate` / `ReminderUpdate` reject explicit null via `field_validator(mode="before")` | Pydantic default + `exclude_unset=True` truyền `None` tới nullable=False DB column → 500; validator trả 422 thay vì 500 |
| Auth store `clearAuth()` sau khi `silentRefresh` fail | `isAuthenticated` stays true nếu không clear → UI stuck, không redirect login |
| `typedRoutes: true` ở top-level `next.config.ts` (không phải trong `experimental`) | Next.js 15 stable API — `experimental.typedRoutes` deprecated |

---

## Sprint 5 — DONE ✅ (merged 2026-06-01)

**Goal:** Reminder + Dashboard + Push notification
**Result:** 211 tests pass. Full reminder CRUD + APScheduler + pywebpush + dashboard + rate limiting + Push FE + review fixes.

| PR | Branch | Tên | Status |
|---|---|---|---|
| #16 | `feat/sprint5-reminder-db` | S5-1: Migration 006 — reminders + push_subscriptions + ORM | MERGED |
| #17 | `feat/sprint5-reminder-api` | S5-2: Reminder CRUD API + create_reminder/list_reminders tools | MERGED |
| #18 | `feat/sprint5-rate-limit` | S5-5: Rate limiting — 60/min general, 20/min chat | MERGED |
| #19 | `feat/sprint5-dashboard-api` | S5-4: Dashboard API — GET /v1/dashboard/today | MERGED |
| #20 | `feat/sprint5-scheduler-push` | S5-3: APScheduler + pywebpush push notifications | MERGED |
| #21 | `fix/ruff-format-post-sprint5-merge` | chore: ruff format cleanup post-merge | MERGED |
| #22 | `feat/sprint5-reminder-fe` | S5-6: Reminder UI | MERGED |
| #23 | `feat/sprint5-dashboard-fe` | S5-7: Dashboard UI (default section khi mở app) | MERGED |
| #24 | `feat/sprint5-push-fe` | S5-8: Push Notification Frontend + Service Worker | MERGED |
| #25 | `fix/review-findings-post-sprint5` | fix: 3 post-sprint5 review findings (null→422, auth clearAuth, typedRoutes) | MERGED |

**Test delta Sprint 5:** 167 → 211 (+44 tests, +15 from parametrize)
- test_reminders.py: +31 (new)
- test_notifications.py: +6 (new)
- test_dashboard.py: +5 (new)
- test_rate_limit.py: +3 (new)
- Others: minor changes

**Deferred from Sprint 5:**
- Conversation summarization → Sprint 6
- Redis Upstash rate limit store (currently in-memory) → Sprint 6
- Per-device push subscription (currently 1 per user) → post-MVP 1

---

## Sprint 6 Plan — QA + Polish + Beta Deploy

**Goal:** Sentry, eval set automation, E2E tests, 4-tier LLM routing, Upstash Redis rate limit
**DoD:** Eval 10 case ≥9/10, Sentry sạch 1 tuần, health monitoring active

### Planned work

| Ticket | Thành phần | Size |
|---|---|---|
| S6-1 | Sentry integration (BE + FE) | ~60 lines |
| S6-2 | Prompt eval automation — `tests/eval/test_prompt_eval.py` | ~150 lines |
| S6-3 | E2E Playwright: login → chat → todo + reminder flow | ~200 lines |
| S6-4 | 4-tier LLM routing (gpt-5.4-nano + gpt-5-mini) | ~50 lines |
| S6-5 | Upstash Redis rate limit store (swap SlowAPI backend) | ~40 lines |
| S6-6 | Conversation summarization (>20 messages → auto-summarize) | ~120 lines |
| S6-7 | Logout UI (button trong Sidebar hoặc Settings) | ~30 lines |
| S6-8 | mypy strict pass — fix 27 errors | ~80 lines |

### Known tech debt (deferred from review)
- Medium: Add logout UI (currently no logout button in frontend)
- Medium: Fix 27 mypy strict errors
- Low: Fix CRLF/biome format pre-existing issues
- Low: Add frontend smoke tests or configure `passWithNoTests`

---

## Deferred (Sprint 6+)

| Feature | Sprint |
|---|---|
| Conversation summarization | 6 |
| 4-tier LLM routing | 6 |
| Eval set automation (10 cases) | 6 |
| E2E Playwright tests | 6 |
| Upstash Redis rate limit | 6 |
| Google OAuth | Post-MVP 1 |
| Idempotency-Key header | Post-MVP 1 |
| Per-device push subscription | Post-MVP 1 |
