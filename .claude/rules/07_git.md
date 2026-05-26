# Rules — Git & PR Workflow

## TUYỆT ĐỐI — Bảo vệ nhánh main

- **KHÔNG BAO GIỜ push trực tiếp lên `main`** — kể cả hotfix, kể cả thay đổi nhỏ.
- **Trước bất kỳ thao tác git làm thay đổi local/remote state hoặc history** (commit, push, merge, rebase, reset, branch -D, ...) — phải hỏi user và được xác nhận rõ ràng trước khi thực hiện.
- **Read-only commands được phép chạy tự do** mà không cần hỏi: `git status`, `git diff`, `git log`, `git show`, `git branch` (liệt kê), `git fetch` (chỉ fetch, không merge).
- Nếu user nói "tự làm đi" hoặc "cứ push" mà không chỉ định nhánh cụ thể — vẫn phải hỏi lại, không tự suy diễn là push lên `main`.

## Workflow bắt buộc

Mọi thay đổi trong repo (code, docs, config, rules) đều phải đi theo thứ tự sau, không được bỏ bước:

```
1. Tạo nhánh mới từ main
      git status                      # kiểm tra worktree sạch trước
      git switch main
      git pull --ff-only              # fast-forward only, không tạo merge commit
      git switch -c feat/sprint1-auth-jwt

2. Commit lên nhánh đó
      git add <files>
      git commit -m "feat(auth): ..."

3. Push nhánh lên remote
      git push -u origin feat/sprint1-auth-jwt

4. Tạo Pull Request (PR) trên GitHub
      gh pr create --title "..." --body "..."

5. Chờ review — KHÔNG tự merge
      Người khác (hoặc user) review và approve trên GitHub

6. Merge vào main SAU KHI được approve
      Thực hiện merge trên GitHub UI, không merge bằng CLI trừ khi được yêu cầu rõ ràng
```

## Quy tắc hỏi trước khi làm

Với các thao tác sau, **bắt buộc mô tả rõ hành động và hỏi user xác nhận** trước khi chạy lệnh:

| Thao tác | Lý do phải hỏi |
|----------|---------------|
| `git push` bất kỳ | Ảnh hưởng remote, không thể undo dễ |
| `git push --force` / `--force-with-lease` | Có thể ghi đè history của người khác |
| `gh pr create` | Tạo PR công khai, cần confirm nội dung |
| `gh pr merge` | Merge vào main — không thể undo dễ |
| `git reset --hard` | Xóa uncommitted work |
| `git rebase` | Rewrite history |
| `git branch -D` | Xóa nhánh |

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
