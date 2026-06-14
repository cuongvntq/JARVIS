"""Secure storage for Google OAuth tokens via the OS credential manager (keyring).

Google access/refresh tokens are the highest-sensitivity secrets in the app
(`.claude/rules/05_security.md`). They are stored ONLY here — in the Windows
Credential Manager via the `keyring` library — never in the database, logs, or
API responses. The DB keeps only metadata (see GoogleOAuthAccount).

One credential entry per user: service="jarvis-google-calendar", username=str(user_id),
value = JSON {refresh_token, access_token, access_token_expires_at}.

keyring is synchronous; we wrap calls in asyncio.to_thread so they don't block
the event loop.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import TypedDict

import keyring
import structlog

log = structlog.get_logger()

_KEYRING_SERVICE = "jarvis-google-calendar"


class GoogleTokens(TypedDict):
    refresh_token: str
    access_token: str
    access_token_expires_at: str  # ISO 8601 UTC


async def save_tokens(
    user_id: uuid.UUID,
    refresh_token: str,
    access_token: str,
    access_token_expires_at: datetime,
) -> None:
    """Persist (or overwrite) the Google tokens for a user."""
    payload: GoogleTokens = {
        "refresh_token": refresh_token,
        "access_token": access_token,
        "access_token_expires_at": access_token_expires_at.isoformat(),
    }
    await asyncio.to_thread(
        keyring.set_password, _KEYRING_SERVICE, str(user_id), json.dumps(payload)
    )
    log.info("google.tokens_saved", user_id=str(user_id))


async def get_tokens(user_id: uuid.UUID) -> GoogleTokens | None:
    """Return stored tokens for a user, or None if not connected."""
    raw = await asyncio.to_thread(keyring.get_password, _KEYRING_SERVICE, str(user_id))
    if not raw:
        return None
    try:
        data: GoogleTokens = json.loads(raw)
        return data
    except (json.JSONDecodeError, TypeError):
        log.warning("google.tokens_corrupt", user_id=str(user_id))
        return None


async def delete_tokens(user_id: uuid.UUID) -> None:
    """Remove stored tokens for a user (idempotent — ignores missing entry)."""
    try:
        await asyncio.to_thread(keyring.delete_password, _KEYRING_SERVICE, str(user_id))
        log.info("google.tokens_deleted", user_id=str(user_id))
    except keyring.errors.PasswordDeleteError:
        # No entry to delete — already disconnected.
        pass
