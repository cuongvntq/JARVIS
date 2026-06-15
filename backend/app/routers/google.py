"""Google Calendar OAuth + read-only sync endpoints (Sprint 8-9)."""

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.google import (
    CalendarEventOut,
    CalendarSelectionIn,
    CalendarSelectionOut,
    GoogleCalendarOut,
    GoogleConnectOut,
    GoogleStatusOut,
    SyncResultOut,
)
from app.services import google_calendar_service, google_oauth_service

# Default /events window when time_min/time_max are omitted (matches dashboard "upcoming" range).
_DEFAULT_EVENTS_WINDOW = timedelta(days=14)

router = APIRouter()


@router.post("/connect", response_model=GoogleConnectOut)
async def connect(
    current_user: User = Depends(get_current_user),
) -> GoogleConnectOut:
    authorize_url = await google_oauth_service.start_connect(current_user.id)
    return GoogleConnectOut(authorize_url=authorize_url)


@router.get("/status", response_model=GoogleStatusOut)
async def status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoogleStatusOut:
    data = await google_oauth_service.get_status(db, current_user.id)
    return GoogleStatusOut.model_validate(data)


@router.delete("/disconnect", status_code=204)
async def disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await google_oauth_service.disconnect(db, current_user.id)
    return Response(status_code=204)


@router.get("/calendars", response_model=list[GoogleCalendarOut])
async def list_calendars(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GoogleCalendarOut]:
    items = await google_calendar_service.list_calendars(db, current_user.id)
    return [GoogleCalendarOut.model_validate(item) for item in items]


@router.get("/events", response_model=list[CalendarEventOut])
async def list_events(
    time_min: datetime | None = Query(default=None),
    time_max: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarEventOut]:
    now = datetime.now(UTC)
    resolved_min = time_min or now
    resolved_max = time_max or (now + _DEFAULT_EVENTS_WINDOW)
    user_tz = current_user.timezone or "Asia/Ho_Chi_Minh"
    events = await google_calendar_service.list_events(
        db, current_user.id, resolved_min, resolved_max, user_tz
    )
    return [CalendarEventOut.model_validate(event) for event in events]


@router.post("/sync", response_model=SyncResultOut)
async def sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncResultOut:
    if google_calendar_service.is_sync_running(current_user.id):
        return SyncResultOut(status="already_running", upserted=0, deleted=0, failed=0)

    result = await google_calendar_service.sync_all_selected(db, current_user.id)
    sync_status: Literal["synced", "partial"] = "partial" if result["failed"] > 0 else "synced"
    return SyncResultOut(
        status=sync_status,
        upserted=result["upserted"],
        deleted=result["deleted"],
        failed=result["failed"],
        synced_at=datetime.now(UTC),
        errors=result["errors"],
    )


@router.get("/selected", response_model=list[CalendarSelectionOut])
async def get_selected(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarSelectionOut]:
    states = await google_calendar_service.get_selected_calendars(db, current_user.id)
    return [CalendarSelectionOut.model_validate(state) for state in states]


@router.put("/selected", response_model=list[CalendarSelectionOut])
async def set_selected(
    body: CalendarSelectionIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarSelectionOut]:
    await google_calendar_service.set_selected_calendars(db, current_user.id, body.calendar_ids)
    states = await google_calendar_service.get_selected_calendars(db, current_user.id)
    return [CalendarSelectionOut.model_validate(state) for state in states]
