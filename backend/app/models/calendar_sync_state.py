"""ORM model: CalendarSyncState (Sprint 9).

Tracks per-(user, Google calendar) sync bookkeeping: selection, sync token for
incremental sync, and the rolling horizon window for full resyncs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class CalendarSyncState(Base):
    __tablename__ = "calendar_sync_states"
    __table_args__ = (UniqueConstraint("user_id", "google_calendar_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    google_calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    calendar_summary: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    time_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sync_token: Mapped[str | None] = mapped_column(String, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    horizon_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_full_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship("User", back_populates="calendar_sync_states")
