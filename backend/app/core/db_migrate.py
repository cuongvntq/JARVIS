"""Run Alembic migrations to head programmatically at startup.

The packaged desktop app never runs `alembic upgrade head` by hand, so a release
that ships a new migration would leave the user's local DB on the old schema. That
is exactly how the Sprint 8 `google_oauth_accounts` table ended up missing: the app
was upgraded but the DB stayed at revision 008, and the OAuth callback failed when
it tried to upsert into a table that did not exist.

Running migrations on startup (non-test envs) keeps the local DB in lockstep with
the shipped code. It is a no-op when already at head.
"""

from __future__ import annotations

import sys
from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config

log = structlog.get_logger()


def _base_dir() -> Path:
    """Locate the dir holding alembic.ini + migrations/.

    PyInstaller onefile extracts bundled data files to ``sys._MEIPASS``; in dev this
    file lives at ``backend/app/core/db_migrate.py`` so the backend root is two
    parents up.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def run_migrations_to_head() -> None:
    """Upgrade the configured database to the latest Alembic revision.

    env.py reads the DB URL from app settings (DATABASE_URL_DIRECT), so we only need
    to point Config at the bundled alembic.ini + migrations dir using absolute paths
    (the relative `script_location` in the ini does not resolve under _MEIPASS).
    """
    base = _base_dir()
    cfg = Config(str(base / "alembic.ini"))
    cfg.set_main_option("script_location", str(base / "migrations"))
    command.upgrade(cfg, "head")
    log.info("jarvis.migrations_applied")
