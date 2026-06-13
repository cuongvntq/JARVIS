# J.A.R.V.I.S - Personal AI Assistant

Trợ lý cá nhân lấy cảm hứng từ J.A.R.V.I.S trong Iron Man, ưu tiên hỗ trợ đời sống hằng ngày bằng tiếng Việt: chat AI, todo, ghi chú, bộ nhớ cá nhân, nhắc nhở và dashboard.

> **Trạng thái hiện tại:** MVP 1 đã hoàn tất. Bản desktop Tauri cũng đã hoàn tất phase 1-4, gồm frontend local, FastAPI sidecar, local PostgreSQL và native OS notification cho reminder.

---

## App hiện có

```
Javis/
├── backend/          # FastAPI + SQLAlchemy async + LiteLLM + Alembic
├── frontend/         # Next.js 15 + React 19 + Tailwind + Tauri v2
├── docs/             # Tài liệu kiến trúc, API, sprint, desktop migration
├── scripts/          # Script build sidecar
├── .env.example      # Template environment variables
└── README.md
```

### Backend

- FastAPI API server, OpenAPI tại `/docs`.
- PostgreSQL + pgvector qua SQLAlchemy async.
- Alembic migrations.
- JWT access token + refresh token HttpOnly cookie.
- LiteLLM routing: Gemini primary, OpenAI fallback/tier routing.
- APScheduler cho reminder due-state.
- Sentry, request id middleware, unified error envelope.
- SlowAPI rate limit, có thể dùng Upstash Redis hoặc fallback in-memory.

### Frontend

- Next.js App Router, React 19, TypeScript.
- TanStack Query cho server state.
- Zustand cho auth state.
- Single-page app với sidebar: Dashboard, Chat, Todo, Notes, Reminders, Memory, Settings.
- Streaming chat qua SSE.
- In-app toast reminder và Tauri native notification.

### Desktop

- Tauri v2 desktop shell.
- Next.js static export chạy trong WebView.
- FastAPI backend chạy dạng PyInstaller sidecar trong release build.
- App config đọc `.env` từ `%APPDATA%\JARVIS\.env` khi chạy bản MSI.
- Installer output theo tài liệu: `frontend/src-tauri/target/release/bundle/msi/JARVIS_1.0.0_x64_en-US.msi`.

---

## Chức năng đã hoàn thành

### Auth

- Đăng ký, đăng nhập, đăng xuất.
- Refresh token rotation, refresh token lưu bằng HttpOnly cookie.
- `/auth/me` và cập nhật profile.
- Chỉnh tên người dùng, tên trợ lý, timezone, locale.

### Chat AI

- Chat với J.A.R.V.I.S bằng tiếng Việt.
- Streaming response qua SSE.
- Lưu conversation và message history.
- Danh sách hội thoại, xem chi tiết, đổi title, soft delete.
- Tool calling loop để AI thao tác todo, note, memory, reminder.
- Conversation summary background task khi hội thoại dài.

### Todo

- Tạo, xem, lọc, tìm kiếm todo.
- Filter: hôm nay, sắp tới, quá hạn, đã hoàn thành, tất cả.
- Complete/uncomplete.
- Xóa mềm.
- AI có thể tạo/list/update todo qua tool.

### Notes

- Tạo, sửa, xóa ghi chú.
- Tìm kiếm theo từ khóa.
- Pin/unpin note.
- AI có thể tạo và tìm ghi chú.

### Memory

- Lưu bộ nhớ cá nhân: fact, preference, rule, relation, goal, other.
- Semantic search bằng embedding.
- RAG: memory liên quan được inject vào system prompt trước khi chat.
- Soft delete memory.
- AI có thể lưu, tìm và quên memory theo yêu cầu.

### Reminders

- Tạo, xem, cập nhật, hủy, xóa reminder.
- Scheduler chuyển reminder đến hạn từ `pending` sang `due`.
- Frontend poll `/v1/reminders/due`.
- Người dùng dismiss toast để ack reminder sang `sent`.
- Native OS notification trong Tauri song song với in-app toast.
- AI có thể tạo và list reminder.

### Dashboard

- Thống kê todo hôm nay.
- Danh sách reminder sắp tới.
- Số lượng memory.
- Refresh thủ công.

### QA / Tooling

- Backend test suite bằng pytest.
- Frontend E2E bằng Playwright: auth, chat, dashboard, reminder.
- Vitest config cho frontend.
- Ruff, mypy strict, Biome, TypeScript typecheck.
- GitHub Actions CI có migration smoke test theo tài liệu sprint.

---

## Yêu cầu hệ thống

| Tool | Version | Mục đích |
|---|---:|---|
| Python | 3.12+ | Backend |
| Node.js | 22+ | Frontend |
| pnpm | 9+ | Frontend package manager |
| uv | latest | Python package manager |
| PostgreSQL | 15+ khuyến nghị | Database local |
| pgvector | installed | Memory semantic search |
| Rust | 1.77+ | Build Tauri desktop |
| WebView2 | Windows runtime | Tauri WebView |

---

## Environment

Tạo `.env` tại root project từ `.env.example`:

```powershell
Copy-Item .env.example .env
notepad .env
```

Các biến quan trọng:

```env
# Database
DATABASE_URL=postgresql+asyncpg://jarvis_user:local_pass@localhost:5432/jarvis
DATABASE_URL_DIRECT=postgresql://jarvis_user:local_pass@localhost:5432/jarvis

# LLM
GEMINI_API_KEY=...
OPENAI_API_KEY=...

# Auth
JWT_SECRET=your-random-secret-at-least-32-chars

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://tauri.localhost,https://tauri.localhost,tauri://localhost

# Optional
SENTRY_DSN=
UPSTASH_REDIS_URL=
APP_ENV=development
```

Frontend dev cần `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> Không thêm `/v1` vào `NEXT_PUBLIC_API_URL`; API client tự append `/auth/*` và `/v1/*`.

---

## Setup database local

Tạo database và user trong PostgreSQL:

```sql
CREATE DATABASE jarvis;
CREATE USER jarvis_user WITH PASSWORD 'local_pass';
GRANT ALL PRIVILEGES ON DATABASE jarvis TO jarvis_user;

\c jarvis
GRANT USAGE, CREATE ON SCHEMA public TO jarvis_user;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Chạy migration:

```powershell
cd backend
alembic upgrade head
```

---

## Chạy dev

### 1. Backend

```powershell
cd backend
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Backend chạy tại:

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 2. Frontend

Mở terminal khác:

```powershell
cd frontend
pnpm install
pnpm dev
```

Frontend chạy tại http://localhost:3000.

### 3. Tauri dev

Trong dev mode, Tauri không spawn sidecar; backend cần chạy riêng như bước trên.

```powershell
cd frontend
pnpm tauri dev
```

---

## Build desktop app

### 1. Build backend sidecar

```powershell
.\scripts\build-sidecar.ps1
```

Script build PyInstaller sidecar và copy binary vào `frontend/src-tauri/binaries/`.

### 2. Build Tauri installer

```powershell
cd frontend
pnpm tauri build
```

Sau khi cài MSI, tạo config user-local:

```powershell
New-Item -ItemType Directory -Force "$env:APPDATA\JARVIS"
Copy-Item ..\.env "$env:APPDATA\JARVIS\.env"
```

---

## Lệnh kiểm tra

### Backend

```powershell
cd backend
ruff check .
ruff format --check .
mypy app/
pytest
```

### Frontend

```powershell
cd frontend
pnpm check
pnpm typecheck
pnpm test
pnpm test:e2e
```

---

## API chính

| Area | Endpoints |
|---|---|
| Health | `GET /health`, `GET /health/ready` |
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET/PATCH /auth/me` |
| Chat | `POST /v1/chat/send`, `GET /v1/chat/conversations`, `GET/PATCH/DELETE /v1/chat/conversations/{id}` |
| Todo | `GET/POST /v1/todos`, `GET/PUT/DELETE /v1/todos/{id}`, `PATCH /complete`, `PATCH /uncomplete` |
| Notes | `GET/POST /v1/notes`, `GET/PATCH/DELETE /v1/notes/{id}`, `PATCH /pin`, `PATCH /unpin` |
| Memory | `GET/POST /v1/memories`, `POST /v1/memories/search`, `GET/PATCH/DELETE /v1/memories/{id}` |
| Reminders | `GET/POST /v1/reminders`, `GET /v1/reminders/due`, `POST /v1/reminders/{id}/ack`, `GET/PATCH/DELETE /v1/reminders/{id}`, `PATCH /cancel` |
| Dashboard | `GET /v1/dashboard/today` |

---

## Tài liệu quan trọng

| File | Nội dung |
|---|---|
| [docs/ai-context/01-architecture.md](./docs/ai-context/01-architecture.md) | Kiến trúc hiện tại |
| [docs/ai-context/02-folder-map.md](./docs/ai-context/02-folder-map.md) | Folder map |
| [docs/ai-context/04-database-schema.md](./docs/ai-context/04-database-schema.md) | Schema hiện tại |
| [docs/ai-context/05-api-contract.md](./docs/ai-context/05-api-contract.md) | API contract |
| [docs/ai-context/06-current-sprint.md](./docs/ai-context/06-current-sprint.md) | Trạng thái sprint mới nhất |
| [docs/ai-context/07-known-issues.md](./docs/ai-context/07-known-issues.md) | Known issues |
| [docs/migration-desktop-app.md](./docs/migration-desktop-app.md) | Desktop migration plan và lessons learned |
| [docs/beta-deploy-plan.md](./docs/beta-deploy-plan.md) | Beta deploy notes |

---

## Lưu ý hiện tại

- Google OAuth đã bị bỏ khỏi MVP 1, vẫn là backlog.
- LLM vẫn cần internet vì Gemini/OpenAI API không chạy local.
- Desktop build hiện giả định máy có local PostgreSQL + pgvector. Nếu muốn phân phối cho máy khác không cài PostgreSQL, cần phase riêng cho embedded DB hoặc SQLite/vector alternative.
- README backend/frontend có thể còn một số mô tả sprint cũ; README root này phản ánh trạng thái mới nhất của project.

---

## License

Personal project. All rights reserved.
