"""ORM model: Memory."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    memory_type: Mapped[str] = mapped_column(
        sa.Enum(
            "fact",
            "preference",
            "rule",
            "relation",
            "goal",
            "other",
            name="memory_type",
            create_type=False,
        ),
        nullable=False,
        server_default="fact",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Intentionally sa.JSON (not pgvector.Vector) for SQLite test compat.
    # Postgres column is vector(1536) via migration DDL.
    # NEVER assign embedding via ORM (SQLAlchemy binds as JSON, breaks Postgres).
    # All writes MUST go through memory_repo.update_embedding() which uses raw SQL + ::vector cast.
    embedding: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="memories")  # noqa: F821
