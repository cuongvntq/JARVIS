"""ORM model: Todo."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        sa.Enum(
            "pending",
            "in_progress",
            "completed",
            "cancelled",
            name="todo_status",
            create_type=False,
        ),
        nullable=False,
        server_default="pending",
    )
    priority: Mapped[str] = mapped_column(
        sa.Enum(
            "low",
            "medium",
            "high",
            "urgent",
            name="todo_priority",
            create_type=False,
        ),
        nullable=False,
        server_default="medium",
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # TEXT[] in Postgres; sa.JSON for SQLite test compatibility
    tags: Mapped[list] = mapped_column(sa.JSON, nullable=False, server_default=sa.text("'[]'"))
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ui")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="todos")  # noqa: F821
