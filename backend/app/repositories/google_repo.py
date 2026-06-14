"""GoogleOAuthAccount repository — DB queries only."""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.google_account import GoogleOAuthAccount


async def get_by_user(db: AsyncSession, user_id: uuid.UUID) -> GoogleOAuthAccount | None:
    result = await db.execute(
        select(GoogleOAuthAccount).where(GoogleOAuthAccount.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def upsert(
    db: AsyncSession,
    user_id: uuid.UUID,
    google_email: str,
    scopes: str,
    access_token_expires_at: datetime,
) -> GoogleOAuthAccount:
    """Create or update the user's Google account metadata."""
    account = await get_by_user(db, user_id)
    if account is None:
        account = GoogleOAuthAccount(
            user_id=user_id,
            google_email=google_email,
            scopes=scopes,
            access_token_expires_at=access_token_expires_at,
        )
        db.add(account)
    else:
        account.google_email = google_email
        account.scopes = scopes
        account.access_token_expires_at = access_token_expires_at
    await db.flush()
    await db.refresh(account)
    return account


async def update_expiry(
    db: AsyncSession, user_id: uuid.UUID, access_token_expires_at: datetime
) -> None:
    account = await get_by_user(db, user_id)
    if account:
        account.access_token_expires_at = access_token_expires_at
        await db.flush()


async def delete_by_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(GoogleOAuthAccount).where(GoogleOAuthAccount.user_id == user_id))
    await db.flush()
