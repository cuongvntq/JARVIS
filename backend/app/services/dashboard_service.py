"""Dashboard aggregation service."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import calendar_event_repo, memory_repo, reminder_repo
from app.schemas.google import CalendarEventOut
from app.schemas.reminder import ReminderOut
from app.services import todo_service


async def get_today_dashboard(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_tz: str = "UTC",
) -> dict[str, Any]:
    """Aggregate dashboard data for the current user."""
    # First page of today's todos for display (up to 20)
    todos_today, _ = await todo_service.list_todos(
        db,
        user_id,
        status=None,
        filter_type="today",
        q=None,
        limit=20,
        cursor=None,
        user_tz=user_tz,
    )

    # Accurate counts via dedicated COUNT queries (no limit=100 cap)
    count_today, count_overdue, count_upcoming = (
        await todo_service.count_todos(db, user_id, filter_type="today", user_tz=user_tz),
        await todo_service.count_todos(db, user_id, filter_type="overdue", user_tz=user_tz),
        await todo_service.count_todos(db, user_id, filter_type="upcoming", user_tz=user_tz),
    )

    # reminders upcoming (top 5)
    reminder_rows = await reminder_repo.list_upcoming_for_dashboard(db, user_id, limit=5)
    reminders_upcoming = [ReminderOut.model_validate(r) for r in reminder_rows]

    # memories count
    memories_count = await memory_repo.count_active(db, user_id)

    # calendar events happening today (local timezone)
    events_today_rows = await calendar_event_repo.list_today(db, user_id, user_tz)
    events_today = [CalendarEventOut.model_validate(e) for e in events_today_rows]

    return {
        "todos_today": todos_today,
        "todos_count": {
            "today": count_today,
            "overdue": count_overdue,
            "upcoming": count_upcoming,
        },
        "reminders_upcoming": reminders_upcoming,
        "memories_count": memories_count,
        "events_today": events_today,
        "as_of": datetime.now(UTC).isoformat(),
    }
