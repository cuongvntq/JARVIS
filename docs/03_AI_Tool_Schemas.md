# TÀI LIỆU 3: AI TOOL JSON SCHEMAS
## J.A.R.V.I.S Personal AI Assistant — MVP 1

**Phiên bản:** 1.0
**Định dạng:** OpenAI Function Calling Schema (JSON Schema Draft-07)
**Tương thích:** OpenAI `tools`, Anthropic `tools`, Vercel AI SDK, LangChain.

---

## 1. NGUYÊN TẮC THIẾT KẾ TOOL

1. **Tên rõ ràng, kiểu `snake_case` ngắn gọn** (`create_todo`, không `createTodoForUser`).
2. **Description giàu thông tin** — đây là phần model dựa vào để quyết định gọi tool.
3. **Parameters phải tự mô tả** — mỗi field có `description` cụ thể (ví dụ format, ràng buộc).
4. **Required tối thiểu** — chỉ những gì thật sự không thể thiếu; còn lại optional.
5. **Datetime luôn ISO 8601 UTC** trong tool input/output. AI tự parse "chiều nay" thành ISO trước khi gọi.
6. **Không nhồi business logic vào schema** — chỉ shape input.
7. **Output trả về kèm `success: bool` + entity** — model dễ tổng hợp lại cho user.

---

## 2. TOOL DEFINITIONS

### 2.1 `create_todo`

```json
{
  "name": "create_todo",
  "description": "Tạo một việc cần làm (todo) cho người dùng. Gọi khi người dùng yêu cầu thêm/ghi nhận một việc cần làm, ví dụ: 'thêm việc mua sữa', 'tôi cần gọi cho mẹ chiều nay', 'nhắc tôi nộp báo cáo tuần sau'. Nếu user nói thời điểm cụ thể (chiều nay, 18h, ngày mai), parse thành due_at ISO 8601 UTC dựa theo timezone trong context. Nếu không có thời gian, để due_at = null.",
  "parameters": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "minLength": 1,
        "maxLength": 500,
        "description": "Tiêu đề ngắn gọn của việc cần làm (5-50 ký tự lý tưởng), viết tiếng Việt tự nhiên."
      },
      "description": {
        "type": ["string", "null"],
        "description": "Mô tả chi tiết nếu user cung cấp thêm context. Mặc định null."
      },
      "due_at": {
        "type": ["string", "null"],
        "format": "date-time",
        "description": "Hạn chót dạng ISO 8601 UTC (ví dụ '2026-05-18T11:00:00Z'). Null nếu không có deadline. Parse các cụm tiếng Việt như 'chiều nay'=>15:00 local, 'tối nay'=>20:00 local, 'sáng mai'=>08:00 local hôm sau, theo timezone user."
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high", "urgent"],
        "default": "medium",
        "description": "Mức độ ưu tiên. Suy luận từ ngữ cảnh: 'gấp', 'quan trọng' => high/urgent; mặc định medium."
      },
      "tags": {
        "type": "array",
        "items": { "type": "string", "maxLength": 32 },
        "maxItems": 5,
        "default": [],
        "description": "Tag phân loại (mua sắm, công việc, gia đình, sức khỏe...). Tối đa 5."
      }
    },
    "required": ["title"],
    "additionalProperties": false
  }
}
```

### 2.2 `list_todos`

```json
{
  "name": "list_todos",
  "description": "Lấy danh sách việc cần làm theo bộ lọc. Gọi khi người dùng hỏi 'tôi có việc gì', 'còn việc nào chưa làm', 'hôm nay làm gì', 'việc quá hạn'.",
  "parameters": {
    "type": "object",
    "properties": {
      "filter": {
        "type": "string",
        "enum": ["today", "upcoming", "overdue", "completed", "all"],
        "default": "today",
        "description": "Bộ lọc: today=việc có due_at trong hôm nay, upcoming=tương lai, overdue=quá hạn chưa xong, completed=đã xong, all=tất cả."
      },
      "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": 50,
        "default": 20,
        "description": "Số lượng tối đa trả về."
      },
      "q": {
        "type": ["string", "null"],
        "description": "Từ khóa tìm kiếm trong title (optional)."
      }
    },
    "additionalProperties": false
  }
}
```

### 2.3 `update_todo`

```json
{
  "name": "update_todo",
  "description": "Cập nhật hoặc đánh dấu hoàn thành một todo. Gọi khi user nói 'đã làm xong X', 'hủy việc Y', 'đổi deadline'. Cần todo_id; nếu user chỉ nói tên việc, gọi list_todos trước để tìm id.",
  "parameters": {
    "type": "object",
    "properties": {
      "todo_id":     { "type": "string", "format": "uuid", "description": "ID của todo cần cập nhật." },
      "title":       { "type": ["string", "null"], "maxLength": 500 },
      "description": { "type": ["string", "null"] },
      "due_at":      { "type": ["string", "null"], "format": "date-time" },
      "priority":    { "type": ["string", "null"], "enum": ["low", "medium", "high", "urgent", null] },
      "status":      {
        "type": ["string", "null"],
        "enum": ["pending", "in_progress", "completed", "cancelled", null],
        "description": "Đặt 'completed' khi user nói đã làm xong."
      },
      "add_tags":    { "type": "array", "items": { "type": "string" }, "default": [] },
      "remove_tags": { "type": "array", "items": { "type": "string" }, "default": [] }
    },
    "required": ["todo_id"],
    "additionalProperties": false
  }
}
```

### 2.4 `create_note`

```json
{
  "name": "create_note",
  "description": "Tạo ghi chú. Gọi khi user nói 'ghi chú', 'note lại', 'lưu thông tin này'. Khác với memory: note là nội dung dài, có thể tìm lại sau; memory là tri thức ngắn về user (sở thích, sự kiện cá nhân, quy tắc).",
  "parameters": {
    "type": "object",
    "properties": {
      "title": {
        "type": ["string", "null"],
        "maxLength": 255,
        "description": "Tiêu đề. Nếu null, server sẽ auto-generate từ 8 từ đầu của content."
      },
      "content": {
        "type": "string",
        "minLength": 1,
        "description": "Nội dung ghi chú (markdown được phép)."
      },
      "tags": {
        "type": "array",
        "items": { "type": "string", "maxLength": 32 },
        "maxItems": 5,
        "default": []
      },
      "pinned": {
        "type": "boolean",
        "default": false,
        "description": "Ghim lên đầu danh sách."
      }
    },
    "required": ["content"],
    "additionalProperties": false
  }
}
```

### 2.5 `search_notes`

```json
{
  "name": "search_notes",
  "description": "Tìm ghi chú đã lưu. Gọi khi user hỏi 'note về X tôi viết hôm nào', 'ghi chú liên quan Y'.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "minLength": 1, "description": "Từ khóa tìm kiếm." },
      "tag":   { "type": ["string", "null"], "description": "Lọc theo tag cụ thể (optional)." },
      "limit": { "type": "integer", "minimum": 1, "maximum": 20, "default": 10 }
    },
    "required": ["query"],
    "additionalProperties": false
  }
}
```

### 2.6 `create_reminder`

```json
{
  "name": "create_reminder",
  "description": "Tạo lời nhắc vào thời điểm cụ thể. KHÁC với create_todo: reminder BẮT BUỘC có remind_at và sẽ push notification đúng giờ. Gọi khi user nói 'nhắc tôi X lúc Y', 'báo tôi Z vào ngày mai'. Nếu user không nói giờ rõ ràng, KHÔNG đoán — hỏi lại trước.",
  "parameters": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "minLength": 1,
        "maxLength": 500,
        "description": "Nội dung lời nhắc."
      },
      "description": { "type": ["string", "null"] },
      "remind_at": {
        "type": "string",
        "format": "date-time",
        "description": "Thời điểm nhắc dạng ISO 8601 UTC. BẮT BUỘC. Phải là tương lai (so với now)."
      }
    },
    "required": ["title", "remind_at"],
    "additionalProperties": false
  }
}
```

### 2.7 `list_reminders`

```json
{
  "name": "list_reminders",
  "description": "Liệt kê các reminder. Gọi khi user hỏi 'có lời nhắc gì sắp tới', 'tôi đã đặt nhắc gì'.",
  "parameters": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["scheduled", "sent", "all"],
        "default": "scheduled"
      },
      "from":  { "type": ["string", "null"], "format": "date-time" },
      "to":    { "type": ["string", "null"], "format": "date-time" },
      "limit": { "type": "integer", "minimum": 1, "maximum": 50, "default": 20 }
    },
    "additionalProperties": false
  }
}
```

### 2.8 `save_memory`

```json
{
  "name": "save_memory",
  "description": "Lưu thông tin dài hạn về người dùng để dùng lại trong các hội thoại tương lai. Gọi khi user nói 'nhớ là...', 'từ giờ tôi muốn...', hoặc khi nhận diện được fact/preference/rule/relation/goal có giá trị bền vững. KHÔNG lưu thông tin nhạy cảm (mật khẩu, số thẻ, OTP). KHÔNG lưu nội dung trùng lặp — nếu thấy giống memory cũ, dùng update.",
  "parameters": {
    "type": "object",
    "properties": {
      "memory_type": {
        "type": "string",
        "enum": ["fact", "preference", "rule", "relation", "goal", "other"],
        "description": "fact=sự kiện về user (sinh nhật, nghề); preference=sở thích; rule=quy tắc ('không họp sau 22h'); relation=người thân; goal=mục tiêu."
      },
      "content": {
        "type": "string",
        "minLength": 3,
        "maxLength": 500,
        "description": "Nội dung ngắn gọn ngôi thứ 3 ('Người dùng thích cà phê đen' không phải 'Tôi thích cà phê đen'). Tự đứng được, không cần context."
      },
      "importance": {
        "type": "integer",
        "minimum": 1,
        "maximum": 10,
        "default": 5,
        "description": "Mức quan trọng. ≥8 cho thông tin quan trọng (sức khỏe, allergy, rule cứng); 5 mặc định; ≤3 cho thông tin vặt."
      }
    },
    "required": ["memory_type", "content"],
    "additionalProperties": false
  }
}
```

### 2.9 `search_memory`

```json
{
  "name": "search_memory",
  "description": "Truy xuất memory liên quan câu hỏi/yêu cầu hiện tại. Thường được orchestrator tự gọi trước khi gọi LLM (RAG), nhưng cũng có thể gọi rõ trong tool loop khi cần. Trả về top-k memory theo cosine similarity.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "minLength": 1, "description": "Câu truy vấn (thường là user message hoặc reformulated query)." },
      "memory_type": {
        "type": ["string", "null"],
        "enum": ["fact", "preference", "rule", "relation", "goal", "other", null],
        "description": "Lọc theo loại memory (optional)."
      },
      "limit": { "type": "integer", "minimum": 1, "maximum": 10, "default": 5 },
      "min_similarity": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.7 }
    },
    "required": ["query"],
    "additionalProperties": false
  }
}
```

### 2.10 `forget_memory`

```json
{
  "name": "forget_memory",
  "description": "Đánh dấu memory inactive (không xóa cứng). Gọi khi user nói 'quên đi việc X', 'đừng nhớ Y nữa'. PHẢI confirm với user trước khi gọi nếu xóa từ 2 memory trở lên hoặc nội dung quan trọng.",
  "parameters": {
    "type": "object",
    "properties": {
      "memory_id": { "type": "string", "format": "uuid", "description": "ID memory cần forget. Dùng search_memory để tìm trước nếu user mô tả bằng lời." }
    },
    "required": ["memory_id"],
    "additionalProperties": false
  }
}
```

### 2.11 `get_today_summary`

```json
{
  "name": "get_today_summary",
  "description": "Lấy tóm tắt hôm nay: todo hôm nay, todo quá hạn, reminder hôm nay. Gọi khi user hỏi 'hôm nay có gì', 'tóm tắt ngày hôm nay', 'tình hình hôm nay'.",
  "parameters": {
    "type": "object",
    "properties": {
      "include_completed": { "type": "boolean", "default": false, "description": "Có gồm việc đã hoàn thành hôm nay không." }
    },
    "additionalProperties": false
  }
}
```

---

## 3. TOOL OUTPUT FORMAT (chuẩn chung)

Mọi tool trả về JSON theo shape sau (orchestrator tự đóng gói):

```json
{
  "success": true,
  "data": { /* entity hoặc list */ },
  "summary": "Đã thêm việc 'Mua sữa' với deadline 18:00 hôm nay.",
  "warnings": []
}
```

Khi lỗi:
```json
{
  "success": false,
  "error": { "code": "missing_remind_at", "message": "Reminder cần remind_at." },
  "data": null
}
```

→ Model LLM sẽ thấy `success/summary/error` và biết cách phản hồi user.

---

## 4. TOOL ROUTING DECISION TABLE

Bảng giúp model (và dev review) quyết định gọi tool nào:

| User intent | Tool |
|-------------|------|
| "Thêm việc X" / "Tôi cần làm Y" | `create_todo` |
| "Còn việc gì" / "Hôm nay làm gì" (todo only) | `list_todos` |
| "Hôm nay có gì" / "Tình hình hôm nay" (todo + reminder + overdue) | `get_today_summary` |
| "Đã xong việc X" / "Hủy việc Y" | `update_todo` (status) |
| "Ghi chú lại Z" / "Note: ..." | `create_note` |
| "Tìm ghi chú về X" | `search_notes` |
| "Nhắc tôi X lúc Y" (có giờ rõ) | `create_reminder` |
| "Nhắc tôi X" (KHÔNG có giờ) | **Không gọi tool**, hỏi user thời gian |
| "Có lời nhắc nào sắp tới" | `list_reminders` |
| "Nhớ là tôi..." / "Từ giờ tôi muốn..." | `save_memory` |
| Bất kỳ hội thoại có info cá nhân giá trị dài hạn | `save_memory` (proactive, đánh giá importance) |
| "Quên việc X đi" (về memory) | `search_memory` → `forget_memory` |
| Pure chitchat / hỏi kiến thức chung | **Không gọi tool**, trả lời thẳng |

---

## 5. MULTI-TOOL FLOW (ví dụ)

**User:** "Tôi không thích cà phê có sữa, nhớ giúp tôi. Mai 7h sáng nhắc tôi đi gym."

**Mô hình gọi:**
1. `save_memory` → `{ "memory_type": "preference", "content": "Người dùng không thích cà phê có sữa", "importance": 6 }`
2. `create_reminder` → `{ "title": "Đi gym", "remind_at": "2026-05-19T00:00:00Z" }` (giả sử user ở UTC+7, 7h sáng local = 00:00 UTC)

**Phản hồi gộp:** "Đã ghi nhớ bạn không thích cà phê có sữa và đặt lời nhắc 'Đi gym' lúc 7:00 sáng mai."

---

## 6. EDGE CASES & GUARDS (Orchestrator implement)

| Trường hợp | Xử lý |
|-----------|------|
| Tool input fail validation | Trả error về model, model sửa & retry tối đa 2 lần. |
| Tool timeout (>10s) | Trả `timeout` error, model thông báo user thử lại. |
| Model gọi tool không tồn tại | Reject, trả lỗi cho model, model rephrase. |
| Model gọi cùng tool 3 lần liên tiếp với input gần giống | Coi như loop, dừng và hỏi user clarification. |
| `forget_memory` với scope rộng (>2 record) | Bắt buộc confirmation step trong UI. |
| `create_reminder` với `remind_at` trong quá khứ | Reject `422`, model hỏi lại. |
| User input chứa prompt injection (override system prompt) | Orchestrator strip + log, không truyền nguyên văn. |

---

## 7. JSON SCHEMA BUNDLE (tham khảo, copy-paste vào code)

File `tools.json` để load runtime:

```json
[
  { "type": "function", "function": { "name": "create_todo", "...": "..." } },
  { "type": "function", "function": { "name": "list_todos",  "...": "..." } },
  ...
]
```

→ Khi gọi OpenAI: `client.chat.completions.create(model=..., messages=..., tools=tools_array)`.
