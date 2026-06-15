"""Google Calendar API access + read-only sync (Sprint 8-9).

Sprint 9 adds incremental/full sync of events into the local cache
(`calendar_events` / `calendar_sync_states`) — see docs/sprint9-plan.md.
"""

from __future__ import annotations

import asyncio
import urllib.parse
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.models.calendar_event import CalendarEvent
from app.models.calendar_sync_state import CalendarSyncState
from app.repositories import calendar_event_repo, calendar_sync_repo
from app.services import google_oauth_service

log = structlog.get_logger()

_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
_EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"

# Rolling horizon (docs/sprint9-plan.md A3): full sync covers [now-30d, now+365d];
# a full refresh is triggered again once horizon_until gets within 330d of now.
_FULL_SYNC_PAST = timedelta(days=30)
_FULL_SYNC_FUTURE = timedelta(days=365)
_HORIZON_REFRESH_THRESHOLD = timedelta(days=330)


class _SyncTokenExpiredError(Exception):
    """Raised when Google returns 410 Gone for an expired syncToken."""


# ── Low-level HTTP helpers ────────────────────────────────────────────────────


async def _request(
    method: str, url: str, access_token: str, **kwargs: Any
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30) as client:
        return await client.request(
            method, url, headers={"Authorization": f"Bearer {access_token}"}, **kwargs
        )


async def _authed_request(
    db: AsyncSession, user_id: uuid.UUID, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    """Issue a request with the user's Google access token, handling 401.

    A 401 can occur even when the cached token has not expired (revoked
    server-side). Force one refresh and retry; if it still fails, clear local
    connection state so the UI prompts a reconnect instead of looping forever.
    """
    access_token = await google_oauth_service.get_valid_access_token(db, user_id)
    resp = await _request(method, url, access_token, **kwargs)

    if resp.status_code == 401:
        log.info("google.calendar_401_force_refresh", user_id=str(user_id))
        access_token = await google_oauth_service.force_refresh_access_token(db, user_id)
        resp = await _request(method, url, access_token, **kwargs)
        if resp.status_code == 401:
            await google_oauth_service.clear_local_connection(db, user_id)
            raise JarvisError(401, "google_reauth_required", "Cần kết nối lại Google Calendar")

    return resp


# ── Calendar list ──────────────────────────────────────────────────────────────


async def list_calendars(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return the user's calendar list (simple, single-page — used by Settings UI)."""
    resp = await _authed_request(db, user_id, "GET", _CALENDAR_LIST_URL)
    resp.raise_for_status()

    items = resp.json().get("items", [])
    return [
        {
            "id": item["id"],
            "summary": item.get("summary", ""),
            "primary": bool(item.get("primary", False)),
            "time_zone": item.get("timeZone"),
        }
        for item in items
    ]


async def _fetch_calendar_list(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Paginate calendarList.list (showHidden=true) to completion.

    Raises on any HTTP error mid-pagination — callers must NOT reconcile
    (delete) vanished calendars unless this returns successfully in full.
    """
    items: list[dict[str, Any]] = []
    params: dict[str, Any] = {"showHidden": "true", "maxResults": 250}
    while True:
        resp = await _authed_request(db, user_id, "GET", _CALENDAR_LIST_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("items", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        params = {"showHidden": "true", "maxResults": 250, "pageToken": page_token}

    return [
        {
            "google_calendar_id": item["id"],
            "calendar_summary": item.get("summary", ""),
            "is_primary": bool(item.get("primary", False)),
            "time_zone": item.get("timeZone"),
            "access_role": item.get("accessRole"),
        }
        for item in items
    ]


async def refresh_calendar_list(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[list[CalendarSyncState], list[str]]:
    """Fetch + upsert calendarList, reconciling vanished calendars (fetch-before-delete).

    Commits on success. On fetch failure, rolls back (no partial reconciliation)
    and re-raises.
    """
    calendars = await _fetch_calendar_list(db, user_id)
    try:
        states, vanished_ids = await calendar_sync_repo.upsert_from_calendar_list(
            db, user_id, calendars
        )
        for google_calendar_id in vanished_ids:
            await calendar_event_repo.delete_all_for_calendar(db, user_id, google_calendar_id)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return states, vanished_ids


# ── Event parsing ─────────────────────────────────────────────────────────────


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


async def _apply_event(
    db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str, item: dict[str, Any]
) -> str:
    """Upsert or delete one Google event item. Returns 'upserted' or 'deleted'."""
    google_event_id = item["id"]
    if item.get("status") == "cancelled":
        await calendar_event_repo.delete_by_google_id(
            db, user_id, google_calendar_id, google_event_id
        )
        return "deleted"

    start = item.get("start", {})
    end = item.get("end", {})
    is_all_day = "date" in start

    fields: dict[str, Any] = {
        "ical_uid": item.get("iCalUID"),
        "summary": item.get("summary", ""),
        "description": item.get("description"),
        "location": item.get("location"),
        "is_all_day": is_all_day,
        "status": item.get("status", "confirmed"),
        "html_link": item.get("htmlLink"),
        "etag": item.get("etag"),
        "google_updated_at": _parse_dt(item.get("updated")),
    }
    if is_all_day:
        fields.update(
            start_date=date.fromisoformat(start["date"]),
            end_date=date.fromisoformat(end["date"]) if end.get("date") else None,
            start_at=None,
            end_at=None,
            event_timezone=None,
        )
    else:
        fields.update(
            start_at=_parse_dt(start.get("dateTime")),
            end_at=_parse_dt(end.get("dateTime")),
            start_date=None,
            end_date=None,
            event_timezone=start.get("timeZone"),
        )

    await calendar_event_repo.upsert(db, user_id, google_calendar_id, google_event_id, **fields)
    return "upserted"


# ── Event sync ────────────────────────────────────────────────────────────────


def _common_event_params() -> dict[str, Any]:
    return {"singleEvents": "true", "showDeleted": "true", "maxResults": 250}


async def _fetch_events_pages(
    db: AsyncSession, user_id: uuid.UUID, google_calendar_id: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch all pages (HTTP only, no DB writes). Raises _SyncTokenExpiredError on 410."""
    url = _EVENTS_URL_TEMPLATE.format(
        calendar_id=urllib.parse.quote(google_calendar_id, safe="")
    )
    items: list[dict[str, Any]] = []
    next_sync_token: str | None = None
    page_params = dict(params)

    while True:
        resp = await _authed_request(db, user_id, "GET", url, params=page_params)
        if resp.status_code == 410:
            raise _SyncTokenExpiredError
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("items", []))
        if "nextSyncToken" in data:
            next_sync_token = data["nextSyncToken"]
        page_token = data.get("nextPageToken")
        if not page_token:
            break
        page_params = {**params, "pageToken": page_token}

    return items, next_sync_token


async def _apply_events_and_save(
    db: AsyncSession,
    user_id: uuid.UUID,
    sync_state: CalendarSyncState,
    items: list[dict[str, Any]],
    next_sync_token: str | None,
    *,
    full: bool,
    now: datetime,
) -> dict[str, int]:
    """Apply fetched items + update sync bookkeeping in one transaction."""
    upserted = deleted = 0
    try:
        if full:
            await calendar_event_repo.delete_all_for_calendar(
                db, user_id, sync_state.google_calendar_id
            )
        for item in items:
            applied = await _apply_event(db, user_id, sync_state.google_calendar_id, item)
            if applied == "deleted":
                deleted += 1
            else:
                upserted += 1

        update_fields: dict[str, Any] = {"sync_token": next_sync_token, "last_synced_at": now}
        if full:
            update_fields["horizon_until"] = now + _FULL_SYNC_FUTURE
            update_fields["last_full_synced_at"] = now
        await calendar_sync_repo.update_sync_state(
            db, user_id, sync_state.google_calendar_id, **update_fields
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {"upserted": upserted, "deleted": deleted}


async def _full_sync(
    db: AsyncSession, user_id: uuid.UUID, sync_state: CalendarSyncState, now: datetime
) -> dict[str, int]:
    params = _common_event_params()
    params["timeMin"] = (now - _FULL_SYNC_PAST).isoformat()
    params["timeMax"] = (now + _FULL_SYNC_FUTURE).isoformat()
    items, next_sync_token = await _fetch_events_pages(
        db, user_id, sync_state.google_calendar_id, params
    )
    return await _apply_events_and_save(
        db, user_id, sync_state, items, next_sync_token, full=True, now=now
    )


async def _incremental_sync(
    db: AsyncSession, user_id: uuid.UUID, sync_state: CalendarSyncState, now: datetime
) -> dict[str, int]:
    params = _common_event_params()
    params["syncToken"] = sync_state.sync_token
    items, next_sync_token = await _fetch_events_pages(
        db, user_id, sync_state.google_calendar_id, params
    )
    return await _apply_events_and_save(
        db, user_id, sync_state, items, next_sync_token, full=False, now=now
    )


async def sync_calendar(
    db: AsyncSession, user_id: uuid.UUID, sync_state: CalendarSyncState
) -> dict[str, int]:
    """Sync one calendar (full or incremental per rolling-horizon rule)."""
    now = datetime.now(UTC)
    needs_full = (
        sync_state.sync_token is None
        or sync_state.horizon_until is None
        or sync_state.horizon_until < now + _HORIZON_REFRESH_THRESHOLD
    )

    if needs_full:
        return await _full_sync(db, user_id, sync_state, now)

    try:
        return await _incremental_sync(db, user_id, sync_state, now)
    except _SyncTokenExpiredError:
        log.info(
            "google.sync_token_expired",
            user_id=str(user_id),
            calendar_id=sync_state.google_calendar_id,
        )
        return await _full_sync(db, user_id, sync_state, now)


# ── Orchestration + concurrency lock ────────────────────────────────────────────

_sync_locks: dict[uuid.UUID, asyncio.Lock] = {}


def _get_lock(user_id: uuid.UUID) -> asyncio.Lock:
    lock = _sync_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _sync_locks[user_id] = lock
    return lock


def is_sync_running(user_id: uuid.UUID) -> bool:
    lock = _sync_locks.get(user_id)
    return lock is not None and lock.locked()


async def sync_all_selected(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """Refresh calendar list, then sync every selected calendar.

    Serialized per-user via an asyncio.Lock so manual /sync and the scheduler
    job never run concurrently on the same calendars. Per-calendar errors are
    swallowed and reported in `errors` so one bad calendar doesn't block others.
    """
    lock = _get_lock(user_id)
    async with lock:
        try:
            await refresh_calendar_list(db, user_id)
        except Exception as e:
            log.error("google.calendarlist_refresh_failed", user_id=str(user_id), error=str(e))

        sync_states = await calendar_sync_repo.list_selected(db, user_id)
        upserted = deleted = failed = 0
        errors: list[dict[str, str]] = []
        for sync_state in sync_states:
            try:
                result = await sync_calendar(db, user_id, sync_state)
                upserted += result["upserted"]
                deleted += result["deleted"]
            except Exception as e:
                failed += 1
                errors.append({"calendar_id": sync_state.google_calendar_id, "message": str(e)})
                log.error(
                    "google.sync_calendar_failed",
                    user_id=str(user_id),
                    calendar_id=sync_state.google_calendar_id,
                    error=str(e),
                )

        return {"upserted": upserted, "deleted": deleted, "failed": failed, "errors": errors}


# ── Read access + selection ─────────────────────────────────────────────────────


async def list_events(
    db: AsyncSession,
    user_id: uuid.UUID,
    time_min: datetime,
    time_max: datetime,
    user_tz: str,
) -> list[CalendarEvent]:
    return await calendar_event_repo.list_in_range(db, user_id, time_min, time_max, user_tz)


async def get_selected_calendars(db: AsyncSession, user_id: uuid.UUID) -> list[CalendarSyncState]:
    return await calendar_sync_repo.list_for_user(db, user_id)


async def set_selected_calendars(
    db: AsyncSession, user_id: uuid.UUID, calendar_ids: list[str]
) -> None:
    """Update calendar selection. Newly-unselected calendars have their cached
    events deleted immediately and their sync_token cleared (re-select = full resync)."""
    newly_unselected = await calendar_sync_repo.set_selected(db, user_id, calendar_ids)
    for google_calendar_id in newly_unselected:
        await calendar_event_repo.delete_all_for_calendar(db, user_id, google_calendar_id)
        await calendar_sync_repo.clear_sync_token(db, user_id, google_calendar_id)
    await db.commit()
