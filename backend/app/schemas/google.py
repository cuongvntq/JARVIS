"""Google Calendar OAuth request/response schemas (Sprint 8)."""

from datetime import datetime

from pydantic import BaseModel


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
