"""Reminder repository — DB queries only."""

import base64
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder


async def get_by_id(
    db: AsyncSession, reminder_id: uuid.UUID, user_id: uuid.UUID
) -> Reminder | None:
    result = await db.execute(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id,
            Reminder.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_reminders(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> tuple[list[Reminder], str | None]:
    query = select(Reminder).where(
        Reminder.user_id == user_id,
        Reminder.deleted_at.is_(None),
    )

    if status:
        query = query.where(Reminder.status == status)

    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode())
            cursor_dt = datetime.fromisoformat(cursor_data["remind_at"])
            cursor_id = uuid.UUID(cursor_data["id"])
            # Correct keyset for (remind_at ASC, id ASC): rows strictly after the cursor
            query = query.where(
                or_(
                    Reminder.remind_at > cursor_dt,
                    and_(Reminder.remind_at == cursor_dt, Reminder.id > cursor_id),
                )
            )
        except Exception:
            pass

    query = query.order_by(Reminder.remind_at.asc(), Reminder.id.asc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        payload = json.dumps({"remind_at": last.remind_at.isoformat(), "id": str(last.id)})
        next_cursor = base64.b64encode(payload.encode()).decode()

    return rows, next_cursor


async def create(db: AsyncSession, user_id: uuid.UUID, **kwargs: object) -> Reminder:
    reminder = Reminder(user_id=user_id, **kwargs)
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    return reminder


async def update_fields(db: AsyncSession, reminder_id: uuid.UUID, **kwargs: object) -> None:
    kwargs["updated_at"] = datetime.now(UTC)
    await db.execute(update(Reminder).where(Reminder.id == reminder_id).values(**kwargs))


async def soft_delete(db: AsyncSession, reminder_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    await db.execute(
        update(Reminder)
        .where(Reminder.id == reminder_id)
        .values(deleted_at=now, status="cancelled", updated_at=now)
    )


async def get_pending_due(db: AsyncSession, before_utc: datetime) -> list[Reminder]:
    """Return all pending reminders due before before_utc (for scheduler claim)."""
    result = await db.execute(
        select(Reminder).where(
            Reminder.status == "pending",
            Reminder.remind_at <= before_utc,
            Reminder.deleted_at.is_(None),
        )
    )
    return list(result.scalars())


async def list_upcoming_for_dashboard(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 5
) -> list[Reminder]:
    """Upcoming reminders: status pending/sending, remind_at >= now, for dashboard."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(Reminder)
        .where(
            Reminder.user_id == user_id,
            Reminder.status.in_(["pending", "sending"]),
            Reminder.remind_at >= now,
            Reminder.deleted_at.is_(None),
        )
        .order_by(Reminder.remind_at.asc())
        .limit(limit)
    )
    return list(result.scalars())


async def claim_pending_due(db: AsyncSession, before_utc: datetime) -> list[Reminder]:
    """Atomically claim pending due reminders by setting status='sending'.

    Single UPDATE...RETURNING statement prevents duplicate sends when multiple
    scheduler instances run concurrently (each instance claims a disjoint set).
    """
    stmt = (
        update(Reminder)
        .where(
            Reminder.status == "pending",
            Reminder.remind_at <= before_utc,
            Reminder.deleted_at.is_(None),
        )
        .values(status="sending", updated_at=datetime.now(UTC))
        .returning(Reminder)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    return list(result.scalars())
