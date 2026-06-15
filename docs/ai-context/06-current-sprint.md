# Current Sprint

> Sprint history (what each PR built): `memory/project-sprint-status.md` *(external Claude memory, không nằm trong repo)*
> This file covers: current state, design decisions chốt.

**As of:** 2026-06-15 | **Branch:** `main` | **Tests:** 263 passed backend, 10 deselected (+ Playwright E2E)

---

## Current State

- Sprint 0–6: MERGED vào main ✅
  - Sprint 6: QA + Polish + Beta Deploy (PR #27, 2026-06-03, 211 backend tests + E2E)
- **MVP 1 hoàn tất**
- **Tauri Desktop Migration: Phase 1-4 hoàn tất 100%** (PR #34, squash merged 2026-06-07, commit `066c011`)
  - Phase 1 ✅ DB local (PostgreSQL 18 + pgvector)
  - Phase 2 ✅ Tauri setup (Rust + WebView2 + tauri-plugin-shell)
  - Phase 3 ✅ PyInstaller sidecar + CORS fix + login hoạt động trong release build
  - Phase 4 ✅ Reminders overhaul (in-app polling) + build `.msi` cuối + test cài đặt clean-install PASS (2026-06-07)
- **Post-Phase 4 polish** (2026-06-07, merged sau PR #34):
  - PR #35 ✅ Loading state khi sidecar khởi động — `AuthGuard` poll `GET /health` (1s, tối đa 90s) trước khi chạy auth flow; fix biome ignore `src-tauri/target`, thêm `jsdom` dep
  - PR #36 ✅ Native OS notification cho reminder đến hạn — `@tauri-apps/plugin-notification`, gọi song song với in-app toast trong `useReminderPolling`
- **MVP2 Sprint 7 — Infra: Auto-update + Idempotency-Key — MERGED 2026-06-13** ✅
  - PR #39 ✅ `IdempotencyMiddleware` (`backend/app/middleware/idempotency.py`) — merged `e691b07`
  - PR #40 ✅ Tauri auto-update infra (`tauri-plugin-updater` + GitHub Releases) — merged `f58819e`
  - 221 backend tests pass, ruff/mypy clean
- **MVP2 Sprint 8 — Google Calendar OAuth (desktop) — DONE ✅ (merged 2026-06-14, QA verified 2026-06-15)**
  - Backend: loopback + PKCE OAuth, keyring token storage, refresh/revoke, list calendars
  - Frontend: Settings → "Kết nối Google Calendar", hook poll status, mở system browser qua plugin-shell
  - 239 backend tests pass, ruff/mypy clean, pnpm lint+typecheck clean
  - PR #43 (core) + #44 (sidecar zombie fix) + #45 (keyring bundling + v1.0.2) + #46/#47 (CI fixes) + #48 (auto-migrate + file logging)
  - **QA thật (2026-06-15):** kết nối Google Cloud project thật → "Đã kết nối: dragonball1997vntq@gmail.com" → `GET /calendars` trả đúng 4 lịch khớp Google Calendar thật
  - **Bug + fix:** lần đầu connect lỗi "Không hoàn tất kết nối" — DB local thiếu migration 009 (`google_oauth_accounts`) vì app không tự migrate khi khởi động. PR #48 thêm auto-migrate (`app/core/db_migrate.py`) + file logging JSON (`app/core/logging_config.py`, `%APPDATA%\JARVIS\logs\`)
  - Còn lại (optional, không block): test thật refresh-token-expired và disconnect/reconnect (đã có unit test mock)
- **MVP2 Sprint 9 — Calendar read-only (Google → JARVIS) — code hoàn tất 2026-06-15** ✅
  - Backend: migration 010 (`calendar_sync_states`, `calendar_events`), incremental sync (`syncToken` + pagination + 410 full resync + cancelled-event deletion + all-day handling), `sync_calendars` scheduler job (5 phút), `events_today` trong dashboard, tool `list_calendar_events` + `get_today_summary` (gộp lịch)
  - Frontend: hooks `useCalendarEvents.ts` (invalidation matrix), "LỊCH" sidebar section + `CalendarPage.tsx` (agenda theo ngày), `TodayEvents.tsx` trong Dashboard, Settings → chọn calendar đồng bộ + "Đồng bộ ngay"
  - 24 test mới `test_calendar_sync.py` + 4 test bổ sung `test_google_oauth.py` (auto-migrate) — full suite 263 passed, ruff/mypy clean, pnpm lint/typecheck/build clean
  - **Còn lại (optional, không block, cần Google Cloud thật):** verify thủ công tạo/xóa event trên Google → lên/biến mất khỏi Dashboard; invalid `syncToken` → full resync

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
| Idempotency cache: in-memory dict + TTL (không Redis) | Desktop app single-process/single-user — Redis là dependency thừa; lệch khỏi `05_security.md` (viết cho cloud multi-instance), lý do ghi trong docstring `idempotency.py` |
| `_IDEMPOTENT_PATHS` exact-match (không prefix `startswith()`) | Tránh bắt nhầm subroute `POST /v1/memories/search` và `POST /v1/reminders/{id}/ack` — các route này không phải create-and-cache |
| Idempotency cache key gồm method+path+query+body hash | Tránh reuse cùng Idempotency-Key giữa 2 route khác nhau trả về cached response sai |
| Per-(user_id, idempotency_key) `asyncio.Lock`, pop trong `finally` nếu không tạo cache entry | Chặn 2 request đồng thời cùng key tạo duplicate record; tránh `_locks` phình vô hạn với request lỗi (4xx/5xx) |
| GitHub Releases làm nơi host update artifact (`latest.json` + `.msi`) | Free, tích hợp sẵn `tauri-action`, không cần thêm storage/CDN riêng |
| Draft release = staged rollout, `--prerelease` = kill-switch | `releases/latest` chỉ trỏ tới release published+non-prerelease; máy đã update lên bản lỗi không tự downgrade — kill-switch chỉ bảo vệ máy chưa update |
| Authenticode code-signing cert: deferred | App vẫn unsigned ở OS level (SmartScreen warning) — chấp nhận được cho personal use; updater signature key (minisign/ed25519) là loại khác, đã setup |
| Google Calendar OAuth tách biệt hoàn toàn với JWT/refresh app | 2 hệ token khác nhau; `users.google_sub` (đã có) KHÔNG dùng — Sprint 8 chỉ kết nối Calendar, không login-with-Google |
| Callback OAuth desktop = loopback server tạm (RFC 8252), random port (bind `127.0.0.1:0`) | Đúng chuẩn native app; không cần custom URI scheme / plugin deep-link; server sống trong lúc auth rồi đóng + timeout 180s |
| Google token lưu qua `keyring` (Credential Manager), DB chỉ metadata | Token = secret cấp cao nhất (`05_security.md`); không vào DB/log/response. `google_oauth_accounts` chỉ email/scopes/expiry |
| `client_secret` trong `.env` local của sidecar (Google "Desktop app" client) | Google bắt gửi secret khi exchange kể cả desktop; chấp nhận cho app cá nhân single-user — cùng mức `GEMINI_API_KEY` |
| Scope `openid email https://www.googleapis.com/auth/calendar.readonly` | `openid email` để nhận diện account (email từ id_token, không cần userinfo call); `calendar.readonly` đủ Sprint 8-9 — Sprint 10 re-consent xin quyền ghi |
| `_pending: dict[state]` in-memory + PKCE S256 + `state` verify | Single-process sidecar; chống CSRF + code interception; refresh `invalid_grant` → xóa account + raise `google_reauth_required` |
| Service tham chiếu `database.AsyncSessionLocal` (không import trực tiếp) | Callback handler chạy ngoài request context, cần session riêng; import-by-name bị bắt cứng lúc load, không nhận override test |
| Auto-run `alembic upgrade head` trong lifespan (non-test env), fail-fast nếu lỗi | Desktop app không có cách nào chạy migration thủ công sau update; release shipping migration mới sẽ làm DB local lệch schema (vd. thiếu `google_oauth_accounts`) |
| structlog → JSON qua stdlib + `RotatingFileHandler` tại `%APPDATA%\JARVIS\logs\` | PyInstaller `console=False` nuốt stderr — không có sink nào khác để debug lỗi production trên máy user |
| All-day event date key = `event.start_date` trực tiếp (không convert timezone) | `formatInTimeZone` trên `start_at` sẽ lệch ngày với timezone âm UTC; `start.date` của Google đã là ngày local đúng |
| `list_events`/`get_selected_calendars` chỉ query DB local, không gọi Google API | An toàn khi chưa kết nối Google (trả `[]`, không lỗi); chỉ `POST /sync` mới gọi Google |
| Per-user `asyncio.Lock` cho `sync_all_selected` + `is_sync_running` | Tránh 2 lần sync chạy song song (user bấm "Đồng bộ ngay" trong khi scheduler đang chạy) — trả `status="already_running"` thay vì chờ |
| `sync_calendars` scheduler job, interval 5 phút, `max_instances=1, coalesce=True` | Tái dùng pattern reminder scheduler; tự động đồng bộ calendar đã chọn không cần user mở app Settings |
| `selected=false` mặc định cho calendar mới phát hiện | User phải chủ động chọn calendar để sync — tránh sync toàn bộ calendar (kể cả "Ngày lễ") không mong muốn |

---

## Sprint 9 — Code complete 2026-06-15, chờ PR/merge (branch `feat/sprint9-calendar-readonly`)

**Goal:** Calendar read-only — pull events từ Google Calendar đã kết nối (Sprint 8) vào cache
local, hiển thị trong Dashboard + sidebar "LỊCH", AI tool `list_calendar_events` +
`get_today_summary` gộp lịch.

**Backend:**
- Migration `010`: `calendar_sync_states` (per-calendar sync state: `sync_token`, `selected`,
  `horizon_until`, `last_synced_at`...) + `calendar_events` (cache event, unique
  `(user_id, google_calendar_id, google_event_id)`, index theo `start_at`/`start_date`/`calendar`)
- `models/calendar_sync_state.py`, `models/calendar_event.py`
- `repositories/calendar_sync_repo.py`, `repositories/calendar_event_repo.py`
- `services/google_calendar_service.py` mở rộng: `refresh_calendar_list` (upsert calendar list
  vào `calendar_sync_states`), `sync_calendar`/`sync_all_selected` (incremental `syncToken` +
  pagination + `410 Gone` → full resync + xóa event `status=cancelled`), `list_events`,
  `get_selected_calendars`, `set_selected_calendars`, `is_sync_running` (per-user
  `asyncio.Lock`)
- `schemas/google.py`: `CalendarEventOut`, `CalendarSelectionOut`, `CalendarSelectionIn`,
  `SyncResultOut`, `SyncErrorOut`
- `routers/google.py`: `GET /events`, `POST /sync`, `GET /selected`, `PUT /selected`
- `services/scheduler_service.py`: job `sync_calendars` (interval 5 phút, `max_instances=1,
  coalesce=True`) — gọi `sync_all_selected` cho mọi user đã kết nối Google
- Dashboard: `DashboardOut.events_today` (event hôm nay theo timezone user)
- AI tools: `list_calendar_events` (range today/tomorrow/week/custom), `get_today_summary` viết
  lại — gộp todo + reminder + lịch, bỏ tham số `include_completed`
- `tests/test_calendar_sync.py` — 24 test (repo upsert/reconcile/selection, service sync +
  error handling, tool executors); + 4 test bổ sung trong `test_google_oauth.py`

**Frontend:**
- `lib/types/api.ts` + `lib/api.ts`: `CalendarEventOut`, `CalendarSelectionOut`, `SyncResultOut`,
  4 method `googleListEvents/googleSyncNow/googleGetSelected/googleSetSelected`,
  `DashboardOut.events_today`
- `hooks/useCalendarEvents.ts` (mới): `useCalendarEvents`, `useSyncCalendar`,
  `useCalendarSelection`, `useSetCalendarSelection` — invalidation matrix đầy đủ
  (`google-calendar/events`, `google-calendar/selected`, `dashboard`)
- `hooks/useGoogleCalendar.ts`: export `openInBrowser`; connect/disconnect invalidate thêm
  `selected`/`events`/`dashboard`
- Sidebar: section mới "LỊCH" (`CalendarDays` icon) → `components/calendar/CalendarPage.tsx`
  (agenda nhóm theo ngày, "Hôm nay"/"Ngày mai", "Đồng bộ ngay")
- `components/dashboard/TodayEvents.tsx` mount trong `DashboardPage.tsx`
- `components/settings/GoogleCalendarSettings.tsx`: checkbox chọn calendar đồng bộ + nút
  "Đồng bộ ngay"

**Verify:** full backend suite 263 passed (10 deselected, ruff/mypy clean); `pnpm
lint`/`typecheck`/`build` clean.

**Còn lại (optional, không block, cần Google Cloud thật):** tạo/xóa event trên Google → vài
phút sau lên/biến mất khỏi Dashboard (chờ scheduler hoặc "Đồng bộ ngay"); làm invalid
`syncToken` → full resync chạy đúng; recurring + all-day hiển thị đúng.

---

## Sprint 8 — DONE ✅ (merged 2026-06-14, QA verified 2026-06-15)

**Goal:** MVP2 Calendar branch kickoff — kết nối Google Calendar (read-only) qua OAuth desktop.

**Backend** (PR #43 `feat/sprint8-google-calendar-oauth`):
- `models/google_account.py` `GoogleOAuthAccount` + migration `009` (metadata, NO token, unique user_id)
- `core/token_store.py` — keyring helper (save/get/delete, `asyncio.to_thread`)
- `services/google_oauth_service.py` — `start_connect` (PKCE + loopback random port), `process_callback` (verify state → exchange → store), `get_status`, `disconnect` (revoke), `get_valid_access_token` (auto-refresh + `invalid_grant` re-auth)
- `services/google_calendar_service.py` — `list_calendars`
- `repositories/google_repo.py`, `schemas/google.py`, `routers/google.py` (`/v1/google/calendar/connect|status|disconnect|calendars`)
- `config.py`: `google_oauth_scopes`, `google_oauth_callback_timeout_seconds`; dep `keyring>=25`
- `tests/test_google_oauth.py` — 15 tests (mock httpx + keyring, real SQLite)

**Review fixes (PR #43):**
- P2a — `get_status` kiểm tra cả token store; nếu DB có metadata nhưng keyring mất/corrupt → tự xóa DB row + báo `connected=false` (self-heal, tránh UI báo "Đã kết nối" nhưng calendars 404).
- P2b — calendar API trả 401 (token bị revoke trước hạn) → `force_refresh_access_token` + retry 1 lần; vẫn 401 → `clear_local_connection` + `google_reauth_required`.
- P3 — `_html_page` dùng `html.escape()` cho title/message (callback page reflect `error` query param).

**Frontend:**
- `@tauri-apps/plugin-shell` + `shell:allow-open` capability — mở system browser
- `lib/api.ts` + `types/api.ts` — 4 method/3 type Google
- `hooks/useGoogleCalendar.ts` — status query + connect (mở browser + poll 2s) + disconnect
- `components/settings/GoogleCalendarSettings.tsx` mount trong `SettingsPage.tsx`

**QA thật (2026-06-15):** Google Cloud project thật → kết nối thành công ("Đã kết nối: dragonball1997vntq@gmail.com") → `list_calendars` trả đúng 4 lịch khớp Google Calendar thật.

**Bug + fix (PR #44/#45/#46/#47/#48):** sidecar zombie process khi đóng app (#44); bundle `keyring` trong sidecar + bump v1.0.2 (#45); CI fixes (#46/#47); auto-migrate `alembic upgrade head` ở lifespan + file logging JSON tại `%APPDATA%\JARVIS\logs\` (#48) — fix lỗi "Không hoàn tất kết nối" do DB local thiếu migration 009.

**Còn lại (optional, không block):** refresh-token-expired và disconnect/reconnect chỉ verify bằng unit test mock, chưa test thật trên Google account.

---

## Sprint 7 — DONE ✅ (merged 2026-06-13)

**Goal:** MVP2 kickoff — infra trước feature: auto-update + dọn tech debt Idempotency-Key.

**PR #39** `feat/sprint7-idempotency-key` → merged `e691b07`
- `IdempotencyMiddleware` (`backend/app/middleware/idempotency.py`) cho `POST /v1/todos|notes|memories|reminders` (exact path)
- In-memory `_cache` (TTL `idempotency_key_ttl_seconds`, default 86400s) + `_locks` per `(user_id, idempotency_key)`
- Cache key = sha256(method+path+query+body); cùng key+body khác → `409 idempotency_conflict`; cùng key+body giống → trả cached response
- Round 1 review fix: scope hash theo route (chống cross-route leak) + lock chống concurrent duplicate
- Round 2 review fix: exact-path match (không bắt `/memories/search`, `/reminders/{id}/ack`) + lock cleanup khi request không tạo cache entry
- `backend/tests/test_idempotency.py` — 7 tests

**PR #40** `feat/sprint7-auto-update-infra` → merged `f58819e`
- `tauri-plugin-updater` + `tauri-plugin-process`: check + download + install + relaunch
- `tauri.conf.json`: `bundle.createUpdaterArtifacts: true` + `plugins.updater` (pubkey + endpoint `releases/latest/download/latest.json`)
- `hooks/useUpdateAvailable.ts` (check mount + 6h) + `components/updater/UpdatePrompt.tsx`, mounted trong `layout.tsx`
- `.github/workflows/release.yml` — trigger tag `v*.*.*`, `tauri-apps/tauri-action@v0`, draft release (staged rollout)
- Updater signing keypair generated — private key/password ở GitHub Actions secrets (`TAURI_SIGNING_PRIVATE_KEY`, `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`)

**Merge conflict resolution:** cả 2 PR sửa cùng block Sprint 7 trong `docs/07_MVP2_MVP3_Plan.md`. Merge PR #39 trước → merge `main` vào branch PR #40 → resolve conflict (giữ tất cả mục `[x]` của cả 2 PR + mục QA `[ ]` toast verify) → merge PR #40.

**Còn lại (QA thủ công, user tự thực hiện sau khi build version mới):**
- [ ] Verify toast reminder hiển thị đúng trong WebView (item Phase 4 chưa verify)
- [ ] Bump `version` trong `tauri.conf.json` → tag `vX.Y.Z` → push tag → CI tạo draft release → cài thử trên máy test → publish → verify app nhận update
- [ ] Test kill-switch (`gh release edit <tag> --prerelease`)

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
| Uninstall không xóa `HKCU\Software\jarvis\JARVIS` | WiX/MSI lưu `InstallDir` ở key này và tái dùng khi cài lại — gỡ uninstall entry "sạch" chưa đủ để có clean-install thật; phải xóa thêm registry key này trước khi test cài lại từ đầu |
| `tauri-plugin-notification` gọi song song với in-app toast (không thay thế) | OS notification hiện kể cả khi window minimize; giữ toast để có nút dismiss/ack trong app — đơn giản hơn track `isFocused()` để chọn 1 trong 2 |

---

## Phase 4 — DONE ✅ (merged trong PR #34, 2026-06-07)

Xem chi tiết trong [`docs/migration-desktop-app.md`](../migration-desktop-app.md#phase-4--notification--build-installer).

Đã hoàn thành:
1. ✅ Migration 008: `ALTER TYPE reminder_status ADD VALUE 'due'` + drop `push_subscriptions`
2. ✅ Backend: `GET /v1/reminders/due` + `POST /v1/reminders/{id}/ack` routes, scheduler set `due` thay vì gọi push
3. ✅ Xóa: `push_service.py`, `push_subscription_repo.py`, `notifications.py`, `push_subscriptions` table
4. ✅ Frontend: `useReminderPolling` hook poll 60s + toast (infinite duration, ack khi user dismiss) + ack; xóa `usePushNotification.ts`, `sw.js`

5. ✅ Build final `.msi` (2026-06-07, `JARVIS_1.0.0_x64_en-US.msi` ~110MB, chứa Phase 4 code) — bản cũ Jun 6 00:24 thiếu reminders overhaul, đã bị ghi đè
6. ✅ Test cài đặt thực tế trên máy sạch (2026-06-07) — PASS cả 3 điểm: `%APPDATA%\JARVIS\.env` resolution, sidecar startup (~20-25s cold start), backend `/due` + `/ack` endpoints hoạt động đúng
   - Lưu ý: chỉ xác nhận backend endpoints; chưa xác nhận trực quan toast hiển thị trong WebView (toast dùng `duration: Infinity`, ack khi user dismiss thủ công — không phải auto-close 30s)
   - Lưu ý: uninstall không xóa `HKCU\Software\jarvis\JARVIS` (WiX nhớ `InstallDir`) — phải xóa key này thủ công để có clean-install thật; lần test đầu (chưa xóa key) không tính

**→ Phase 4 hoàn tất 100%. Tauri Desktop Migration (Phase 1-4) DONE.**

---

## Post-MVP 1 Backlog

| Feature | Lý do defer |
|---|---|
| Google OAuth (login) | Scope reduction Sprint 1; Sprint 8 chỉ làm kết nối Calendar, login-with-Google vẫn defer |
| Per-device push subscription | 1 sub/user đủ MVP1 |
| Beta deploy (Railway + Vercel) | Bỏ — đã chuyển sang desktop app |
| Authenticode code-signing cert | Sprint 7: deferred — app unsigned ở OS level, chấp nhận được cho personal use |
