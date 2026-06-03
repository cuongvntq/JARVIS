"""Memory business logic."""

import asyncio
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.database import AsyncSessionLocal, engine
from app.repositories import memory_repo
from app.schemas.memory import MemoryCreate, MemoryOut, MemoryUpdate
from app.services.embedding_service import embed_text

log = structlog.get_logger()

# Keep strong references to background tasks so they aren't GC'd before completion (RUF006).
_bg_tasks: set[asyncio.Task[None]] = set()


def _schedule_embed(memory_id: uuid.UUID, content: str) -> None:
    task = asyncio.create_task(_embed_and_update(memory_id, content))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


async def _embed_and_update(memory_id: uuid.UUID, content: str) -> None:
    """Background task: embed content and update DB. Uses own session, never touches request session."""
    if engine.dialect.name == "sqlite":
        return  # no-op in test env — no LiteLLM call, no vector cast on SQLite
    async with AsyncSessionLocal() as db:
        try:
            vec = await embed_text(content)
            await memory_repo.update_embedding(db, memory_id, vec, content)
            await db.commit()
            log.info("embedding.bg_task.done", memory_id=str(memory_id))
        except Exception as e:
            await db.rollback()
            log.error("embedding.bg_task.failed", memory_id=str(memory_id), error=str(e))
            # Silent failure — embedding=None, RAG will skip this record


async def create(db: AsyncSession, user_id: uuid.UUID, data: MemoryCreate) -> MemoryOut:
    """REST path — called from router, session managed by get_db() dependency."""
    memory = await memory_repo.create(db, user_id, data)
    await db.commit()
    await db.refresh(memory)
    out = MemoryOut.model_validate(memory)
    _schedule_embed(out.id, out.content)
    return out


async def create_committed(user_id: uuid.UUID, data: MemoryCreate) -> MemoryOut:
    """Tool executor path — opens its own session to avoid committing the shared chat session."""
    async with AsyncSessionLocal() as db:
        memory = await memory_repo.create(db, user_id, data)
        await db.commit()
        await db.refresh(memory)
        out = MemoryOut.model_validate(memory)  # snapshot before session closes
    _schedule_embed(out.id, out.content)
    return out


async def get(db: AsyncSession, memory_id: uuid.UUID, user_id: uuid.UUID) -> MemoryOut:
    memory = await memory_repo.get_by_id(db, memory_id, user_id)
    if memory is None:
        raise JarvisError(404, "memory_not_found", "Memory không tồn tại")
    return MemoryOut.model_validate(memory)


async def list_memories(
    db: AsyncSession,
    user_id: uuid.UUID,
    memory_type: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[MemoryOut], str | None]:
    rows, next_cursor = await memory_repo.list_memories(
        db, user_id, memory_type=memory_type, limit=limit, cursor=cursor
    )
    return [MemoryOut.model_validate(r) for r in rows], next_cursor


async def update(
    db: AsyncSession,
    memory_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MemoryUpdate,
) -> MemoryOut:
    memory = await memory_repo.get_by_id(db, memory_id, user_id)
    if memory is None:
        raise JarvisError(404, "memory_not_found", "Memory không tồn tại")

    fields = data.model_dump(exclude_unset=True)
    if fields:
        await memory_repo.update_fields(db, memory_id, **fields)
    await db.commit()
    if fields and "content" in fields:
        _schedule_embed(memory_id, fields["content"])
    updated = await memory_repo.get_by_id(db, memory_id, user_id)
    return MemoryOut.model_validate(updated)


async def forget(db: AsyncSession, memory_id: uuid.UUID, user_id: uuid.UUID) -> None:
    memory = await memory_repo.get_by_id(db, memory_id, user_id)
    if memory is None:
        raise JarvisError(404, "memory_not_found", "Memory không tồn tại")
    await memory_repo.soft_delete(db, memory_id)
    await db.commit()


async def forget_committed(memory_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Tool executor path — opens its own session to avoid committing the shared chat session.
    Returns True if deleted, False if not found (caller decides how to surface this).
    """
    async with AsyncSessionLocal() as db:
        memory = await memory_repo.get_by_id(db, memory_id, user_id)
        if memory is None:
            return False
        await memory_repo.soft_delete(db, memory_id)
        await db.commit()
    return True


async def search_semantic(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    limit: int = 5,
    min_similarity: float = 0.7,
    memory_type: str | None = None,
) -> list[MemoryOut]:
    """Embed query then run cosine similarity search. Returns [] on SQLite without calling LLM."""
    if engine.dialect.name == "sqlite":
        return []
    query_vec = await embed_text(query)
    memories = await memory_repo.semantic_search(
        db, user_id, query_vec, limit, min_similarity, memory_type
    )
    return [MemoryOut.model_validate(m) for m in memories]
