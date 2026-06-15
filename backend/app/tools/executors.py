"""Tool executors (Sprint 2-4).

Each executor:
  - Accepts raw tool_call params dict from LLM
  - Calls the appropriate service function
  - Returns a standardised ToolResult dict
"""

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.memory import MemoryCreate
from app.schemas.note import NoteCreate
from app.schemas.reminder import ReminderCreate
from app.schemas.todo import TodoCreate, TodoPartialUpdate
from app.services import (
    dashboard_service,
    google_calendar_service,
    memory_service,
    note_service,
    reminder_service,
    todo_service,
)
from app.utils.datetime_parser import ParseDatetimeError, parse_datetime

log = structlog.get_logger()

ToolResult = dict[str, Any]


def _ok(data: Any, summary: str, warnings: list[str] | None = None) -> ToolResult:
    return {"success": True, "data": data, "summary": summary, "warnings": warnings or []}


def _err(code: str, message: str) -> ToolResult:
    return {"success": False, "error": {"code": code, "message": message}, "data": None}


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


# ── create_todo ───────────────────────────────────────────────────────────────


async def execute_create_todo(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    title = params.get("title", "").strip()
    if not title:
        return _err("missing_title", "title là bắt buộc.")

    try:
        due_at = _parse_iso(params.get("due_at"))
    except (ValueError, TypeError) as e:
        return _err("invalid_due_at", f"due_at không hợp lệ: {e}")

    data = TodoCreate(
        title=title,
        description=params.get("description"),
        due_at=due_at,
        priority=params.get("priority", "medium"),
        tags=params.get("tags", []),
        source="chat",
    )
    todo = await todo_service.create_todo(db, user_id, data, commit=False)

    due_str = f" (deadline: {params['due_at']})" if params.get("due_at") else ""
    return _ok(
        todo.model_dump(mode="json"),
        f"Đã thêm việc '{title}'{due_str}.",
    )


# ── list_todos ────────────────────────────────────────────────────────────────


async def execute_list_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
    user_tz: str = "UTC",
) -> ToolResult:
    filter_type = params.get("filter", "today")
    limit = min(int(params.get("limit", 20)), 50)
    q = params.get("q") or None

    todos, _ = await todo_service.list_todos(
        db,
        user_id,
        status=None,
        filter_type=filter_type,
        q=q,
        limit=limit,
        cursor=None,
        user_tz=user_tz,
    )

    return _ok(
        {"todos": [t.model_dump(mode="json") for t in todos], "count": len(todos)},
        f"Tìm thấy {len(todos)} việc (filter: {filter_type}).",
    )


# ── update_todo ───────────────────────────────────────────────────────────────


async def execute_update_todo(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    try:
        todo_id = uuid.UUID(params["todo_id"])
    except (KeyError, ValueError):
        return _err("invalid_todo_id", "todo_id không hợp lệ hoặc thiếu.")

    # Build the partial update payload — extract status separately to use dedicated methods
    patch_data: dict[str, Any] = {}
    for f in ("title", "description", "priority"):
        if f in params and params[f] is not None:
            patch_data[f] = params[f]

    if "due_at" in params:
        try:
            patch_data["due_at"] = _parse_iso(params["due_at"])
        except (ValueError, TypeError) as e:
            return _err("invalid_due_at", f"due_at không hợp lệ: {e}")

    new_status = params.get("status")

    from app.core.errors import JarvisError

    try:
        if patch_data:
            patch = TodoPartialUpdate.model_validate(patch_data)
            todo = await todo_service.patch_todo(db, todo_id, user_id, patch, commit=False)
        else:
            todo = await todo_service.get_todo(db, todo_id, user_id)

        # Use dedicated methods for status transitions — they set/clear completed_at correctly
        if new_status == "completed":
            todo = await todo_service.complete_todo(db, todo_id, user_id, commit=False)
        elif new_status == "pending":
            todo = await todo_service.uncomplete_todo(db, todo_id, user_id, commit=False)
        elif new_status in ("in_progress", "cancelled"):
            status_patch = TodoPartialUpdate.model_validate({"status": new_status})
            todo = await todo_service.patch_todo(db, todo_id, user_id, status_patch, commit=False)
    except JarvisError:
        return _err("todo_not_found", "Todo không tồn tại.")

    # Apply tag mutations after main update
    add_tags = params.get("add_tags") or []
    remove_tags = params.get("remove_tags") or []
    if add_tags or remove_tags:
        current = set(todo.tags)
        current.update(add_tags)
        current -= set(remove_tags)
        tag_patch = TodoPartialUpdate.model_validate({"tags": list(current)})
        todo = await todo_service.patch_todo(db, todo_id, user_id, tag_patch, commit=False)

    status_note = f" → {new_status}" if new_status else ""
    return _ok(
        todo.model_dump(mode="json"),
        f"Đã cập nhật việc '{todo.title}'{status_note}.",
    )


# ── create_note ───────────────────────────────────────────────────────────────


async def execute_create_note(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    title = params.get("title", "").strip()
    if not title:
        return _err("missing_title", "title là bắt buộc.")

    data = NoteCreate(
        title=title,
        content=params.get("content", ""),
        tags=params.get("tags", []),
        pinned=params.get("pinned", False),
        source="chat",
    )
    note = await note_service.create_note(db, user_id, data, commit=False)
    return _ok(note.model_dump(mode="json"), f"Đã tạo ghi chú '{title}'.")


# ── search_notes ──────────────────────────────────────────────────────────────


async def execute_search_notes(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    q = params.get("q") or None
    pinned_only = params.get("pinned_only", False)
    limit = min(int(params.get("limit", 20)), 50)

    notes, _ = await note_service.list_notes(
        db,
        user_id,
        pinned=True if pinned_only else None,
        q=q,
        limit=limit,
        cursor=None,
    )
    summary = f"Tìm thấy {len(notes)} ghi chú"
    if q:
        summary += f" cho '{q}'"
    return _ok(
        {"notes": [n.model_dump(mode="json") for n in notes], "count": len(notes)}, summary + "."
    )


# ── save_memory ───────────────────────────────────────────────────────────────


async def execute_save_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    content = (params.get("content") or "").strip()
    if len(content) < 3:
        return _err("invalid_content", "content phải có ít nhất 3 ký tự.")

    memory_type = params.get("memory_type", "fact")
    valid_types = {"fact", "preference", "rule", "relation", "goal", "other"}
    if memory_type not in valid_types:
        return _err(
            "invalid_memory_type", f"memory_type phải là một trong: {', '.join(valid_types)}."
        )

    try:
        importance = int(params.get("importance", 5))
    except (TypeError, ValueError):
        return _err("invalid_importance", "importance phải là số nguyên từ 1 đến 10.")
    if not (1 <= importance <= 10):
        return _err("invalid_importance", "importance phải từ 1 đến 10.")

    data = MemoryCreate(content=content, memory_type=memory_type, importance=importance)
    out = await memory_service.create_committed(user_id, data)
    return _ok(
        out.model_dump(mode="json"),
        f"Đã ghi nhớ: {content[:60]}{'...' if len(content) > 60 else ''}.",
    )


# ── search_memory ─────────────────────────────────────────────────────────────


async def execute_search_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    query = (params.get("query") or "").strip()
    if not query:
        return _err("missing_query", "query là bắt buộc.")

    try:
        limit = int(params.get("limit", 5))
        min_similarity = max(0.0, min(1.0, float(params.get("min_similarity", 0.7))))
    except (TypeError, ValueError):
        return _err(
            "invalid_params", "limit phải là số nguyên, min_similarity phải là số thực 0-1."
        )
    if not (1 <= limit <= 10):
        return _err("invalid_params", "limit phải là số nguyên từ 1 đến 10.")
    memory_type = params.get("memory_type") or None

    memories = await memory_service.search_semantic(
        db, user_id, query, limit, min_similarity, memory_type
    )
    return _ok(
        {"memories": [m.model_dump(mode="json") for m in memories], "count": len(memories)},
        f"Tìm thấy {len(memories)} memory liên quan đến '{query}'.",
    )


# ── forget_memory ─────────────────────────────────────────────────────────────


async def execute_forget_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
) -> ToolResult:
    try:
        memory_id = uuid.UUID(params["memory_id"])
    except (KeyError, ValueError):
        return _err("invalid_memory_id", "memory_id không hợp lệ hoặc thiếu.")

    deleted = await memory_service.forget_committed(memory_id, user_id)
    if not deleted:
        return _err("memory_not_found", "Memory không tồn tại hoặc đã bị xóa.")
    return _ok({"memory_id": str(memory_id)}, "Đã xóa memory.")


# ── create_reminder ───────────────────────────────────────────────────────────


async def execute_create_reminder(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
    user_tz: str = "UTC",
) -> ToolResult:
    title = params.get("title", "").strip()
    if not title:
        return _err("missing_title", "title là bắt buộc.")

    raw_remind_at = params.get("remind_at")
    if not raw_remind_at:
        return _err("missing_remind_at", "remind_at là bắt buộc — hỏi user giờ cụ thể.")

    try:
        remind_at = await parse_datetime(str(raw_remind_at), user_tz)
    except ParseDatetimeError as e:
        return _err("invalid_remind_at", f"Không thể parse remind_at: {e}")

    from app.core.errors import JarvisError

    try:
        data = ReminderCreate(
            title=title,
            remind_at=remind_at,
            description=params.get("description"),
            source="chat",
        )
        reminder = await reminder_service.create_reminder(db, user_id, data, commit=False)
    except JarvisError as e:
        return _err(e.code, e.message)

    return _ok(
        reminder.model_dump(mode="json"),
        f"Đã đặt lời nhắc '{title}' lúc {raw_remind_at}.",
    )


# ── list_reminders ────────────────────────────────────────────────────────────


async def execute_list_reminders(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
    user_tz: str = "UTC",
) -> ToolResult:
    # Distinguish missing key (→ default "pending") from explicit None (→ all statuses)
    status = params["status"] if "status" in params else "pending"  # noqa: SIM401
    _valid_statuses = {"pending", "sending", "sent", "failed", "cancelled", "due"}
    if status is not None and status not in _valid_statuses:
        return _err(
            "invalid_status",
            f"status phải là một trong: {', '.join(sorted(_valid_statuses))} hoặc null.",
        )
    limit = min(int(params.get("limit", 10)), 50)

    reminders, _ = await reminder_service.list_reminders(
        db, user_id, status=status, limit=limit, cursor=None
    )
    return _ok(
        {"reminders": [r.model_dump(mode="json") for r in reminders], "count": len(reminders)},
        f"Tìm thấy {len(reminders)} lời nhắc (status: {status}).",
    )


# ── list_calendar_events ─────────────────────────────────────────────────────


def _format_event_line(event: Any, tz: ZoneInfo) -> str:
    if event.is_all_day:
        when = "Cả ngày"
    else:
        start_local = event.start_at.astimezone(tz) if event.start_at else None
        when = start_local.strftime("%H:%M") if start_local else "?"
    return f"{when} - {event.summary or '(không có tiêu đề)'}"


async def execute_list_calendar_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
    user_tz: str = "UTC",
) -> ToolResult:
    tz = ZoneInfo(user_tz)
    now_local = datetime.now(tz)
    today_start = datetime.combine(now_local.date(), time.min, tzinfo=tz)

    range_type = params.get("range", "today")
    if range_type == "today":
        time_min_local, time_max_local = today_start, today_start + timedelta(days=1)
    elif range_type == "tomorrow":
        time_min_local = today_start + timedelta(days=1)
        time_max_local = today_start + timedelta(days=2)
    elif range_type == "week":
        time_min_local, time_max_local = today_start, today_start + timedelta(days=7)
    elif range_type == "custom":
        try:
            time_min_local = _parse_iso(params.get("time_min")) or today_start
            time_max_local = _parse_iso(params.get("time_max")) or (today_start + timedelta(days=1))
        except (ValueError, TypeError) as e:
            return _err("invalid_time_range", f"time_min/time_max không hợp lệ: {e}")
    else:
        return _err("invalid_range", "range phải là một trong: today, tomorrow, week, custom.")

    events = await google_calendar_service.list_events(
        db, user_id, time_min_local.astimezone(UTC), time_max_local.astimezone(UTC), user_tz
    )

    from app.schemas.google import CalendarEventOut

    return _ok(
        {"events": [CalendarEventOut.model_validate(e).model_dump(mode="json") for e in events]},
        f"Có {len(events)} sự kiện: " + "; ".join(_format_event_line(e, tz) for e in events)
        if events
        else "Không có sự kiện nào trong khoảng thời gian này.",
    )


# ── get_today_summary ─────────────────────────────────────────────────────────


async def execute_get_today_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, Any],
    user_tz: str = "UTC",
) -> ToolResult:
    data = await dashboard_service.get_today_dashboard(db, user_id, user_tz)

    tz = ZoneInfo(user_tz)
    todos_count = data["todos_count"]["today"]
    overdue_count = data["todos_count"]["overdue"]
    reminders_count = len(data["reminders_upcoming"])
    events = data["events_today"]

    parts = [f"{todos_count} việc cần làm hôm nay"]
    if overdue_count:
        parts.append(f"{overdue_count} việc quá hạn")
    parts.append(f"{reminders_count} lời nhắc sắp tới")
    if events:
        parts.append(
            f"{len(events)} sự kiện lịch ({'; '.join(_format_event_line(e, tz) for e in events)})"
        )
    else:
        parts.append("không có sự kiện lịch")

    return _ok(
        {
            "todos_today": [t.model_dump(mode="json") for t in data["todos_today"]],
            "todos_count": data["todos_count"],
            "reminders_upcoming": [r.model_dump(mode="json") for r in data["reminders_upcoming"]],
            "events_today": [e.model_dump(mode="json") for e in events],
            "memories_count": data["memories_count"],
        },
        "Hôm nay: " + ", ".join(parts) + ".",
    )


# ── dispatch ──────────────────────────────────────────────────────────────────

_EXECUTOR_MAP = {
    "create_todo": execute_create_todo,
    "list_todos": execute_list_todos,
    "update_todo": execute_update_todo,
    "create_note": execute_create_note,
    "search_notes": execute_search_notes,
    "save_memory": execute_save_memory,
    "search_memory": execute_search_memory,
    "forget_memory": execute_forget_memory,
    "create_reminder": execute_create_reminder,
    "list_reminders": execute_list_reminders,
    "list_calendar_events": execute_list_calendar_events,
    "get_today_summary": execute_get_today_summary,
}


async def dispatch(
    tool_name: str,
    params: dict[str, Any],
    db: AsyncSession,
    user_id: uuid.UUID,
    user_tz: str = "UTC",
) -> ToolResult:
    """Route a tool call to the appropriate executor."""
    executor = _EXECUTOR_MAP.get(tool_name)
    if executor is None:
        return _err("unknown_tool", f"Tool '{tool_name}' không tồn tại.")
    _needs_tz = {
        "list_todos",
        "create_reminder",
        "list_reminders",
        "list_calendar_events",
        "get_today_summary",
    }
    try:
        if tool_name in _needs_tz:
            return await executor(db, user_id, params, user_tz)  # type: ignore[call-arg]
        return await executor(db, user_id, params)
    except SQLAlchemyError:
        raise  # propagate so orchestrator can abort turn with a clean session
    except Exception as e:
        log.exception("tool.executor_error", tool=tool_name)
        return _err("executor_error", str(e))
