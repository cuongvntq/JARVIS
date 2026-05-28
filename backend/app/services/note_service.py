"""Note business logic."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.repositories import note_repo
from app.schemas.note import NoteCreate, NoteOut, NotePatch, NoteUpdate


async def create_note(
    db: AsyncSession, user_id: uuid.UUID, data: NoteCreate, commit: bool = True
) -> NoteOut:
    note = await note_repo.create(
        db,
        user_id,
        title=data.title,
        content=data.content,
        tags=data.tags,
        pinned=data.pinned,
        source=data.source,
    )
    if commit:
        await db.commit()
    else:
        await db.flush()
    await db.refresh(note)
    return NoteOut.model_validate(note)


async def get_note(db: AsyncSession, note_id: uuid.UUID, user_id: uuid.UUID) -> NoteOut:
    note = await note_repo.get_by_id(db, note_id, user_id)
    if note is None:
        raise JarvisError(404, "note_not_found", "Ghi chú không tồn tại")
    return NoteOut.model_validate(note)


async def list_notes(
    db: AsyncSession,
    user_id: uuid.UUID,
    pinned: bool | None,
    q: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[NoteOut], str | None]:
    rows, next_cursor = await note_repo.list_notes(
        db, user_id, pinned=pinned, q=q, limit=limit, cursor=cursor
    )
    return [NoteOut.model_validate(r) for r in rows], next_cursor


async def update_note(
    db: AsyncSession,
    note_id: uuid.UUID,
    user_id: uuid.UUID,
    data: NoteUpdate,
) -> NoteOut:
    note = await note_repo.get_by_id(db, note_id, user_id)
    if note is None:
        raise JarvisError(404, "note_not_found", "Ghi chú không tồn tại")

    fields = data.model_dump(exclude_unset=True)
    if fields:
        await note_repo.update_fields(db, note_id, **fields)
    await db.commit()
    updated = await note_repo.get_by_id(db, note_id, user_id)
    return NoteOut.model_validate(updated)


async def patch_note(
    db: AsyncSession,
    note_id: uuid.UUID,
    user_id: uuid.UUID,
    data: NotePatch,
    commit: bool = True,
) -> NoteOut:
    """Internal partial update — used by tool executor."""
    note = await note_repo.get_by_id(db, note_id, user_id)
    if note is None:
        raise JarvisError(404, "note_not_found", "Ghi chú không tồn tại")

    fields = data.model_dump(exclude_unset=True)
    if fields:
        await note_repo.update_fields(db, note_id, **fields)
    if commit:
        await db.commit()
    else:
        await db.flush()
    updated = await note_repo.get_by_id(db, note_id, user_id)
    return NoteOut.model_validate(updated)


async def pin_note(db: AsyncSession, note_id: uuid.UUID, user_id: uuid.UUID) -> NoteOut:
    note = await note_repo.get_by_id(db, note_id, user_id)
    if note is None:
        raise JarvisError(404, "note_not_found", "Ghi chú không tồn tại")
    await note_repo.update_fields(db, note_id, pinned=True)
    await db.commit()
    updated = await note_repo.get_by_id(db, note_id, user_id)
    return NoteOut.model_validate(updated)


async def unpin_note(db: AsyncSession, note_id: uuid.UUID, user_id: uuid.UUID) -> NoteOut:
    note = await note_repo.get_by_id(db, note_id, user_id)
    if note is None:
        raise JarvisError(404, "note_not_found", "Ghi chú không tồn tại")
    await note_repo.update_fields(db, note_id, pinned=False)
    await db.commit()
    updated = await note_repo.get_by_id(db, note_id, user_id)
    return NoteOut.model_validate(updated)


async def delete_note(db: AsyncSession, note_id: uuid.UUID, user_id: uuid.UUID) -> None:
    note = await note_repo.get_by_id(db, note_id, user_id)
    if note is None:
        raise JarvisError(404, "note_not_found", "Ghi chú không tồn tại")
    await note_repo.soft_delete(db, note_id)
    await db.commit()
