"""Tool JSON schemas (Sprint 2-4).

Each entry is an OpenAI-compatible "type: function" tool object.
LiteLLM accepts this format for all supported providers.
"""

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "create_todo",
            "description": (
                "Tạo một việc cần làm (todo) cho người dùng. "
                "Gọi khi người dùng yêu cầu thêm/ghi nhận một việc cần làm, "
                "ví dụ: 'thêm việc mua sữa', 'tôi cần gọi cho mẹ chiều nay'. "
                "Nếu user nói thời điểm cụ thể, parse thành due_at ISO 8601 UTC. "
                "Nếu không có thời gian, để due_at = null."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                        "description": "Tiêu đề ngắn gọn của việc cần làm.",
                    },
                    "description": {
                        "type": ["string", "null"],
                        "description": "Mô tả chi tiết nếu có thêm context. Mặc định null.",
                    },
                    "due_at": {
                        "type": ["string", "null"],
                        "format": "date-time",
                        "description": (
                            "Hạn chót ISO 8601 UTC (ví dụ '2026-05-18T11:00:00Z'). "
                            "Null nếu không có deadline. "
                            "Parse các cụm tiếng Việt: chiều nay=15:00 local, "
                            "sáng mai=08:00 local, tối nay=20:00 local."
                        ),
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "default": "medium",
                        "description": (
                            "Mức ưu tiên. Suy luận từ ngữ cảnh: "
                            "'gấp','quan trọng' => high/urgent; mặc định medium."
                        ),
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 32},
                        "maxItems": 5,
                        "default": [],
                        "description": "Tag phân loại (mua sắm, công việc, ...). Tối đa 5.",
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_todos",
            "description": (
                "Lấy danh sách việc cần làm theo bộ lọc. "
                "Gọi khi người dùng hỏi 'tôi có việc gì', "
                "'còn việc nào chưa làm', 'hôm nay làm gì', 'việc quá hạn'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "enum": ["today", "upcoming", "overdue", "completed", "all"],
                        "default": "today",
                        "description": (
                            "Bộ lọc: today=due hôm nay, upcoming=tương lai, "
                            "overdue=quá hạn chưa xong, completed=đã xong, all=tất cả."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "Số lượng tối đa trả về.",
                    },
                    "q": {
                        "type": ["string", "null"],
                        "description": "Từ khóa tìm kiếm trong title (optional).",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_todo",
            "description": (
                "Cập nhật hoặc đánh dấu hoàn thành một todo. "
                "Gọi khi user nói 'đã làm xong X', 'hủy việc Y', 'đổi deadline'. "
                "Cần todo_id; nếu user chỉ nói tên việc, gọi list_todos trước để tìm id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "ID của todo cần cập nhật.",
                    },
                    "title": {"type": ["string", "null"], "maxLength": 500},
                    "description": {"type": ["string", "null"]},
                    "due_at": {
                        "type": ["string", "null"],
                        "format": "date-time",
                        "description": "ISO 8601 UTC. Null để xóa deadline.",
                    },
                    "priority": {
                        "type": ["string", "null"],
                        "enum": ["low", "medium", "high", "urgent", None],
                    },
                    "status": {
                        "type": ["string", "null"],
                        "enum": ["pending", "in_progress", "completed", "cancelled", None],
                        "description": "Đặt 'completed' khi user nói đã làm xong.",
                    },
                    "add_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                    "remove_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "required": ["todo_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": (
                "Tạo một ghi chú cho người dùng. "
                "Gọi khi người dùng muốn ghi lại thông tin, ý tưởng, công thức, "
                "ví dụ: 'ghi chú lại công thức này', 'tôi muốn lưu ý điều này'. "
                "Nếu user muốn ghim ngay, đặt pinned=true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                        "description": "Tiêu đề ngắn gọn của ghi chú.",
                    },
                    "content": {
                        "type": "string",
                        "default": "",
                        "description": "Nội dung ghi chú (markdown được hỗ trợ).",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "maxLength": 32},
                        "maxItems": 5,
                        "default": [],
                        "description": "Tag phân loại. Tối đa 5.",
                    },
                    "pinned": {
                        "type": "boolean",
                        "default": False,
                        "description": "Ghim ghi chú lên đầu danh sách.",
                    },
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": (
                "Tìm kiếm ghi chú theo từ khóa hoặc lấy danh sách ghi chú. "
                "Gọi khi người dùng hỏi 'tôi đã ghi gì', 'tìm ghi chú về X', "
                "'ghi chú nào đang ghim'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {
                        "type": ["string", "null"],
                        "description": "Từ khóa tìm kiếm trong title. Null để lấy tất cả.",
                    },
                    "pinned_only": {
                        "type": "boolean",
                        "default": False,
                        "description": "Chỉ trả về ghi chú đang ghim.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 20,
                        "description": "Số lượng tối đa trả về.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    # ── Sprint 4: Memory tools ─────────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Lưu thông tin dài hạn của người dùng vào bộ nhớ cá nhân. "
                "Gọi khi người dùng tiết lộ fact, sở thích, quy tắc, quan hệ, hoặc mục tiêu quan trọng. "
                "VD: 'Tôi dị ứng tôm', 'Nhớ là tôi thích cà phê đen', 'Tôi làm ca đêm'. "
                "Content viết ngôi thứ ba: 'Người dùng dị ứng tôm'. "
                "KHÔNG gọi khi chitchat đơn giản. KHÔNG lưu mật khẩu, OTP, dấu hiệu khủng hoảng."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "minLength": 3,
                        "maxLength": 500,
                        "description": (
                            "Nội dung memory viết ngôi thứ ba. "
                            "VD: 'Người dùng dị ứng tôm', 'Người dùng thích cà phê đen không đường'."
                        ),
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["fact", "preference", "rule", "relation", "goal", "other"],
                        "description": (
                            "Loại memory: fact=sự thật/dị ứng/thông tin, "
                            "preference=sở thích, rule=quy tắc cá nhân, "
                            "relation=quan hệ với người khác, goal=mục tiêu."
                        ),
                    },
                    "importance": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": (
                            "Mức quan trọng 1-10. "
                            "Dị ứng/sức khỏe/quy tắc cứng=8-10; sở thích thông thường=5; thông tin vặt=1-3."
                        ),
                    },
                },
                "required": ["content", "memory_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "Tìm kiếm bộ nhớ cá nhân bằng semantic search. "
                "Gọi khi cần context cá nhân để trả lời: sở thích, dị ứng, thói quen, mục tiêu đã lưu. "
                "RAG — orchestrator gọi tự động trước mỗi LLM turn khi cần."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Câu truy vấn để tìm memory liên quan.",
                    },
                    "memory_type": {
                        "type": ["string", "null"],
                        "enum": ["fact", "preference", "rule", "relation", "goal", "other", None],
                        "description": "Lọc theo loại memory. Null để tìm tất cả loại.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": "Số lượng memory tối đa trả về.",
                    },
                    "min_similarity": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.7,
                        "description": "Ngưỡng cosine similarity tối thiểu (0-1). Mặc định 0.7.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_memory",
            "description": (
                "Xóa một memory khỏi bộ nhớ cá nhân (soft delete). "
                "Gọi khi người dùng yêu cầu xóa/quên thông tin đã lưu. "
                "Chỉ xóa 1 record/lần. Nếu không biết memory_id, gọi search_memory trước."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "ID của memory cần xóa. Lấy từ kết quả search_memory.",
                    },
                },
                "required": ["memory_id"],
                "additionalProperties": False,
            },
        },
    },
    # ── Sprint 5: Reminder tools ───────────────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": (
                "Tạo lời nhắc cho người dùng vào một thời điểm cụ thể. "
                "Gọi khi người dùng muốn được nhắc: 'nhắc tôi uống thuốc lúc 8h', "
                "'mai 7h nhắc tôi đi gym'. "
                "PHẢI có remind_at rõ ràng — nếu người dùng không nói giờ, "
                "KHÔNG gọi tool, hỏi lại giờ cụ thể trước."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                        "description": "Tiêu đề ngắn gọn của lời nhắc.",
                    },
                    "remind_at": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "Thời điểm nhắc ISO 8601 UTC (ví dụ '2026-06-01T01:00:00Z'). "
                            "Bắt buộc — KHÔNG để null. "
                            "Parse cụm tiếng Việt: sáng mai=08:00 local, chiều nay=15:00 local, "
                            "tối nay=20:00 local, rồi convert sang UTC."
                        ),
                    },
                    "description": {
                        "type": ["string", "null"],
                        "description": "Mô tả thêm nếu có. Mặc định null.",
                    },
                },
                "required": ["title", "remind_at"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": (
                "Lấy danh sách lời nhắc sắp tới. "
                "Gọi khi người dùng hỏi 'tôi có nhắc gì không', "
                "'lời nhắc hôm nay', 'reminder nào đang chờ'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": ["string", "null"],
                        "enum": ["pending", "sent", "cancelled", "failed", None],
                        "default": "pending",
                        "description": (
                            "Lọc theo trạng thái. "
                            "pending=chưa gửi (mặc định), sent=đã gửi, "
                            "cancelled=đã hủy, null=tất cả."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Số lượng tối đa trả về.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
]

# Lookup by tool name for the orchestrator
TOOL_MAP: dict[str, dict] = {t["function"]["name"]: t for t in TOOLS}
