"""Reminder business logic."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import JarvisError
from app.repositories import reminder_repo
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderUpdate


async def create_reminder(
    db: AsyncSession, user_id: uuid.UUID, data: ReminderCreate, commit: bool = True
) -> ReminderOut:
    if data.remind_at.astimezone(UTC) <= datetime.now(UTC):
        raise JarvisError(422, "remind_at_past", "remind_at phải là thời điểm trong tương lai")

    reminder = await reminder_repo.create(
        db,
        user_id,
        title=data.title,
        description=data.description,
        remind_at=data.remind_at.astimezone(UTC),
        source=data.source,
    )
    if commit:
        await db.commit()
    else:
        await db.flush()
    await db.refresh(reminder)
    return ReminderOut.model_validate(reminder)


async def get_reminder(db: AsyncSession, reminder_id: uuid.UUID, user_id: uuid.UUID) -> ReminderOut:
    reminder = await reminder_repo.get_by_id(db, reminder_id, user_id)
    if reminder is None:
        raise JarvisError(404, "reminder_not_found", "Lời nhắc không tồn tại")
    return ReminderOut.model_validate(reminder)


async def list_reminders(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[ReminderOut], str | None]:
    rows, next_cursor = await reminder_repo.list_reminders(
        db, user_id, status=status, limit=limit, cursor=cursor
    )
    return [ReminderOut.model_validate(r) for r in rows], next_cursor


async def update_reminder(
    db: AsyncSession,
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    data: ReminderUpdate,
) -> ReminderOut:
    reminder = await reminder_repo.get_by_id(db, reminder_id, user_id)
    if reminder is None:
        raise JarvisError(404, "reminder_not_found", "Lời nhắc không tồn tại")

    fields = data.model_dump(exclude_unset=True)
    if "remind_at" in fields and fields["remind_at"] is not None:
        fields["remind_at"] = fields["remind_at"].astimezone(UTC)
        if fields["remind_at"] <= datetime.now(UTC):
            raise JarvisError(422, "remind_at_past", "remind_at phải là thời điểm trong tương lai")

    if fields:
        await reminder_repo.update_fields(db, reminder_id, **fields)
    await db.commit()
    updated = await reminder_repo.get_by_id(db, reminder_id, user_id)
    return ReminderOut.model_validate(updated)


async def cancel_reminder(
    db: AsyncSession, reminder_id: uuid.UUID, user_id: uuid.UUID
) -> ReminderOut:
    reminder = await reminder_repo.get_by_id(db, reminder_id, user_id)
    if reminder is None:
        raise JarvisError(404, "reminder_not_found", "Lời nhắc không tồn tại")
    if reminder.status not in ("pending", "sending"):
        raise JarvisError(409, "reminder_not_cancellable", "Chỉ có thể hủy reminder đang pending")

    await reminder_repo.update_fields(db, reminder_id, status="cancelled")
    await db.commit()
    updated = await reminder_repo.get_by_id(db, reminder_id, user_id)
    return ReminderOut.model_validate(updated)


async def delete_reminder(db: AsyncSession, reminder_id: uuid.UUID, user_id: uuid.UUID) -> None:
    reminder = await reminder_repo.get_by_id(db, reminder_id, user_id)
    if reminder is None:
        raise JarvisError(404, "reminder_not_found", "Lời nhắc không tồn tại")
    await reminder_repo.soft_delete(db, reminder_id)
    await db.commit()
