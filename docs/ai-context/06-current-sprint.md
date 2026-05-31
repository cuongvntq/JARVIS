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

### Design Decisions (chốt trước khi code)

| Câu hỏi | Quyết định | Lý do |
|---|---|---|
| Scheduler | APScheduler in-process, `max_instances=1`, `coalesce=True` | MVP1, single Railway instance; max_instances=1 ngăn job overlap khi chạy lâu hơn interval |
| Scheduler claim | Atomic `UPDATE reminders SET status='sending' WHERE status='pending' AND remind_at <= now` trước khi gửi push | Idempotent: nếu pod restart giữa chừng, row đã ở trạng thái `sending` không bị fire lại |
| Scheduler stuck-sending recovery | Job cũng reset `sending → failed` nếu `updated_at < now - interval '5 minutes'` | Tránh reminder bị kẹt `sending` mãi nếu app crash sau claim nhưng trước khi update sent/failed |
| Push subscription table | Tách `push_subscriptions` (endpoint/p256dh/auth/is_active) khỏi delivery state | Delivery state thuộc về `reminders.status`; trộn 2 trách nhiệm vào 1 table gây ambiguous `reminder_id nullable` |
| Push subscription scope | 1 active per user (overwrite khi re-subscribe) | Đơn giản hơn per-device; mở rộng ở Sprint 6+ |
| Rate limit store | In-memory (SlowAPI default) | Không cần Redis cho MVP1; swap sang Upstash Redis ở Sprint 6 |
| Dashboard data | Multiple service calls (không raw SQL aggregation) | Dễ maintain hơn |

---

### S5-1 — DB + ORM
**Branch:** `feat/sprint5-reminder-db` | **Depends:** main | **Size:** ~80 lines

**Files:**
- `migrations/versions/006_sprint5_reminders.py` — tạo `reminders` + `push_subscriptions` tables, ENUM `reminder_status`
- `app/models/reminder.py` — Reminder ORM
- `app/models/push_subscription.py` — PushSubscription ORM (chỉ lưu push endpoint/keys)
- `app/models/user.py` — thêm relationships `reminders`, `push_subscriptions`

**reminders schema:**
```
id UUID PK, user_id FK, title TEXT, description TEXT?,
remind_at TIMESTAMPTZ NOT NULL, status reminder_status DEFAULT 'pending',
source TEXT DEFAULT 'ui', created_at, updated_at, deleted_at
-- ENUM reminder_status: pending | sending | sent | failed | cancelled
--   sending = đã được scheduler claim, đang gửi (tránh duplicate push khi restart)
-- idx: (user_id, remind_at) WHERE status='pending' AND deleted_at IS NULL
```

**push_subscriptions schema:**
```
id UUID PK, user_id FK UNIQUE (1 active per user),
endpoint TEXT NOT NULL, p256dh TEXT NOT NULL, auth TEXT NOT NULL,
is_active BOOL DEFAULT TRUE, created_at, updated_at
-- Chỉ lưu push subscription keys — KHÔNG lưu reminder_id hay delivery state
-- Delivery state thuộc reminders.status
-- idx: (user_id) WHERE is_active=TRUE
```

---

### S5-2 — Reminder CRUD API + Tools
**Branch:** `feat/sprint5-reminder-api` | **Depends:** S5-1 | **Size:** ~400 lines

**Files:**
- `app/schemas/reminder.py` — ReminderCreate, ReminderUpdate, ReminderOut, ReminderListOut
- `app/repositories/reminder_repo.py` — CRUD + `get_pending_due(before_utc)` cho scheduler
- `app/services/reminder_service.py` — CRUD + validate `remind_at` phải là tương lai
- `app/routers/reminders.py` — mount `/v1/reminders`
- `app/tools/definitions.py` — thêm `create_reminder`, `list_reminders` schemas
- `app/tools/executors.py` — thêm `execute_create_reminder`, `execute_list_reminders`
  - `execute_create_reminder` phải parse `remind_at` qua `datetime_parser.parse_datetime(raw, user_tz)` trước khi lưu — giống todo executor, không trust ISO string thẳng từ LLM
  - Nếu parse fail hoặc `remind_at` là quá khứ → trả `{ success: False, error: { code: "invalid_remind_at" } }` (không raise exception)
- `tests/test_reminders.py` — ≥15 tests (happy path + error + ownership)
  - Bao gồm: remind_at trong quá khứ → 422, thiếu remind_at → 422
  - Executor tests: parse "chiều nay" với user_tz, parse ISO UTC, invalid time → error result

**Endpoints:**
```
GET    /v1/reminders            ?status=pending&limit=20&cursor=
POST   /v1/reminders → 201      { title*, remind_at* ISO UTC, description?, source? }
GET    /v1/reminders/{id}
PATCH  /v1/reminders/{id}       { title?, remind_at?, description? }
PATCH  /v1/reminders/{id}/cancel → 200
DELETE /v1/reminders/{id} → 204  (soft delete)
```

**ReminderOut:** `{ id, user_id, title, description, remind_at, status, source, created_at, updated_at }`

---

### S5-3 — APScheduler + Push backend
**Branch:** `feat/sprint5-scheduler-push` | **Depends:** S5-2 | **Size:** ~300 lines

**Files:**
- `app/services/scheduler_service.py` — APScheduler setup (`max_instances=1`, `coalesce=True`), job `check_reminders()` mỗi 60s
- `app/services/push_service.py` — pywebpush wrapper: `send_push(endpoint, p256dh, auth, payload)`
- `app/repositories/push_subscription_repo.py` — upsert subscription (1 per user), get active by user_id
- `app/routers/notifications.py` — `/v1/notifications/subscribe`, `/v1/notifications/unsubscribe`
- `app/main.py` — start/stop scheduler trong `lifespan` context manager
- `app/config.py` — keys đã có (`vapid_public_key`, `vapid_private_key`, `vapid_subject`), không cần thêm

**Scheduler job logic:**
```python
# APScheduler config: max_instances=1, coalesce=True (skip missed fires)
# Mỗi 60s — 2 bước:
#
# Bước A — recovery: reset stuck-sending
#   UPDATE reminders SET status='failed'
#     WHERE status='sending' AND updated_at < now - interval '5 minutes'
#   (tránh reminder kẹt sending mãi nếu crash sau claim)
#
# Bước B — claim + send:
#   UPDATE reminders SET status='sending'
#     WHERE status='pending' AND remind_at <= now AND deleted_at IS NULL
#     RETURNING id, user_id, title
#   Với mỗi claimed reminder:
#     sub = get push_subscriptions WHERE user_id AND is_active=TRUE
#     result = push_service.send_push(sub.endpoint, sub.p256dh, sub.auth, { title, body })
#     UPDATE reminder.status = 'sent' | 'failed'
```

**SQLite compat note:** `UPDATE...RETURNING` là Postgres-only.
Tests mock `scheduler_service.check_reminders()` hoặc test từng unit function riêng (claim, recovery, push, update).
Không integration-test scheduler loop trên SQLite.

**Endpoints:**
```
POST /v1/notifications/subscribe    { endpoint*, p256dh*, auth* }  → 201
POST /v1/notifications/unsubscribe  → 204
```

---

### S5-4 — Dashboard API
**Branch:** `feat/sprint5-dashboard-api` | **Depends:** S5-2 | **Size:** ~150 lines

**Files:**
- `app/services/dashboard_service.py` — tổng hợp từ todo/reminder/memory service
- `app/routers/dashboard.py` — `GET /v1/dashboard/today`
- `tests/test_dashboard.py` — ≥5 tests

**Response shape:**
```json
{
  "todos_today":        [ TodoOut ],
  "todos_count":        { "today": N, "overdue": N, "upcoming": N },
  "reminders_upcoming": [ ReminderOut ],
  "memories_count":     N,
  "as_of":              "ISO UTC"
}
```

`reminders_upcoming`: top 5, `status IN ('pending', 'sending')`, `remind_at >= now`, `ORDER BY remind_at ASC`, `deleted_at IS NULL`.

---

### S5-5 — Rate Limiting
**Branch:** `feat/sprint5-rate-limit` | **Depends:** main (standalone) | **Size:** ~80 lines

**Files:**
- `backend/pyproject.toml` — thêm `slowapi` dependency
- `app/middleware/rate_limit.py` — SlowAPI limiter setup, in-memory store
- `app/routers/chat.py` — `@limiter.limit("20/minute")` trên `/v1/chat/send`
- `app/main.py` — register SlowAPI state + exception handler (429)
- `tests/test_rate_limit.py` — test 429 trả về đúng format

---

### S5-6 — Frontend Reminder UI
**Branch:** `feat/sprint5-reminder-fe` | **Depends:** S5-2 | **Size:** ~350 lines

**Files:**
- `lib/types/api.ts` — ReminderOut, ReminderCreate, ReminderListOut
- `hooks/useReminders.ts` — useInfiniteQuery (cursor) + useCreateReminder + useCancelReminder + useDeleteReminder
- `components/reminders/ReminderCard.tsx` — status badge, countdown đến remind_at, cancel/delete
- `components/reminders/ReminderList.tsx` — filter tabs upcoming/sent/all, list cards
- `components/reminders/ReminderForm.tsx` — title + datetime input + submit
- `components/reminders/RemindersPage.tsx` — section root + EditorState pattern
- `app/page.tsx` — mount RemindersPage (thay ComingSoon placeholder)
- `components/layout/Sidebar.tsx` — nav item đã có, KHÔNG cần sửa

---

### S5-7 — Frontend Dashboard UI
**Branch:** `feat/sprint5-dashboard-fe` | **Depends:** S5-4 | **Size:** ~250 lines

**Files:**
- `lib/types/api.ts` — DashboardOut
- `hooks/useDashboard.ts` — useQuery `GET /v1/dashboard/today`, refetchInterval 5 phút
- `components/dashboard/DashboardPage.tsx` — section root, grid layout
- `components/dashboard/TodayStats.tsx` — count cards (today / overdue / upcoming)
- `components/dashboard/UpcomingReminders.tsx` — next 5 reminders + countdown
- `components/dashboard/MemoryCount.tsx` — memory count chip
- `app/page.tsx` — Dashboard là default section khi mở app (thay Chat)

---

### S5-8 — Push Notification Frontend
**Branch:** `feat/sprint5-push-fe` | **Depends:** S5-3 | **Size:** ~200 lines

**Files:**
- `public/sw.js` — Service Worker: handle `push` event → `showNotification(title, { body, icon })`
- `hooks/usePushNotification.ts` — register SW → `PushManager.subscribe(vapidPublicKey)` → POST `/v1/notifications/subscribe`
- `components/settings/SettingsPage.tsx` — thêm toggle "Bật thông báo đẩy", gọi `usePushNotification`
- `.env.example` — thêm `NEXT_PUBLIC_VAPID_PUBLIC_KEY`

**Note:** VAPID public key expose qua `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (safe — public key).

---

### Dependency Graph

```
main ──┬── S5-1 ── S5-2 ──┬── S5-3 ────────────────── S5-8 (push FE)
       │                  ├── S5-4 ── S5-7 (dashboard FE)
       │                  └── S5-6 (reminder FE)
       └── S5-5 (rate limit, bất kỳ lúc nào)
```

**Song song được:** S5-5 | S5-6 sau S5-2 merge | S5-7 sau S5-4 merge | S5-8 sau S5-3 merge

### Summary

| PR | Scope | Est. size |
|---|---|---|
| S5-1 | Migration 006 + ORM | ~80 lines |
| S5-2 | Reminder CRUD API + Tools | ~400 lines |
| S5-3 | Scheduler + Push BE | ~300 lines |
| S5-4 | Dashboard API | ~150 lines |
| S5-5 | Rate limiting | ~80 lines |
| S5-6 | Reminder UI | ~350 lines |
| S5-7 | Dashboard UI | ~250 lines |
| S5-8 | Push FE + Service Worker | ~200 lines |

---

## Deferred (Sprint 5+)

| Feature | Sprint |
|---|---|
| Conversation summarization | 5 hoặc 6 |
| Rate limiting (429) | 5 (S5-5) |
| 4-tier LLM routing | 6 |
| Eval set automation (10 cases) | 6 |
| E2E Playwright tests | 6 |
| Google OAuth | Post-MVP 1 |
| Idempotency-Key header | Post-MVP 1 |
