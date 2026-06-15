"""CalendarEvent repository — DB queries only.

list_in_range/list_today implement the portable overlap query from
docs/sprint9-plan.md A2: a coarse SQL candidate query (works on both Postgres
and SQLite) followed by a Python-side refine pass for all-day events that
applies the exact half-open overlap using `user_tz`.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent


async def upsert(
    db: AsyncSession,
    user_id: uuid.UUID,
    google_calendar_id: str,
    google_event_id: str,
    **fields: object,
) -> CalendarEvent:
    result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.google_calendar_id == google_calendar_id,
            CalendarEvent.google_event_id == google_event_id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        event = CalendarEvent(
            user_id=user_id,
            google_calendar_id=google_calendar_id,
            google_event_id=google_event_id,
            **fields,
        )
        db.add(event)
    else:
        for key, value in fields.items():
            setattr(event, key, value)
    await db.flush()
    return event


async def delete_by_google_id(
    db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str, google_event_id: str
) -> None:
    await db.execute(
        delete(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.google_calendar_id == google_calendar_id,
            CalendarEvent.google_event_id == google_event_id,
        )
    )


async def delete_all_for_calendar(
    db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str
) -> None:
    await db.execute(
        delete(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.google_calendar_id == google_calendar_id,
        )
    )


async def delete_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(CalendarEvent).where(CalendarEvent.user_id == user_id))


def _effective_start(event: CalendarEvent, tz: ZoneInfo) -> datetime:
    if event.start_at is not None:
        return event.start_at
    assert event.start_date is not None
    return datetime.combine(event.start_date, time.min, tzinfo=tz)


async def list_in_range(
    db: AsyncSession,
    user_id: uuid.UUID,
    time_min: datetime,
    time_max: datetime,
    user_tz: str,
) -> list[CalendarEvent]:
    tz = ZoneInfo(user_tz)

    # Coarse local-date margin for the all-day candidate query — refined below.
    local_range_start_date: date = time_min.astimezone(tz).date() - timedelta(days=1)
    local_range_end_date: date = time_max.astimezone(tz).date() + timedelta(days=1)

    timed_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.is_all_day.is_(False),
            CalendarEvent.start_at < time_max,
            sa.func.coalesce(CalendarEvent.end_at, CalendarEvent.start_at) > time_min,
        )
    )
    allday_result = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.is_all_day.is_(True),
            CalendarEvent.start_date <= local_range_end_date,
            sa.func.coalesce(CalendarEvent.end_date, CalendarEvent.start_date)
            >= local_range_start_date,
        )
    )

    events = list(timed_result.scalars())

    for event in allday_result.scalars():
        assert event.start_date is not None
        start_local = datetime.combine(event.start_date, time.min, tzinfo=tz)
        end_date = event.end_date or (event.start_date + timedelta(days=1))
        end_local = datetime.combine(end_date, time.min, tzinfo=tz)
        if start_local < time_max and end_local > time_min:
            events.append(event)

    events.sort(key=lambda e: _effective_start(e, tz))
    return events


async def list_today(db: AsyncSession, user_id: uuid.UUID, user_tz: str) -> list[CalendarEvent]:
    tz = ZoneInfo(user_tz)
    now_local = datetime.now(tz)
    start_of_day = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    start_of_next_day = start_of_day + timedelta(days=1)
    return await list_in_range(
        db, user_id, start_of_day.astimezone(UTC), start_of_next_day.astimezone(UTC), user_tz
    )
