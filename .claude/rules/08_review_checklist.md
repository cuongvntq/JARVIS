# Rules — Review Checklist

Dùng checklist này trước khi submit PR, merge branch, hoặc deploy lên staging/production.

---

## 1. Trước khi bắt đầu code (Pre-implementation)

- [ ] Đã đọc toàn bộ yêu cầu, hiểu rõ scope — không implement thêm gì ngoài yêu cầu.
- [ ] Đã tìm kiếm implementation hiện có (Grep/Glob) — không duplicate code.
- [ ] Đã kiểm tra docs liên quan: API spec (docs/02), schema (docs/01), tool schema (docs/03).
- [ ] Nếu cần thêm dependency mới → đã hỏi và được chấp thuận.
- [ ] Nếu cần thêm bảng/cột mới → đã kiểm tra docs/01 và sẽ tạo migration đúng cách.
- [ ] Nếu cần endpoint mới → đã kiểm tra docs/02, không tự bịa API không có trong spec.

---

## 2. Code Review — General

- [ ] Chỉ chỉnh sửa file liên quan trực tiếp đến task — không có file thay đổi ngoài phạm vi.
- [ ] Không có `TODO`, `FIXME`, `HACK` mới thêm vào mà không có issue track.
- [ ] Không có `print()`, `console.log()` debug còn sót.
- [ ] Không có code bị comment out (xóa hẳn, git history đã lưu rồi).
- [ ] Không có hardcode giá trị nên ở config (URL, timeout, model name, magic number).
- [ ] Logic mới đơn giản, không over-engineer cho requirement chưa tồn tại.

---

## 3. Code Review — Backend

### Layered Architecture
- [ ] Router chỉ validate + gọi service + trả response — không có DB query trong router.
- [ ] Service chứa toàn bộ business logic — không import `Request`/`Response` FastAPI.
- [ ] Repository chỉ có SQLAlchemy query — không có business logic.

### Async & DB
- [ ] Tất cả hàm DB và I/O là `async def` + `await` — không có blocking call.
- [ ] Dùng SQLAlchemy 2.0 style: `select()`, `session.execute()` — không dùng `session.query()`.
- [ ] Không N+1 query — relationship load qua `selectinload`/`joinedload` hoặc batch.
- [ ] Multi-write operation (≥2 bảng) wrap trong 1 transaction.
- [ ] Soft delete: set `deleted_at`, không hard delete (trừ retention job).
- [ ] Mọi query có filter `user_id = current_user.id` + `deleted_at IS NULL`.

### Pydantic & Types
- [ ] Dùng `model_validate()` thay `.from_orm()`, `.model_dump()` thay `.dict()`.
- [ ] Response schema tách riêng DB model — không expose SQLAlchemy object trực tiếp.
- [ ] Datetime: dùng `datetime.now(UTC)` — không dùng `datetime.utcnow()`.

### Error & Logging
- [ ] Lỗi trả về đúng format chuẩn: `{ "error": { "code", "message", "details", "request_id" } }`.
- [ ] Không có stack trace lộ ra response client.
- [ ] Log dùng `structlog` với context key rõ ràng — không dùng `print()`.
- [ ] Không log secret, token, password.

---

## 4. Code Review — Frontend

### Components & State
- [ ] Không tạo component mới nếu đã có component tương tự trong `components/`.
- [ ] `"use client"` chỉ thêm khi thực sự cần (event, hook, browser API) — không thêm thừa.
- [ ] State để local khi có thể — không đưa vào Zustand nếu chỉ dùng trong 1 component.
- [ ] Không prop drilling quá 3 level — dùng Tanstack Query cache hoặc Zustand.
- [ ] Không `useEffect` + raw `fetch` để load data — dùng Tanstack Query.

### TypeScript
- [ ] Không dùng `any` — dùng `unknown` + narrow hoặc type rõ ràng.
- [ ] API response types dùng đúng type từ `lib/types/api.ts`.
- [ ] `pnpm typecheck` pass không có lỗi.

### Datetime & i18n
- [ ] Hiển thị datetime luôn dùng timezone của user (`date-fns` + `formatInTimeZone`).
- [ ] Không dùng `new Date().toLocaleString()` trực tiếp — phụ thuộc locale browser, không nhất quán.

### Build & Lint
- [ ] `pnpm lint` pass (Biome).
- [ ] `pnpm typecheck` pass.
- [ ] Không có unused import.

---

## 5. Code Review — Database / Migration

- [ ] Migration file đặt tên đúng: `YYYYMMDDHHMM_mô_tả.py`.
- [ ] Migration có đủ `upgrade()` và `downgrade()`.
- [ ] `downgrade()` thực sự reverses `upgrade()` — không bỏ trống.
- [ ] Cột mới có index nếu thường xuyên filter/sort.
- [ ] FK mới có index.
- [ ] Không sửa migration đã tồn tại — tạo migration mới.
- [ ] Extension cần thiết (`vector`, `pg_trgm`) đã enable trước khi dùng.
- [ ] Partial index dùng đúng khi filter `deleted_at IS NULL`.

---

## 6. Code Review — AI / LLM

### Tool Schema
- [ ] Tool schema mới follow đúng format JSON Schema trong docs/03.
- [ ] Mọi datetime field trong tool schema có `"format": "date-time"` và mô tả UTC rõ ràng.
- [ ] `additionalProperties: false` có trong tất cả tool schema.
- [ ] `required` chỉ chứa field thực sự bắt buộc.

### Orchestrator
- [ ] `search_memory` được gọi trước khi call LLM — không bỏ qua bước RAG.
- [ ] Hard cap 5 tool call/turn được enforce — không bỏ giới hạn.
- [ ] Retry tối đa 2 lần/tool — không retry vô hạn.
- [ ] Mọi tool execution log vào `tool_execution_logs` kể cả khi fail.

### Prompt
- [ ] System prompt lấy từ template file (`prompts/system.j2`) — không hardcode trong code.
- [ ] User context inject đầy đủ: `user_name`, `timezone`, `now_utc`, `now_local`.
- [ ] Memory content viết ngôi thứ ba: "Người dùng..." không phải "Tôi...".
- [ ] `prompt_version` được lưu vào `messages.metadata`.

### Prompt Eval (chỉ khi thay đổi prompt/tool schema)
- [ ] Chạy 10 eval case trong `tests/eval/test_prompt_eval.py`.
- [ ] Pass rate ≥ 9/10 — nếu không đạt thì không merge.
- [ ] Kết quả eval lưu vào `eval_results/YYYYMMDD_HHMM.json`.

---

## 7. Code Review — Security

- [ ] Không có secret/key/token nào trong diff.
- [ ] Không có raw SQL string concatenation với user input.
- [ ] Mọi endpoint cần auth đã có JWT middleware — không endpoint nào bị bỏ sót.
- [ ] Authorization check: query có filter `user_id = current_user.id`.
- [ ] Input validation chỉ ở boundary (Pydantic/Zod) — không duplicate validate ở nhiều layer.
- [ ] Không `allow_origins=["*"]` trong CORS config.
- [ ] Rate limit middleware áp dụng cho endpoint mới.

---

## 8. Testing

- [ ] Endpoint mới có test: ít nhất 1 happy path + 1 error path.
- [ ] Test không mock DB — dùng test database thật.
- [ ] `pytest` pass toàn bộ.
- [ ] `vitest` pass toàn bộ.
- [ ] Coverage không giảm so với trước.

---

## 9. Trước khi Deploy (Pre-deploy Checklist)

### Code & Build
- [ ] CI pipeline xanh toàn bộ (lint + typecheck + test).
- [ ] Build production không có warning nghiêm trọng: `pnpm build` (FE), `uvicorn` start sạch (BE).
- [ ] Không có migration chưa apply trên staging DB.

### Config & Secrets
- [ ] Tất cả env var cần thiết đã set trên môi trường target (Railway / Vercel).
- [ ] Không có giá trị dev/local lọt vào production config.
- [ ] CORS origin config đúng với domain production.
- [ ] `APP_ENV=production` được set.

### Database
- [ ] Migration đã test `downgrade` thủ công trên staging — rollback được nếu cần.
- [ ] Không có migration nào phá vỡ backward compatibility trong rolling deploy.
- [ ] Backup gần nhất của DB còn hợp lệ (kiểm tra Supabase dashboard).

### LLM & AI
- [ ] API key LLM còn hạn và đủ quota (Gemini: kiểm tra aistudio.google.com, OpenAI: platform.openai.com).
- [ ] LLM timeout config hợp lý cho production load.
- [ ] Prompt eval 10 case đã pass lần cuối trước deploy.

### Observability
- [ ] Sentry DSN được set — test error tracking hoạt động.
- [ ] Structlog output sang JSON (production mode).
- [ ] Health endpoint `/health/ready` trả `200` sau deploy.
- [ ] UptimeRobot monitor đang active cho domain production.

### Notification
- [ ] VAPID keys giống với keys đã dùng để tạo subscription của user (không regenerate).
- [ ] APScheduler reminder job start thành công — kiểm tra log startup.

---

## 10. Sprint Completion Checklist

Dùng khi kết thúc mỗi sprint:

- [ ] Tất cả DoD (Definition of Done) của sprint đã pass.
- [ ] Prompt eval set ≥9/10 pass.
- [ ] Không có P0/P1 bug mở.
- [ ] API thay đổi đã cập nhật docs/02.
- [ ] DB schema thay đổi đã cập nhật docs/01.
- [ ] Tool schema thay đổi đã cập nhật docs/03.
- [ ] CLAUDE.md / rules cập nhật nếu có convention mới.
- [ ] Backlog MVP 2+ được cập nhật với idea mới phát sinh trong sprint.
- [ ] Cost LLM của sprint được ghi nhận (token in/out từ `messages.metadata`).
