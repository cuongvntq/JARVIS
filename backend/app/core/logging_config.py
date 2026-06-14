"""Structured logging with a persistent file sink.

The packaged desktop app runs with no console (PyInstaller ``console=False``), so
anything written to stderr is discarded. That is why the Google OAuth exchange
failure was invisible — the only record of it went to a stderr nobody could see.

We route structlog through stdlib logging and add a rotating file handler in the
user data dir, so production errors are inspectable after the fact.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

import structlog

_LOG_FILENAME = "jarvis-backend.log"


def _log_dir() -> Path:
    """User-writable log dir, next to the app's .env (%APPDATA%\\JARVIS on Windows)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "JARVIS" / "logs"
    return Path(__file__).resolve().parents[2] / "logs"


def configure_logging(level: str = "INFO") -> Path | None:
    """Configure structlog (JSON) + stdlib handlers. Returns the log file path.

    Adds a stderr handler (useful in dev) and a rotating file handler (the only
    durable sink for the windowed desktop build). Falls back to stderr-only if the
    log dir cannot be created. Safe to call more than once — Alembic's ``fileConfig``
    resets stdlib logging during migrations, so we re-run this afterwards.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    log_path: Path | None = None
    try:
        log_dir = _log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / _LOG_FILENAME
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
            )
        )
    except OSError:
        pass  # keep stderr-only if the filesystem is not writable

    logging.basicConfig(format="%(message)s", level=numeric_level, handlers=handlers, force=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return log_path
