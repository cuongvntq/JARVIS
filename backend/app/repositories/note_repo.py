"""Note repository — DB queries only."""

import base64
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select, update
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
            cursor_data = json.loads(base64.b64decode(cursor).decode())
            cursor_pinned: bool = cursor_data["pinned"]
            cursor_dt = datetime.fromisoformat(cursor_data["created_at"])
            cursor_id: uuid.UUID | None = (
                uuid.UUID(cursor_data["id"]) if cursor_data.get("id") else None
            )
            # Composite cursor: (pinned DESC, created_at DESC, id DESC)
            # Move past the last seen row using strict ordering conditions.
            same_ts = and_(Note.pinned == cursor_pinned, Note.created_at == cursor_dt)
            id_tiebreak = and_(same_ts, Note.id < cursor_id) if cursor_id is not None else None
            conditions = [
                Note.pinned < cursor_pinned,
                and_(Note.pinned == cursor_pinned, Note.created_at < cursor_dt),
            ]
            if id_tiebreak is not None:
                conditions.append(id_tiebreak)
            query = query.where(or_(*conditions))
        except Exception:
            pass

    # Pinned notes first, then by created_at desc, then id desc as tie-breaker
    query = query.order_by(Note.pinned.desc(), Note.created_at.desc(), Note.id.desc()).limit(
        limit + 1
    )
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        cursor_payload = json.dumps(
            {
                "pinned": last.pinned,
                "created_at": last.created_at.isoformat(),
                "id": str(last.id),
            }
        )
        next_cursor = base64.b64encode(cursor_payload.encode()).decode()

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
