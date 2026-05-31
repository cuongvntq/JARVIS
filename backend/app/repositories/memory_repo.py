"""Memory repository — DB queries only."""

import base64
import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models.memory import Memory
from app.schemas.memory import MemoryCreate


async def create(db: AsyncSession, user_id: uuid.UUID, data: MemoryCreate) -> Memory:
    memory = Memory(
        user_id=user_id,
        memory_type=data.memory_type,
        content=data.content,
        importance=data.importance,
    )
    db.add(memory)
    await db.flush()
    await db.refresh(memory)
    return memory


async def get_by_id(
    db: AsyncSession, memory_id: uuid.UUID, user_id: uuid.UUID
) -> Memory | None:
    result = await db.execute(
        select(Memory).where(
            Memory.id == memory_id,
            Memory.user_id == user_id,
            Memory.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_memories(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    memory_type: str | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> tuple[list[Memory], str | None]:
    query = select(Memory).where(
        Memory.user_id == user_id,
        Memory.deleted_at.is_(None),
    )

    if memory_type is not None:
        query = query.where(Memory.memory_type == memory_type)

    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode())
            cursor_dt = datetime.fromisoformat(cursor_data["created_at"])
            cursor_id = uuid.UUID(cursor_data["id"])
            query = query.where(
                sa.or_(
                    Memory.created_at < cursor_dt,
                    sa.and_(Memory.created_at == cursor_dt, Memory.id < cursor_id),
                )
            )
        except Exception:
            pass

    query = query.order_by(Memory.created_at.desc(), Memory.id.desc()).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        payload = json.dumps({"created_at": last.created_at.isoformat(), "id": str(last.id)})
        next_cursor = base64.b64encode(payload.encode()).decode()

    return rows, next_cursor


async def update_fields(db: AsyncSession, memory_id: uuid.UUID, **kwargs) -> None:
    kwargs["updated_at"] = datetime.now(UTC)
    await db.execute(update(Memory).where(Memory.id == memory_id).values(**kwargs))


async def update_embedding(
    db: AsyncSession, memory_id: uuid.UUID, embedding: list[float], content: str
) -> None:
    """Update the embedding column via raw SQL with ::vector cast (Postgres only).
    Conditional on content match to prevent stale background tasks from overwriting newer embeddings.
    """
    await db.execute(
        sa.text(
            "UPDATE memories SET embedding = cast(:vec as vector), updated_at = :now "
            "WHERE id = :mid AND content = :content AND deleted_at IS NULL"
        ).bindparams(vec=str(embedding), now=datetime.now(UTC), mid=str(memory_id), content=content)
    )


async def soft_delete(db: AsyncSession, memory_id: uuid.UUID) -> None:
    await db.execute(
        update(Memory).where(Memory.id == memory_id).values(
            deleted_at=datetime.now(UTC), is_active=False
        )
    )


def _build_semantic_search_stmt(
    user_id: uuid.UUID,
    query_vec: list[float],
    limit: int,
    min_similarity: float,
    memory_type: str | None = None,
) -> sa.Select:
    """Build pgvector cosine similarity SELECT (Postgres only — not executable on SQLite)."""
    vec_literal = str(query_vec)  # "[0.1, 0.2, ...]" — valid pgvector array input
    stmt = (
        select(Memory)
        .where(
            Memory.user_id == user_id,
            Memory.is_active.is_(True),
            Memory.deleted_at.is_(None),
            Memory.embedding.isnot(None),
            sa.text(
                f"1 - (embedding <=> '{vec_literal}'::vector) >= :min_sim"
            ).bindparams(min_sim=min_similarity),
        )
        .order_by(sa.text(f"embedding <=> '{vec_literal}'::vector"))
        .limit(limit)
    )
    if memory_type is not None:
        stmt = stmt.where(Memory.memory_type == memory_type)
    return stmt


async def semantic_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    query_vec: list[float],
    limit: int = 5,
    min_similarity: float = 0.7,
    memory_type: str | None = None,
) -> list[Memory]:
    """Cosine similarity search. Returns [] on SQLite (test env)."""
    if engine.dialect.name == "sqlite":
        return []
    stmt = _build_semantic_search_stmt(user_id, query_vec, limit, min_similarity, memory_type)
    result = await db.execute(stmt)
    return list(result.scalars())
