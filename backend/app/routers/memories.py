"""Memory endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.schemas.memory import (
    MemoryCreate,
    MemoryListOut,
    MemoryOut,
    MemorySearchRequest,
    MemoryUpdate,
)
from app.services import memory_service

router = APIRouter()


@router.get("", response_model=MemoryListOut)
async def list_memories(
    memory_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items, next_cursor = await memory_service.list_memories(
        db, current_user.id, memory_type=memory_type, limit=limit, cursor=cursor
    )
    return MemoryListOut(items=items, next_cursor=next_cursor)


@router.post("", response_model=MemoryOut, status_code=201)
async def create_memory(
    data: MemoryCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.create(db, current_user.id, data)


@router.post("/search", response_model=MemoryListOut)
async def search_memories(
    data: MemorySearchRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await memory_service.search_semantic(
        db, current_user.id, data.query, limit=data.limit, min_similarity=data.min_similarity
    )
    return MemoryListOut(items=items, next_cursor=None)


@router.get("/{memory_id}", response_model=MemoryOut)
async def get_memory(
    memory_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.get(db, memory_id, current_user.id)


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: uuid.UUID,
    data: MemoryUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.update(db, memory_id, current_user.id, data)


@router.delete("/{memory_id}", status_code=204)
async def forget_memory(
    memory_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await memory_service.forget(db, memory_id, current_user.id)
    return Response(status_code=204)
