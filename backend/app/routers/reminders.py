"""Reminder endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import JarvisError
from app.database import get_db
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderListOut, ReminderOut, ReminderUpdate
from app.services import reminder_service

router = APIRouter()

_VALID_STATUS = {"pending", "sending", "sent", "failed", "cancelled", "due"}


@router.get("", response_model=ReminderListOut)
async def list_reminders(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderListOut:
    if status and status not in _VALID_STATUS:
        raise JarvisError(
            400, "invalid_status", f"status phải là một trong: {', '.join(sorted(_VALID_STATUS))}"
        )
    items, next_cursor = await reminder_service.list_reminders(
        db, current_user.id, status=status, limit=limit, cursor=cursor
    )
    return ReminderListOut(items=items, next_cursor=next_cursor)


@router.post("", response_model=ReminderOut, status_code=201)
async def create_reminder(
    data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.create_reminder(db, current_user.id, data)


# Static routes must come BEFORE /{reminder_id} to avoid FastAPI matching "due" as a UUID
@router.get("/due", response_model=list[ReminderOut])
async def list_due_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReminderOut]:
    return await reminder_service.list_due(db, current_user.id)


@router.post("/{reminder_id}/ack", response_model=ReminderOut)
async def ack_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.ack_reminder(db, reminder_id, current_user.id)


@router.get("/{reminder_id}", response_model=ReminderOut)
async def get_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.get_reminder(db, reminder_id, current_user.id)


@router.patch("/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: uuid.UUID,
    data: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.update_reminder(db, reminder_id, current_user.id, data)


@router.patch("/{reminder_id}/cancel", response_model=ReminderOut)
async def cancel_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderOut:
    return await reminder_service.cancel_reminder(db, reminder_id, current_user.id)


@router.delete("/{reminder_id}", status_code=204)
async def delete_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await reminder_service.delete_reminder(db, reminder_id, current_user.id)
    return Response(status_code=204)
