"""Todo endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import JarvisError
from app.database import get_db
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoListOut, TodoOut, TodoReplace
from app.services import todo_service

router = APIRouter()

_VALID_STATUS = {"pending", "in_progress", "completed", "cancelled"}
_VALID_FILTER = {"today", "upcoming", "overdue", "completed", "all"}


@router.get("", response_model=TodoListOut)
async def list_todos(
    status: str | None = Query(default=None),
    filter: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoListOut:
    if status and status not in _VALID_STATUS:
        raise JarvisError(
            400, "invalid_status", f"status phải là một trong: {', '.join(_VALID_STATUS)}"
        )
    if filter and filter not in _VALID_FILTER:
        raise JarvisError(
            400, "invalid_filter", f"filter phải là một trong: {', '.join(_VALID_FILTER)}"
        )

    items, next_cursor = await todo_service.list_todos(
        db,
        current_user.id,
        status=status,
        filter_type=filter,
        q=q,
        limit=limit,
        cursor=cursor,
        user_tz=current_user.timezone,
    )
    return TodoListOut(items=items, next_cursor=next_cursor)


@router.post("", response_model=TodoOut, status_code=201)
async def create_todo(
    data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoOut:
    return await todo_service.create_todo(db, current_user.id, data)


@router.get("/{todo_id}", response_model=TodoOut)
async def get_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoOut:
    return await todo_service.get_todo(db, todo_id, current_user.id)


@router.put("/{todo_id}", response_model=TodoOut)
async def replace_todo(
    todo_id: uuid.UUID,
    data: TodoReplace,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoOut:
    return await todo_service.replace_todo(db, todo_id, current_user.id, data)


@router.patch("/{todo_id}/complete", response_model=TodoOut)
async def complete_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoOut:
    return await todo_service.complete_todo(db, todo_id, current_user.id)


@router.patch("/{todo_id}/uncomplete", response_model=TodoOut)
async def uncomplete_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoOut:
    return await todo_service.uncomplete_todo(db, todo_id, current_user.id)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await todo_service.delete_todo(db, todo_id, current_user.id)
    return Response(status_code=204)
