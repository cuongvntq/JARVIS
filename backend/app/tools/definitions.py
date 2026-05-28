"""Tool JSON schemas for the 3 todo tools (Sprint 2).

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
]

# Lookup by tool name for the orchestrator
TOOL_MAP: dict[str, dict] = {t["function"]["name"]: t for t in TOOLS}
