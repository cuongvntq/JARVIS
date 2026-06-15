"""CalendarSyncState repository — DB queries only."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_sync_state import CalendarSyncState


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[CalendarSyncState]:
    result = await db.execute(
        select(CalendarSyncState)
        .where(CalendarSyncState.user_id == user_id)
        .order_by(CalendarSyncState.calendar_summary.asc())
    )
    return list(result.scalars())


async def list_selected(db: AsyncSession, user_id: uuid.UUID) -> list[CalendarSyncState]:
    result = await db.execute(
        select(CalendarSyncState).where(
            CalendarSyncState.user_id == user_id,
            CalendarSyncState.selected.is_(True),
        )
    )
    return list(result.scalars())


async def get(
    db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str
) -> CalendarSyncState | None:
    result = await db.execute(
        select(CalendarSyncState).where(
            CalendarSyncState.user_id == user_id,
            CalendarSyncState.google_calendar_id == google_calendar_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert_from_calendar_list(
    db: AsyncSession, user_id: uuid.UUID, calendars: list[dict[str, object]]
) -> tuple[list[CalendarSyncState], list[str]]:
    """Upsert sync states from Google calendarList.list().

    Selection rule: a newly-created state gets `selected=is_primary`; an existing
    state keeps its `selected`/`sync_token`/horizon fields untouched (only
    summary/time_zone/access_role/is_primary are refreshed).

    Returns (states_for_incoming_calendars, vanished_google_calendar_ids) — the
    latter are calendars present in `calendar_sync_states` but absent from
    `calendars` (caller is responsible for deleting their cached events).
    """
    existing = await list_for_user(db, user_id)
    existing_by_id = {s.google_calendar_id: s for s in existing}
    incoming_ids = {str(c["google_calendar_id"]) for c in calendars}

    states: list[CalendarSyncState] = []
    for c in calendars:
        google_calendar_id = str(c["google_calendar_id"])
        state = existing_by_id.get(google_calendar_id)
        is_primary = bool(c.get("is_primary", False))
        if state is None:
            state = CalendarSyncState(
                user_id=user_id,
                google_calendar_id=google_calendar_id,
                calendar_summary=str(c["calendar_summary"]),
                is_primary=is_primary,
                time_zone=c.get("time_zone"),
                access_role=c.get("access_role"),
                selected=is_primary,
            )
            db.add(state)
        else:
            state.calendar_summary = str(c["calendar_summary"])
            state.is_primary = is_primary
            state.time_zone = c.get("time_zone")  # type: ignore[assignment]
            state.access_role = c.get("access_role")  # type: ignore[assignment]
        states.append(state)

    vanished_ids = [gcid for gcid in existing_by_id if gcid not in incoming_ids]
    if vanished_ids:
        await db.execute(
            delete(CalendarSyncState).where(
                CalendarSyncState.user_id == user_id,
                CalendarSyncState.google_calendar_id.in_(vanished_ids),
            )
        )

    await db.flush()
    for state in states:
        await db.refresh(state)
    return states, vanished_ids


async def set_selected(db: AsyncSession, user_id: uuid.UUID, calendar_ids: list[str]) -> list[str]:
    """Set `selected` per `calendar_ids`. Returns google_calendar_id list that
    transitioned from selected -> unselected (caller must clear their cache)."""
    states = await list_for_user(db, user_id)
    selected_set = set(calendar_ids)
    newly_unselected: list[str] = []
    for state in states:
        new_selected = state.google_calendar_id in selected_set
        if state.selected and not new_selected:
            newly_unselected.append(state.google_calendar_id)
        state.selected = new_selected
    await db.flush()
    return newly_unselected


async def update_sync_state(
    db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str, **kwargs: object
) -> None:
    kwargs["updated_at"] = datetime.now(UTC)
    await db.execute(
        update(CalendarSyncState)
        .where(
            CalendarSyncState.user_id == user_id,
            CalendarSyncState.google_calendar_id == google_calendar_id,
        )
        .values(**kwargs)
    )


async def clear_sync_token(db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str) -> None:
    """Reset sync bookkeeping so the next sync runs a full resync from scratch."""
    await update_sync_state(
        db,
        user_id,
        google_calendar_id,
        sync_token=None,
        horizon_until=None,
        last_full_synced_at=None,
    )


async def delete_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(CalendarSyncState).where(CalendarSyncState.user_id == user_id))
