"""Dashboard aggregation service."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import memory_repo, reminder_repo
from app.schemas.reminder import ReminderOut
from app.services import todo_service


async def get_today_dashboard(
    db: AsyncSession,
    user_id: uuid.UUID,
    user_tz: str = "UTC",
) -> dict:
    """Aggregate dashboard data for the current user."""
    # todos today + counts
    todos_today, _ = await todo_service.list_todos(
        db,
        user_id,
        status=None,
        filter_type="today",
        q=None,
        limit=100,
        cursor=None,
        user_tz=user_tz,
    )
    overdue, _ = await todo_service.list_todos(
        db,
        user_id,
        status=None,
        filter_type="overdue",
        q=None,
        limit=100,
        cursor=None,
        user_tz=user_tz,
    )
    upcoming, _ = await todo_service.list_todos(
        db,
        user_id,
        status=None,
        filter_type="upcoming",
        q=None,
        limit=100,
        cursor=None,
        user_tz=user_tz,
    )

    # reminders upcoming (top 5)
    reminder_rows = await reminder_repo.list_upcoming_for_dashboard(db, user_id, limit=5)
    reminders_upcoming = [ReminderOut.model_validate(r) for r in reminder_rows]

    # memories count
    memories_count = await memory_repo.count_active(db, user_id)

    return {
        "todos_today": todos_today,
        "todos_count": {
            "today": len(todos_today),
            "overdue": len(overdue),
            "upcoming": len(upcoming),
        },
        "reminders_upcoming": reminders_upcoming,
        "memories_count": memories_count,
        "as_of": datetime.now(UTC).isoformat(),
    }
