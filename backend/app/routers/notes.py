"""Note endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.schemas.note import NoteCreate, NoteListOut, NoteOut, NoteUpdate
from app.services import note_service

router = APIRouter()


@router.get("", response_model=NoteListOut)
async def list_notes(
    pinned: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, next_cursor = await note_service.list_notes(
        db, current_user.id, pinned=pinned, q=q, limit=limit, cursor=cursor
    )
    return NoteListOut(items=items, next_cursor=next_cursor)


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    data: NoteCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.create_note(db, current_user.id, data)


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.get_note(db, note_id, current_user.id)


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: uuid.UUID,
    data: NoteUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.update_note(db, note_id, current_user.id, data)


@router.patch("/{note_id}/pin", response_model=NoteOut)
async def pin_note(
    note_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.pin_note(db, note_id, current_user.id)


@router.patch("/{note_id}/unpin", response_model=NoteOut)
async def unpin_note(
    note_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await note_service.unpin_note(db, note_id, current_user.id)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await note_service.delete_note(db, note_id, current_user.id)
    return Response(status_code=204)
