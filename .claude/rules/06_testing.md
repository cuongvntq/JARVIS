# Rules — Testing

## Backend (pytest)

- Mỗi API endpoint cần tối thiểu: **1 happy path + 1 error path** integration test.
- Test file đặt trong `backend/tests/`, mirror structure `app/`: `tests/routers/test_todos.py` cho `app/routers/todos.py`.
- Dùng **test database** thật (SQLite async hoặc Postgres test schema) — không mock DB session.
- Factory fixture cho test data (dùng `pytest-factoryboy` hoặc factory function thuần).
- Auth trong test: tạo test user + JWT token thật, không skip auth middleware.

## Frontend (vitest)

- Test utility functions trong `lib/` và custom hooks (`lib/hooks/`).
- Component test chỉ khi logic phức tạp — không test render đơn thuần.
- Mock API calls trong FE test bằng `msw` (Mock Service Worker).

## E2E (Playwright)

- Critical flows bắt buộc có E2E test:
  - Login (email/pass + Google) → Dashboard load.
  - Chat: gõ "Thêm việc mua sữa chiều nay" → todo xuất hiện trong list.
  - Đặt reminder → nhận notification (test headless với mock push).
  - Memory: lưu → retrieve đúng trong chat tiếp theo.
- E2E chạy trên môi trường staging, không production.

## Prompt Eval Set

- Trước mọi PR thay đổi system prompt hoặc tool schema: chạy **10 eval case** (xem docs/04).
- Pass rate target: ≥9/10. Fail → không merge.
- Eval script đặt tại `backend/tests/eval/test_prompt_eval.py`.
- Log kết quả eval vào file `eval_results/YYYYMMDD_HHMM.json` để track regression.

## Coverage

- Backend: target ≥70% line coverage cho `app/services/` và `app/routers/`.
- Không cần 100% — tập trung vào business logic, không test framework boilerplate.

## CI

- GitHub Actions chạy tự động khi push/PR: `ruff check`, `pytest`, `pnpm lint`, `pnpm typecheck`, `vitest`.
- E2E Playwright chạy riêng trên schedule (không block mọi PR — tốn thời gian).
- PR không được merge nếu CI fail.
