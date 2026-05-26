# Rules — Git & PR Workflow

## Branch Naming

```
feat/sprint1-auth-jwt
feat/sprint2-todo-tool
fix/reminder-scheduler-timezone
chore/update-deps-may2026
docs/add-api-examples
```

Format: `<type>/<sprint hoặc context>-<mô tả-ngắn>` dùng kebab-case.

## Commit Message

```
feat(auth): add JWT refresh token rotation
fix(scheduler): handle timezone edge case for remind_at
chore(deps): bump litellm to 1.40.0
```

Format: `<type>(<scope>): <mô tả ngắn tiếng Anh, động từ hiện tại>`.
Scope: `auth`, `chat`, `todo`, `note`, `reminder`, `memory`, `dashboard`, `llm`, `db`, `scheduler`, `fe`, `deps`.

## Pre-commit Checklist (bắt buộc trước khi commit)

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
```

## PR Checklist

Trước khi tạo PR:
- [ ] Tests pass (CI xanh).
- [ ] Không có secret/key trong diff.
- [ ] Nếu đổi API: cập nhật docs/02_API_Specification.md.
- [ ] Nếu đổi DB schema: có migration file đầy đủ (up + down).
- [ ] Nếu đổi system prompt hoặc tool schema: eval set 10 case ≥9/10 pass.
- [ ] Nếu đổi tool JSON schema: cập nhật docs/03_AI_Tool_Schemas.md.

## Những gì KHÔNG được commit

- `.env` — đã có trong `.gitignore`.
- `*.pyc`, `__pycache__/`, `.venv/`, `node_modules/` — đã có trong `.gitignore`.
- API key, JWT secret, VAPID key ở bất kỳ dạng nào (kể cả trong comment).
- File log, file test output, coverage report.
- File IDE cá nhân (`.idea/`, `.vscode/settings.json` cá nhân — chỉ commit extension recommendations).

## Gitignore bổ sung cần có

```
# Đảm bảo có trong .gitignore
.env
.env.local
*.log
backend/.venv/
backend/__pycache__/
backend/.pytest_cache/
backend/htmlcov/
frontend/node_modules/
frontend/.next/
frontend/out/
eval_results/
```
