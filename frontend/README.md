# JARVIS Frontend

Frontend cho J.A.R.V.I.S Personal AI Assistant. App hiện là single-page product UI chạy bằng Next.js, đồng thời được export static để đóng gói trong Tauri desktop.

---

## Stack

- Next.js 15 App Router
- React 19 + TypeScript
- Tailwind CSS 4
- TanStack Query
- Zustand
- Sonner toast
- Lucide icons
- Sentry Next.js
- Tauri v2 desktop shell
- Vitest + Playwright E2E
- Biome lint/format

---

## Setup

Chạy từ thư mục `frontend/`:

```powershell
pnpm install
```

Tạo `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Không thêm `/v1` vào cuối URL. API client tự gọi `/auth/*` và `/v1/*`.

Chạy dev server:

```powershell
pnpm dev
```

Frontend chạy tại http://localhost:3000. Backend cần chạy riêng tại http://localhost:8000.

---

## App Sections

Sidebar hiện có các section:

- Dashboard: thống kê todo hôm nay, reminder sắp tới, memory count.
- Chat: streaming chat với J.A.R.V.I.S, conversation history.
- Todo: quản lý todo, filter/search, complete/uncomplete.
- Notes: tạo/sửa/xóa note, pin/unpin, search.
- Reminders: tạo/sửa/hủy/xóa reminder, hiển thị reminder đến hạn.
- Memory: quản lý memory dài hạn và semantic search.
- Settings: profile, tên trợ lý, timezone, locale.

---

## Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # QueryProvider + AuthGuard + ReminderPolling
│   │   ├── page.tsx                # Single-page section navigation
│   │   ├── auth/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── auth/
│   │   ├── chat/
│   │   ├── dashboard/
│   │   ├── layout/
│   │   ├── memories/
│   │   ├── notes/
│   │   ├── reminders/
│   │   ├── settings/
│   │   └── todos/
│   ├── hooks/                      # TanStack Query hooks
│   ├── lib/
│   │   ├── api.ts                  # API client + SSE stream parser
│   │   ├── queryClient.ts
│   │   └── types/api.ts
│   ├── providers/
│   └── stores/
├── e2e/                            # Playwright specs
├── src-tauri/                      # Tauri v2 desktop shell
├── package.json
├── next.config.ts                  # output: "export"
├── playwright.config.ts
├── vitest.config.ts
└── biome.json
```

---

## Commands

```powershell
pnpm dev           # Next.js dev server
pnpm build         # Static export build for production/Tauri
pnpm start         # Next production server, mostly for web mode
pnpm lint          # Biome lint
pnpm format        # Biome format --write
pnpm check         # Biome check
pnpm typecheck     # TypeScript check
pnpm test          # Vitest
pnpm test:e2e      # Playwright E2E
pnpm test:e2e:ui   # Playwright UI
```

Tauri CLI is installed as a dev dependency, so these are available:

```powershell
pnpm tauri dev
pnpm tauri build
```

---

## Tauri Desktop

`next.config.ts` uses:

```ts
output: "export";
images: { unoptimized: true }
```

In Tauri dev mode, backend is not spawned by Tauri; run backend separately:

```powershell
cd ..\backend
uvicorn app.main:app --reload --port 8000
```

Then:

```powershell
cd ..\frontend
pnpm tauri dev
```

For release build, first build/stage the backend sidecar from repo root:

```powershell
.\scripts\build-sidecar.ps1
```

Then build installer:

```powershell
cd frontend
pnpm tauri build
```

Installed MSI expects backend config at:

```text
%APPDATA%\JARVIS\.env
```

---

## API Client

`src/lib/api.ts` handles:

- Bearer access token injection.
- Silent refresh on `401`.
- Refresh cookie via `credentials: "include"`.
- JARVIS error envelope parsing.
- Chat SSE stream parsing.
- CRUD methods for conversations, todos, notes, memories, reminders and dashboard.

---

## Reminder Notifications

`useReminderPolling` polls due reminders while the app is open:

- `GET /v1/reminders/due`
- Shows Sonner in-app toast.
- Sends Tauri native OS notification when permission is available.
- Calls `POST /v1/reminders/{id}/ack` when user dismisses/acks.

This replaces the old web push flow.

---

## E2E

Playwright specs live in `e2e/`:

- `auth.spec.ts`
- `chat.spec.ts`
- `dashboard.spec.ts`
- `reminder.spec.ts`

Run:

```powershell
pnpm test:e2e
```

Backend must be available and test env/database must be configured for reliable E2E runs.
