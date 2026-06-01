# Known Issues & Tech Debt

## Resolved (for reference)

| Issue | Fixed in | How |
|---|---|---|
| Streaming not supported | Sprint 3 (PR #7) | SSE `stream_message()` + `StreamingResponse` |
| No conversation auto-title | Sprint 3 (PR #5) | `chat_service.py` sets title from first message |
| Memory/RAG placeholder | Sprint 4 (PR #15) | `_build_prompt_with_rag()` + `save/search/forget_memory` tools |
| Frontend no error boundary for editor | Sprint 4 (PR #14/#15) | `validationError` state + try/catch in Notes & Memory editors |
| No optimistic assistant response | Sprint 3 (PR #7) | SSE streaming shows delta in real time |
| HTTPException returns `{ detail }` (not unified envelope) | Sprint 4 (PR #15 review) | `http_exception_handler` registered in `main.py` |
| No rate limiting | Sprint 5 (PR #18) | SlowAPI middleware: 60/min general, 20/min chat |
| PATCH null on NOT NULL field → 500 | Sprint 5 (PR #25 review) | `field_validator(mode="before")` in NoteUpdate/ReminderUpdate → 422 |
| Auth state not cleared after session expiry | Sprint 5 (PR #25 review) | `clearAuth()` + `_accessToken=null` on silentRefresh fail |
| `experimental.typedRoutes` deprecated warning | Sprint 5 (PR #25 review) | Moved to top-level `typedRoutes: true` in next.config.ts |

---

## Active Limitations

### No idempotency keys
- POST /todos, /notes, /memories không có Idempotency-Key support
- **Post-MVP 1**

### conversation.updated_at không auto-update trong SQLite test env
- Postgres: có trigger `trg_conv_updated_at` (migration 002)
- SQLite (test): không có DB trigger → `updated_at` không tự update
- **SQLite-only issue, không ảnh hưởng production**

### message_count double-increment
- `chat_service.py` calls `increment_message_count` twice (user + assistant)
- Intentional but fragile — should be single call with increment=2 or transactional
- **Tech debt, low priority**

### Conversation summarization not implemented
- `build_system_prompt()` nhận `summary` param nhưng never passed
- Auto-summarize khi >20 messages: **Sprint 6**

### RAG end-to-end requires real Postgres
- `memory_repo.semantic_search()` trả `[]` trên SQLite
- Unit tests mock semantic_search — không cover thực tế vector search trên Postgres
- **Manual integration test required** khi deploy lên Postgres

---

## SQLite Test Compatibility Notes

| Issue | SQLite workaround | File |
|---|---|---|
| PostgreSQL UUID type | `sa.Uuid` instead of `postgresql.UUID` | All models |
| JSONB | `sa.JSON` | All models |
| ENUM CREATE TYPE | `create_type=False` | Models with ENUMs |
| Boolean server_default | Both `default=True` AND `server_default="true"` | `models/user.py` |
| pool_size/max_overflow | Skipped for SQLite (StaticPool) | `database.py` |
| TEXT[] arrays | `sa.JSON` | `models/todo.py` |
| RETURNING clause | Works in SQLite 3.35+ (aiosqlite) | `auth_repo.py` |
| vector(1536) + `<=>` operator | `sa.JSON` ORM column; `semantic_search()` short-circuits | `models/memory.py` |

---

## Security Notes (known gaps)

### VAPID keys not configured in dev
- Web push not testable locally without VAPID keys in `.env`
- Generate once: `npx web-push generate-vapid-keys` → set `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`
- **Production ready** (Sprint 5 done); local dev optional

### No Sentry error tracking
- `structlog` logs to stdout only
- Sentry DSN integration: Sprint 6 (pre-deploy)

### No Redis (optional)
- Rate limiting: currently in-memory (SlowAPI default store) — resets on pod restart
- Idempotency keys: not implemented (post-MVP 1)
- Swap to Upstash Redis for persistent rate limit state: **Sprint 6**

### refresh_token not hashed in test
- Tests use raw token strings via body (not cookie)
- Hash logic is correct in production flow

---

## Performance Notes

### N+1 potential
- `list_conversations` không load messages — acceptable
- `list_todos` không load related data — acceptable (flat table)

### LLM timeout
- Classifier: 3s hard timeout (asyncio.wait_for)
- Main LLM call: 30s (`settings.llm_timeout_seconds`)

---

## Frontend Known Issues

### Token refresh race condition
- Multiple simultaneous 401 responses could trigger multiple refresh attempts
- `api.ts` silentRefresh() không có mutex
- **Acceptable for now** (JWT TTL 15 min; unlikely in practice)

---

## Tech Debt Backlog

| Item | Priority | Sprint |
|---|---|---|
| Sentry integration | High | 6 |
| Eval set automation (10 cases) | High | 6 |
| Playwright E2E tests | Medium | 6 |
| Upstash Redis rate limit store | Medium | 6 |
| Conversation auto-summarize | Medium | 6 |
| Logout UI (no button in frontend currently) | Medium | 6 |
| mypy strict pass (27 errors) | Medium | 6 |
| 4-tier LLM routing | Low | 6 |
| Frontend vitest unit tests | Low | 6 |
| CRLF/biome format (pre-existing) | Low | 6 |
| `passWithNoTests` for frontend test suite | Low | 6 |
