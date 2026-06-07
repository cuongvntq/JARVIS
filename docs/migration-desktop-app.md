# Migration Plan: Web App → Tauri Desktop App

**Ngày tạo:** 2026-06-04

**Cập nhật:** 2026-06-06 (Phase 4 complete)

**Trạng thái:** DONE — tất cả 4 phase đã hoàn thành

**Lý do:** Giảm chi phí hosting, chạy offline trên máy cá nhân

---

## Quyết định kiến trúc

| Thành phần | Trước | Sau |
|---|---|---|
| Desktop wrapper | — | **Tauri** (WebView, ~15MB app) |
| Frontend host | Vercel (cloud) | Tauri WebView (local) |
| Backend host | Railway (cloud, $5/tháng) | FastAPI sidecar (PyInstaller .exe) |
| Database | Supabase PostgreSQL (cloud) | **Local PostgreSQL** (máy dev, đã cài sẵn) |
| Push notification | Web Push / VAPID | **In-app notification** (phase đầu), Tauri OS notification (phase sau) |
| LLM | Gemini/OpenAI API | **Giữ nguyên** (vẫn cần internet) |
| Chi phí hàng tháng | ~$5.15 | ~$0 |

> **Lưu ý về PostgreSQL:** Phương án này phù hợp để chạy trên máy dev cá nhân (đã có sẵn Postgres + pgvector).
> Nếu muốn đóng gói cho người khác dùng mà không cần cài Postgres, cần phase riêng để embedded Postgres hoặc bỏ pgvector và chuyển sang SQLite + sqlite-vec. Không nằm trong scope hiện tại.

---

## Phần lớn giữ nguyên

Phần lớn domain code giữ nguyên — chỉ thay đổi ở lớp infrastructure và notification flow:

- Tất cả domain logic: chat, todo, note, memory, dashboard
- SQLAlchemy models (trừ thêm `due` vào `reminder_status` enum)
- LiteLLM routing (Gemini primary / OpenAI fallback)
- 211 backend tests

**Thay đổi có scope nhỏ:** reminders router (thêm 2 route), scheduler_service (xóa push logic), push_service/push_subscription (xóa), schemas/types (thêm `due`), frontend notification hook (thêm mới).

---

## Phase 1 — Đổi DB sang local PostgreSQL

**Thời gian ước tính:** 30 phút

**Rủi ro:** Thấp

### Việc cần làm

- [ ] Tạo database `jarvis` và user trên local PostgreSQL (chạy bằng superuser):
  ```sql
  CREATE DATABASE jarvis;
  CREATE USER jarvis_user WITH PASSWORD 'local_pass';
  GRANT ALL PRIVILEGES ON DATABASE jarvis TO jarvis_user;
  -- PostgreSQL 15+ mặc định revoke CREATE trên public schema, cần grant thêm:
  \c jarvis
  GRANT USAGE, CREATE ON SCHEMA public TO jarvis_user;
  ```
- [ ] Enable pgvector extension (chạy bằng superuser — `jarvis_user` thường không đủ quyền CREATE EXTENSION):
  ```sql
  \c jarvis
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  ```
- [ ] Cập nhật `.env`:
  ```env
  DATABASE_URL=postgresql+asyncpg://jarvis_user:local_pass@localhost:5432/jarvis
  DATABASE_URL_DIRECT=postgresql://jarvis_user:local_pass@localhost:5432/jarvis
  ```
- [ ] Sửa `backend/app/database.py` — xóa `statement_cache_size: 0` khỏi `connect_args`:
  - Param đó chỉ cần cho Supabase transaction pooler (pgbouncer), local Postgres không cần
  - File: `backend/app/database.py` line 25 — xóa `"connect_args": {"statement_cache_size": 0}`
- [ ] Chạy `alembic upgrade head` (dùng `DATABASE_URL_DIRECT`)
- [ ] Cập nhật CORS trong `.env` — thêm `tauri://localhost` cho Tauri WebView:
  ```env
  BACKEND_CORS_ORIGINS=tauri://localhost,http://localhost:3000
  ```
  > **Tại sao:** `config.py:27` default chỉ có `http://localhost:3000`. Tauri WebView dùng origin `tauri://localhost` — nếu không add thì mọi API call từ Tauri app sẽ bị CORS block. Giữ env var thay vì đổi default trong code để không ảnh hưởng dev workflow.
- [ ] Verify: `GET /health/ready` trả `200`

### File thay đổi

- `.env` — đổi DATABASE_URL, thêm `BACKEND_CORS_ORIGINS`
- `backend/app/database.py` — xóa Supabase-specific `connect_args`

---

## Phase 2 — Setup Tauri

**Thời gian ước tính:** 2–3 giờ

**Rủi ro:** Trung bình (cần cài Rust lần đầu)

### Prerequisites

- [ ] Cài Rust: https://rustup.rs — chọn **MSVC toolchain** trên Windows
- [ ] Cài Visual Studio C++ Build Tools (nếu chưa có) — Rust yêu cầu
- [ ] Verify: `cargo --version` và `rustc --version`
- [ ] Cài WebView2 (thường đã có sẵn trên Windows 10/11): https://developer.microsoft.com/en-us/microsoft-edge/webview2/

### Việc cần làm

- [ ] Trong `frontend/`, chạy: `npx @tauri-apps/cli@2 init`
  - App name: `JARVIS`
  - Window title: `J.A.R.V.I.S`
  - Dist dir: `../out`
  - Dev server URL: `http://localhost:3000`
- [ ] Sửa `frontend/next.config.ts` cho static export:
  ```ts
  // Xóa hoàn toàn rewrites() — static export không support, và api.ts không dùng /api/ proxy
  // BASE_URL trong api.ts gọi thẳng đến NEXT_PUBLIC_API_URL, không qua /api/ rewrite
  const nextConfig: NextConfig = {
    reactStrictMode: true,
    output: 'export',
    images: { unoptimized: true },
    // rewrites() đã xóa
  };
  ```
  > **Lý do xóa rewrites:** `frontend/src/lib/api.ts:46` dùng `BASE_URL` gọi thẳng `http://localhost:8000/auth/login`, không qua `/api/` proxy — rewrites không được dùng trong API client, chỉ dùng cho static export không support nó.

- [ ] Set env cho Tauri dev build — tạo `frontend/.env.local`:
  ```env
  # KHÔNG có /v1 ở cuối — api.ts tự append /auth/*, /v1/chat/*, etc.
  NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
  ```
  > **Quan trọng:** `api.ts` build path theo pattern `${BASE_URL}/auth/login`, `${BASE_URL}/v1/chat/send`. Nếu set `http://127.0.0.1:8000/v1` thì auth sẽ thành `/v1/auth/login` (sai), chat thành `/v1/v1/chat/send` (sai).

- [ ] Config `frontend/src-tauri/tauri.conf.json`:
  ```json
  {
    "productName": "JARVIS",
    "version": "1.0.0",
    "identifier": "com.jarvis.app",
    "build": {
      "frontendDist": "../out",
      "devUrl": "http://localhost:3000"
    },
    "app": {
      "windows": [{
        "title": "J.A.R.V.I.S",
        "width": 1280,
        "height": 800,
        "minWidth": 900,
        "minHeight": 600
      }]
    }
  }
  ```
- [ ] Test dev mode: `pnpm tauri dev` (Tauri mở WebView, backend phải đang chạy riêng)
- [ ] Verify các trang load đúng, không có server-side feature nào bị break bởi static export

### File tạo mới / thay đổi

- `frontend/src-tauri/` — toàn bộ Tauri scaffold
- `frontend/next.config.ts` — xóa rewrites, thêm `output: 'export'`
- `frontend/.env.local` — API URL không có `/v1`

---

## Phase 3 — FastAPI sidecar (PyInstaller + Tauri shell plugin)

**Thời gian ước tính:** 2–3 giờ

**Rủi ro:** Trung bình-cao (PyInstaller + hidden imports phức tạp)

### 3.0 — Setup Tauri shell plugin (bắt buộc cho sidecar)

Tauri v2 yêu cầu `tauri-plugin-shell` để dùng sidecar — không thể dùng `app.shell()` mà không có plugin.

- [ ] Thêm dependency vào `frontend/src-tauri/Cargo.toml`:
  ```toml
  [dependencies]
  tauri-plugin-shell = "2"
  ```
- [ ] Đăng ký plugin trong `frontend/src-tauri/src/main.rs`:
  ```rust
  use tauri_plugin_shell::ShellExt;  // thêm import

  tauri::Builder::default()
      .plugin(tauri_plugin_shell::init())  // thêm trước .setup()
      .setup(|app| { ... })
  ```
- [ ] Verify capability trong `frontend/src-tauri/capabilities/default.json`:
  - **Rust-side `sidecar.spawn()` trong `setup()` không cần JS capability** — plugin init là đủ. Để trống / không thêm gì.
  - `shell:allow-execute` dành cho `Command.create(...).execute()` — **khác** với `spawn()`, không dùng nhầm.
  - Chỉ thêm capability bên dưới nếu **sau này muốn spawn từ JS** (frontend code gọi `Command.sidecar()`):
    ```json
    {
      "permissions": ["shell:allow-spawn", "shell:allow-kill"]
    }
    ```
    *(optional, JS-only — không thêm ngay bây giờ)*

### 3.1 — Build FastAPI exe

- [ ] Cài PyInstaller: `uv pip install pyinstaller`

- [ ] Tạo `backend/jarvis_server.py` — entry point (đọc port từ settings, không hardcode):
  ```python
  import os, sys
  from pathlib import Path

  # Khi chạy dưới dạng PyInstaller exe, resolve .env theo vị trí exe
  # config.py dùng env_file="../.env" (relative path chỉ đúng khi chạy từ backend/)
  # Packaged exe chạy từ install dir nên cần override env_file bằng env var
  _exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
  _env_path = _exe_dir / ".env"
  if _env_path.exists():
      os.environ.setdefault("ENV_FILE_PATH", str(_env_path))

  import uvicorn
  from app.config import get_settings

  if __name__ == "__main__":
      settings = get_settings()
      port = int(os.environ.get("BACKEND_PORT", settings.backend_port))
      uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level=settings.log_level.lower())
  ```
  > **Cần sửa `config.py`** để nhận `ENV_FILE_PATH` override:
  > ```python
  > import os  # thêm import này ở đầu file nếu chưa có
  >
  > model_config = SettingsConfigDict(
  >     env_file=os.environ.get("ENV_FILE_PATH", "../.env"),
  >     env_file_encoding="utf-8",
  >     case_sensitive=False,  # giữ nguyên từ config cũ
  >     extra="ignore",
  > )
  > ```
  > **Env lookup order (implemented):**
  > 1. `%APPDATA%\JARVIS\.env` — user config dir, writable even when installed to `C:\Program Files\JARVIS\`
  > 2. `.env` cạnh exe — dev hoặc portable mode
  >
  > Với installed MSI: copy `.env` vào `%APPDATA%\JARVIS\.env` một lần sau khi cài đặt. File này tồn tại qua upgrade (Tauri MSI không xóa AppData khi update).

- [ ] Tạo `backend/jarvis_server.spec` (KHÔNG dùng `--onefile` đơn giản):
  ```python
  # jarvis_server.spec
  from PyInstaller.utils.hooks import collect_all

  # Thu thập tất cả submodule của litellm (nhiều hidden import)
  litellm_datas, litellm_binaries, litellm_hiddenimports = collect_all('litellm')

  a = Analysis(
      ['jarvis_server.py'],
      pathex=['.'],
      datas=[
          ('app/vi_time_dict.json', 'app'),        # Vietnamese datetime dict
          ('alembic.ini', '.'),                      # Nếu app tự migrate khi khởi động
          ('migrations/', 'migrations/'),            # Alembic migration files (script_location = migrations)
          *litellm_datas,
      ],
      hiddenimports=[
          'uvicorn.logging',
          'uvicorn.loops.auto',
          'uvicorn.protocols.http.auto',
          'passlib.handlers.bcrypt',
          'apscheduler.schedulers.asyncio',
          'apscheduler.triggers.interval',
          'asyncpg',
          *litellm_hiddenimports,
      ],
      binaries=[*litellm_binaries],
  )
  pyz = PYZ(a.pure)
  exe = EXE(
      pyz, a.scripts, a.binaries, a.datas,  # a.binaries bắt buộc — chứa litellm native deps
      name='jarvis-server',
      console=False,  # không hiện terminal window
  )
  ```

- [ ] Build: `pyinstaller jarvis_server.spec`

- [ ] **Test exe độc lập TRƯỚC khi tích hợp Tauri** (rủi ro cao nhất):
  ```powershell
  dist\jarvis-server.exe
  # Verify:
  curl http://127.0.0.1:8000/health
  curl http://127.0.0.1:8000/health/ready
  # Test chat flow, reminder, memory search
  ```

- [ ] Copy exe vào Tauri:
  ```powershell
  Copy-Item dist\jarvis-server.exe `
    frontend\src-tauri\binaries\jarvis-server-x86_64-pc-windows-msvc.exe
  ```

- [ ] Đăng ký sidecar trong `tauri.conf.json`:
  ```json
  "bundle": {
    "externalBin": ["binaries/jarvis-server"]
  }
  ```

- [ ] Viết Tauri command trong `frontend/src-tauri/src/main.rs`:
  ```rust
  use tauri::Manager;
  use tauri_plugin_shell::ShellExt;
  use tauri_plugin_shell::process::CommandChild;  // type từ plugin, không phải std::process::Child
  use std::sync::Mutex;

  struct BackendProcess(Mutex<Option<CommandChild>>);

  fn main() {
      tauri::Builder::default()
          .plugin(tauri_plugin_shell::init())
          .manage(BackendProcess(Mutex::new(None)))
          .setup(|app| {
              let sidecar = app.shell().sidecar("jarvis-server").unwrap();
              let (_, child) = sidecar.spawn().expect("Failed to start backend");
              *app.state::<BackendProcess>().0.lock().unwrap() = Some(child);
              Ok(())
          })
          .on_window_event(|window, event| {
              if let tauri::WindowEvent::Destroyed = event {
                  if let Some(mut child) = window.app_handle()
                      .state::<BackendProcess>().0.lock().unwrap().take() {
                      let _ = child.kill();
                  }
              }
          })
          .run(tauri::generate_context!())
          .expect("error while running tauri application");
  }
  ```
  > **Child type:** `tauri_plugin_shell::process::CommandChild` — không phải `std::process::Child`. Để compiler infer type nếu không chắc: `let (_, child) = sidecar.spawn()...` và không annotate type trên struct field; để Rust compiler báo đúng type.

### File tạo mới / thay đổi

- `backend/jarvis_server.py` — PyInstaller entry point
- `backend/jarvis_server.spec` — build spec với hidden imports
- `backend/app/config.py` — thêm `ENV_FILE_PATH` override cho `env_file`
- `frontend/src-tauri/src/main.rs` — sidecar start/stop
- `frontend/src-tauri/binaries/` — chứa FastAPI exe

---

## Phase 4 — Notification + Build installer

**Thời gian ước tính:** 1–2 giờ

**Rủi ro:** Thấp-Trung bình

### 4.1 — Thay Web Push bằng in-app notification (Phase đầu)

> **Giới hạn rõ ràng:** In-app notification **chỉ hiện khi app đang mở**. Nếu app đóng, reminder không bị mất — vẫn ở trạng thái `due` trong DB, sẽ hiện lại khi mở app. Native/background notification để backlog sau (dùng cùng API `/due` + `/ack`).

Vấn đề cốt lõi: scheduler chạy trong Python process, Tauri notification API nằm ở Rust/WebView process — không có bridge trực tiếp. Giải pháp: scheduler chỉ quản lý thời gian, frontend quản lý hiển thị.

#### State machine mới

```
pending  ──[scheduler: remind_at đã qua]──►  due  ──[frontend: POST /ack]──►  sent
                                               │
                                    [app đóng, chưa ack]
                                               │
                                        vẫn là `due`
                                    (hiện lại khi mở app)
```

Bỏ trạng thái `sending` (chỉ cần cho web push async). Giữ `failed` cho lỗi scheduler.

| Status | Ai set | Ý nghĩa |
|---|---|---|
| `pending` | User/create | Chưa đến giờ |
| `due` | Scheduler | Đã đến giờ, chờ frontend ack |
| `sent` | Frontend (POST /ack) | Đã hiển thị toast |
| `failed` | Scheduler (error) | Lỗi khi xử lý |

#### Backend — việc cần làm

**Bước 1 — Thêm `due` vào Postgres enum (migration mới):**
- [ ] Tạo migration mới:
  ```python
  def upgrade():
      op.execute("ALTER TYPE reminder_status ADD VALUE IF NOT EXISTS 'due'")
      # Không cần downgrade: Postgres không cho DROP enum value

  def downgrade():
      pass  # intentionally no-op — Postgres không support DROP ENUM VALUE
  ```
  > **Đã xác nhận:** `reminder_status` là Postgres enum (`create_type=False` ở `models/reminder.py:38`). Không thể chỉ sửa Pydantic.

- [ ] Cập nhật `backend/app/models/reminder.py:32` — thêm `"due"` vào danh sách enum values
- [ ] Cập nhật `backend/app/schemas/reminder.py:67` — thêm `"due"` vào Literal:
  ```python
  ReminderStatus = Literal["pending", "sending", "sent", "failed", "cancelled", "due"]
  ```
  > **Giữ `sending`** trong enum — không DROP (phức tạp, rủi ro). Chỉ ngừng tạo transition mới sang `sending`. Recovery `sending → failed` vẫn hợp lý cho data cũ.

**Bước 2 — Thêm 2 route mới, đặt TRƯỚC `/{reminder_id}`:**
- [ ] Thêm `GET /due` và `POST /{reminder_id}/ack` **trước** `GET /{reminder_id}` trong `reminders.py`
  > **Quan trọng:** Router hiện có `GET /{reminder_id}` tại line 47. Nếu đặt `/due` sau, FastAPI match `"due"` vào UUID path param → `422 Unprocessable Entity`. Route static phải đứng trước route dynamic.

  ```python
  # Thêm trước @router.get("/{reminder_id}")
  @router.get("/due", response_model=list[ReminderOut])
  async def list_due_reminders(current_user=Depends(get_current_user), db=Depends(get_db)):
      return await reminder_service.list_due(db, current_user.id)

  @router.post("/{reminder_id}/ack", response_model=ReminderOut)
  async def ack_reminder(reminder_id: uuid.UUID, current_user=Depends(get_current_user), db=Depends(get_db)):
      return await reminder_service.ack_reminder(db, reminder_id, current_user.id)
  ```

**Bước 3 — Sửa scheduler:**
- [ ] Sửa `scheduler_service.py`:
  - Xóa toàn bộ logic gọi `push_service.send_push`
  - Bỏ step `claim pending → sending` (chỉ cần cho web push concurrent)
  - Thay bằng: query `pending` có `remind_at <= now` → bulk set `due`
  - Giữ step recovery: reset `sending` cũ → `failed`

**Bước 4 — Cập nhật tool executors:**
- [ ] `backend/app/tools/executors.py:359` — thêm `"due"` vào `_valid_statuses`:
  ```python
  _valid_statuses = {"pending", "sending", "sent", "failed", "cancelled", "due"}
  ```

**Bước 5 — Xóa web push (đủ file, theo thứ tự):**

Backend:
- [ ] Xóa `backend/app/services/push_service.py`
- [ ] Xóa `backend/app/repositories/push_subscription_repo.py`
- [ ] Xóa `backend/app/routers/notifications.py`
- [ ] Sửa `backend/app/main.py`: xóa `import notifications` (line 33) và `app.include_router(notifications.router, ...)` (line 129)
- [ ] Xóa `backend/app/models/push_subscription.py`
- [ ] Sửa `backend/app/models/__init__.py`: xóa `from app.models.push_subscription import PushSubscription` (line 6) và `"PushSubscription"` khỏi `__all__` (line 19)
- [ ] Sửa `backend/app/models/user.py`: xóa `TYPE_CHECKING` import `PushSubscription` (line 18) và relationship `push_subscription` (lines 66–67)
- [ ] Thêm migration: `op.drop_table("push_subscriptions")` + thêm index cho `/due` poll:
  ```python
  import sqlalchemy as sa  # cần có ở đầu migration file để dùng sa.text(...)

  op.create_index(
      "idx_reminders_user_due",
      "reminders",
      ["user_id", "remind_at"],
      postgresql_where=sa.text("status = 'due' AND deleted_at IS NULL"),
  )
  ```
  > App cá nhân không bắt buộc, nhưng poll 60s sẽ nhanh hơn và intent rõ ràng hơn.

Frontend:
- [ ] Xóa `frontend/src/hooks/usePushNotification.ts`
- [ ] Xóa `frontend/public/sw.js`
- [ ] Sửa `frontend/src/lib/api.ts`: xóa `PushSubscribeRequest` import (line 19), xóa methods `subscribePush` (line 353) và `unsubscribePush` (line 360)
- [ ] Sửa `frontend/src/components/settings/SettingsPage.tsx`: xóa `import { usePushNotification }` (line 3), xóa `const push = usePushNotification()` (line 48), xóa toàn bộ section Push Notifications UI (lines 274–348)
- [ ] Xóa khỏi `frontend/src/lib/types/api.ts`: `PushSubscribeRequest` type
- [ ] Verify `pnpm typecheck` pass sau khi xóa

#### Frontend — việc cần làm

- [ ] Cập nhật `frontend/src/lib/types/api.ts:195`:
  ```ts
  export type ReminderStatus = "pending" | "sending" | "sent" | "failed" | "cancelled" | "due";
  ```
- [ ] Kiểm tra `ReminderCard` và status filter — thêm hiển thị/label cho trạng thái `due` nếu cần

- [ ] Tạo hook `frontend/src/lib/hooks/useReminderPolling.ts`:
  - Poll `GET /v1/reminders/due` mỗi 60s (`refetchInterval: 60_000`)
  - Dùng `pendingAckIds` ref (Set) để track reminder đang trong quá trình ack — tránh toast lặp
  - **Thứ tự đúng:** add vào `pendingAckIds` → show toast → gọi `POST /ack` → nếu thành công thì remove khỏi `pendingAckIds` + invalidate cache; nếu `/ack` fail thì remove khỏi `pendingAckIds` để lần poll tiếp theo thử lại
  - **Không dùng `seenIds` permanent** — nếu mark seen trước khi ack thành công, ack fail sẽ làm reminder `due` mãi trong DB nhưng không bao giờ toast lại trong session đó

  ```ts
  const pendingAckIds = useRef(new Set<string>());

  useEffect(() => {
    if (!dueReminders?.length) return;
    for (const r of dueReminders) {
      if (pendingAckIds.current.has(r.id)) continue; // đang ack, skip
      pendingAckIds.current.add(r.id);
      toast(r.title, {
        description: r.description,
        onDismiss: async () => {
          try {
            await apiClient.ackReminder(r.id);
            queryClient.invalidateQueries({ queryKey: ['reminders'] });
          } finally {
            pendingAckIds.current.delete(r.id); // dù success hay fail đều unlock
          }
        },
      });
    }
  }, [dueReminders]);
  ```

  > **Lưu ý:** `onDismiss` phụ thuộc Sonner API. Nếu muốn auto-ack (không cần user dismiss), gọi `/ack` ngay sau khi `toast()` thay vì trong callback.

- [ ] Mount hook trong `app/layout.tsx` (luôn active khi app mở)

#### Xóa khỏi `.env`

- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`

> **Native OS notification — DONE:**
> Đã thêm `@tauri-apps/plugin-notification` (+ `tauri-plugin-notification` Rust crate, `notification:default` capability). `useReminderPolling.ts` gọi `sendNotification()` song song với in-app toast mỗi khi reminder due — request permission qua `isPermissionGranted()`/`requestPermission()`. OS notification hiện kể cả khi window bị minimize; toast vẫn giữ để user dismiss → trigger `/ack`.

### 4.2 — Build installer

- [ ] Thêm app icon: đặt file PNG 512x512 vào `frontend/src-tauri/icons/`, chạy `pnpm tauri icon`
- [ ] Build: `pnpm tauri build`
  - Output: `frontend/src-tauri/target/release/bundle/msi/JARVIS_1.0.0_x64_en-US.msi`
- [ ] Test cài đặt `.msi` — verify app start, backend sidecar khởi động, chat hoạt động

---

## Env vars sau migration (`.env` tối giản)

```env
# Database (local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://jarvis_user:local_pass@localhost:5432/jarvis
DATABASE_URL_DIRECT=postgresql://jarvis_user:local_pass@localhost:5432/jarvis

# LLM (cần internet)
GEMINI_API_KEY=...
OPENAI_API_KEY=...

# Auth
JWT_SECRET=...

# Optional
SENTRY_DSN=...
APP_ENV=production
```

**Loại bỏ hoàn toàn:**
- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` — bỏ web push
- `UPSTASH_REDIS_URL` — rate limit dùng in-memory fallback đã có sẵn
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Google OAuth (backlog)
- `NEXT_PUBLIC_VAPID_PUBLIC_KEY` — frontend web push

**Giữ lại (đổi giá trị):**
- `BACKEND_CORS_ORIGINS=tauri://localhost,http://localhost:3000` — Tauri WebView cần origin `tauri://localhost`

---

## Rủi ro và mitigation

| Rủi ro | Mức độ | Mitigation |
|---|---|---|
| PyInstaller thiếu hidden imports (LiteLLM, providers) | **Cao** | Dùng `.spec` với `collect_all('litellm')`, test exe độc lập kỹ trước tích hợp |
| `vi_time_dict.json` không được bundle | Trung bình | Đã có trong `.spec` `datas` — verify sau khi build |
| Next.js static export break server feature | Trung bình | Audit từng page, `rewrites()` đã xóa (không dùng trong api.ts) |
| Port 8000 conflict với process khác | Thấp | Config `BACKEND_PORT` qua env var — `jarvis_server.py` đọc `os.environ.get("BACKEND_PORT", ...)`, Tauri set env khi spawn sidecar (không dùng argv) |
| pgvector chưa cài trên local Postgres | Trung bình | Bước đầu tiên trong Phase 1: verify extension trước khi migrate |

---

## Thứ tự thực hiện

```
Phase 1 (DB local)  →  Phase 2 (Tauri setup)  →  Phase 3 (sidecar)  →  Phase 4 (notify + build)
     30 min                  2-3 giờ                  2-3 giờ                  1-2 giờ
```

**Tổng thời gian ước tính:** 6–8 giờ

---

## Trạng thái hiện tại

- [x] Quyết định kiến trúc (Tauri + local PostgreSQL)
- [x] Review pass 1 — route ordering, seen IDs, enum update, CORS, section scope
- [x] Review pass 2 — Tauri v2 shell plugin, web push file list, DB permissions, /due index
- [x] Review pass 3 — migrations path, .env packaged path, capability spawn vs execute, CommandChild type, port hardcode
- [x] Review pass 4 (self) — EXE binaries, config.py file list, duplicate frontend section
- [x] Review pass 5 — import os trong config.py, .env Program Files warning, risk table argv→env, capability JSON là optional JS-only
- [x] Phase 1 — DB local (PostgreSQL 18 + pgvector 0.8.2 + 3 extensions + alembic 7 migrations)
- [x] Phase 2 — Tauri setup (Rust 1.96 + WebView2 + tauri-plugin-shell + app mở thành công)
- [x] Phase 3 — FastAPI sidecar (PyInstaller onefile + Tauri shell plugin + CORS fix + login xác nhận hoạt động)
- [ ] Phase 4 — Notification + Build installer

---

## Phase 3 — Lessons Learned (2026-06-05)

### Hidden imports bổ sung so với plan gốc

`collect_all("litellm")` **không** tự kéo tiktoken data. Phải thêm:
```python
tiktoken_datas, tiktoken_binaries, tiktoken_hiddenimports = collect_all("tiktoken")
# + hiddenimports: "tiktoken_ext", "tiktoken_ext.openai_public"
```
Lỗi nếu thiếu: `ValueError: Unknown encoding cl100k_base` khi LiteLLM init.

### Tauri v2 + WebView2 CORS origin

Tauri v2 trên Windows dùng **`http://tauri.localhost`** làm origin của WebView2 (không phải `tauri://localhost` như docs ghi). CORS phải include:
```env
BACKEND_CORS_ORIGINS=http://tauri.localhost,https://tauri.localhost,tauri://localhost,http://localhost:3000
```
Cách debug: thêm tạm button gọi `/health` và log `window.location.origin` + fetch error.

### Sidecar chỉ spawn trong release build

Dùng `#[cfg(not(debug_assertions))]` guard — sidecar không spawn khi `pnpm tauri dev` (backend chạy riêng bên ngoài). Đây là behavior đúng, không phải bug.

### PyInstaller onefile startup time

Onefile exe extract ra temp dir trước khi chạy — mất ~20-25 giây lần đầu. Frontend không nên hiện login form ngay, cần loading state. **(UX todo cho Phase 4)**

### .env phải tạo thủ công sau khi cài MSI

Tauri không bundle `.env` (gitignored). Sau khi cài MSI, copy `.env` vào thư mục user config:

```powershell
# Tạo thư mục nếu chưa có
New-Item -ItemType Directory -Force "$env:APPDATA\JARVIS"
# Copy .env từ repo vào user config dir
Copy-Item .env "$env:APPDATA\JARVIS\.env"
```

Sidecar sẽ tự tìm `%APPDATA%\JARVIS\.env` trước khi tìm cạnh exe. File này không bị xóa khi upgrade MSI.
