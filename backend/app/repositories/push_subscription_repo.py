"""Push subscription repository."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_subscription import PushSubscription


async def upsert(
    db: AsyncSession,
    user_id: uuid.UUID,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> PushSubscription:
    """Create or update the push subscription for a user (1 per user).

    If the endpoint is currently registered to a different user (e.g. same browser,
    different login), the old user's subscription is deleted first to avoid a UNIQUE
    constraint violation on the endpoint column.
    """
    now = datetime.now(UTC)

    # Check if this endpoint belongs to a different user and delete it
    old = (
        await db.execute(
            select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
    ).scalar_one_or_none()
    if old is not None and old.user_id != user_id:
        await db.delete(old)
        await db.flush()

    # Upsert for the current user
    sub = (
        await db.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
    ).scalar_one_or_none()

    if sub is None:
        sub = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            is_active=True,
        )
        db.add(sub)
    else:
        sub.endpoint = endpoint
        sub.p256dh = p256dh
        sub.auth = auth
        sub.is_active = True
        sub.updated_at = now

    await db.flush()
    await db.refresh(sub)
    return sub


async def get_active_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> PushSubscription | None:
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def deactivate_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Mark subscription inactive. Returns True if a record was found."""
    sub = await get_active_by_user_id(db, user_id)
    if sub is None:
        return False
    sub.is_active = False
    sub.updated_at = datetime.now(UTC)
    await db.flush()
    return True
