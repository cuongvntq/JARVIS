# TÀI LIỆU 6: KẾ HOẠCH THỰC THI CẬP NHẬT
## J.A.R.V.I.S Personal AI Assistant — MVP 1

**Phiên bản:** 2.0 (cập nhật sau khi hoàn thiện 5 tài liệu phụ)
**Ngày:** 18/05/2026
**Nguồn:** Plan gốc MVP1 v1.0 + 5 tài liệu phụ (01–05).

---

## 1. TÓM TẮT THAY ĐỔI SO VỚI PLAN GỐC

| Mục | Plan gốc | Cập nhật |
|-----|---------|---------|
| Stack | "FastAPI hoặc Next.js" | **CHỐT: FastAPI BE + Next.js FE** |
| LLM | "OpenAI API hoặc LLM tương đương" | **CHỐT: Tiered Routing — Gemini Free + gpt-5.4-nano + gpt-4o-mini + gpt-5-mini, fallback Claude Haiku 4.5. Chi tiết [05c](./05c_Tiered_Routing_Strategy.md)** |
| DB | "PostgreSQL, có thể mở rộng pgvector" | **CHỐT: Supabase + pgvector, full schema sẵn (8 bảng + auth_sessions)** |
| API | "Endpoint chính" | **Full OpenAPI spec, error codes, pagination, rate limit** |
| Tool | "Khi nào dùng" | **JSON Schema chi tiết cho 11 tool + multi-tool flow + edge case** |
| Prompt | "Rút gọn" | **Full production prompt 900 token + eval set 10 case** |
| Notification | "Notification" | **Web Push (VAPID) + In-app, email là MVP 2** |
| Datetime VN | (chưa nói) | **Hybrid dict + dateparser + LLM fallback** |
| Cost | (chưa định lượng) | **~$5.4/tháng cho 1 user (LLM ~$0.40 nhờ Tiered Routing); scale 5 user vẫn dưới $20** |
| Observability | "logging cơ bản" | **Sentry + Better Stack + UptimeRobot + custom LLM usage tracking** |

---

## 2. ROADMAP 6 SPRINT (CẬP NHẬT)

Mỗi sprint **2 tuần**. Tổng MVP 1 = **12 tuần**.

### Sprint 0 — Foundation (Tuần 0, 1 tuần làm trước)
**Mục tiêu:** Setup hạ tầng và 5 tài liệu đã sẵn.

- [ ] Tạo repo `jarvis-bff` (FastAPI) và `jarvis-web` (Next.js).
- [ ] Setup Supabase project, enable extensions (vector, pg_trgm, pgcrypto).
- [ ] Setup Vercel project + Railway project.
- [ ] Setup Sentry + Better Stack.
- [ ] Tạo Google OAuth client.
- [ ] Tạo VAPID keys cho Web Push.
- [ ] **Lấy Gemini API key** (free, no card) tại https://aistudio.google.com/apikey.
- [ ] **Lấy OpenAI API key** (~$5 credit khởi tạo) tại https://platform.openai.com.
- [ ] (Optional) Lấy Anthropic API key cho fallback chain.
- [ ] CI workflow cơ bản (lint + test + build).
- [ ] Pin version: Python 3.12, Node 22, pnpm 9.

**Deliverable:** `README.md` có sẵn các bước chạy local + env template.

### Sprint 1 — Auth + Skeleton + Chat basic
**Mục tiêu:** App chạy được, login được, chat 1 chiều với LLM (chưa tool).

Backend:
- [ ] Migration `001_init_schema.sql` (toàn bộ 8 bảng + auth_sessions).
- [ ] Endpoint `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`.
- [ ] JWT middleware (access 15 phút + refresh 30 ngày).
- [ ] Endpoint `/auth/google` (id_token verify).
- [ ] Endpoint `/health`, `/health/ready`.
- [ ] LiteLLM wrapper + endpoint `POST /chat/send` (chưa tool, chỉ system prompt + user message).
- [ ] **Sprint 1 dùng đơn giản: chỉ Gemini 2.5 Flash (free) cho mọi message**. Tiered routing thêm vào Sprint 2.

Frontend:
- [ ] Layout cơ bản: Login → Dashboard (placeholder) → Chat (placeholder).
- [ ] Login page (email/pass + Google button).
- [ ] Auth flow: store access token in memory + refresh trong httpOnly cookie.
- [ ] Chat screen với streaming response (Vercel AI SDK).

**DoD Sprint 1:** Login → vào Chat → gõ "Xin chào" → nhận phản hồi tiếng Việt từ JARVIS.

### Sprint 2 — Conversation, Message Storage, Tool Router v1
**Mục tiêu:** Lưu hội thoại, AI gọi được tool nội bộ.

- [ ] Endpoint `POST /chat/send` (full): tạo/lấy conversation, lưu user msg, gọi LLM với tools array, parse tool_calls, execute, lưu assistant msg.
- [ ] Endpoint `GET /chat/conversations`, `GET /chat/conversations/{id}`, `PATCH/DELETE`.
- [ ] Implement orchestrator pattern: detect tool_call → dispatch → feed back result → re-call LLM nếu cần.
- [ ] **Implement Tiered Routing v1 (2 tier):** Gemini Flash (chitchat) + gpt-4o-mini (tool_call). Classifier theo §6 [Phụ lục 5C](./05c_Tiered_Routing_Strategy.md).
- [ ] Migration `llm_call_logs` table.
- [ ] Implement Vietnamese datetime parser (hybrid).
- [ ] Implement 3 tool đầu: `create_todo`, `list_todos`, `update_todo`.
- [ ] Lưu `tool_execution_logs` + `llm_call_logs`.
- [ ] FE: chat sidebar liệt kê conversation, history load khi click.

**DoD Sprint 2:** Gõ "Thêm việc mua sữa chiều nay" → tạo todo trong DB → user nhận xác nhận. Eval E-01, E-02 passed.

### Sprint 3 — Todo Full + Note Module
**Mục tiêu:** Todo và Note hoàn chỉnh trên cả UI và chat.

Backend:
- [ ] Full Todo API: GET/POST/PUT/PATCH/DELETE + filter today/upcoming/overdue/completed.
- [ ] Full Notes API + `POST /notes/search`.
- [ ] Tool `create_note`, `search_notes`.

Frontend:
- [ ] Todo screen: list + filter chips + add/edit modal + complete checkbox + drag/drop reorder (optional).
- [ ] Notes screen: list + search bar + tag filter + editor (TipTap hoặc textarea + markdown).
- [ ] Empty state + loading state.

**DoD Sprint 3:** CRUD todo/note hoàn chỉnh trên UI + chat tạo được. Test E-10 passed.

### Sprint 4 — Memory System + Memory Screen
**Mục tiêu:** Memory đầy đủ, RAG hoạt động trong chat.

Backend:
- [ ] Auto-embed memory khi `save_memory` (BackgroundTask).
- [ ] Full Memory API (CRUD + search).
- [ ] Tool `save_memory`, `search_memory`, `forget_memory`.
- [ ] Orchestrator: trước khi gọi LLM, tự run `search_memory(query=user_message)` và inject vào context.
- [ ] Conversation summarization job (khi msg >= 20).

Frontend:
- [ ] Memory screen: list theo type, filter, sửa, xóa, importance slider.
- [ ] Settings screen: assistant_name, timezone, locale.

**DoD Sprint 4:** Gõ "Nhớ là tôi dị ứng tôm" → memory lưu + embed. Hỏi "tôi có dị ứng gì?" → memory được retrieve và trả lời đúng. Eval E-04 passed.

### Sprint 5 — Reminder + Notification + Dashboard
**Mục tiêu:** Reminder chạy đúng, push noti, dashboard today live.

Backend:
- [ ] Full Reminders API + tool `create_reminder`, `list_reminders`.
- [ ] APScheduler job: mỗi 60s `SELECT FOR UPDATE SKIP LOCKED` reminder đến hạn → insert notification → gửi Web Push.
- [ ] Endpoint `/notifications/push/subscribe`, push delivery với `pywebpush`.
- [ ] Endpoint `GET /dashboard/today` + `GET /dashboard/briefing` (cache 1h, LLM call riêng).
- [ ] Tool `get_today_summary`.

Frontend:
- [ ] Reminders screen.
- [ ] Dashboard screen (sections: greeting + briefing + todos today + overdue + reminders today + quick chat input).
- [ ] Service Worker: register VAPID, handle push event → show notification.
- [ ] Browser permission request flow.

**DoD Sprint 5:** Đặt reminder 1 phút sau → notification hiện trên Chrome/Edge. Dashboard load đúng dữ liệu hôm nay theo timezone user. Eval E-06, E-09 passed.

### Sprint 6 — QA, Polish, Logging, Beta Deploy
**Mục tiêu:** Sẵn sàng để dùng thật.

- [ ] Test eval đầy đủ 10 case prompt (≥ 9/10 pass).
- [ ] **Mở rộng Tiered Routing lên 4 tier:** thêm `gpt-5.4-nano` cho simple_query + `gpt-5-mini` cho complex. Eval 30 case classifier (≥ 27/30 pass).
- [ ] Dashboard `/admin/llm-usage` (chart $/ngày + intent distribution + fallback rate).
- [ ] Integration test toàn bộ API (happy + 1 error path).
- [ ] E2E Playwright: login → tạo todo → đặt reminder → memory → dashboard.
- [ ] Logging: structlog JSON → Better Stack; error → Sentry.
- [ ] Rate limit middleware.
- [ ] Backup verification (restore thử từ Supabase backup).
- [ ] Security pass: review CSRF, XSS, SQL injection prevention, secret rotation procedure.
- [ ] Data export endpoint `/settings/export-data`.
- [ ] Deploy production: Vercel + Railway domain custom.
- [ ] Onboarding flow: first login → tutorial 3 step.
- [ ] Error UX: error boundary, retry button, friendly message tiếng Việt.

**DoD Sprint 6:** Bản beta accessible qua https://jarvis.yourdomain.com, đầy đủ checklist DoD trong Tài liệu MVP1 gốc + Sentry không có lỗi P0/P1 trong 1 tuần.

---

## 3. TIMELINE CHI TIẾT

| Tuần | Sprint | Mốc |
|------|--------|-----|
| 0 | Sprint 0 | Setup hạ tầng |
| 1–2 | Sprint 1 | Skeleton + Auth + Chat 1 chiều |
| 3–4 | Sprint 2 | Tool router + 3 todo tool |
| 5–6 | Sprint 3 | Todo UI + Note module |
| 7–8 | Sprint 4 | Memory + RAG |
| 9–10 | Sprint 5 | Reminder + Dashboard + Push |
| 11–12 | Sprint 6 | QA, polish, deploy beta |
| 13 | Buffer | Dự phòng bug nặng |

**Tổng: 13 tuần ≈ 3 tháng** (1 dev part-time ~20h/tuần).

Nếu full-time 40h/tuần: rút gọn xuống **6-7 tuần**.

---

## 4. RISK & MITIGATION (CẬP NHẬT)

| Rủi ro | Likelihood | Impact | Mitigation |
|--------|-----------|--------|-----------|
| Scope creep (muốn thêm voice, calendar sớm) | 🔴 Cao | 🔴 Cao | **Lock scope MVP 1**, ghi nhận idea vào backlog cho MVP 2+. |
| Tiếng Việt parse datetime sai | 🟠 Vừa | 🟠 Vừa | Hybrid parser + LLM fallback + log mọi case fail. |
| LLM tool call lệch schema (gọi nhầm tool) | 🟠 Vừa | 🟠 Vừa | Eval set 10 case; thêm assertion runtime + retry tối đa 2 lần. |
| Cost LLM tăng đột biến (loop tool) | 🟡 Thấp | 🟠 Vừa | Hard cap: 5 tool call/turn; max 4000 tokens output/request. |
| Web Push không hoạt động Safari iOS cũ | 🟠 Vừa | 🟡 Thấp | In-app fallback; cảnh báo user nếu browser không support. |
| Supabase free tier quá tải | 🟡 Thấp | 🟠 Vừa | Monitor usage; nâng cấp Pro $25/tháng nếu vượt. |
| Demo bị prompt injection (phá persona) | 🟠 Vừa | 🟡 Thấp | Test eval E-05, E-07; system prompt có defense. |
| Reminder không firing | 🟠 Vừa | 🔴 Cao | Scheduler có log + dashboard status; eval trên QA env trước deploy. |
| Memory false retrieval (lấy memory không liên quan) | 🟠 Vừa | 🟡 Thấp | min_similarity = 0.7; limit top-k = 5; theo dõi qua tool_execution_logs. |
| Mất key API OpenAI (commit nhầm) | 🟡 Thấp | 🔴 Cao | git-secrets pre-commit hook; key rotation procedure ghi rõ. |

---

## 5. TÀI LIỆU & ARTIFACTS ĐÃ CÓ

```
C:\Users\Admin\Desktop\Javis\
├── JARVIS_Personal_AI_Assistant_Plan_MVP1.docx   (gốc)
├── JARVIS_Personal_AI_Assistant_Plan_MVP1.pdf    (gốc)
├── REVIEW_JARVIS_MVP1.md                          (review từ vòng 1)
└── docs\
    ├── 01_Database_Schema_ERD.md                  ✅ Full SQL DDL + indexes
    ├── 02_API_Specification.md                    ✅ Full endpoints + error codes
    ├── 03_AI_Tool_Schemas.md                      ✅ 11 tool JSON Schema
    ├── 04_System_Prompt.md                        ✅ Production prompt + eval
    ├── 05_Tech_Stack_Decision.md                  ✅ Stack chốt + cost (updated v2)
    ├── 05a_LLM_Provider_Comparison.md              ✅ So sánh OpenAI vs Anthropic
    ├── 05b_Ollama_Local_LLM_Analysis.md            ✅ Phân tích Ollama local
    ├── 05c_Tiered_Routing_Strategy.md              ✅ Router code + cost optimization
    └── 06_Updated_Execution_Plan.md               ✅ File này
```

---

## 6. CÁC BƯỚC CẦN LÀM TIẾP (THEO THỨ TỰ HÀNH ĐỘNG)

### Bước A — Trước khi code (tuần này)
1. **Đọc qua 5 tài liệu phụ**, comment góp ý / điều chỉnh nếu có constraint riêng (budget, framework muốn dùng khác...).
2. **Đăng ký account:** OpenAI, Anthropic (optional), Supabase, Vercel, Railway, Sentry, Better Stack, Google Cloud Console.
3. **Generate VAPID keys** (`npx web-push generate-vapid-keys`).
4. **Tạo 2 repo Github** (private).

### Bước B — Sprint 0 (1 tuần)
5. Khởi tạo project FastAPI + Next.js theo stack chốt.
6. Setup CI/CD GitHub Actions.
7. Setup Supabase + migration đầu tiên từ Tài liệu 1.
8. Wire OpenAPI auto-generation (FastAPI).
9. Tạo `.env.example` đầy đủ.

### Bước C — Sprint 1-6 (12 tuần) theo roadmap §2.

### Bước D — Trong khi code, song song
- Maintain backlog cho MVP 2+ (calendar, voice).
- Mỗi 2 sprint review lại scope: có cắt được tính năng nào không?
- Mỗi PR có:
  - [ ] Test pass
  - [ ] Eval set (nếu liên quan prompt) pass
  - [ ] Cập nhật doc nếu thay đổi API
  - [ ] No secret committed

---

## 7. TIÊU CHÍ "READY TO START SPRINT 1"

Sprint 1 chỉ được start khi:

- [x] 5 tài liệu phụ đã hoàn thành (đã ✅).
- [ ] User (bạn) đã review & approve stack + scope.
- [ ] Supabase project + Vercel project + Railway project đã tồn tại.
- [ ] OpenAI API key đã có credit ≥ $5.
- [ ] Repo + branch protection setup.
- [ ] `.env.example` + README có lệnh `make dev` chạy được local.

---

## 8. UPDATED RISK CHECKLIST: J.A.R.V.I.S vs "JARVIS phim"

> ⚠️ **STALE — đã có nguồn chính thức:** Tài liệu này viết khi JARVIS còn là web app deploy cloud.
> Sau Tauri desktop migration, **MVP2/MVP3 được lập kế hoạch lại** trong
> [`docs/07_MVP2_MVP3_Plan.md`](./07_MVP2_MVP3_Plan.md) — đó là **source of truth** cho MVP2/MVP3.
> Đặc biệt: Calendar **dùng polling + `syncToken`, KHÔNG dùng webhook** (app local không có public
> endpoint). Bảng dưới chỉ giữ làm tham chiếu lịch sử.

Sau khi xong MVP 1, vẫn còn các khoảng cách dưới đây với JARVIS Iron Man — nên ghi nhận để planning MVP 2-Advanced:

| Khoảng cách | Phase tới đây |
|------------|---------------|
| Voice in/out (STT + TTS) | MVP 3 — xem docs/07 Track 2 (offline whisper.cpp/Piper vs cloud) |
| Calendar 2-way sync | MVP 2 — Google Calendar API + **polling/syncToken** (KHÔNG webhook); xem docs/07 |
| Proactive nudge (chủ động) | MVP 2 — cron job phân tích pattern + OS notification; xem docs/07 |
| Agentic multi-step planning | MVP 4 — chuyển từ function call sang ReAct/Plan-Execute loop |
| Computer-use / automation | MVP 3 — xem docs/07 Track 3 (tier tăng dần, local-only) |
| Smart home / IoT | Advanced — Home Assistant API bridge |
| Visual context (camera) | MVP 3 — docs/07 Track 1 (multimodal); camera/screen-share = Advanced |
| Multi-agent (sub-agents) | Advanced — agent orchestrator + memory chia sẻ |

---

## 9. KẾT LUẬN

Sau khi hoàn thành 5 tài liệu phụ, plan đã ở mức **executable** — một dev có thể bắt đầu code Sprint 1 ngay tuần tới mà không cần thêm clarification kỹ thuật quan trọng.

**Điểm cần bạn xác nhận trước khi start:**

1. ✅ Stack chốt (FastAPI + Next.js + Supabase + Tiered LLM Routing) — OK chưa?
2. ✅ Budget $5-10/tháng vận hành (LLM ~$0.40 nhờ Tiered + ~$5 Railway) — OK chưa?
3. ✅ Timeline 12 tuần (part-time) hoặc 6-7 tuần (full-time) — phù hợp?
4. ✅ Scope MVP 1 không thêm/bớt — đồng ý lock?

Nếu cả 4 đều ✅ → start Sprint 0 ngay.
