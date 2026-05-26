"""AuthSession repository — DB queries only."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuthSession


async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    token_hash: str,
    user_agent: str | None,
    ip_address: str | None,
    expires_at: datetime,
) -> AuthSession:
    session = AuthSession(
        user_id=user_id,
        refresh_token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_session_by_hash(db: AsyncSession, token_hash: str) -> AuthSession | None:
    now = datetime.now(UTC)
    result = await db.execute(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )
    return result.scalar_one_or_none()


async def revoke_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    result = await db.execute(select(AuthSession).where(AuthSession.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.revoked_at = datetime.now(UTC)
        await db.flush()


async def atomic_revoke_session(db: AsyncSession, token_hash: str):
    """Atomically revoke a non-expired, non-revoked session in one round-trip.

    Returns a Row(user_id, user_agent, ip_address) if the session was successfully
    claimed, or None if it was already revoked, expired, or never existed.
    This prevents replay attacks under concurrent requests.
    """
    now = datetime.now(UTC)
    stmt = (
        sql_update(AuthSession)
        .where(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .values(revoked_at=now)
        .returning(AuthSession.user_id, AuthSession.user_agent, AuthSession.ip_address)
    )
    result = await db.execute(stmt)
    return result.one_or_none()
