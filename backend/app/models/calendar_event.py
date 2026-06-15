"""ORM model: CalendarEvent (Sprint 9).

Local cache mirroring Google Calendar events within the sync horizon
(now-30d .. now+365d). Not soft-deleted: cancelled events are hard-deleted to
keep the cache an accurate mirror of remote state.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (
        UniqueConstraint("user_id", "google_calendar_id", "google_event_id"),
        Index("ix_calendar_events_user_start_at", "user_id", "start_at"),
        Index("ix_calendar_events_user_start_date", "user_id", "start_date"),
        Index("ix_calendar_events_user_calendar", "user_id", "google_calendar_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    google_calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    google_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    ical_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="confirmed")
    html_link: Mapped[str | None] = mapped_column(String, nullable=True)
    etag: Mapped[str | None] = mapped_column(String, nullable=True)
    google_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="calendar_events")
