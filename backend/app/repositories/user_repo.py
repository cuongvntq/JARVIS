"""User repository — DB queries only."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, email: str, password_hash: str, name: str) -> User:
    user = User(email=email, password_hash=password_hash, name=name)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_last_login(db: AsyncSession, user_id: uuid.UUID) -> None:
    user = await get_by_id(db, user_id)
    if user:
        user.last_login_at = datetime.now(UTC)
        await db.flush()
