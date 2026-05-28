"""Note repository — DB queries only."""

import base64
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


async def get_by_id(db: AsyncSession, note_id: uuid.UUID, user_id: uuid.UUID) -> Note | None:
    result = await db.execute(
        select(Note).where(
            Note.id == note_id,
            Note.user_id == user_id,
            Note.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_notes(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    pinned: bool | None = None,
    q: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> tuple[list[Note], str | None]:
    query = select(Note).where(
        Note.user_id == user_id,
        Note.deleted_at.is_(None),
    )

    if pinned is not None:
        query = query.where(Note.pinned == pinned)

    if q:
        query = query.where(Note.title.ilike(f"%{q}%"))

    if cursor:
        try:
            cursor_str = base64.b64decode(cursor).decode()
            cursor_dt = datetime.fromisoformat(cursor_str)
            query = query.where(Note.created_at < cursor_dt)
        except Exception:
            pass

    # Pinned notes first, then by created_at desc
    query = query.order_by(Note.pinned.desc(), Note.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = base64.b64encode(rows[-1].created_at.isoformat().encode()).decode()

    return rows, next_cursor


async def create(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Note:
    note = Note(user_id=user_id, **kwargs)
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


async def update_fields(db: AsyncSession, note_id: uuid.UUID, **kwargs) -> None:
    kwargs["updated_at"] = datetime.now(UTC)
    await db.execute(update(Note).where(Note.id == note_id).values(**kwargs))


async def soft_delete(db: AsyncSession, note_id: uuid.UUID) -> None:
    await db.execute(update(Note).where(Note.id == note_id).values(deleted_at=datetime.now(UTC)))
