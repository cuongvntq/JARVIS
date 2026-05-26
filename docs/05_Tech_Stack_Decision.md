# TÀI LIỆU 5: TECH STACK DECISION
## J.A.R.V.I.S Personal AI Assistant — MVP 1

**Phiên bản:** 1.0
**Người ra quyết định:** Tech Lead (đề xuất)
**Ngày:** 18/05/2026

---

## 1. CRITERIA ĐÁNH GIÁ

Mọi quyết định stack dưới đây được cân nhắc theo 6 tiêu chí:

| # | Tiêu chí | Trọng số |
|---|----------|----------|
| 1 | Chi phí vận hành (free-tier friendly cho cá nhân) | 25% |
| 2 | Tốc độ phát triển (1 dev cá nhân hoàn thành 6 sprint) | 20% |
| 3 | Latency end-to-end (chat phản hồi < 3s p95) | 15% |
| 4 | Chất lượng tiếng Việt | 15% |
| 5 | Cộng đồng + tài liệu | 15% |
| 6 | Khả năng mở rộng sang MVP 2-4 (voice, calendar, automation) | 10% |

---

## 2. LLM PROVIDER

### So sánh các lựa chọn

| Provider / Model | $ Input / 1M | $ Output / 1M | Latency p50 | Tiếng Việt | Tool calling | Ghi chú |
|------------------|--------------|---------------|-------------|-----------|--------------|--------|
| OpenAI GPT-4o-mini | $0.15 | $0.60 | ~1.5s | Tốt | ⭐⭐⭐⭐⭐ | Function calling chuẩn nhất. |
| OpenAI GPT-4o | $2.50 | $10.00 | ~2.5s | Rất tốt | ⭐⭐⭐⭐⭐ | Đắt, dùng cho task khó. |
| Anthropic Claude Haiku 4.5 | $1.00 | $5.00 | ~1.8s | Rất tốt | ⭐⭐⭐⭐⭐ | Tool use ổn định. |
| Anthropic Claude Sonnet 4.6 | $3.00 | $15.00 | ~3s | Xuất sắc | ⭐⭐⭐⭐⭐ | Reasoning mạnh nhất tầm giá. |
| Google Gemini 2.0 Flash | $0.075 | $0.30 | ~1.2s | Tốt | ⭐⭐⭐⭐ | Rẻ nhất, latency thấp, đôi khi tool call lệch schema. |
| Llama 3.3 70B (Groq / Together) | $0.59 | $0.79 | ~0.8s (Groq) | Khá | ⭐⭐⭐ | Tool call yếu hơn, cần prompt engineering kỹ. |
| Local Llama 3.1 8B (Ollama) | $0 (điện) | $0 | ~3-10s (CPU) | Trung bình | ⭐⭐ | Privacy tốt nhưng chậm, không phù hợp MVP. |

### Ước lượng cost (1 user, 1 ngày)

Giả định: 50 message/ngày × (1500 token in + 200 token out) trung bình.

| Model | $/ngày | $/tháng |
|-------|--------|---------|
| GPT-4o-mini | $0.018 | **$0.55** |
| Claude Haiku 4.5 | $0.125 | $3.75 |
| GPT-4o | $0.39 | $11.70 |
| Gemini 2.0 Flash | $0.009 | **$0.27** |
| Claude Sonnet 4.6 | $0.45 | $13.50 |

### ✅ QUYẾT ĐỊNH CUỐI CÙNG (v3.0 — 2-tier đơn giản)

**Sau khi user chọn approach đơn giản, chốt 2-tier:**

| Tier | Model | Cost/1M | Vai trò |
|------|-------|---------|---------|
| **Primary** | **gemini-2.5-flash** | **FREE** (1500 req/ngày) | Tất cả request — chitchat + tool calling |
| **Fallback** | **gpt-4o-mini** | $0.15/$0.60 | Khi Gemini fail/rate limit/tool unreliable |

**Cost ước tính:** **$0-0.30/tháng/user** (gần như free cho cá nhân).

**Lý do chọn 2-tier (không phải 4-tier):**
- Đơn giản, ít code, dễ debug.
- Gemini Free quota 1500/ngày đủ cho 1 user (typical 50-300 LLM call/ngày sau tool round-trips).
- Có fallback đảm bảo reliability.
- Tránh over-engineering ở MVP1.
- Có thể nâng cấp lên 4-tier ở post-MVP nếu cần.

**Lý do chọn tiered:**
- Gemini 2.5 Flash FREE 1500 req/ngày — đủ cho 1 user dùng cá nhân.
- gpt-5.4-nano rẻ 2x gpt-4o-mini, đủ dùng cho list/search.
- gpt-4o-mini giữ cho tool call (function calling reliability cao).
- gpt-5-mini chỉ cho ~5% complex case — ít ảnh hưởng tổng cost.
- LiteLLM hỗ trợ cả 4 model + fallback chain natively.

**MVP1 đơn giản (Sprint 2):** Bắt đầu với 2 tier — Gemini Free + gpt-4o-mini fallback. Mở rộng dần khi memory + briefing có (Sprint 4-5).

**Chi tiết implementation:** Xem [Phụ lục 5C — Tiered Routing Strategy](./05c_Tiered_Routing_Strategy.md) — có router code Python sẵn copy-paste.

**KHÔNG chọn (lý do):**
- Single model gpt-4o-mini: Tốt nhưng đắt hơn tiered 40%.
- Single Claude Haiku 4.5: Quality cao nhất nhưng đắt 6x với side-project.
- Local Llama qua Groq free: Tool call không đủ tin cậy cho tier_call.
- Ollama local: RTX 2060 6GB VRAM chỉ chạy được Qwen3 8B — quality kém hơn cloud rõ rệt (xem [Phụ lục 5B](./05b_Ollama_Local_LLM_Analysis.md)).

---

## 3. PROVIDER ABSTRACTION

Implement một interface để dễ swap model:

```python
# llm/client.py (pseudo)
class LLMClient(Protocol):
    async def chat(self, messages, tools=None, stream=False) -> Response: ...

class OpenAIClient(LLMClient): ...
class AnthropicClient(LLMClient): ...
```

Hoặc dùng **Vercel AI SDK** (nếu Next.js) / **LiteLLM** (Python) làm wrapper sẵn.

→ Khuyến nghị: **LiteLLM** (Python) — chuẩn hóa cả OpenAI/Anthropic/Gemini về cùng API + có retry/fallback built-in.

---

## 4. EMBEDDING MODEL

| Model | Dim | $/1M tokens | Multilingual | Ghi chú |
|-------|-----|-------------|--------------|--------|
| OpenAI text-embedding-3-small | 1536 | $0.02 | Tốt | Khuyến nghị. |
| OpenAI text-embedding-3-large | 3072 | $0.13 | Rất tốt | Đắt 6x, lợi ích nhỏ với memory ngắn. |
| Cohere embed-multilingual-v3 | 1024 | $0.10 | Xuất sắc tiếng Việt | Lib riêng. |
| BGE-M3 (local, HuggingFace) | 1024 | $0 | Rất tốt | Cần server riêng. |

### ✅ QUYẾT ĐỊNH: `text-embedding-3-small`

**Lý do:**
- Rẻ ($0.02/1M).
- Dim 1536 ăn khớp với pgvector schema đã thiết kế.
- Multilingual đủ cho tiếng Việt (so với baseline OpenAI cũ).
- Tương thích trực tiếp khi đã dùng OpenAI cho LLM (cùng SDK, cùng billing).

**Memory cost ước lượng:** 500 memory/user × 50 token/memory × $0.02/1M = **$0.0005/user/lần index**. Không đáng kể.

---

## 5. BACKEND FRAMEWORK

| Framework | Pros | Cons |
|-----------|------|------|
| **FastAPI** (Python) | OpenAPI auto, async, hệ sinh thái AI/ML mạnh, Pydantic validation. | Phải tự setup auth/ORM. |
| **Next.js API routes** (TS) | Full-stack 1 codebase, deploy Vercel 1-click, Server Actions tiện. | AI ecosystem TS yếu hơn Python; long-running task khó. |
| **Hono** (TS) | Cực nhanh, edge runtime. | Quá mới, cần wire thêm nhiều thứ. |
| **Express** (TS) | Phổ biến nhất. | Cũ, không có async types tốt. |

### ✅ QUYẾT ĐỊNH: **FastAPI (Python 3.12)**

**Lý do:**
- AI ecosystem Python vượt trội (LiteLLM, LangChain, instructor, dateparser, openai SDK).
- Tài liệu MVP đã đề xuất FastAPI → consistent.
- Async I/O tốt, hợp với streaming LLM response.
- Auto OpenAPI = nhất quán với API spec đã viết (Tài liệu 2).
- Scheduler dùng `APScheduler` hoặc Celery dễ.

**Stack chi tiết:**
- Web: **FastAPI** + **Uvicorn**
- ORM: **SQLAlchemy 2.0** (async) + **Alembic** migration
- Validation: **Pydantic v2**
- Auth: **python-jose** (JWT) + **passlib[bcrypt]**
- LLM client: **LiteLLM**
- Scheduler: **APScheduler** (đơn giản, in-process) cho MVP 1; nâng cấp Celery + Redis ở MVP 2 nếu cần.
- Background task: **FastAPI BackgroundTasks** cho task ngắn (embed memory mới).
- Logging: **structlog** + JSON output → Grafana Loki / Vercel Logs.

---

## 6. FRONTEND

| Framework | Pros | Cons |
|-----------|------|------|
| **Next.js 15** (App Router) | SSR, PWA support, Vercel deploy 1-click, ecosystem mạnh. | Bundle hơi nặng. |
| Remix / React Router 7 | Routing tốt. | Ít hosting 1-click hơn. |
| SvelteKit | Nhỏ, nhanh. | Ecosystem nhỏ hơn React. |

### ✅ QUYẾT ĐỊNH: **Next.js 15 + React 19**

**Lý do:**
- PWA + service worker dễ setup (`next-pwa`).
- Streaming UI tốt cho chat (`use server` + `Suspense`).
- Vercel deploy free tier rất hào phóng.
- Tailwind + shadcn/ui là combo chuẩn (đẹp, nhanh, customize được).

**Stack chi tiết:**
- **Next.js 15** App Router (chỉ dùng cho FE/render, không dùng API routes làm BE).
- **TypeScript 5.5+**
- **Tailwind CSS 4** + **shadcn/ui**
- **Tanstack Query** cho data fetching/cache.
- **Zustand** cho global state nhỏ (user, theme).
- **react-hook-form** + **zod** cho form validation.
- **Vercel AI SDK** (`useChat`) cho streaming chat UI.
- **date-fns** (timezone-aware) cho format datetime.
- **next-pwa** cho service worker + Web Push.

---

## 7. DATABASE

| Option | Free Tier | Pros | Cons |
|--------|----------|------|------|
| **Supabase** | 500 MB, 50K MAU, pgvector built-in | Auth + Realtime + Storage sẵn | Vendor lock-in nhẹ |
| **Neon** | 0.5 GB, autoscale | Postgres pure, branching | Không có pgvector mặc định (cần enable) |
| **Railway PG** | $5 credit/tháng | Đơn giản, đi kèm BE | Hết credit thì trả tiền |
| Local Postgres | $0 | Full control | Không deploy được trên cloud |

### ✅ QUYẾT ĐỊNH: **Supabase (managed Postgres + pgvector)**

**Lý do:**
- pgvector enable 1-click → memory search ready out of the box.
- Bonus: auth (nếu muốn rút gọn), storage (cho avatar sau).
- Free tier 500 MB đủ cho 5 user × 1 năm (theo ước lượng Tài liệu 1).
- Có connection pooling (PgBouncer) sẵn → tránh exhaust connection từ FastAPI async.
- Migration tự quản bằng Alembic, không phụ thuộc Supabase tool.

**Setup cần làm:**
- 1 project trên Supabase.
- Bật extension: `vector`, `pg_trgm`, `pgcrypto`.
- Connection string lưu trong env, dùng pooler mode `transaction` (port 6543).
- Backup tự động đã có free tier (7 ngày point-in-time).

---

## 8. HOSTING / DEPLOY

| Component | Provider | Tier | Cost |
|-----------|----------|------|------|
| Frontend (Next.js) | **Vercel** | Hobby | $0 |
| Backend (FastAPI) | **Railway** (hoặc Fly.io) | $5 credit | $5/tháng |
| Database | **Supabase** | Free | $0 |
| Redis (optional, cho cache + scheduler) | **Upstash** | Free 10K cmd/ngày | $0 |
| Object storage (avatar) | Supabase Storage | 1 GB free | $0 |
| Monitoring | **Sentry** free 5K event/tháng + **Better Stack** logs | Free | $0 |
| Web Push | Tự host (VAPID keys) | — | $0 |
| Domain | Namecheap / Cloudflare | — | ~$10/năm |

**Tổng cost MVP 1:** ~$5/tháng + $10/năm domain. **Với 1 user, ~$0.30-0.50/tháng cho LLM nhờ Tiered Routing (giảm từ $1 xuống).**

### ✅ QUYẾT ĐỊNH: Vercel (FE) + Railway (BE) + Supabase (DB) + Upstash Redis

---

## 9. VIETNAMESE DATETIME PARSER

Đây là quyết định khó — có 3 approach:

| Approach | Pros | Cons |
|----------|------|------|
| **A. Để LLM tự parse** (system prompt có rule) | Đơn giản, hỗ trợ ngôn ngữ tự nhiên rộng. | Tốn token, đôi khi sai (đặc biệt với "thứ 5 tuần sau"). |
| **B. Library: `dateparser` (Python)** | Free, support tiếng Việt cơ bản. | Tiếng Việt support yếu, "chiều nay" không hiểu. |
| **C. Hybrid: regex/dict preprocess + dateparser fallback** | Chính xác cho 90% case phổ biến. | Phải maintain dict manually. |

### ✅ QUYẾT ĐỊNH: **Hybrid (Approach C) + LLM cuối cùng**

**Pipeline:**

```
User text → 
  1. Vietnamese normalizer (lowercase, remove dấu sai chỗ).
  2. Dict-based replacer ("chiều nay" → "15:00 today", "tối nay" → "20:00 today", "sáng mai" → "tomorrow 08:00", ...).
  3. `dateparser.parse(text, settings={'TIMEZONE': user_tz, 'RELATIVE_BASE': now_local})`.
  4. Nếu fail → LLM với prompt focus parse + return ISO.
  5. Validate: phải là tương lai (cho reminder).
```

**Dict mẫu (file `vi_time_dict.json`):**

```json
{
  "chiều nay": "today 15:00",
  "trưa nay":  "today 12:00",
  "tối nay":   "today 20:00",
  "sáng nay":  "today 08:00",
  "đêm nay":   "today 22:00",
  "sáng mai":  "tomorrow 08:00",
  "trưa mai":  "tomorrow 12:00",
  "chiều mai": "tomorrow 15:00",
  "tối mai":   "tomorrow 20:00",
  "ngày mai":  "tomorrow 09:00",
  "hôm nay":   "today",
  "ngày kia":  "in 2 days 09:00",
  "tuần sau":  "next monday 09:00",
  "tháng sau": "first day of next month 09:00",
  "cuối tuần": "next saturday 09:00"
}
```

**Bonus regex pattern:**
```
\b(\d{1,2})h(?:(\d{1,2}))?\b           → "8h", "8h30"
\b(\d{1,2}):(\d{2})\b                  → "08:30"
\bthứ\s*([2-7]|bảy)\b                  → "thứ 2", "thứ bảy"
\bngày\s*(\d{1,2})/(\d{1,2})\b         → "ngày 18/5"
```

---

## 10. AUTH STRATEGY

| Option | Implement |
|--------|-----------|
| Email + Password | bcrypt hash, JWT access 15 min + refresh 30 days (rotating). |
| Google OAuth | Authorization Code flow với PKCE, validate `id_token` server-side. |

→ Implement cả 2 ngay từ MVP 1 (cần Google cho onboarding mượt).

**Library:** `authlib` (Python) hoặc tự build với `python-jose` + `google-auth`.

---

## 11. NOTIFICATION DELIVERY

| Kênh | Implement | Reliability |
|------|-----------|------------|
| In-app banner | Trivial (DB notifications + polling/SSE) | 100% khi user mở app |
| **Web Push** | Service Worker + VAPID + Web Push Protocol | ~80% (browser phải support, user phải allow) |
| Email fallback | Resend (free 3K/tháng) hoặc SendGrid | 99% nhưng chậm |
| SMS | Twilio | Đắt, không cần MVP |

### ✅ QUYẾT ĐỊNH cho MVP 1
- **Web Push** là kênh chính (tự host VAPID, dùng lib `pywebpush`).
- **In-app** là fallback (badge + notification screen).
- **Email** đẩy sang MVP 2.

---

## 12. OBSERVABILITY

| Mục | Tool | Cost |
|-----|------|------|
| Error tracking | **Sentry** | Free 5K event |
| Logs | **Better Stack** (Logtail) | Free 1 GB/tháng |
| Metrics (latency, tool call rate) | **Grafana Cloud** | Free 10K series |
| LLM usage tracking | Custom — log vào `tool_execution_logs` + `messages.metadata.tokens` | $0 |
| Uptime monitor | **UptimeRobot** | Free 50 monitors |

---

## 13. DEV TOOLING

| Mục | Tool |
|-----|------|
| Package manager | **uv** (Python) — nhanh hơn pip 10x. **pnpm** (Node). |
| Lint/Format | **ruff** (Python) + **biome** (TS) — 1 tool thay cho 5. |
| Pre-commit | husky + lint-staged + ruff/biome check |
| Test | **pytest** (BE) + **vitest** (FE) + **playwright** (E2E) |
| API client test | **bruno** (free Postman alternative, git-friendly) |
| CI/CD | **GitHub Actions** (free 2000 min/tháng cho repo private) |

---

## 14. TỔNG KẾT STACK

```
┌─────────────────────────────────────────────────────────────┐
│                    User (Browser / PWA)                       │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS
┌──────────────────────────────▼──────────────────────────────┐
│ Frontend                                                      │
│ ─ Next.js 15 + React 19 + TS                                 │
│ ─ Tailwind + shadcn/ui                                       │
│ ─ Tanstack Query + Zustand                                   │
│ ─ Vercel AI SDK (chat stream)                                │
│ ─ next-pwa + Web Push                                        │
│ ─ Deploy: Vercel                                              │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST + SSE
┌──────────────────────────────▼──────────────────────────────┐
│ Backend                                                       │
│ ─ FastAPI + Uvicorn (Python 3.12)                            │
│ ─ SQLAlchemy 2.0 (async) + Alembic                            │
│ ─ Pydantic v2                                                  │
│ ─ APScheduler (reminder scheduler)                            │
│ ─ LiteLLM (OpenAI primary, Anthropic fallback)               │
│ ─ Vietnamese datetime parser hybrid                           │
│ ─ Deploy: Railway / Fly.io                                    │
└────────────────────┬──────────────────────┬────────────────┘
                     │                      │
                     │                      ▼
                     │           ┌─────────────────────┐
                     │           │ LLM Provider         │
                     │           │ ─ OpenAI (gpt-4o-mini)│
                     │           │ ─ Anthropic (haiku 4.5) fallback │
                     │           │ ─ OpenAI embedding 3-small │
                     │           └─────────────────────┘
                     ▼
            ┌────────────────────┐
            │ Supabase Postgres  │
            │ ─ pgvector          │
            │ ─ pg_trgm           │
            │ ─ pgcrypto          │
            └────────────────────┘

            ┌────────────────────┐
            │ Upstash Redis      │  (session cache + scheduler lock)
            └────────────────────┘

            ┌────────────────────┐
            │ Sentry + Better    │  (observability)
            │ Stack + Grafana    │
            └────────────────────┘
```

**Tổng chi phí monthly cho 1 user (active) — phiên bản Tiered Routing:**

| Mục | $/tháng |
|-----|---------|
| LLM Primary (Gemini Flash FREE) | $0 |
| LLM Fallback (gpt-4o-mini, ~5% requests) | $0.10 |
| Embedding (text-embedding-3-small) | $0.05 |
| Railway BE | $5 |
| Vercel FE | $0 |
| Supabase DB | $0 |
| Upstash Redis | $0 |
| Monitoring | $0 |
| **TỔNG LLM** | **~$0.10-0.30/tháng** |
| **TỔNG TẤT CẢ** | **~$5.15/tháng** |

---

## 15. RỦI RO DECISION & PLAN B

| Quyết định | Rủi ro | Plan B |
|-----------|--------|--------|
| OpenAI 4o-mini | Provider down hoặc tăng giá | LiteLLM swap sang Claude Haiku ngay. |
| Supabase free tier | Vượt 500 MB | Upgrade Pro $25/tháng hoặc migrate Neon. |
| Railway BE | Hết credit $5 | Migrate Fly.io free tier (1 small VM). |
| FastAPI single instance | Down 1 node = down toàn bộ | MVP 1 chấp nhận; MVP 2 thêm 2nd instance + LB. |
| Web Push không support Safari iOS < 16.4 | User iOS cũ không nhận noti | Email fallback (MVP 2). |

---

## 16. CHECKLIST QUYẾT ĐỊNH ĐÃ CHỐT

- [x] LLM: **2-tier** — Gemini 2.5 Flash (primary, FREE) + gpt-4o-mini (fallback). Chi tiết: [05c](./05c_Tiered_Routing_Strategy.md).
- [x] Embedding: **OpenAI text-embedding-3-small** (1536-dim)
- [x] LLM wrapper: **LiteLLM** (cần `litellm` + `google-generativeai`)
- [x] Backend: **FastAPI + SQLAlchemy 2.0 async + Alembic + APScheduler**
- [x] Frontend: **Next.js 15 + Tailwind + shadcn/ui + Tanstack Query + Vercel AI SDK**
- [x] DB: **Supabase Postgres + pgvector**
- [x] Cache: **Upstash Redis**
- [x] Hosting: **Vercel (FE) + Railway (BE)**
- [x] Auth: **JWT (email/pass) + Google OAuth**
- [x] Notification: **Web Push + In-app** (email là MVP 2)
- [x] Datetime parse: **Hybrid dict + dateparser + LLM fallback**
- [x] Observability: **Sentry + Better Stack + UptimeRobot**
- [x] CI/CD: **GitHub Actions**
- [x] Dev tools: **uv + pnpm + ruff + biome + bruno + pytest + vitest + playwright**
