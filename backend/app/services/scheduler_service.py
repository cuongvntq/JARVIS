"""APScheduler setup and reminder check job."""

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = structlog.get_logger()
_scheduler: AsyncIOScheduler | None = None


async def check_reminders() -> None:
    """
    Scheduler job: runs every 60s.
    Step A — recovery: reset stuck 'sending' reminders (updated_at > 5 min ago) -> 'failed'
    Step B — claim pending due reminders -> send push -> mark sent/failed
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.reminder import Reminder
    from app.repositories import push_subscription_repo, reminder_repo
    from app.services import push_service

    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)

        # Step A: recovery — reset stuck sending reminders
        stuck_cutoff = now - timedelta(minutes=5)
        result = await db.execute(
            select(Reminder).where(
                Reminder.status == "sending",
                Reminder.updated_at < stuck_cutoff,
                Reminder.deleted_at.is_(None),
            )
        )
        stuck = list(result.scalars())
        for r in stuck:
            await reminder_repo.update_fields(db, r.id, status="failed")
            log.info("scheduler.reminder_stuck_reset", reminder_id=str(r.id))
        if stuck:
            await db.commit()

        # Step B: claim pending due reminders
        due = await reminder_repo.get_pending_due(db, before_utc=now)
        if not due:
            return

        # Mark as sending (claim)
        for r in due:
            await reminder_repo.update_fields(db, r.id, status="sending")
        await db.commit()

        # Send push for each claimed reminder
        for r in due:
            try:
                sub = await push_subscription_repo.get_active_by_user_id(db, r.user_id)
                if sub is None:
                    log.info(
                        "scheduler.no_subscription",
                        reminder_id=str(r.id),
                        user_id=str(r.user_id),
                    )
                    await reminder_repo.update_fields(db, r.id, status="failed")
                    continue

                success = await push_service.send_push(
                    endpoint=sub.endpoint,
                    p256dh=sub.p256dh,
                    auth=sub.auth,
                    title=r.title,
                    body=r.description or "",
                )
                new_status = "sent" if success else "failed"
                await reminder_repo.update_fields(db, r.id, status=new_status)
                log.info(
                    "scheduler.reminder_processed",
                    reminder_id=str(r.id),
                    status=new_status,
                )
            except Exception:
                log.exception("scheduler.reminder_error", reminder_id=str(r.id))
                await reminder_repo.update_fields(db, r.id, status="failed")

        await db.commit()


def start_scheduler() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        check_reminders,
        "interval",
        seconds=60,
        id="check_reminders",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info("scheduler.started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("scheduler.stopped")
    _scheduler = None
