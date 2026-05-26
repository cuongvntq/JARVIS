# Rules — Database (PostgreSQL / Alembic)

## Query Boundaries

- **Không query DB trong controller (router).** Mọi DB access đều qua repository layer.
- **Transactions cho multi-write:** khi một request thực hiện ≥2 write operation (ví dụ: tạo todo + tạo notification), wrap trong cùng 1 transaction — nếu 1 cái fail thì rollback toàn bộ.
- **Tránh N+1 query:** không load relationship trong vòng lặp. Dùng `selectinload` / `joinedload` hoặc batch query.

```python
# SAI — N+1
todos = await repo.list_todos(user_id)
for todo in todos:
    tags = await repo.get_tags(todo.id)  # query mới mỗi vòng lặp

# ĐÚNG — 1 query với eager load
todos = await repo.list_todos_with_tags(user_id)  # selectinload tags
```

## Soft Delete

- Bảng có cột `deleted_at TIMESTAMPTZ` thì **không hard delete** — luôn set `deleted_at = NOW()`.
- Mọi query lấy active record phải filter: `WHERE deleted_at IS NULL`.
- Hard delete chỉ có ở cleanup job định kỳ (scheduled), không có trong API handler.
- Bảng không có `deleted_at` (ví dụ `messages`, `tool_execution_logs`): có thể hard delete theo retention policy.

## Primary Key & UUID

- Tất cả bảng dùng `UUID PRIMARY KEY DEFAULT uuid_generate_v4()`. Không dùng `SERIAL` / `BIGSERIAL`.
- Trong Python: dùng `uuid.UUID` type, không string. SQLAlchemy map sang `Uuid` type.

## Datetime

- Tất cả cột datetime dùng `TIMESTAMPTZ` (UTC). Không dùng `TIMESTAMP WITHOUT TIME ZONE`.
- Application layer chịu trách nhiệm convert sang timezone user — DB luôn lưu UTC.

## Migration

- Đặt tên file: `YYYYMMDDHHMM_mô_tả_ngắn.py` (ví dụ: `202605181500_add_summary_to_conversations.py`).
- Mỗi migration phải có cả `upgrade()` và `downgrade()`.
- **Không sửa migration đã chạy production** — luôn tạo migration mới.
- Chạy autogenerate: `alembic revision --autogenerate -m "mô tả"`, sau đó review kỹ file sinh ra trước khi apply.
- Dùng `DATABASE_URL_DIRECT` (port 5432) cho Alembic, không dùng pooler URL.

## Index

- Index bắt buộc trên: tất cả FK column, cột thường filter (`status`, `deleted_at`, `user_id`, `due_at`).
- Dùng partial index khi filter kết hợp `deleted_at IS NULL` (giảm kích thước index đáng kể).
- Full-text search: dùng GIN index với `pg_trgm` — không LIKE scan toàn bảng.
- Vector search: HNSW index với `vector_cosine_ops` trên cột `embedding`.

## Query Patterns

- Luôn filter `user_id = :current_user_id` trong mọi query — không để user truy cập data của user khác.
- Pagination: cursor-based (dùng `created_at` hoặc `id` làm cursor), không offset-based.
- Lấy reminder đến hạn: dùng `SELECT FOR UPDATE SKIP LOCKED` để tránh race condition giữa scheduler instances.

## JSONB

- Dùng `JSONB` cho `metadata` (dữ liệu linh hoạt, thay đổi theo thời gian).
- Không lưu trường thường xuyên filter/sort vào JSONB — đưa thành cột riêng có index.

## Extensions

Các extension bắt buộc enable trên Supabase: `uuid-ossp`, `pgcrypto`, `pg_trgm`, `vector`.
