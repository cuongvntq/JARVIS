"""Tests for startup infrastructure: auto-migrate path resolution + file logging."""

from __future__ import annotations

import logging
from pathlib import Path

import structlog

from app.core import db_migrate
from app.core.logging_config import configure_logging


def test_base_dir_points_at_backend_root_in_dev() -> None:
    """In dev (not frozen) the base dir holds alembic.ini + migrations/."""
    base = db_migrate._base_dir()
    assert (base / "alembic.ini").is_file()
    assert (base / "migrations").is_dir()


def test_configure_logging_writes_to_file(tmp_path: Path, monkeypatch) -> None:
    """configure_logging creates a rotating file sink and structlog logs land in it."""
    monkeypatch.setenv("APPDATA", str(tmp_path))

    log_path = configure_logging("INFO")

    assert log_path is not None
    assert log_path == tmp_path / "JARVIS" / "logs" / "jarvis-backend.log"

    structlog.get_logger().info("startup.smoke", marker="abc123")
    logging.shutdown()

    content = log_path.read_text(encoding="utf-8")
    assert "startup.smoke" in content
    assert "abc123" in content


def test_configure_logging_falls_back_when_dir_unwritable(monkeypatch) -> None:
    """If the log dir cannot be created, fall back to stderr-only (no crash)."""
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(
        db_migrate.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("nope"))
    )
    # _log_dir() falls back to repo logs/ when APPDATA is unset; force mkdir to fail.
    from app.core import logging_config

    monkeypatch.setattr(
        logging_config.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("nope"))
    )

    log_path = configure_logging("INFO")

    assert log_path is None  # stderr-only; must not raise
