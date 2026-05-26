# Rules — Security

## Secrets & Credentials

- **Không bao giờ commit** `.env`, API key, JWT secret, VAPID key vào git.
- Không log token, password, API key — kể cả trong debug/test.
- Mọi secret qua `get_settings()` — không hardcode string trong source code.
- Không đặt secret trong comment, tên biến rõ ràng, hay test fixture checked vào git.

## Input Validation

- Validate input **chỉ tại boundary** (Pydantic schema ở router layer, Zod ở FE form).
- Không validate lại ở service/repository layer cho cùng một dữ liệu.
- Không tự viết regex validate email/UUID — dùng Pydantic `EmailStr`, `UUID` type.

## SQL Injection

- **Không concatenate user input vào SQL string.** Mọi query đều qua SQLAlchemy ORM hoặc parameterized query (`text("... WHERE id = :id").bindparams(id=...)`).
- Không dùng `f"SELECT ... WHERE name = '{user_input}'"` dù là quick-fix tạm.

## Authentication & Authorization

- JWT access token TTL: 15 phút. Refresh token TTL: 30 ngày, rotating (mỗi lần dùng cấp mới, cũ bị revoke).
- Lưu refresh token dưới dạng hash (`bcrypt` hoặc `SHA-256`) trong DB — không lưu raw token.
- Mọi endpoint (trừ `/health`, `/auth/login`, `/auth/register`, `/auth/google`) đều cần JWT.
- **Authorization check**: mọi query DB phải filter `user_id = current_user.id` — không tin tưởng ID trong request body.
- Không trả về data của user khác dù có ID hợp lệ → `403 forbidden`.

## CORS

- Chỉ allow origin từ `settings.cors_origins_list` (parse từ env `BACKEND_CORS_ORIGINS`).
- Không set `allow_origins=["*"]` trong production.

## Rate Limiting

- 60 req/phút/user cho endpoint thông thường.
- 20 req/phút/user cho `/v1/chat/send` (tốn token LLM).
- Trả về `429` kèm header `Retry-After`.

## Error Exposure

- Không expose stack trace, internal path, SQL query trong response client.
- Log đầy đủ server-side (structlog), trả về `{ "error": { "code": "internal_error", "message": "..." } }` cho 5xx.
- `request_id` trong mọi response — để trace log mà không cần expose detail.

## XSS

- FE: React tự escape JSX content. Không dùng `dangerouslySetInnerHTML` trừ khi content đã sanitize (dùng DOMPurify).
- Markdown từ notes/memory: render qua sanitizer trước khi display.

## Idempotency

- Endpoint POST quan trọng (`/todos`, `/reminders`, `/memories`) hỗ trợ `Idempotency-Key` header (UUID, TTL 24h, cache bằng Redis).
- Trả về `409 idempotency_conflict` nếu key đã dùng với payload khác.

## Web Push

- VAPID keys: generate 1 lần, lưu vào env. Không regenerate tùy tiện (sẽ invalid subscription cũ).
- Subscription data của user lưu encrypted hoặc chỉ lưu endpoint + keys hash.
