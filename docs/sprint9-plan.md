# Sprint 9 — Calendar Read-Only (Google → JARVIS)

> **Trạng thái:** PLAN v8 (đã sửa qua 7 vòng review, chờ duyệt) · **Ngày:** 2026-06-15
> **Branch dự kiến:** `feat/sprint9-calendar-readonly` từ `main`
> Tiếp nối Sprint 8 (OAuth kết nối Calendar — DONE). Sprint 10 (2-way sync) phụ thuộc sprint này.

> **Revision v2 — review vòng 1 (P1×4, P2×2 + 2 open question):** all-day query/index, default-selected
> = chỉ primary, dọn cache khi disconnect, transaction boundary per-calendar, prompt path thật
> `app/llm/prompt.py`, dashboard giữ `dict` backend, horizon `timeMax`, bỏ chọn calendar → xóa cache. **[v2]**
>
> **Revision v3 — review vòng 2 (P1×2, P2×3), đối chiếu Google Calendar API docs:** **[v3]**
> (1) `syncToken` không đi cùng `timeMin/timeMax` → thêm `horizon_until`/`last_full_synced_at` +
> rule rolling full-refresh khi `horizon_until < now+330d`; (2) all-day `end.date` **exclusive** →
> query half-open; (3) sửa tên tool đúng trong prompt (`search_notes`/`list_reminders`...);
> (4) `calendarList.list` paginate `nextPageToken`; (5) 410 → fetch-before-delete (không mất cache nếu fetch fail).
>
> **Revision v4 — review vòng 3 (P1×1, P2×2):** **[v4]** (1) `list_in_range`/`list_events`/`list_today`
> nhận **`user_tz`** để tính range date all-day theo ngày local (tránh lệch ngày ở timezone boundary);
> (2) sửa dòng checklist 410 cũ còn ghi "wipe cache trước" → thống nhất fetch-before-delete;
> (3) `list_today` dùng half-open `[start_of_day, start_of_next_day)` thay vì "cuối ngày 23:59:59.999".
>
> **Revision v5 — review vòng 4 (P1×1, P2×1, P3×1):** **[v5]** (1) all-day overlap so bằng **local-midnight
> datetime** (`event_start_local < time_max AND event_end_local > time_min`) — bỏ truncate `time_max`→date
> (lỗi "ceil" loại nhầm all-day ngày cuối range); (2) **reconciliation** calendar biến mất khỏi
> `calendarList` (showHidden=true) → dọn sync_state + cache; (3) FE **invalidation matrix** cho
> sync/selection/disconnect/connect (disconnect Sprint 8 hiện chỉ invalidate `status`).
>
> **Self-review (v5-self):** **[v5-self]** (1) **lock `asyncio.Lock` per user** serialize `/sync` thủ công
> vs scheduler (tránh 2 full-sync đè nhau hỏng data); (2) `primary`→**`is_primary`** (tránh keyword Postgres);
> (3) scheduler cần **`google_repo.list_all()`** (hiện chỉ `get_by_user`); (4) ghi chú index all-day; (5)
> đồng bộ wording checklist all-day với cách v5.
>
> **Revision v6 — review vòng 5 (P1×1, P2×2):** **[v6]** (1) CalendarList reconciliation cũng
> **fetch-before-delete** (lỗi pagination → không xóa nhầm); (2) query all-day **portable** (bỏ hardcode
> `AT TIME ZONE` Postgres → candidate query + Python-refine để **test SQLite chạy được**); (3) thêm test
> **sync concurrency** (lock per user).
>
> **Revision v7 — review vòng 6 (P1×1, P2×1):** **[v7]** (1) candidate query dùng **overlap thô**
> (`start_at < time_max AND coalesce(end_at,start_at) > time_min`; all-day tương tự theo local range date)
> thay cửa sổ `±1d` cố định → **không miss event dài ngày** bắt đầu trước range; (2) `SyncResultOut` thêm
> `status: "synced"|"already_running"` (+ upserted/deleted/synced_at) để FE đọc trạng thái lock, không parse message.
>
> **Revision v8 — review vòng 7 (P2×1, P3×1):** **[v8]** (1) `SyncResultOut` thêm `status="partial"` +
> `failed`/`errors[]` (khớp `sync_all_selected` nuốt lỗi per-calendar → FE biết sync xong một phần);
> (2) candidate query all-day **bỏ date arithmetic SQL** (`start_date + 1 day`) → dùng
> `coalesce(end_date, start_date)` coarse + tính `end = start_date+1` ở Python refine (portable SQLite/Postgres).

## Mục tiêu & scope đã chốt

Đồng bộ **một chiều** Google Calendar → cache local JARVIS, hiển thị trong app và cho chat truy vấn.
Tách read-only trước 2-way (Sprint 10) để xác nhận sync + auth ổn trước khi cho ghi ngược.

**Quyết định chốt (2026-06-15):**
1. **UI:** Dashboard block "Lịch hôm nay" + section **LỊCH** mới (sidebar) dạng **agenda**
   (danh sách theo ngày, ~14 ngày tới). KHÔNG làm month-grid.
2. **Multi-calendar:** user chọn calendar nào để sync (Settings). **[v2]** Mặc định **chỉ primary**
   được `selected=true`; calendar khác `selected=false` cho tới khi user tick. Bỏ chọn calendar →
   **xóa cache events của calendar đó ngay** (xem A2/A3).
3. **Chat tool:** thêm `list_calendar_events` **và** tạo mới `get_today_summary` (gộp todo +
   reminder + lịch) — đúng như CLAUDE.md mô tả (hiện tool này thiếu trong code thật).

---

## A. Backend

### A1. DB models + migration `010`

**`backend/app/models/calendar_sync_state.py`** — `CalendarSyncState` (per calendar được chọn sync):

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK→users CASCADE | |
| `google_calendar_id` | String(255) | id calendar bên Google |
| `calendar_summary` | String(255) | tên hiển thị (snapshot) |
| `is_primary` | Boolean, default false | **[v2/v5-self]** calendar chính của user (`is_primary` — tránh keyword `primary` của Postgres) |
| `time_zone` | String(64), nullable | **[v2]** tz của calendar (từ calendarList) |
| `access_role` | String(20), nullable | **[v2]** owner/reader/... (chuẩn bị Sprint 10 ghi ngược) |
| `sync_token` | String, nullable | `nextSyncToken`; null = cần full sync |
| `selected` | Boolean, default false | **[v2]** mặc định false; chỉ primary set true khi tạo mới |
| `horizon_until` | TIMESTAMPTZ, nullable | **[v3]** mốc `timeMax` của lần full sync gần nhất |
| `last_full_synced_at` | TIMESTAMPTZ, nullable | **[v3]** lần full sync gần nhất (để biết khi nào cần refresh window) |
| `last_synced_at` | TIMESTAMPTZ, nullable | lần sync bất kỳ (full/incremental) gần nhất |
| `created_at`/`updated_at` | TIMESTAMPTZ | |

- **Unique** `(user_id, google_calendar_id)`.
- **[v2] Rule selection:** `upsert_from_calendar_list` — calendar **mới** chỉ `selected=true` nếu
  `is_primary=true`; calendar **đã tồn tại giữ nguyên** `selected` + `sync_token` (chỉ cập nhật
  summary/time_zone/access_role/is_primary).
- **[v5] Reconciliation (P2):** calendar có `sync_state` cũ nhưng **không còn trong Google list**
  (mất quyền / bị xóa / unshared) → **xóa `sync_state` + `delete_all_for_calendar`** cache của nó.
  Nếu không, state cũ vẫn `selected`, cache stale vẫn hiện, scheduler sync lỗi lặp vô hạn.
  Để tránh "rớt nhầm" calendar bị **ẩn** (hidden nhưng vẫn còn quyền), fetch `calendarList.list` với
  **`showHidden=true`** → chỉ những calendar thực sự biến mất mới bị dọn.
- **[v6] Reconciliation cũng fetch-before-delete (P1):** **chỉ reconcile sau khi fetch HẾT các trang
  `calendarList.list` thành công.** Nếu pagination lỗi giữa chừng, danh sách trả về **thiếu** không
  có nghĩa calendar biến mất → **KHÔNG reconcile/xóa** lần đó (giữ nguyên state/cache, thử lại lần sau).
  Cùng nguyên tắc với events 410.

**`backend/app/models/calendar_event.py`** — `CalendarEvent` (cache local **trong horizon
`[now-30d, now+365d]`**, **không soft-delete** — mirror remote trong horizon, cancelled → hard delete):

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK→users CASCADE | |
| `google_calendar_id` | String(255) | |
| `google_event_id` | String(255) | |
| `ical_uid` | String(255), nullable | cho Sprint 10 mapping |
| `summary` | String(500) | có thể rỗng ("(không tiêu đề)") |
| `description` | Text, nullable | |
| `location` | String(500), nullable | |
| `is_all_day` | Boolean | |
| `start_at`/`end_at` | TIMESTAMPTZ, nullable | event có giờ (UTC) |
| `start_date`/`end_date` | Date, nullable | event cả ngày |
| `event_timezone` | String(64), nullable | từ `start.timeZone` |
| `status` | String(20) | confirmed/tentative |
| `html_link` | String, nullable | link mở trên Google |
| `etag` | String, nullable | cho Sprint 10 conflict |
| `google_updated_at` | TIMESTAMPTZ, nullable | `event.updated` |
| `created_at`/`updated_at` | TIMESTAMPTZ | |

- **Unique** `(user_id, google_calendar_id, google_event_id)`.
- **Index** `(user_id, start_at)` cho event có giờ; **[v2]** `(user_id, start_date)` cho all-day;
  `(user_id, google_calendar_id)` cho full-resync delete.
- **[v2] Sort key thống nhất:** khi list, sort theo `effective_start = coalesce(start_at,
  start_date@00:00 theo tz user)` để all-day và timed xen kẽ đúng thứ tự.
- **[v5-self/v6] Index all-day:** với cách v6 (candidate query theo `start_date` trong range thô rồi
  refine bằng Python), index `(user_id, start_date)` **được dùng** cho bước lấy candidate; phần tinh
  chỉnh tz chạy trên tập nhỏ. Volume nhỏ (horizon ~1 năm, single-user) nên đủ nhanh.

**`backend/migrations/versions/010_sprint9_calendar_events.py`** — `down_revision = "009_sprint8_google_oauth"`,
đủ `upgrade()` + `downgrade()` (drop 2 bảng). Thêm import 2 model vào `app/models/__init__.py`
+ relationship optional vào `User` (không bắt buộc — query qua user_id).

### A2. Repositories
- **`calendar_sync_repo.py`**: `list_for_user`, `list_selected`, `get`, `upsert_from_calendar_list`
  (theo rule selection ở A1), `set_selected(user_id, ids)`, `update_sync_state(token, last_synced_at)`,
  `clear_sync_token` (cho 410), **[v2]** `delete_all_for_user` (disconnect).
- **`calendar_event_repo.py`**: `upsert(event)`, `delete_by_google_id`, `delete_all_for_calendar`
  (full resync **và** khi user bỏ chọn calendar), **[v2]** `delete_all_for_user` (disconnect),
  **[v4]** `list_in_range(user_id, time_min, time_max, user_tz)`, `list_today(user_id, user_tz)`.
  - **[v2/v3/v5] Query overlap (half-open, P1):** `list_in_range`/`list_today` phải lọc **OR 2 nhánh**,
    so cùng **không gian local datetime**:
    - timed: `start_at < time_max AND coalesce(end_at, start_at) > time_min`
    - all-day (**`end.date` exclusive**): coi event span = `[start_date 00:00 local, end_date 00:00 local)`
      (nếu thiếu `end_date` → `start_date + 1 day`). Overlap với range `[time_min, time_max)`:
      **`event_start_local < time_max AND event_end_local > time_min`**.
    rồi sort theo `effective_start`. Chỉ lọc `start_at` sẽ làm **mất all-day** khỏi agenda/dashboard/chat.
  - **[v6/v7] Portable, KHÔNG hardcode SQL Postgres (P2):** biểu thức `AT TIME ZONE` là Postgres-only,
    trong khi **test chạy SQLite in-memory** (`06_testing.md`). → Candidate query dùng **overlap thô**
    (portable cả 2 DB, **không** cửa sổ `±1d` cố định — sẽ miss event dài ngày, **P1 v7**):
    - timed: `start_at < time_max AND coalesce(end_at, start_at) > time_min` (so UTC timestamp trực tiếp)
    - all-day (**[v8] tránh date arithmetic không portable** — bỏ `start_date + 1 day` trong SQL):
      `start_date <= local_range_end_date AND coalesce(end_date, start_date) >= local_range_start_date`
      (coarse, dùng `<=`/`>=` cho rộng — superset an toàn). `local_range_start_date`/`local_range_end_date`
      **tính sẵn ở Python** (`date(time_min/​time_max in user_tz)` ± 1 ngày biên) rồi truyền vào như tham số
      → không `AT TIME ZONE`, không `+ interval` (Postgres) / `date(...,'+1 day')` (SQLite) trong SQL.
    Sau đó **Python refine** mới tính chính xác `end = end_date or (start_date + 1 day)` + half-open + tz
    (`zoneinfo`) + sort `effective_start` trên tập nhỏ.
    (Tiền lệ dialect branching: `memory_repo.semantic_search` trả `[]` trên SQLite vì `<=>` không tồn tại.)
    Nếu sau cần tối ưu, thêm nhánh `AT TIME ZONE` riêng cho Postgres; mặc định sprint này Python-refine cho gọn + test được.
  - **[v5] KHÔNG truncate `time_max` thành date (P1):** nếu lấy `range_end_date = date(time_max_local)`,
    all-day event ở **ngày cuối** sẽ bị loại nhầm khi `time_max` không đúng 00:00 (vd range tới 15:00
    ngày D14 → mất all-day ngày D14). So bằng local-midnight datetime như trên tránh hẳn lỗi "ceil" này.
  - **[v4] `user_tz` bắt buộc (P1):** mọi mốc local đều tính theo `user_tz` (không có → range UTC gần
    nửa đêm lệch ngày local → all-day sai/mất ở timezone boundary). Endpoint/tool lấy `user_tz` từ
    `current_user.timezone`.
  - **[v2/v4] `list_today(user_id, user_tz)`:** chuẩn hóa **half-open** `[start_of_day_local,
    start_of_next_day_local)` (KHÔNG dùng "cuối ngày 23:59:59.999" — tránh precision edge case),
    convert 2 mốc sang UTC cho nhánh timed, và so all-day theo date local.

### A3. Sync logic — mở rộng `services/google_calendar_service.py`

Refactor: tách helper `_authed_request(db, user_id, method, url, **kw)` gói logic
401→force_refresh→retry→clear (hiện đang lặp trong `list_calendars`), dùng chung cho list + events.

- **`sync_calendar(db, user_id, sync_state) -> dict`** (counts upserted/deleted):
  - **Params chung** (phải **nhất quán** giữa full & incremental để token hợp lệ): `singleEvents=true`
    (expand recurring), `showDeleted=true`, `maxResults=250`. KHÔNG set `orderBy`/`q`/`timeMin`/`timeMax`
    khi đi cùng `syncToken`.
  - **[v3] Chọn full vs incremental:**
    - **Full sync** khi: `sync_token` null, **hoặc** `horizon_until` null, **hoặc**
      `horizon_until < now + 330 ngày` (rolling — window sắp hết, cần mở rộng). Full sync gửi
      `timeMin = now - 30d` + `timeMax = now + 365d` (**KHÔNG** gửi `syncToken` — Google trả 400 nếu
      kèm timeMin/timeMax). Sau khi apply thành công: set `horizon_until = now+365d`,
      `last_full_synced_at = now`, lưu `nextSyncToken`.
    - **Incremental** ngược lại: gửi **chỉ `syncToken`** (+ params chung). Cập nhật `nextSyncToken`.
    - *(Lý do: `syncToken` chỉ track thay đổi trong window của lần full gần nhất; không tự "trôi"
      sang tương lai xa hơn → cần full refresh định kỳ để đẩy `horizon_until` về phía trước.)*
  - **Pagination:** lặp `nextPageToken` đến hết; `nextSyncToken` chỉ ở **trang cuối** → lưu.
  - **[v2/v3] Transaction boundary + fetch-before-delete (P1/P2):** **fetch hết các trang trước
    (chỉ HTTP, KHÔNG ghi DB)**, gom vào memory. **Chỉ khi fetch toàn bộ thành công** mới mở
    **một transaction của riêng calendar này** để apply: (full sync → `delete_all_for_calendar`
    rồi upsert toàn bộ; incremental → upsert/delete theo delta) + lưu `sync_token`/`horizon_until`/
    `last_*` → `commit`. Fetch lỗi giữa chừng → **không đụng cache** (giữ nguyên dữ liệu cũ còn
    hữu dụng), không lưu token. Tách fetch/ghi cũng tránh `_authed_request` (gọi
    `clear_local_connection` có `commit`) **commit nhầm partial** nếu token chết giữa lúc phân trang.
  - **[v3] 410 Gone** (syncToken hết hạn) → **không xóa cache ngay**; chuyển sang **full sync**
    (fetch full pages trước) → nếu fetch OK thì trong transaction mới `delete_all_for_calendar` +
    upsert + lưu token mới. Nếu full sync cũng fail → cache cũ vẫn còn (chấp nhận stale tạm thời,
    sync lần sau).
  - Mỗi event: `status == "cancelled"` → `delete_by_google_id`; ngược lại parse + `upsert`.
  - **Parse:** all-day = có `start.date` (→ `is_all_day=true`, `start_date`/`end_date` — **`end.date`
    là exclusive**, xem A2); có giờ = `start.dateTime` (→ `start_at`/`end_at` UTC,
    `event_timezone = start.timeZone`).
- **`sync_all_selected(db, user_id) -> dict`**: refresh danh sách calendar (`upsert_from_calendar_list`) →
  loop `list_selected` → `sync_calendar` từng cái, **[v2] mỗi calendar 1 transaction riêng**
  (đã commit/rollback bên trong). Nuốt lỗi per-calendar (1 calendar fail không chặn cái khác), log rõ.
  **[v8]** Trả về tổng hợp `{upserted, deleted, failed, errors: [{calendar_id, message}]}` để endpoint
  `/sync` map sang `SyncResultOut.status` (`synced`/`partial`).
- **[v5-self] Serialize sync (concurrency, P1):** `POST /sync` thủ công và job scheduler có thể chạy
  **đè nhau trên cùng calendar** (full sync `delete_all_for_calendar` + upsert đua với lần sync khác)
  → hỏng dữ liệu. Dùng **`asyncio.Lock` per `user_id`** (dict in-memory, single-process desktop) bọc
  `sync_all_selected`; nếu đang sync, lần gọi thứ 2 chờ hoặc bỏ qua (scheduler `coalesce=True` đã giảm,
  nhưng manual + scheduled vẫn cần lock). **[v7]** Endpoint `/sync` nếu lock đang giữ → trả ngay
  `SyncResultOut(status="already_running")` (không chờ) để FE hiển thị "đang đồng bộ".
- **[v3/v5/v6] CalendarList pagination + reconciliation (P1/P2):** `upsert_from_calendar_list` lặp
  `nextPageToken` của `calendarList.list` (`showHidden=true`) **đến hết và thành công** → mới upsert
  calendar còn tồn tại + **dọn calendar đã biến mất** (xem A1). **[v6]** Nếu pagination lỗi giữa chừng
  → **không reconcile** (tránh xóa nhầm khi list trả thiếu do lỗi mạng). Không paginate → Settings thiếu
  calendar; không reconcile → cache/state stale + scheduler lỗi lặp.
- **[v4] `list_events(db, user_id, time_min, time_max, user_tz)`**: query cache (overlap OR ở A2,
  all-day theo `user_tz`), trả đã sort. Endpoint truyền `user_tz` từ `current_user.timezone`.
- **`set_selected_calendars(user_id, ids)` / `get_selected_calendars`**: **[v2]** khi một calendar
  chuyển từ selected→unselected, `delete_all_for_calendar` cache của nó + `clear_sync_token` (để lần
  sau chọn lại sync full); calendar không chọn thì không query, không sync.
- **[v2] Mở rộng `google_oauth_service.disconnect` (P1):** sau khi revoke + xóa token + xóa account
  metadata, gọi thêm `calendar_event_repo.delete_all_for_user` + `calendar_sync_repo.delete_all_for_user`
  trong **cùng transaction disconnect** — nếu không, UI/chat vẫn thấy lịch cũ sau khi ngắt kết nối.
  (2 bảng FK về `users` chứ không FK về `google_oauth_accounts` nên không tự cascade khi xóa account row.)

### A4. Scheduler — thêm job vào `services/scheduler_service.py`
- Job `sync_calendars` **interval 5 phút**, `max_instances=1, coalesce=True`.
- Job: lặp các account (**[v5-self]** cần `google_repo.list_all()` — hiện chỉ có `get_by_user`) →
  `sync_all_selected` (đã có lock per user). Bọc try/except, log; không crash scheduler.
- **Constraint:** chỉ chạy khi app mở (sidecar sống) — ghi rõ vào docs (giống nudge Sprint 11).

### A5. Endpoints — mở rộng `routers/google.py` (prefix `/v1/google/calendar`)

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/events?time_min&time_max` | List events từ cache (mặc định: now → +14 ngày) |
| `POST` | `/sync` | Trigger sync ngay, trả counts hoặc trạng thái `already_running` |
| `GET` | `/selected` | Danh sách calendar + cờ `selected` |
| `PUT` | `/selected` | Body `{calendar_ids: [...]}` — đặt calendar nào sync |

Schemas mới trong `schemas/google.py`: `CalendarEventOut`, `CalendarSelectionOut`,
`CalendarSelectionIn`, `SyncResultOut`.
- **[v7/v8] `SyncResultOut` (P2):** field `status: Literal["synced", "partial", "already_running"]`
  (FE đọc trực tiếp, không parse message) + `upserted: int`, `deleted: int`, `synced_at: datetime | None`
  (None khi `already_running`), **[v8]** `failed: int` + `errors: list[{calendar_id, message}]`. Endpoint `/sync`:
  - lock per-user đang giữ → `status="already_running"` (HTTP 200, không 409 — trạng thái bình thường).
  - **[v8]** ≥1 calendar fail nhưng ≥1 thành công → `status="partial"` + `errors` liệt kê calendar lỗi
    (khớp với `sync_all_selected` nuốt lỗi per-calendar ở A3 — FE biết sync chỉ xong một phần).
  - tất cả OK → `status="synced"`.

### A6. Chat tools — `tools/definitions.py` + `tools/executors.py`
- **`list_calendar_events`**: params `range` enum `["today","tomorrow","week","custom"]` +
  `time_min`/`time_max` (ISO, optional). Executor query cache (cần `user_tz` → thêm vào `_needs_tz`).
  Trả events kèm summary tiếng Việt.
- **`get_today_summary`** (tạo mới): gộp `dashboard_service` (todos hôm nay + reminders sắp tới) +
  events hôm nay. Thêm vào `definitions.py`, `executors.py`, `_EXECUTOR_MAP`, `_needs_tz`.
  → đưa tool count thật về đúng 12 (CLAUDE.md ghi 11, sẽ cập nhật).
- **[v2] Cập nhật system prompt (P2):** sửa **`backend/app/llm/prompt.py`** (KHÔNG phải
  `prompts/system.j2` — file đó không tồn tại). Trong `_PART_C`, mục `=== AVAILABLE TOOLS ===`
  hiện **ghi "(Sprint 4)" và thiếu cả reminder tools** — cập nhật cho đủ **đúng tên thật** (P2):
  `create_todo, list_todos, update_todo, create_note, search_notes, save_memory, search_memory,
  forget_memory, create_reminder, list_reminders, list_calendar_events, get_today_summary`.
  Bump `PROMPT_VERSION` `"1.0.0-sprint4"` → **`"1.1.0-sprint9"`**.
  → **chạy lại eval set 10 case** (rule bắt buộc khi đổi prompt/tool).

### A7. Dashboard — `services/dashboard_service.py`
- Thêm `events_today` (từ `calendar_event_repo.list_today`) vào payload.
- **[v2] Schema (P2):** router `dashboard.py` hiện trả `dict[str, Any]` (không có Pydantic backend);
  `DashboardOut` chỉ tồn tại ở **frontend** `lib/types/api.ts`. → Sprint 9 **giữ nguyên `dict` ở backend**
  (đúng pattern hiện tại), chỉ **thêm field `events_today` vào type `DashboardOut` bên FE**. (Không tạo
  Pydantic schema backend trong sprint này để tránh nở scope; có thể làm sau nếu cần typed contract.)

---

## B. Frontend

### B1. Types + API client
- `lib/types/api.ts`: `CalendarEventOut`, `CalendarSelectionOut`, `SyncResultOut`; mở rộng
  `DashboardOut` thêm `events_today`.
- `lib/api.ts`: `googleListEvents(timeMin?, timeMax?)`, `googleSyncNow()`, `googleGetSelected()`,
  `googleSetSelected(ids)`.

### B2. Hooks
- `hooks/useCalendarEvents.ts`: `useCalendarEvents(range)` (query, refetch 5 phút),
  `useSyncCalendar()` (mutation → invalidate), `useCalendarSelection()` + `useSetCalendarSelection()`.
- **[v5] Invalidation matrix (P3)** — sau mỗi mutation phải invalidate đủ query, nếu không UI giữ lịch cũ:
  | Mutation | Invalidate query keys |
  |---|---|
  | `useSyncCalendar` (POST /sync) | `["google-calendar","events"]`, `["dashboard"]` |
  | `useSetCalendarSelection` (PUT /selected) | `["google-calendar","selected"]`, `["google-calendar","events"]`, `["dashboard"]` |
  | **disconnect** (mở rộng hook Sprint 8) | `["google-calendar","status"]`, `["google-calendar","selected"]`, `["google-calendar","events"]`, `["dashboard"]` |
  | **connect** (sau khi poll status = connected) | `["google-calendar","selected"]`, `["google-calendar","events"]`, `["dashboard"]` |
  > Hook disconnect Sprint 8 hiện **chỉ** invalidate `status` — phải bổ sung selected/events/dashboard.

### B3. Section LỊCH (agenda)
- `components/layout/Sidebar.tsx`: thêm `Section` `"calendar"` + icon (CalendarDays), label "LỊCH".
- `app/page.tsx`: mount component theo section (pattern hiện có).
- `components/calendar/CalendarPage.tsx`: agenda — group events theo ngày (date-fns-tz, tz user),
  phân biệt all-day vs có giờ, nút sync thủ công + trạng thái "đồng bộ lúc HH:mm", link mở Google
  (`html_link`). Empty state khi chưa kết nối → CTA tới Settings.

### B4. Dashboard block
- `components/dashboard/TodayEvents.tsx`: list events hôm nay; mount trong `DashboardPage.tsx`
  (cạnh reminders).

### B5. Settings — chọn calendar để sync
- Mở rộng `components/settings/GoogleCalendarSettings.tsx`: khi đã kết nối → list calendar
  (từ `/selected`) với checkbox; lưu qua `PUT /selected`. Nút "Đồng bộ ngay".

---

## C. Edge cases (checklist bắt buộc)
- [ ] Pagination `nextPageToken` đến hết; `nextSyncToken` chỉ trang cuối
- [ ] **[v3]** `410 Gone` → full sync **fetch-before-delete** (xem dòng dưới; KHÔNG xóa cache trước khi fetch OK)
- [ ] `status=="cancelled"` → xóa khỏi cache
- [ ] Recurring → `singleEvents=true`
- [ ] All-day (`start.date`) parse riêng event có giờ **[v2] + query OR (timed overlap | all-day date overlap)** — đừng để all-day mất khỏi agenda/dashboard/chat
- [ ] **[v3/v5]** All-day `end.date` **exclusive** → so local-midnight datetime: `event_end_local > time_min`
- [ ] **[v4/v5]** All-day so theo **`user_tz`** (local-midnight datetime, KHÔNG truncate range thành date) — tránh lệch ngày ở timezone boundary
- [ ] **[v4]** `list_today` dùng half-open `[start_of_day_local, start_of_next_day_local)` (không "23:59:59.999")
- [ ] Timezone: lưu UTC + `event_timezone`, hiển thị theo tz user ở FE
- [ ] First-sync `timeMin = now-30d` **[v2] + `timeMax = now+365d`** (horizon hữu hạn)
- [ ] **[v3]** `syncToken` KHÔNG đi cùng `timeMin/timeMax` (Google 400); incremental gửi chỉ `syncToken` + params nhất quán
- [ ] **[v3]** Rolling horizon: `horizon_until < now+330d` → full refresh để mở rộng window (token không tự trôi)
- [ ] **[v3]** CalendarList pagination: lặp `nextPageToken` của `calendarList.list` (`showHidden=true`) đến hết
- [ ] **[v5]** Reconciliation: calendar biến mất khỏi Google list → xóa sync_state + cache (không sync lỗi lặp)
- [ ] **[v6]** Reconciliation **fetch-before-delete**: CalendarList lỗi giữa pagination → KHÔNG xóa nhầm calendar
- [ ] **[v6]** Query all-day **portable** (không hardcode `AT TIME ZONE`): candidate query + Python-refine để test SQLite chạy được
- [ ] **[v7]** Candidate query dùng **overlap thô** (không cửa sổ `±1d`) → không miss event dài ngày
- [ ] **[v5-self]** Lock per user: `/sync` thủ công + scheduler không sync đè cùng calendar
- [ ] **[v5]** All-day ngày cuối range (time_max=15:00 local) vẫn hiện — không truncate time_max thành date
- [ ] **[v2/v3]** Transaction per-calendar: fetch hết pages (HTTP) → **chỉ khi fetch OK** mới apply+commit; lỗi → giữ nguyên cache cũ, không lưu token
- [ ] **[v3]** 410 → full sync, **fetch trước rồi mới replace cache** (không xóa cache nếu fetch fail)
- [ ] **[v2]** Disconnect → xóa `calendar_events` + `calendar_sync_states` của user (tránh cache stale)
- [ ] **[v2]** Bỏ chọn calendar → xóa cache events + clear sync_token của calendar đó
- [ ] 401 token revoke giữa chừng → reuse `_authed_request` (force refresh / reauth)

---

## D. Tests (`backend/tests/test_calendar_sync.py` + mở rộng)
Mock `httpx` + `keyring`, DB SQLite thật:
- [ ] First sync (no token) → upsert events + lưu `nextSyncToken`
- [ ] Incremental sync với token → chỉ áp delta
- [ ] Pagination 2 trang → token lấy ở trang cuối
- [ ] `410` → full resync; **[v3]** nếu full fetch fail thì cache cũ **không bị xóa**
- [ ] **[v3]** Rolling horizon: `horizon_until` cũ → lần sync sau chuyển full refresh, set `horizon_until` mới
- [ ] **[v3]** CalendarList 2 trang (`nextPageToken`) → lấy đủ calendar
- [ ] **[v5]** Calendar removed from CalendarList → stale sync_state + cache được dọn
- [ ] **[v6]** CalendarList lỗi giữa pagination → KHÔNG reconcile (không xóa nhầm calendar/cache còn hợp lệ)
- [ ] **[v5-self/v7]** Concurrency: lock đang giữ → `/sync` thứ 2 trả `SyncResultOut(status="already_running")` (HTTP 200) — không chạy đè
- [ ] **[v7]** Candidate query trả **event dài ngày** bắt đầu trước range nhưng overlap (timed multi-day + all-day multi-day không bị miss)
- [ ] **[v8]** `/sync` partial: 1 calendar fail + 1 OK → `status="partial"` + `errors` có calendar lỗi
- [ ] **[v8]** Candidate query all-day chạy SQLite (không date arithmetic SQL) — refine end_date ở Python
- [ ] **[v5]** All-day ngày cuối range với `time_max` không phải 00:00 (vd 15:00) → vẫn trả về (không bị "ceil" loại)
- [ ] `cancelled` → xóa khỏi cache
- [ ] All-day vs timed parse đúng
- [ ] **[v2]** `list_in_range` trả **cả all-day lẫn timed** khi overlap range (test all-day không bị mất)
- [ ] **[v3]** All-day boundary: event `end.date` = ngày bắt đầu range → **KHÔNG** xuất hiện (exclusive)
- [ ] **[v4]** Timezone boundary: all-day event với `user_tz` lệch UTC (vd Asia/Ho_Chi_Minh +7) quanh
      nửa đêm → hiện đúng ngày local (test range gần 00:00 local không mất/nhân đôi event)
- [ ] **[v2/v4]** `list_today(user_id, user_tz)` half-open đúng all-day theo ngày local + tz
- [ ] `list_events` lọc đúng range
- [ ] `set_selected` chỉ sync calendar được chọn; **[v2]** bỏ chọn → cache calendar đó bị xóa
- [ ] **[v2]** `upsert_from_calendar_list`: calendar mới non-primary `selected=false`; primary `true`; calendar cũ giữ nguyên selection/sync_token
- [ ] **[v2]** Sync lỗi giữa chừng → rollback, sync_token cũ giữ nguyên (không partial commit)
- [ ] **[v2]** `disconnect` → `calendar_events` + `calendar_sync_states` của user bị xóa sạch
- [ ] Tool `list_calendar_events` + `get_today_summary` happy + error
- [ ] Dashboard có `events_today` (gồm all-day)
- [ ] Mỗi endpoint mới: 1 happy + 1 error path
- [ ] Eval set 10 case ≥ 9/10 (đổi prompt/tool)

---

## E. Docs + memory (sau khi code xong)
- `docs/05_API_Specification.md` / `02` — endpoints calendar mới
- `docs/01_Database_Schema_ERD.md` + `docs/ai-context/04-database-schema.md` — 2 bảng + migration 010
- `docs/03_AI_Tool_Schemas.md` — 2 tool mới (tool count thật 10→12)
- `CLAUDE.md` — sửa "11 tools" → 12, thêm `list_calendar_events` + `get_today_summary`
  (**[v2]** lưu ý: code thật trước sprint này mới có 10 tool — `get_today_summary` chưa từng tồn tại)
- `docs/07_MVP2_MVP3_Plan.md` tick Sprint 9; `docs/ai-context/06` + `02-folder-map`;
  memory `project-sprint-status`

---

## E2. Open questions — đã chốt (v2)
- **Cache = mirror remote toàn bộ tương lai hay theo horizon?** → **Theo horizon** `[now-30d, now+365d]`.
  Sửa từ "mirror remote" thành **"mirror remote trong horizon"** ở mọi chỗ. Đủ cho agenda (~14 ngày)
  + dashboard + chat; tránh recurring vô hạn. Mở rộng horizon = sprint sau nếu cần.
- **Bỏ chọn calendar có xóa cache ngay không?** → **Có.** `set_selected` xóa
  `calendar_events` + clear `sync_token` của calendar bị bỏ chọn ngay (chọn lại = sync full).

---

## F. DoD (Definition of Done)
1. Tạo event trên Google → ≤5 phút (hoặc bấm "Đồng bộ ngay") → lên Dashboard + section LỊCH
2. Xóa event trên Google → biến mất khỏi cache
3. Làm invalid `syncToken` → full resync chạy đúng, dữ liệu khớp lại
4. Recurring + all-day hiển thị đúng; timezone đúng theo tz user
5. Chọn/bỏ chọn calendar trong Settings → sync đúng tập đã chọn
6. Chat "hôm nay có gì" → `get_today_summary` trả cả todo + reminder + lịch
7. `ruff`/`mypy`/`pytest` xanh; `pnpm lint`/`typecheck` xanh; eval ≥9/10

---

## G. Thứ tự thực thi (task breakdown)
1. Models + migration 010 + đăng ký model
2. Repos (sync_state + event)
3. Service: refactor `_authed_request` → `sync_calendar` (+ edge cases) → `sync_all_selected`
   → `list_events` → selection
4. Endpoints + schemas
5. Scheduler job
6. Tools (`list_calendar_events`, `get_today_summary`) + prompt + eval
7. Dashboard backend
8. Tests backend (song song từng phần)
9. FE: types/api/hooks → section LỊCH → Dashboard block → Settings selection
10. Docs + memory

## H. Git
Theo `.claude/rules/07_git.md`: nhánh `feat/sprint9-calendar-readonly` từ `main`. Mặc định **1 PR**
cho cả sprint (tách BE/FE thành 2 PR nếu user muốn). Mọi commit/push/PR/merge hỏi xác nhận user
trước. Không tự merge.
