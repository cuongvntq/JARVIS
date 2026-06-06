# Current Sprint

> Sprint history (what each PR built): `memory/project-sprint-status.md` *(external Claude memory, không nằm trong repo)*
> This file covers: current state, design decisions chốt.

**As of:** 2026-06-06 | **Branch:** `main` (Sprint 6 merged) | **Tests:** 211 collected backend (+ Playwright E2E)

---

## Current State

- Sprint 0–6: MERGED vào main ✅
  - Sprint 6: QA + Polish + Beta Deploy (PR #27, 2026-06-03, 211 backend tests + E2E)
- **MVP 1 hoàn tất**
- **Tauri desktop migration đang thực hiện** — Phase 3/4 xong, Phase 4 (notification) là tiếp theo
  - Phase 1 ✅ DB local (PostgreSQL 18 + pgvector)
  - Phase 2 ✅ Tauri setup (Rust + WebView2 + tauri-plugin-shell)
  - Phase 3 ✅ PyInstaller sidecar + CORS fix + login hoạt động trong release build
  - Phase 4 ⬜ Reminders overhaul (xóa web push → in-app polling) + final MSI

---

## Design Decisions (chốt, không reopen)

| Decision | Why |
|---|---|
| `call_model = None` khi route to primary (Gemini) | `client.py` chỉ kích hoạt primary→fallback chain khi `model=None`; pinning model string bỏ qua fallback |
| `dateparser` vẫn còn trong `pyproject.toml` (line 37), chưa remove | Decision "bỏ dateparser" chưa được thực thi — lib vẫn là dependency |
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
| `EditorState` discriminated union cho Memory/Notes | Thay `isCreating + editingItem` bằng `{ mode: "closed"\|"create"\|"edit" }` — loại bỏ state inconsistency |
| HTTPException handler thống nhất ở `main.py` | FastAPI default `{ detail }` shape gây crash `new ApiException(res.status, body.error)` khi `body.error` là undefined |
| isSaving guard + disable fields trong editor (Memory & Notes) | Tránh overwrite draft khi `mutateAsync` resolve sau khi user đã sửa tiếp |
| APScheduler `max_instances=1, coalesce=True` in-process | MVP1, single Railway instance; max_instances=1 ngăn job overlap khi chạy lâu hơn interval |
| Atomic `UPDATE...RETURNING` cho scheduler claim | Idempotent: nếu pod restart giữa chừng, row ở trạng thái `sending` không bị fire lại |
| Stuck-sending recovery: `sending → failed` sau 5 phút | Tránh reminder kẹt `sending` mãi nếu app crash sau claim nhưng trước khi update sent/failed |
| `push_subscriptions` tách riêng khỏi `reminders` | Delivery state thuộc `reminders.status`; subscription keys là concern khác |
| 1 active push subscription per user (overwrite khi re-subscribe) | Đơn giản hơn per-device; mở rộng ở post-MVP1 |
| SlowAPI Upstash Redis rate limit store (Sprint 6) | Swap từ in-memory; cần `UPSTASH_REDIS_URL` env var; fallback in-memory nếu URL rỗng |
| `_bg_tasks: set[asyncio.Task]` trong `chat_service.py` và `memory_service.py` | Strong reference pattern (RUF006) — tasks bị GC nếu không giữ reference |
| `pnpm check` không dùng `--write` | CI-safe: biome check . (read-only); format dùng `pnpm format` riêng |
| SQLite `create_all` guard: `startswith("sqlite") AND app_env=="test"` | Ngăn schema mutation nếu dev/prod vô tình dùng SQLite URL |
| `DATABASE_URL_DIRECT` dùng `psycopg2` (sync) cho Alembic | Alembic `env.py` dùng sync `engine_from_config` — không tương thích `asyncpg` |
| Playwright `globalSetup` warm-up trước tests | Next.js dev JIT-compile route trên first request; warm-up loại cold-start flakiness |

---

## Sprint 6 — DONE ✅ (merged 2026-06-03)

**Goal:** QA + polish + beta deploy

**PR:** #27 `feat/sprint6` — single PR, all tickets + review fixes

| Ticket | Nội dung |
|---|---|
| S6-1 | Sentry BE (FastAPIIntegration + SqlalchemyIntegration) + FE (`@sentry/nextjs`, `instrumentation.ts`) |
| S6-2 | Prompt eval automation — `tests/eval/test_prompt_eval.py`, 10 cases, `RUN_EVAL=1` flag |
| S6-3 | E2E Playwright — `playwright.config.ts`, 4 spec files (auth/chat/reminder/dashboard), `globalSetup` warm-up |
| S6-4 | 4-tier LLM routing — `llm_tier3=gpt-5.4-nano`, `llm_tier4=gpt-5-mini` trong Settings + client.py |
| S6-5 | Upstash Redis rate limit — `redis[asyncio]` dep, `upstash_redis_url` setting, fallback in-memory |
| S6-6 | Conversation summarization — migration 007 `summary TEXT`, `_auto_summarize_conversation()` background task |
| S6-7 | Logout UI — logout button trong Sidebar, `authStore.logout()` action |
| S6-8 | mypy strict pass — 0 errors trong 69 source files |

**Review fixes (post-PR):**
- pnpm 11 `allowBuilds` format (`pnpm-workspace.yaml`)
- Email domain `@example.com` trong E2E fixtures (thay `@test.local`)
- Sentry `instrumentation.ts` migration (Next.js App Router)
- Playwright strict locator — `getByRole("heading")` thay `text=JARVIS`
- E2E `globalSetup` warm-up + `waitForURL` 30s
- `biome check --write` fix 52 files + `test-results/` vào ignore
- Alembic CI dùng `psycopg2` sync driver
- Background task strong reference (`_bg_tasks` set) trong `chat_service.py`
- Vector SQL validation trước f-string interpolation
- SQLite `create_all` guard bằng `app_env=="test"`
- GitHub Actions CI workflow với Alembic migration smoke test (pgvector/pg16 container)
- `global-error.tsx` + `sourcemaps.deleteSourcemapsAfterUpload: true`

---

## Tauri Desktop Migration — Design Decisions

| Decision | Why |
|---|---|
| Tauri v2 + WebView2 dùng origin `http://tauri.localhost` (không phải `tauri://localhost`) | WebView2 trên Windows set origin này; docs Tauri ghi sai. CORS phải include `http://tauri.localhost` |
| `#[cfg(not(debug_assertions))]` guard cho sidecar spawn | Trong dev mode (`pnpm tauri dev`) backend chạy riêng bên ngoài — không spawn sidecar |
| tiktoken cần `collect_all("tiktoken")` + `hiddenimports: ["tiktoken_ext", "tiktoken_ext.openai_public"]` | `collect_all("litellm")` không tự kéo tiktoken BPE data; thiếu → `ValueError: Unknown encoding cl100k_base` |
| `.env` phải copy thủ công vào `target/release/.env` sau mỗi build | Tauri không bundle `.env` (gitignored); không thể automate vì file chứa secret |
| PyInstaller `console=False` trong onefile | Không hiện terminal window khi user chạy app; log qua structlog JSON vào file nếu cần |
| Sidecar kill trong `on_window_event(Destroyed)` | Nếu kill trong `CloseRequested`, window có thể bị cancel close; `Destroyed` là event chắc chắn window đã đóng |

---

## Phase 4 — Tiếp theo (reminders overhaul)

Xem chi tiết trong [`docs/migration-desktop-app.md`](../migration-desktop-app.md#phase-4--notification--build-installer).

Tóm tắt việc cần làm:
1. Migration: `ALTER TYPE reminder_status ADD VALUE 'due'`
2. Backend: `GET /due` + `POST /{id}/ack` routes, scheduler set `due` thay vì gọi push
3. Xóa: `push_service.py`, `push_subscription_repo.py`, `notifications.py`, `push_subscriptions` table
4. Frontend: `useReminderPolling` hook poll 60s + toast + ack; xóa `usePushNotification.ts`, `sw.js`
5. Build final `.msi` + test cài đặt

---

## Post-MVP 1 Backlog

| Feature | Lý do defer |
|---|---|
| Google OAuth | Scope reduction Sprint 1 |
| Idempotency-Key header | Không cần MVP1 |
| Per-device push subscription | 1 sub/user đủ MVP1 |
| Native OS notification khi app minimize | Dùng `@tauri-apps/plugin-notification`; cùng API `/due`+`/ack` |
| Loading state khi sidecar start (~25s) | UX: hiện spinner thay vì login form khi backend chưa ready |
| Beta deploy (Railway + Vercel) | Bỏ — đã chuyển sang desktop app |
