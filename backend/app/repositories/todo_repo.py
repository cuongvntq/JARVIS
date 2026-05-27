"""Todo repository — DB queries only."""

import base64
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.todo import Todo


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
) -> tuple[list[Todo], str | None]:
    now = datetime.now(UTC)

    query = select(Todo).where(
        Todo.user_id == user_id,
        Todo.deleted_at.is_(None),
    )

    if status:
        query = query.where(Todo.status == status)

    if filter_type == "today":
        from sqlalchemy import Date, cast

        today_date = now.date()
        query = query.where(
            cast(Todo.due_at, Date) == today_date,
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
            cursor_str = base64.b64decode(cursor).decode()
            cursor_dt = datetime.fromisoformat(cursor_str)
            query = query.where(Todo.created_at < cursor_dt)
        except Exception:
            pass

    query = query.order_by(Todo.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = base64.b64encode(rows[-1].created_at.isoformat().encode()).decode()

    return rows, next_cursor


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
