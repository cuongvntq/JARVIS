# Rules — Backend (FastAPI / Python)

## Layered Architecture

Controller → Service → Repository. Mỗi layer chỉ làm đúng một việc:

- **Controller (router):** validate request, gọi service, trả response. Không chứa business logic, không query DB trực tiếp.
- **Service:** toàn bộ business logic, orchestration, gọi repository. Không biết về HTTP request/response.
- **Repository:** chỉ chứa DB query (SQLAlchemy). Không có business logic, không gọi service khác.

```
app/routers/todos.py      ← controller: parse request, call service
app/services/todo.py      ← service: business logic
app/repositories/todo.py  ← repository: DB queries only
```

## Async

- Tất cả hàm xử lý request, DB, LLM đều phải `async def` + `await`. Không dùng blocking I/O trong async context.
- Database session luôn qua dependency injection: `session: AsyncSession = Depends(get_session)`. Không tự tạo session thủ công trong router.

## SQLAlchemy 2.0

- Dùng `select(Model)`, `await session.execute(...)`, `await session.scalar(...)` — **không dùng** `session.query()` (SQLAlchemy 1.x style).
- Luôn `await session.commit()` sau write, `await session.refresh(obj)` để lấy data sau insert.
- Relationship load: dùng `selectinload` / `joinedload` khi cần — không để N+1 query.

## Pydantic v2

- Mọi request body và response đều là Pydantic model.
- Dùng `Model.model_validate(obj)` thay `.from_orm()`, dùng `.model_dump()` thay `.dict()`.
- Response schema tách riêng khỏi DB model (không trả raw SQLAlchemy object).

## Datetime

- **Luôn dùng UTC.** Tạo datetime bằng `datetime.now(UTC)` hoặc `datetime.now(timezone.utc)`.
- **Không dùng** `datetime.utcnow()` — deprecated, trả về naive datetime.
- Convert sang timezone user chỉ khi format response hiển thị cho FE, không lưu vào DB.

## Settings & Config

- Lấy config qua `get_settings()` (cached singleton). **Không dùng** `os.environ.get()` trực tiếp trong business logic.
- Không hardcode giá trị config (port, model name, timeout) — tất cả qua `Settings`.

## Logging

- Dùng `structlog.get_logger()` — **không dùng** `print()` hoặc stdlib `logging.getLogger()`.
- Log JSON (structlog tự xử lý). Thêm context key rõ ràng: `log.info("todo.created", todo_id=str(todo.id), user_id=str(user_id))`.
- **Không log** secret, token, password, API key.

## Error Responses

- Tất cả lỗi trả về theo format chuẩn (docs/02): `{ "error": { "code", "message", "details", "request_id" } }`.
- Dùng `HTTPException` với custom handler, hoặc raise custom exception class → middleware bắt.
- Không để stack trace rò ra response client (log server-side, trả về `internal_error`).

## Router Structure

- Mỗi domain một file router trong `app/routers/` (todos.py, notes.py, ...).
- Business logic để trong `app/services/` — router chỉ validate + gọi service + trả response.
- Service gọi repository trong `app/repositories/` cho DB queries.

## Dependency Injection

- Auth middleware kiểm tra JWT và inject `current_user: User = Depends(get_current_user)`.
- Không gọi verify JWT trong từng endpoint riêng lẻ.
