# Beta Deploy Plan — MVP 1

Thứ tự thực hiện: A → B → C → D → E (xem sơ đồ cuối file)

---

## Nhóm A — Chuẩn bị secrets & keys

> Làm trước, không cần server nào đang chạy.

### A1. Generate VAPID keys

- [ ] Chạy local: `npx web-push generate-vapid-keys`
- [ ] Lưu 3 giá trị vào password manager: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`
- [ ] `VAPID_SUBJECT` = `mailto:dragonball1997vntq@gmail.com`

> Keys phải cố định từ đầu — nếu regenerate sau khi có user subscribe thì toàn bộ subscription cũ bị invalid.

### A2. Tạo Sentry projects

- [ ] Tạo project `jarvis-backend` (platform: Python / FastAPI)
- [ ] Tạo project `jarvis-frontend` (platform: Next.js)
- [ ] Copy 2 DSN vào notepad
- [ ] Tạo 1 Auth Token (Settings → Auth Tokens → Create) — dùng cho `SENTRY_AUTH_TOKEN` ở bước D2

### A3. Tạo Upstash Redis instance

- [ ] Tạo database trên upstash.com (free tier, region: **ap-southeast-1** Singapore)
- [ ] Vào database → **Redis** tab → copy **Redis URL** dạng `rediss://default:<token>@<host>.upstash.io:6379`
- [ ] Lưu giá trị này — đây là `UPSTASH_REDIS_URL` (backend đọc dạng Redis URI, không phải REST URL)

---

## Nhóm B — Database production (Supabase)

### B1. Kiểm tra Supabase extensions

Vào Supabase Dashboard → Database → Extensions, xác nhận đã enable:

- [ ] `uuid-ossp`
- [ ] `pgcrypto`
- [ ] `pg_trgm`
- [ ] `vector`

Nếu chưa enable thì enable từng cái trước khi chạy migration.

Lấy 2 connection strings từ Supabase → Settings → Database:

- [ ] **Pooler** (Transaction mode, port 6543) → dùng cho `DATABASE_URL` (app runtime, asyncpg)
- [ ] **Direct** (port 5432) → dùng cho `DATABASE_URL_DIRECT` (Alembic, psycopg2)

### B2. Chạy Alembic migration lên production

Settings bắt buộc có cả `DATABASE_URL` lẫn `DATABASE_URL_DIRECT` khi app load (xem `config.py`).
Set cả hai trước khi chạy. Supabase yêu cầu SSL — cú pháp tham số SSL khác nhau theo driver:

```powershell
cd backend
# asyncpg dùng ssl=require
$env:DATABASE_URL = "postgresql+asyncpg://<user>:<pass>@<host>:6543/<db>?ssl=require"
# psycopg2 dùng sslmode=require
$env:DATABASE_URL_DIRECT = "postgresql+psycopg2://<user>:<pass>@<host>:5432/<db>?sslmode=require"
alembic upgrade head
alembic current   # phải show revision 007_... (latest)
```

> Supabase Dashboard → Settings → Database đã ghi rõ connection string khuyến nghị kèm SSL param —
> copy y chang từ đó để tránh sai cú pháp.

- [ ] `alembic upgrade head` thành công, không có lỗi
- [ ] `alembic current` trả về revision mới nhất

---

## Nhóm C — Backend deploy (Railway)

### C1. Tạo Railway service

- [ ] railway.app → New Project → Deploy from GitHub repo → `cuongvntq/JARVIS`
- [ ] Root directory: `backend/`
- [ ] Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Build command: `pip install -e .`
- [ ] Confirm Railway dùng Python ≥ 3.12 (yêu cầu của `pyproject.toml`). Nếu Railway auto-detect sai version → set build variable: `NIXPACKS_PYTHON_VERSION=3.12`

### C2. Set environment variables trên Railway

Deploy backend trước với `BACKEND_CORS_ORIGINS=http://localhost:3000` tạm — sẽ update đúng domain sau bước D1 ở D3.
`allow_credentials=True` không tương thích với wildcard origin, nên không dùng `*`.

| Biến | Giá trị |
|------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://...` (pooler port 6543) |
| `DATABASE_URL_DIRECT` | `postgresql+psycopg2://...` (direct port 5432) |
| `GEMINI_API_KEY` | key từ aistudio.google.com |
| `OPENAI_API_KEY` | key từ platform.openai.com |
| `JWT_SECRET` | random 64 chars (`openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | từ Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | từ Google Cloud Console |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` (tạm — update ở D3 sau khi có Vercel domain) |
| `VAPID_PUBLIC_KEY` | từ bước A1 |
| `VAPID_PRIVATE_KEY` | từ bước A1 |
| `VAPID_SUBJECT` | `mailto:dragonball1997vntq@gmail.com` |
| `SENTRY_DSN` | jarvis-backend DSN từ bước A2 |
| `UPSTASH_REDIS_URL` | `rediss://default:<token>@<host>.upstash.io:6379` từ bước A3 |
| `COOKIE_SAMESITE` | `none` |
| `COOKIE_SECURE` | `true` |
| `APP_ENV` | `production` |

> `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true` bắt buộc khi FE (Vercel) và BE (Railway) khác domain —
> nếu để default `lax`/`false` thì silent refresh token sẽ fail và user bị logout liên tục.

- [ ] Tất cả biến đã set, không thiếu biến nào

### C3. Verify backend healthy

- [ ] Railway deploy xong (status: Active)
- [ ] `GET https://<railway-domain>/health/ready` → HTTP 200

Lưu ý: endpoint này luôn trả HTTP 200 kể cả khi DB lỗi (exception bị catch, body trả về `"status":"degraded"`).
Phải check **body**, không chỉ status code:

```powershell
Invoke-RestMethod https://<railway-domain>/health/ready | ConvertTo-Json
# Phải thấy: "status": "ready", "db": "ok"
```

- [ ] Body có `"status": "ready"` và `"db": "ok"`
- [ ] Railway logs: APScheduler started, không có ERROR khi startup
- [ ] Ghi lại Railway domain để dùng ở bước D2

---

## Nhóm D — Frontend deploy (Vercel)

### D1. Import project lên Vercel

- [ ] vercel.com → Add New Project → Import `cuongvntq/JARVIS`
- [ ] Root directory: `frontend/`
- [ ] Framework: Next.js (Vercel tự detect)
- [ ] Ghi lại Vercel domain (dạng `jarvis-xxx.vercel.app`)

### D2. Set environment variables trên Vercel

Vào Vercel → Project → Settings → Environment Variables:

| Biến | Giá trị |
|------|---------|
| `NEXT_PUBLIC_API_URL` | `https://<railway-domain>` |
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | `VAPID_PUBLIC_KEY` từ bước A1 |
| `NEXT_PUBLIC_SENTRY_DSN` | jarvis-frontend DSN từ bước A2 |
| `SENTRY_AUTH_TOKEN` | Auth Token từ bước A2 |
| `SENTRY_ORG` | slug org trên sentry.io |
| `SENTRY_PROJECT` | `jarvis-frontend` |

> Tên biến VAPID là `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (không phải `NEXT_PUBLIC_VAPID_KEY`) —
> code đọc tên này trong `usePushNotification.ts`.

> `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` cần có tại **build time** để Vercel upload source maps —
> set cho environment **Production** (không chỉ Runtime).

- [ ] Tất cả biến đã set cho **Production** environment
- [ ] Confirm Vercel dùng đúng package manager. Vercel thường tự detect qua `pnpm-lock.yaml`, nhưng nếu build fail thì set thủ công:
  - Install command: `pnpm install --frozen-lockfile`
  - Build command: `pnpm build`
- [ ] Trigger redeploy sau khi set xong

### D3. Update CORS trên Railway

- [ ] Sau khi có Vercel domain, quay lại Railway update `BACKEND_CORS_ORIGINS` = `https://<vercel-domain>.vercel.app`
- [ ] Railway tự redeploy — verify body `/health/ready` vẫn có `"status":"ready","db":"ok"`
- [ ] Test auth thật từ browser: mở Vercel URL → register hoặc login → verify redirect dashboard thành công (health check không chứng minh CORS/cookie đúng)

### D4. Chuẩn bị Google OAuth credential (future OAuth)

> Google OAuth callback chưa được implement trong codebase hiện tại — chỉ có config field và model.
> Bước này là chuẩn bị credential để không phải làm lại khi implement.

- [ ] Vào Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client ID
- [ ] Thêm Authorized redirect URI (để sẵn): `https://<vercel-domain>/auth/callback/google`
- [ ] Thêm Authorized JavaScript origin: `https://<vercel-domain>`
- [ ] **Không test Google login** — chưa có endpoint callback, sẽ fail

---

## Nhóm E — Smoke test & monitoring

### E1. Happy path test thủ công

Mở `https://<vercel-domain>` trên browser:

- [ ] Register tài khoản mới → nhận về JWT, redirect dashboard
- [ ] Gửi chat message → nhận phản hồi từ JARVIS (Gemini)
- [ ] Tạo todo qua chat: "Thêm việc mua sữa chiều nay" → todo xuất hiện trong list
- [ ] Tạo reminder: "Nhắc tôi uống thuốc 8h tối nay" → reminder được lưu
- [ ] Subscribe push notification trên browser → kiểm tra DB (`push_subscriptions` table) có subscription
- [ ] Logout → login lại → session hợp lệ (silent refresh không bị block bởi cookie)

### E2. Sentry smoke test

> Gọi endpoint 404 không phải Sentry test tốt — 404 thường không được capture như exception.

Cách đúng — trigger real exception qua route debug có guard bằng env:

**Phần 1 — Backend Sentry**

Commit route debug có guard vào `main` (Railway deploy từ GitHub, nên code phải lên repo):

```python
# backend/app/routers/health.py
# Merge vào import hiện có (không thêm dòng import riêng):
# from fastapi import APIRouter, Depends  →  from fastapi import APIRouter, Depends, HTTPException
import os
from fastapi import APIRouter, Depends, HTTPException

@router.get("/health/sentry-test")
async def sentry_test():
    if os.getenv("ENABLE_SENTRY_TEST_ROUTE") != "true":
        raise HTTPException(status_code=404)
    raise ValueError("Sentry smoke test")
```

Route disabled vĩnh viễn trên production khi không set env — có thể giữ trong codebase.

- [ ] Commit route debug lên `main` (Railway auto-deploy)
- [ ] Set `ENABLE_SENTRY_TEST_ROUTE=true` tạm trên Railway
- [ ] Gọi `GET https://<railway-domain>/health/sentry-test`, verify event xuất hiện trên sentry.io
- [ ] Xóa biến `ENABLE_SENTRY_TEST_ROUTE` khỏi Railway → route trở về 404

**Phần 2 — Frontend source maps**

Gọi `/health/sentry-test` chỉ test BE — stack trace FE sẽ không xuất hiện. Cần trigger lỗi từ browser:

```typescript
// Thêm tạm vào frontend/src/app/page.tsx hoặc dashboard page
// Bọc bằng guard tương tự để không ảnh hưởng production
<button onClick={() => { throw new Error("Sentry FE smoke test"); }}>
  Sentry Test
</button>
```

- [ ] Thêm button test vào trang dashboard (chỉ render khi `NEXT_PUBLIC_SENTRY_TEST=true`)
- [ ] Set `NEXT_PUBLIC_SENTRY_TEST=true` trên Vercel → redeploy
- [ ] Click button trên browser → verify FE event xuất hiện trên sentry.io
- [ ] Click vào event → stack trace phải show file/line rõ ràng (không phải bundle hash)
- [ ] Xóa biến `NEXT_PUBLIC_SENTRY_TEST` khỏi Vercel → **trigger redeploy** (biến là build-time, bundle cũ vẫn chứa button nếu không redeploy), revert code nếu không giữ guard lại

### E3. Setup UptimeRobot

> Không dùng keyword check "200 OK" vì `/health/ready` luôn trả 200 dù DB lỗi.
> Phải check nội dung body.

- [ ] uptimerobot.com → Add New Monitor
  - Monitor type: **Keyword**
  - URL: `https://<railway-domain>/health/ready`
  - Keyword: `"db":"ok"` (phải có trong body)
  - Interval: 5 phút
  - Alert contact: dragonball1997vntq@gmail.com
- [ ] Confirm monitor active, status green (keyword found)

---

## Sơ đồ thứ tự

```
A1 ──┐
A2 ──┼──► B1 ──► B2 ──► C1 ──► C2 ──► C3
A3 ──┘                               │
                                     ▼
                              D1 ──► D2 ──► D3 ──► D4*
                                               │
                                               ▼
                                    E1 ──► E2 ──► E3

* D4: chỉ chuẩn bị credential, không test OAuth flow
```

- A1/A2/A3 có thể làm song song.
- C2 deploy với CORS tạm → verify health C3 → sau đó D1 lấy Vercel domain → D3 update CORS.
- D4 không block E1 (OAuth chưa implement).

---

## Troubleshooting

### Supabase transaction pooler + asyncpg: prepared statement error

`DATABASE_URL` dùng transaction pooler (port 6543) — mỗi query có thể chạy trên connection khác nhau,
khiến asyncpg gặp lỗi khi cố reuse prepared statement từ connection cũ:

```
asyncpg.exceptions.InvalidSQLStatementNameError: prepared statement does not exist
```

Fix: thêm `prepared_statement_cache_size=0` vào connection string để tắt prepared statement cache:

```
postgresql+asyncpg://...?ssl=require&prepared_statement_cache_size=0
```

> Hiện `database.py` chưa set option này. Nếu gặp lỗi trên production, update `DATABASE_URL` trên Railway
> thêm param đó là đủ — không cần sửa code.

---

## Ước tính thời gian

| Nhóm | Thời gian |
|------|-----------|
| A (secrets) | ~30 phút |
| B (database) | ~20 phút |
| C (Railway) | ~30 phút |
| D (Vercel) | ~20 phút |
| E (test + monitor) | ~40 phút |
| **Tổng** | **~2.5 giờ** |
