# TÀI LIỆU 7: KẾ HOẠCH THỰC THI MVP 2 & MVP 3
## J.A.R.V.I.S Personal AI Assistant — Desktop Era

**Phiên bản:** 1.0 (draft)
**Ngày:** 2026-06-13
**Nguồn:** `docs/06_Updated_Execution_Plan.md` §8 (gaps vs "JARVIS phim") + Tauri desktop migration + MVP2 proposal.

---

## 0. BỐI CẢNH — Desktop-local đổi luật chơi

Roadmap MVP2/MVP3 trong `docs/06` §8 được viết khi JARVIS còn là web app deploy cloud
(Railway + Vercel). Sau Tauri desktop migration (Phase 1-4, PR #34), app chạy **local trên
máy người dùng, không có public endpoint**. Các ràng buộc mới chi phối toàn bộ plan dưới đây:

| Ràng buộc | Hệ quả |
|---|---|
| Không có public endpoint | Google Calendar **push webhook bất khả thi** → dùng **polling + `syncToken`** (incremental sync). Tái dùng APScheduler đã có. |
| OAuth trên desktop | Dùng **OAuth Desktop flow** (loopback `http://localhost:PORT` + PKCE); Tauri mở system browser, local server bắt `code`. Không cần redirect cloud. |
| Single-user, DB local | Token Google lưu **OS Credential Manager** (xem Quyết định kiến trúc bên dưới) — **không** lưu raw token trong DB, **không** log token. Đây là rủi ro bảo mật mới lớn nhất MVP2. |
| Login Google (deferred Sprint 1) | Giá trị thấp (app local 1 user đã có email/pass). OAuth ở MVP2 chỉ để **xin scope Calendar**, không phải để login. |
| App chạy local | Computer-use (MVP3 track B) trở nên **khả thi** — đây là "đặc sản" hướng desktop, không làm được khi còn là web-cloud. |

### Quyết định kiến trúc: lưu Google OAuth token (chốt)

> Reviewer chỉ ra "OS keychain / encrypted DB" là 2 kiến trúc khác nhau — chốt cụ thể như sau.

- **Bên gọi Calendar API là sidecar Python**, không phải lớp Tauri (Rust/JS). Nên **không**
  đẩy token qua IPC Tauri → Python; thay vào đó **sidecar Python đọc/ghi token trực tiếp**
  vào **Windows Credential Manager** qua lib `keyring` (cross-platform, dùng đúng credential
  store của OS).
- **DB chỉ lưu metadata/reference**: account email, scopes đã cấp, expiry —
  **không** lưu access/refresh token. Calendar `sync_token` là per-calendar sync state
  (bảng `calendar_sync_states`, xem Sprint 9) — không thuộc OAuth account metadata.
- Không có "encryption key tự quản" → tránh hẳn bài toán key-from-where / rotate.
- **Tuyệt đối không log** access token, refresh token, authorization code (kể cả debug/test).
- Disconnect = xóa entry trong Credential Manager + gọi Google **revoke endpoint** + xóa metadata DB.

---

## 1. MVP 2 — Calendar Sync + Proactive Nudge

Mục tiêu: thu hẹp gap lớn nhất với "JARVIS thật" — biết lịch của bạn và chủ động nhắc.
Mỗi sprint ~2 tuần.

### Sprint 7 — Infra: Auto-update + dọn tech debt

> Làm riêng, **trước** mọi feature MVP2: app đã ship `.msi` nhưng chưa có cơ chế update —
> cần có trước khi đẩy thêm feature để không phải bắt user cài lại thủ công mỗi lần.

- [x] Tauri **updater plugin** (`tauri-plugin-updater` + `tauri-plugin-process`) — check +
      tải + cài bản mới + relaunch. Rust: đăng ký plugin trong `lib.rs`, permission
      `updater:default` + `process:default` trong `capabilities/default.json`. Frontend:
      hook `useUpdateAvailable` (check lúc mount + mỗi 6h) + component `UpdatePrompt`
      (mount trong `layout.tsx`) — hiện toast sonner "Có bản cập nhật mới: vX.Y.Z" với nút
      "Cập nhật ngay" → `downloadAndInstall()` → `relaunch()`.
- [x] Hạ tầng phân phối update — **đã chốt: GitHub Releases**. `tauri.conf.json`:
      `bundle.createUpdaterArtifacts: true` + `plugins.updater.endpoints` trỏ
      `https://github.com/cuongvntq/JARVIS/releases/latest/download/latest.json`. CI mới
      `.github/workflows/release.yml` (trigger tag `v*.*.*`, Windows, dùng
      `tauri-apps/tauri-action@v0`) build + ký + tạo `latest.json` + draft release.
- [x] **Phân biệt 2 loại key (đừng nhầm):**
      - **Updater signature key** (minisign/ed25519 của Tauri) — đã generate, public key
        nhúng trong `tauri.conf.json` (`plugins.updater.pubkey`); private key + password
        lưu ở GitHub Actions secrets `TAURI_SIGNING_PRIVATE_KEY` /
        `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` (không commit — file gốc ở
        `frontend/src-tauri/secrets/`, đã gitignore).
      - **Windows code-signing cert** (Authenticode) — **DEFERRED**. App vẫn unsigned ở OS
        level (SmartScreen sẽ warning khi cài `.msi`) — chấp nhận được cho personal use.
        Mua + cấu hình Authenticode cert là việc riêng, ngoài scope Sprint 7.
- [x] **Release safety:**
      - **Staged rollout:** CI tạo release ở trạng thái **draft** (`releaseDraft: true`) —
        không xuất hiện ở `releases/latest` nên updater không thấy. Cài thử `.msi` từ draft
        trên 1 máy test → nếu OK, `gh release edit <tag> --draft=false` để publish.
      - **Kill-switch:** nếu bản đã publish bị lỗi, `gh release edit <tag> --prerelease` →
        GitHub `releases/latest` tự fallback về release ổn định trước đó → app dừng nhận
        update lỗi. **Lưu ý:** máy đã update lên bản lỗi sẽ không tự downgrade (updater chỉ
        đi tới); kill-switch chỉ bảo vệ máy *chưa* update — fix thật cần ship version mới hơn.
- [x] UI: thông báo có bản mới + nút "Cập nhật" — xem `UpdatePrompt`/`useUpdateAvailable` ở trên.
- [x] Tech debt: **Idempotency-Key** header (POST /todos, /notes, /memories, /reminders) —
      `IdempotencyMiddleware` (`backend/app/middleware/idempotency.py`), **in-memory dict +
      TTL** (`idempotency_key_ttl_seconds`, default 86400s) — không dùng Redis như
      `05_security.md` ghi, vì desktop app single-process/single-user (lý do ghi trong
      docstring của middleware). Cùng key + body khác → `409 idempotency_conflict`; cùng
      key + body giống → trả lại response đã cache, không tạo bản ghi mới.
- [ ] Verify trực quan **toast reminder trong WebView** (chưa verify từ Phase 4) — QA thủ
      công, không có code thay đổi
- **DoD:** Bump version → build → app đang chạy nhận diện bản mới → cập nhật thành công không cài lại tay; **test bật kill-switch → app không tự update**; verify updater signature key tách biệt code-signing cert.

**Checklist QA thủ công (sau khi merge PR1 — user tự thực hiện):**
- [ ] Verify toast reminder hiển thị đúng trong WebView (item còn lại từ Phase 4)
- [ ] Bump `version` trong `frontend/src-tauri/tauri.conf.json` → tag `vX.Y.Z` → `git push --tags`
      → CI `release.yml` build xong tạo **draft release** với `.msi` + `latest.json` + `.sig`
- [ ] Cài `.msi` từ draft release trên máy test (version cũ hơn) → `gh release edit <tag>
      --draft=false` để publish → app cũ tự phát hiện bản mới (trong vòng 6h hoặc mở lại
      app) → bấm "Cập nhật ngay" → cài thành công + tự relaunch ở version mới
- [ ] Test kill-switch: `gh release edit <tag> --prerelease` trên bản vừa publish → xác nhận
      `releases/latest/download/latest.json` trả về bản trước đó (app không nhận update lỗi)

### Sprint 8 — Google OAuth (desktop) + kết nối Calendar

- [ ] OAuth Desktop flow: loopback redirect + PKCE; Tauri mở system browser, local server bắt `code`
- [ ] **Acceptance criteria bảo mật (bắt buộc):**
      - **PKCE**: `code_verifier` random + `code_challenge` (S256)
      - **`state`** random chống CSRF, verify khi nhận callback
      - **Random loopback port** (không hardcode), redirect_uri = `http://127.0.0.1:<port>`
      - Validate **origin/redirect** của callback; chỉ chấp nhận đúng `state` + đúng port đã mở
      - **`access_type=offline`** + **`prompt=consent`** (khi cần) để chắc chắn lấy được refresh token
      - Loopback server chỉ sống trong lúc auth rồi đóng; timeout nếu user không hoàn tất
- [ ] Lưu token theo Quyết định kiến trúc (Credential Manager qua `keyring`); DB chỉ metadata
- [ ] Token refresh tự động khi access token hết hạn; xử lý refresh token bị **revoke** (re-auth)
- [ ] DB: bảng `google_oauth_accounts` (email, scopes, expiry — **không token**) + migration
      (`sync_token` thuộc per-calendar sync state, xem `calendar_sync_states` ở Sprint 9 — không để ở đây)
- [ ] Backend: service gọi Google API (httpx, không cần SDK nặng) + endpoints connect/disconnect/status
- [ ] UI: Settings → "Kết nối Google Calendar" / "Ngắt kết nối" / trạng thái
- **DoD:** Kết nối → list calendars OK → **giả lập access token hết hạn → refresh tự động thành công** → **disconnect gọi revoke endpoint → token mất hiệu lực tại Google** → reconnect lại được. State/PKCE sai → từ chối.

### Sprint 9 — Calendar read-only (Google → JARVIS)

> Tách riêng read-only trước 2-way **cho an toàn**: xác nhận sync + auth ổn trước khi cho ghi ngược.

- [ ] Pull events qua Calendar API, **incremental sync bằng `syncToken`** (per calendar)
- [ ] **Edge case bắt buộc của Google incremental sync** (không ghi vào đây thì Sprint 10 sẽ vỡ):
      - **Pagination**: lặp `nextPageToken` đến hết; `nextSyncToken` chỉ có ở trang cuối
      - **`410 Gone`** khi `syncToken` invalid → **full resync** (xóa cache calendar đó, sync lại từ đầu)
      - **Deleted/cancelled events**: `status == "cancelled"` → xóa khỏi cache (không hiển thị)
      - **Recurring events**: dùng `singleEvents=true` (expand instances) cho hiển thị; lưu ý quota/lượng data
      - **All-day events**: `start.date` (không `start.dateTime`) → xử lý riêng với event có giờ
      - **Timezone**: tôn trọng `start.timeZone`; convert sang tz user ở app layer
      - **Chọn calendar nào sync**: mặc định primary; cho user chọn (multi-calendar = post-MVP nếu cần)
- [ ] DB: bảng `calendar_events` (cache local) + bảng `calendar_sync_states` (per calendar:
      `calendar_id`, `sync_token`, `last_synced_at`) + migration
- [ ] APScheduler job poll định kỳ (vd 5 phút) — tái dùng infra scheduler
- [ ] Dashboard: hiển thị event hôm nay cạnh todo/reminder
- [ ] Tool mới: `list_calendar_events`; `get_today_summary` gộp thêm lịch
- **DoD:** Tạo event trên Google → vài phút sau lên Dashboard; **xóa event trên Google → biến mất khỏi cache**; **làm invalid syncToken → full resync chạy đúng**; recurring + all-day hiển thị đúng; hỏi "hôm nay có gì" → trả cả lịch.

### Sprint 10 — Calendar 2-way sync (JARVIS → Google)

- [ ] Tools: `create_calendar_event`, `update_calendar_event`, `delete_calendar_event`
- [ ] Liên kết reminder/todo có `due_at` → tùy chọn tạo event Google tương ứng
- [ ] **Stable mapping (chống duplicate — rủi ro lớn nhất MVP2):**
      - Bảng mapping local: `calendar_event_id` (local) ↔ Google `event.id` ↔ `iCalUID`
      - **Idempotent create**: JARVIS **tự sinh `event.id`** (client-side, base32hex) khi insert →
        retry cùng id không tạo trùng (Google trả 409 nếu đã tồn tại, coi như thành công)
      - Gắn `extendedProperties.private.jarvis_id` = local id để truy ngược + tránh nhận nhầm event của nguồn khác
- [ ] **Conflict resolution**: `etag`/`sequence` (last-write-wins hoặc báo conflict) + reconcile qua `syncToken`
- [ ] Xử lý retry / network failure: thao tác create/update/delete phải an toàn khi gọi lại
- **DoD:** "Đặt lịch họp 2h chiều mai" → tạo event trên Google; sửa trên Google → JARVIS cập nhật ngược; **test: ngắt mạng giữa create rồi retry → không nhân đôi event**; xóa 2 đầu → reconcile đúng.

### Sprint 11 — Proactive Nudge

- [ ] **Lifecycle constraint (ghi rõ để tránh hiểu nhầm):** sidecar backend chỉ chạy **khi app đang mở**
      (minimize vẫn chạy nhờ OS notification từ PR #36). Khi **app đóng / logout / sau reboot** → backend
      không chạy → **không có nudge**. Reminder/event không mất (vẫn trong DB/Google), sẽ nudge lại khi mở app.
      - *Nếu* muốn nudge chạy nền cả khi app đóng / sau reboot → **scope bổ sung**: auto-start lúc đăng nhập
        Windows + background process (tray app hoặc Windows service). **Quyết định cần chốt** — mặc định MVP2
        **không** bao gồm (chỉ nudge khi app mở), để tránh nở scope.
- [ ] APScheduler job phân tích: digest buổi sáng, cảnh báo overdue, "chuẩn bị" trước event sắp tới
- [ ] Dùng **native OS notification** (plugin có sẵn từ PR #36) — chạy cả khi window minimize
- [ ] Engine rule-based trước (overdue todos, event trong 1h tới, reminder đến hạn); tùy chọn LLM sinh câu digest
- [ ] DB: `nudge_log` (chống nhắc trùng, kể cả sau khi mở lại app) + migration
- [ ] Settings: quiet hours, bật/tắt từng loại nudge
- **DoD:** Sáng (app đang mở) nhận 1 notification tổng hợp ngày; có việc overdue → nudge; không spam trùng; tôn trọng quiet hours; constraint "chỉ khi app mở" được verify + ghi rõ cho user.

### MVP2 — Cross-cutting

| Mục | Ghi chú |
|---|---|
| Dependency mới | `httpx` (calls Calendar REST); `tauri-plugin-updater`; Python `keyring` (token storage qua Windows Credential Manager) |
| Cost | Calendar API free (quota rộng); LLM cost ~0 (chỉ digest tùy chọn) |
| Rủi ro chính | Token storage (Sprint 8); conflict resolution 2-way (Sprint 10) |
| Bảo mật | OAuth token = secret cấp cao nhất; audit theo `.claude/rules/05_security.md` |

---

## 2. MVP 3 — Voice / Computer-use / Multimodal (tuần tự, sâu)

Quyết định: làm **tuần tự, từng track sâu, tránh lỗi** — không chạy song song.
Thứ tự C → A → B chọn theo rủi ro tăng dần + dependency.

> **Chủ đích:** MVP3 cố ý giữ ở mức **định hướng** (không sprint/DoD chi tiết như MVP2) — chốt chi
> tiết khi gần xong MVP2, vì stack voice/computer-use thay đổi nhanh. Đây là quyết định của user,
> không phải thiếu sót. Mỗi track sẽ được "executable-hóa" (sprint + DoD kiểu MVP2) ngay trước khi bắt đầu.

### Track 1 (trước) — Multimodal / Visual context

- Vì sao trước: Gemini 2.5 Flash + GPT-4o **đã multimodal sẵn** → ít việc backend; rủi ro thấp;
  và **mở khóa vision cho Track 3** (computer-use tier cao cần "nhìn" màn hình).
- Phạm vi: đọc ảnh, PDF, screenshot. Use case: "tóm tắt PDF này", "hoá đơn này bao nhiêu", "trên màn hình có gì".
- Việc chính: upload/attach file ở chat UI; truyền image vào LLM qua LiteLLM; xử lý kích thước/định dạng.
- **Caveat PDF (chốt fallback):** không phải provider nào qua LiteLLM cũng nhận PDF trực tiếp ổn —
  Gemini xử lý PDF native, nhưng đường khác có thể không. **Fallback bắt buộc:** text extraction
  (vd `pypdf`) cho PDF dạng text, hoặc **render từng trang ra ảnh** rồi đưa vào model như image.
  Quyết định route theo provider đang dùng — không giả định "mọi PDF đều qua thẳng LLM".
- Rủi ro: **Thấp** (trừ PDF cần fallback như trên).

### Track 2 (giữa) — Voice (STT + TTS)

- Vì sao giữa: độc lập, **tái dùng toàn bộ chat backend**; chỉ thêm lớp audio I/O ở frontend.
- Local-first là lợi thế: STT (whisper.cpp) + TTS (Piper) chạy **offline, free, riêng tư**; mic trực tiếp.
- Vòng lặp voice: wake word ("Hey JARVIS") → STT → chat orchestrator hiện có → TTS.
- **Quyết định cần chốt:** offline (whisper.cpp/Piper) vs cloud (Whisper API/OpenAI/ElevenLabs) — riêng tư+free ↔ chất lượng.
- Rủi ro: **Trung bình** (audio I/O, wake word độ chính xác, latency).

### Track 3 (cuối) — Computer-use / Automation

- Vì sao cuối: bề mặt bảo mật **lớn nhất**; phụ thuộc Track 1 cho vision (tier cao).
- Làm theo **tier tăng dần**, mỗi tier là 1 cột mốc riêng:
  1. **Whitelist actions** — mở app / mở URL / chạy script đã duyệt trước
  2. **File ops** — đọc/ghi/tìm file trong folder được cho phép
  3. **Full computer-use** — screenshot + click/keyboard (Anthropic computer-use style, cần vision model)
- Bắt buộc mọi tier: **confirm rõ ràng từng hành động + allowlist + audit log + gating hành động nguy hiểm**.
- **Quyết định cần chốt:** dừng ở tier nào (khuyến nghị bắt đầu tier 1, đánh giá rồi mới lên tier sau).
- Rủi ro: **Cao nhất** — cho LLM quyền thực thi trực tiếp trên máy.

---

## 3. RISK CHECKLIST tổng

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| OAuth token bị lộ (local storage) | 🔴 Cao | Credential Manager qua `keyring` (sidecar Python đọc trực tiếp); DB chỉ metadata; không log token |
| Calendar 2-way tạo event trùng / mất sync | 🔴 Cao | Client-gen `event.id` (idempotent create) + `iCalUID` + `extendedProperties.jarvis_id` mapping; etag/sequence; 410→full resync; **test retry/network-fail** |
| Calendar sync edge case (410, recurring, all-day) bỏ sót | 🟠 TB | Liệt kê đầy đủ trong Sprint 9 DoD trước khi sang 2-way |
| Proactive nudge spam | 🟡 Thấp | `nudge_log` chống trùng + quiet hours |
| Nudge không chạy khi app đóng/reboot | 🟡 Thấp | Constraint ghi rõ; background process là scope tùy chọn, không mặc định MVP2 |
| Computer-use thực thi sai/nguy hiểm | 🔴 Cao | Tier tăng dần, confirm từng action, allowlist, audit log |
| Auto-update đẩy bản hỏng | 🟠 TB | Phân biệt updater key vs code-signing cert; kill-switch + staged rollout + test máy sạch |
| Scope creep (nhảy track MVP3) | 🟠 TB | Lock 1 track/lần; không song song |

---

## 4. CẦN CHỐT TRƯỚC KHI START

**Đã chốt trong bản này:**
- Token storage: Credential Manager qua `keyring` (sidecar Python đọc trực tiếp), DB chỉ metadata.
- Calendar: polling + `syncToken`, không webhook.
- `docs/06` §8: đã đánh dấu STALE + trỏ sang tài liệu này làm source of truth.

**Còn để ngỏ — chốt trước khi start sprint liên quan:**
1. ~~Sprint 7: ai/đâu host update artifact~~ — **đã chốt: GitHub Releases** (xem Sprint 7).
2. Sprint 11: nudge có cần chạy **nền khi app đóng / sau reboot** không? (mặc định: KHÔNG — chỉ khi app mở).
   Nếu CÓ → thêm scope auto-start + background process.
3. MVP3 Track 2 (Voice): **offline (whisper.cpp/Piper) vs cloud** — riêng tư+free ↔ chất lượng.
4. MVP3 Track 3 (Computer-use): **dừng ở tier nào** (khuyến nghị bắt đầu tier 1, đánh giá rồi mới lên).
