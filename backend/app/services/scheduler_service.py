"""APScheduler setup and reminder check job."""

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = structlog.get_logger()
_scheduler: AsyncIOScheduler | None = None


async def check_reminders() -> None:
    """
    Scheduler job: runs every 60s.
    Step A — recovery: reset stuck 'sending' reminders (updated_at > 5 min ago) -> 'failed'
    Step B — bulk set pending due reminders -> 'due' (frontend polls GET /due to show toast)
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.reminder import Reminder
    from app.repositories import reminder_repo

    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)

        # Step A: recovery — reset stuck sending reminders (legacy from web push flow)
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

        # Step B: atomically claim pending due reminders -> set status to 'due'
        due = await reminder_repo.claim_pending_due(db, before_utc=now)
        if due:
            await db.commit()
            for r in due:
                log.info("scheduler.reminder_due", reminder_id=str(r.id), user_id=str(r.user_id))


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
