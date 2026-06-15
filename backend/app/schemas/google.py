"""Google Calendar OAuth + read-only sync schemas (Sprint 8-9)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class GoogleConnectOut(BaseModel):
    authorize_url: str


class GoogleStatusOut(BaseModel):
    connected: bool
    email: str | None = None
    scopes: str | None = None
    access_token_expires_at: datetime | None = None


class GoogleCalendarOut(BaseModel):
    id: str
    summary: str
    primary: bool
    time_zone: str | None = None


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    google_calendar_id: str
    google_event_id: str
    summary: str
    description: str | None = None
    location: str | None = None
    is_all_day: bool
    start_at: datetime | None = None
    end_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    event_timezone: str | None = None
    status: str
    html_link: str | None = None


class CalendarSelectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    google_calendar_id: str
    calendar_summary: str
    is_primary: bool
    selected: bool
    access_role: str | None = None
    time_zone: str | None = None


class CalendarSelectionIn(BaseModel):
    calendar_ids: list[str]


class SyncErrorOut(BaseModel):
    calendar_id: str
    message: str


class SyncResultOut(BaseModel):
    status: Literal["synced", "partial", "already_running"]
    upserted: int
    deleted: int
    failed: int
    synced_at: datetime | None = None
    errors: list[SyncErrorOut] = []
