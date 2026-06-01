"""Todo repository — DB queries only."""

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.todo import Todo


def _today_range_utc(user_tz: str) -> tuple[datetime, datetime]:
    """Return (start_of_today_utc, start_of_tomorrow_utc) in the user's timezone."""
    try:
        tz = ZoneInfo(user_tz)
    except (ZoneInfoNotFoundError, KeyError):
        tz = ZoneInfo("UTC")
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


async def get_by_id(db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID) -> Todo | None:
    result = await db.execute(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == user_id,
            Todo.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    filter_type: str | None = None,
    q: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
    user_tz: str = "UTC",
) -> tuple[list[Todo], str | None]:
    now = datetime.now(UTC)

    query = select(Todo).where(
        Todo.user_id == user_id,
        Todo.deleted_at.is_(None),
    )

    if status:
        query = query.where(Todo.status == status)

    if filter_type == "today":
        start_utc, end_utc = _today_range_utc(user_tz)
        query = query.where(
            Todo.due_at >= start_utc,
            Todo.due_at < end_utc,
            Todo.status.in_(["pending", "in_progress"]),
        )
    elif filter_type == "upcoming":
        query = query.where(
            Todo.due_at > now,
            Todo.status.in_(["pending", "in_progress"]),
        )
    elif filter_type == "overdue":
        query = query.where(
            Todo.due_at < now,
            Todo.status.in_(["pending", "in_progress"]),
        )
    elif filter_type == "completed":
        query = query.where(Todo.status == "completed")
    # "all" or None: no extra filter

    if q:
        query = query.where(Todo.title.ilike(f"%{q}%"))

    if cursor:
        try:
            raw = base64.b64decode(cursor).decode()
            cursor_data = json.loads(raw)
            cursor_dt = datetime.fromisoformat(cursor_data["created_at"])
            cursor_id: uuid.UUID | None = (
                uuid.UUID(cursor_data["id"]) if cursor_data.get("id") else None
            )
            # Composite cursor: (created_at DESC, id DESC)
            same_ts = Todo.created_at == cursor_dt
            id_tiebreak = and_(same_ts, Todo.id < cursor_id) if cursor_id is not None else None
            conditions = [Todo.created_at < cursor_dt]
            if id_tiebreak is not None:
                conditions.append(id_tiebreak)
            query = query.where(or_(*conditions))
        except Exception:
            pass

    # id desc as tie-breaker so rows with identical created_at are stable across pages
    query = query.order_by(Todo.created_at.desc(), Todo.id.desc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        cursor_payload = json.dumps({"created_at": last.created_at.isoformat(), "id": str(last.id)})
        next_cursor = base64.b64encode(cursor_payload.encode()).decode()

    return rows, next_cursor


async def count_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    filter_type: str | None = None,
    user_tz: str = "UTC",
) -> int:
    """Return accurate count for dashboard without the limit=100 cap."""
    now = datetime.now(UTC)
    query = (
        select(func.count())
        .select_from(Todo)
        .where(Todo.user_id == user_id, Todo.deleted_at.is_(None))
    )
    if filter_type == "today":
        start_utc, end_utc = _today_range_utc(user_tz)
        query = query.where(
            Todo.due_at >= start_utc,
            Todo.due_at < end_utc,
            Todo.status.in_(["pending", "in_progress"]),
        )
    elif filter_type == "upcoming":
        query = query.where(
            Todo.due_at > now,
            Todo.status.in_(["pending", "in_progress"]),
        )
    elif filter_type == "overdue":
        query = query.where(
            Todo.due_at < now,
            Todo.status.in_(["pending", "in_progress"]),
        )
    return (await db.execute(query)).scalar_one()


async def create(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Todo:
    todo = Todo(user_id=user_id, **kwargs)
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return todo


async def update_fields(db: AsyncSession, todo_id: uuid.UUID, **kwargs) -> None:
    """Partial update — only sets provided fields plus updated_at."""
    kwargs["updated_at"] = datetime.now(UTC)
    await db.execute(update(Todo).where(Todo.id == todo_id).values(**kwargs))


async def complete(db: AsyncSession, todo_id: uuid.UUID) -> None:
    await db.execute(
        update(Todo)
        .where(Todo.id == todo_id)
        .values(status="completed", completed_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    )


async def uncomplete(db: AsyncSession, todo_id: uuid.UUID) -> None:
    await db.execute(
        update(Todo)
        .where(Todo.id == todo_id)
        .values(status="pending", completed_at=None, updated_at=datetime.now(UTC))
    )


async def soft_delete(db: AsyncSession, todo_id: uuid.UUID) -> None:
    await db.execute(update(Todo).where(Todo.id == todo_id).values(deleted_at=datetime.now(UTC)))
