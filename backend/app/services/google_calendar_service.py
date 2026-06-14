"""Google Calendar API access (Sprint 8): list calendars.

Sprint 9 will extend this to read events with incremental sync.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.services import google_oauth_service

log = structlog.get_logger()

_CALENDAR_LIST_URL = "https://www.googleapis.com/calendar/v3/users/me/calendarList"


async def _get_calendar_list(access_token: str) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30) as client:
        return await client.get(
            _CALENDAR_LIST_URL, headers={"Authorization": f"Bearer {access_token}"}
        )


async def list_calendars(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return the user's calendar list, refreshing the access token if needed.

    A 401 can occur even when the cached token has not expired (the token was
    revoked server-side). In that case force one refresh and retry; if it still
    fails, clear local state so the UI prompts a reconnect instead of looping on a
    dead token until expiry.
    """
    access_token = await google_oauth_service.get_valid_access_token(db, user_id)
    resp = await _get_calendar_list(access_token)

    if resp.status_code == 401:
        log.info("google.calendar_401_force_refresh", user_id=str(user_id))
        # force_refresh_access_token raises google_reauth_required if the refresh
        # token itself is revoked (invalid_grant), already clearing local state.
        access_token = await google_oauth_service.force_refresh_access_token(db, user_id)
        resp = await _get_calendar_list(access_token)
        if resp.status_code == 401:
            await google_oauth_service.clear_local_connection(db, user_id)
            raise JarvisError(401, "google_reauth_required", "Cần kết nối lại Google Calendar")

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
