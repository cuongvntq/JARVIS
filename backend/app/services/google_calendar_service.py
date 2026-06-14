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


async def list_calendars(db: AsyncSession, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return the user's calendar list. Refreshes the access token if needed."""
    access_token = await google_oauth_service.get_valid_access_token(db, user_id)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            _CALENDAR_LIST_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
    if resp.status_code == 401:
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
