"""Todo business logic."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.repositories import todo_repo
from app.schemas.todo import TodoCreate, TodoOut, TodoPartialUpdate, TodoReplace


async def create_todo(
    db: AsyncSession, user_id: uuid.UUID, data: TodoCreate, commit: bool = True
) -> TodoOut:
    todo = await todo_repo.create(
        db,
        user_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_at=data.due_at,
        tags=data.tags,
        source=data.source,
    )
    if commit:
        await db.commit()
    else:
        await db.flush()
    await db.refresh(todo)
    return TodoOut.model_validate(todo)


async def get_todo(db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID) -> TodoOut:
    todo = await todo_repo.get_by_id(db, todo_id, user_id)
    if todo is None:
        raise JarvisError(404, "todo_not_found", "Todo không tồn tại")
    return TodoOut.model_validate(todo)


async def list_todos(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str | None,
    filter_type: str | None,
    q: str | None,
    limit: int,
    cursor: str | None,
    user_tz: str = "UTC",
) -> tuple[list[TodoOut], str | None]:
    rows, next_cursor = await todo_repo.list_todos(
        db,
        user_id,
        status=status,
        filter_type=filter_type,
        q=q,
        limit=limit,
        cursor=cursor,
        user_tz=user_tz,
    )
    return [TodoOut.model_validate(r) for r in rows], next_cursor


async def replace_todo(
    db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID, data: TodoReplace
) -> TodoOut:
    """PUT — full replacement (title required, other fields use new values)."""
    todo = await todo_repo.get_by_id(db, todo_id, user_id)
    if todo is None:
        raise JarvisError(404, "todo_not_found", "Todo không tồn tại")

    await todo_repo.update_fields(
        db,
        todo_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_at=data.due_at,
        tags=data.tags,
    )
    await db.commit()
    updated = await todo_repo.get_by_id(db, todo_id, user_id)
    return TodoOut.model_validate(updated)


async def patch_todo(
    db: AsyncSession,
    todo_id: uuid.UUID,
    user_id: uuid.UUID,
    data: TodoPartialUpdate,
    commit: bool = True,
) -> TodoOut:
    """Internal partial update — only sets provided fields. Used by tool executor."""
    todo = await todo_repo.get_by_id(db, todo_id, user_id)
    if todo is None:
        raise JarvisError(404, "todo_not_found", "Todo không tồn tại")

    fields = data.model_dump(exclude_unset=True)
    if fields:
        await todo_repo.update_fields(db, todo_id, **fields)
    if commit:
        await db.commit()
    else:
        await db.flush()
    updated = await todo_repo.get_by_id(db, todo_id, user_id)
    return TodoOut.model_validate(updated)


async def complete_todo(
    db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID, commit: bool = True
) -> TodoOut:
    todo = await todo_repo.get_by_id(db, todo_id, user_id)
    if todo is None:
        raise JarvisError(404, "todo_not_found", "Todo không tồn tại")

    await todo_repo.complete(db, todo_id)
    if commit:
        await db.commit()
    else:
        await db.flush()
    updated = await todo_repo.get_by_id(db, todo_id, user_id)
    return TodoOut.model_validate(updated)


async def uncomplete_todo(
    db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID, commit: bool = True
) -> TodoOut:
    todo = await todo_repo.get_by_id(db, todo_id, user_id)
    if todo is None:
        raise JarvisError(404, "todo_not_found", "Todo không tồn tại")

    await todo_repo.uncomplete(db, todo_id)
    if commit:
        await db.commit()
    else:
        await db.flush()
    updated = await todo_repo.get_by_id(db, todo_id, user_id)
    return TodoOut.model_validate(updated)


async def delete_todo(db: AsyncSession, todo_id: uuid.UUID, user_id: uuid.UUID) -> None:
    todo = await todo_repo.get_by_id(db, todo_id, user_id)
    if todo is None:
        raise JarvisError(404, "todo_not_found", "Todo không tồn tại")

    await todo_repo.soft_delete(db, todo_id)
    await db.commit()
