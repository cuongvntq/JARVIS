# J.A.R.V.I.S — Personal AI Assistant

Trợ lý cá nhân lấy cảm hứng từ J.A.R.V.I.S trong Iron Man, hỗ trợ đời sống hằng ngày bằng tiếng Việt.

> **Trạng thái:** MVP1 — Sprint 0 (setup foundation).

---

## Kiến trúc

```
Javis/
├── backend/          # FastAPI + SQLAlchemy + LiteLLM
├── frontend/         # Next.js 15 + React 19 + Tailwind + shadcn/ui
├── docs/             # Tài liệu kỹ thuật (6 file, đọc theo thứ tự)
├── .env.example      # Template environment variables
├── .gitignore
└── README.md         # File này
```

---

## Yêu cầu hệ thống

| Tool | Version | Cài đặt |
|------|---------|---------|
| Python | 3.12+ | https://www.python.org/downloads/ |
| Node.js | 22+ | https://nodejs.org |
| pnpm | 9+ | `npm install -g pnpm` |
| uv (Python pkg manager) | latest | `pip install uv` hoặc `pipx install uv` |
| Git | any | https://git-scm.com |
| VS Code | latest | https://code.visualstudio.com |

---

## Setup nhanh (lần đầu)

### Bước 1 — Clone & mở VS Code

```powershell
# Trong thư mục C:\Users\Admin\Desktop\Javis
code .
```

### Bước 2 — Đăng ký các service (free, không cần card)

| Service | Link | Mục đích | Lưu vào env |
|---------|------|----------|-------------|
| Google AI Studio | https://aistudio.google.com/apikey | Gemini API key (FREE 1500/ngày) | `GEMINI_API_KEY` |
| OpenAI Platform | https://platform.openai.com | Fallback model + có $5 free credit | `OPENAI_API_KEY` |
| Supabase | https://supabase.com | Postgres + pgvector (FREE 500MB) | `DATABASE_URL` |
| Google Cloud Console | https://console.cloud.google.com | OAuth client (login Google) | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |

### Bước 3 — Tạo file `.env`

```powershell
# Tại root project
Copy-Item .env.example .env
# Mở .env và điền các key đã lấy ở Bước 2
notepad .env
```

### Bước 4 — Setup Backend

```powershell
cd backend
uv venv                          # Tạo virtualenv
.venv\Scripts\activate           # Kích hoạt (PowerShell)
uv pip install -e ".[dev]"       # Cài deps
alembic upgrade head             # Chạy migration
uvicorn app.main:app --reload    # Chạy dev server
```

→ Backend chạy tại http://localhost:8000
→ OpenAPI docs tự sinh tại http://localhost:8000/docs

### Bước 5 — Setup Frontend

Mở terminal mới:

```powershell
cd frontend
pnpm install                     # Cài deps
pnpm dev                         # Chạy dev server
```

→ Frontend chạy tại http://localhost:3000

---

## Cấu trúc môi trường

### `.env` (root, dùng chung)
- `DATABASE_URL` — Supabase Postgres connection string
- `GEMINI_API_KEY` — Google AI Studio key
- `OPENAI_API_KEY` — OpenAI key (fallback)
- `ANTHROPIC_API_KEY` — (optional) Claude key cho fallback chain
- `JWT_SECRET` — random string ≥ 32 ký tự
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth

### `frontend/.env.local`
- `NEXT_PUBLIC_API_URL` — URL Backend (mặc định `http://localhost:8000`)

---

## VS Code Extensions khuyến nghị

Mở VS Code → Cmd/Ctrl+Shift+X → cài:

- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Ruff** (charliermarsh.ruff)
- **ESLint** (dbaeumer.vscode-eslint)
- **Biome** (biomejs.biome)
- **Tailwind CSS IntelliSense** (bradlc.vscode-tailwindcss)
- **Prisma** (Prisma.prisma) — optional, nếu xem SQL syntax
- **dotenv** (mikestead.dotenv)
- **Error Lens** (usernamehw.errorlens)
- **GitLens** (eamodio.gitlens)

Hoặc đơn giản: VS Code sẽ tự gợi ý cài khi mở project (do có file `.vscode/extensions.json`).

---

## Workflow phát triển

### Mỗi ngày
1. `git pull` (nếu làm nhóm)
2. Bật 2 terminal: backend (`uvicorn`) + frontend (`pnpm dev`).
3. Mở browser http://localhost:3000.
4. Code, hot reload tự update.

### Trước khi commit
```powershell
# Backend
cd backend
ruff check . --fix
ruff format .
pytest

# Frontend
cd ../frontend
pnpm lint
pnpm typecheck
pnpm test
```

### Tạo migration mới (khi đổi DB schema)
```powershell
cd backend
alembic revision --autogenerate -m "add field xyz to todos"
alembic upgrade head
```

---

## Roadmap

Đọc chi tiết tại [`docs/06_Updated_Execution_Plan.md`](./docs/06_Updated_Execution_Plan.md).

- **Sprint 0** (đang ở đây): Setup hạ tầng, env, repo structure.
- **Sprint 1:** Auth + Chat 1 chiều với Gemini.
- **Sprint 2:** Tool router + 3 todo tool + LLM fallback chain.
- **Sprint 3:** Todo UI + Note module.
- **Sprint 4:** Memory + RAG.
- **Sprint 5:** Reminder + Dashboard + In-app notification polling.
- **Sprint 6:** QA, polish, deploy beta.

---

## Tài liệu

| File | Nội dung |
|------|----------|
| [01_Database_Schema_ERD.md](./docs/01_Database_Schema_ERD.md) | DB schema, ERD, SQL DDL |
| [02_API_Specification.md](./docs/02_API_Specification.md) | REST API endpoints, error codes |
| [03_AI_Tool_Schemas.md](./docs/03_AI_Tool_Schemas.md) | 11 tool JSON Schema cho LLM |
| [04_System_Prompt.md](./docs/04_System_Prompt.md) | Production system prompt |
| [05_Tech_Stack_Decision.md](./docs/05_Tech_Stack_Decision.md) | Stack chốt + cost |
| [05a_LLM_Provider_Comparison.md](./docs/05a_LLM_Provider_Comparison.md) | So sánh OpenAI vs Anthropic |
| [05b_Ollama_Local_LLM_Analysis.md](./docs/05b_Ollama_Local_LLM_Analysis.md) | Phân tích Ollama local |
| [05c_Tiered_Routing_Strategy.md](./docs/05c_Tiered_Routing_Strategy.md) | LLM router code |
| [06_Updated_Execution_Plan.md](./docs/06_Updated_Execution_Plan.md) | Plan 6 sprint chi tiết |

---

## Troubleshooting

### Backend không chạy được
- Check Python version: `python --version` (cần 3.12+).
- Activate venv: `.venv\Scripts\activate` (PowerShell) hoặc `source .venv/bin/activate` (Mac/Linux).
- Database connection fail → check `DATABASE_URL` trong `.env`.

### Frontend không chạy được
- Check Node version: `node -v` (cần 22+).
- Xóa `node_modules` + `pnpm install` lại.
- Port 3000 đã dùng → `pnpm dev -p 3001`.

### LLM call fail
- Check Gemini API key tại https://aistudio.google.com/apikey.
- Check OpenAI credit tại https://platform.openai.com/usage.
- Xem log tại `backend/logs/` hoặc terminal output.

---

## License

Personal project. All rights reserved.
