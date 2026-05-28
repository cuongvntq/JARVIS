# Known Issues & Tech Debt

## Active Limitations (Sprint 2)

### Streaming not supported
- `POST /v1/chat/send` với `stream: true` → 422 `stream_not_supported`
- Vercel AI SDK `useChat` deferred to Sprint 3
- **Workaround:** client sends `stream: false`

### No rate limiting
- Endpoints không có rate limit middleware
- Planned: 60 req/min/user (normal), 20 req/min/user (`/v1/chat/send`)
- **Sprint 5**

### No idempotency keys
- POST /todos, /notes, /memories không có Idempotency-Key support
- **Post-MVP 1**

### conversation.updated_at không auto-update trong SQLite test env
- Postgres: có trigger `trg_conv_updated_at` (migration 002) — `updated_at` tự update khi bất kỳ UPDATE nào xảy ra
- SQLite (test): không có DB trigger → `updated_at` không tự update khi `increment_message_count` chạy
- **SQLite-only issue, không ảnh hưởng production**

### message_count double-increment
- `chat_service.py` calls `increment_message_count` twice (user + assistant)
- This is intentional but fragile — should be a single call with increment=2 or transactional
- **Tech debt, low priority**

### No conversation auto-title
- Conversation title mãi là "Cuộc hội thoại mới"
- Auto-title from first message not implemented
- **Sprint 3**

### Memory/RAG placeholder
- `build_system_prompt()` nhận `memories` param nhưng không có search_memory call
- Hiện tại inject "(Không có memory liên quan.)"
- **Sprint 4**

### Conversation summary not implemented
- `conversation_summary` param trong `build_system_prompt()` unused
- Auto-summarize khi >20 messages: **Sprint 4**

---

## SQLite Test Compatibility Notes

Những chỗ có special handling cho SQLite (test env) vs Postgres (production):

| Issue | SQLite workaround | File |
|---|---|---|
| PostgreSQL UUID type | `sa.Uuid` instead of `postgresql.UUID` | All models |
| JSONB | `sa.JSON` | All models |
| ENUM CREATE TYPE | `create_type=False` | Models with ENUMs |
| Boolean server_default | Both `default=True` AND `server_default="true"` | `models/user.py` |
| pool_size/max_overflow | Skipped for SQLite (StaticPool) | `database.py` |
| TEXT[] arrays | `sa.JSON` (both envs use JSON now) | `models/todo.py` |
| RETURNING clause | Works in SQLite 3.35+ (aiosqlite) | `auth_repo.py` |

---

## Security Notes (known gaps)

### VAPID keys not configured in dev
- Web push not testable locally without VAPID keys
- Sprint 5

### No Sentry error tracking
- `structlog` logs to stdout only
- Sentry DSN integration: Sprint 6 (pre-deploy)

### No Redis (optional)
- Idempotency keys, rate limiting, session cache: require Redis (Upstash)
- Currently all in-memory or DB-backed

### refresh_token not hashed in test
- Tests use raw token strings via body (not cookie)
- Hash logic is correct in production flow

---

## Performance Notes

### N+1 potential
- `list_conversations` không load messages — acceptable (messages loaded per conversation)
- `list_todos` không load related data — acceptable (flat table)

### LLM timeout
- Classifier: 3s hard timeout (asyncio.wait_for)
- Main LLM call: 30s (`settings.llm_timeout_seconds`)
- No streaming = user waits full response time (Sprint 3 addresses with SSE)

---

## Frontend Known Issues

### No error boundary
- API errors in hooks không được displayed properly
- **Sprint 3**

### No optimistic update cho assistant response
- User message được append ngay lập tức (optimistic) tại `ChatInterface.tsx:74`
- Assistant response vẫn phải chờ full response từ server — không streaming
- **Sprint 3** (fix with SSE streaming)

### Token refresh race condition
- Multiple simultaneous 401 responses could trigger multiple refresh attempts
- `api.ts` silentRefresh() không có mutex
- **Acceptable for now** (JWT TTL 15 min; unlikely in practice)

---

## Tech Debt Backlog

| Item | Priority | Sprint |
|---|---|---|
| Streaming chat (SSE) | High | 3 |
| Auto-title conversation from first message | Medium | 3 |
| Rate limiting middleware | High | 5 |
| Sentry integration | Medium | 6 |
| Redis for idempotency + rate limit | Medium | 5 |
| 4-tier LLM routing | Low | 6 |
| Playwright E2E tests | Medium | 6 |
| Eval set automation (10 cases) | High | 6 |
| Frontend vitest unit tests | Low | 3+ |
| Conversation auto-summarize | Medium | 4 |
| Updated_at trigger (DB-level) | Low | next migration |
