"""Web push notification service (pywebpush wrapper)."""

import asyncio
import json
from functools import partial

import structlog

from app.config import get_settings

log = structlog.get_logger()


async def send_push(
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str = "",
) -> bool:
    """Send a web push notification. Returns True on success, False on failure."""
    settings = get_settings()
    if not settings.vapid_private_key or not settings.vapid_public_key:
        log.warning("push.vapid_keys_missing")
        return False

    try:
        from pywebpush import webpush  # lazy import — optional dep

        payload = json.dumps({"title": title, "body": body})
        subscription_info = {
            "endpoint": endpoint,
            "keys": {"p256dh": p256dh, "auth": auth},
        }

        # pywebpush is synchronous — run in thread executor
        await asyncio.to_thread(
            partial(
                webpush,
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                vapid_claims={"sub": settings.vapid_subject},
            )
        )
        return True
    except Exception as exc:
        log.warning("push.send_failed", error=str(exc))
        return False
