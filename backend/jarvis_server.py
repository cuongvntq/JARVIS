"""
PyInstaller entry point for JARVIS backend.
Resolves .env path relative to exe location when packaged.
"""

import os
import sys
from pathlib import Path

# Resolve .env for packaged app. Priority:
# 1. %APPDATA%\JARVIS\.env — user config dir, writable even when installed to Program Files
# 2. .env next to executable — dev or portable mode
_exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
_env_candidates: list[Path] = []
_appdata = os.environ.get("APPDATA")
if _appdata:
    _env_candidates.append(Path(_appdata) / "JARVIS" / ".env")
_env_candidates.append(_exe_dir / ".env")

for _candidate in _env_candidates:
    if _candidate.exists():
        os.environ.setdefault("ENV_FILE_PATH", str(_candidate))
        break

import uvicorn  # noqa: E402 — must come after ENV_FILE_PATH is set

from app.config import get_settings  # noqa: E402
from app.main import (  # noqa: E402
    app as fastapi_app,
)

if __name__ == "__main__":
    settings = get_settings()
    port = int(os.environ.get("BACKEND_PORT", settings.backend_port))
    uvicorn.run(
        fastapi_app,  # pass object directly — string import fails in PyInstaller onefile
        host="127.0.0.1",
        port=port,
        log_level=settings.log_level.lower(),
        log_config=None,  # disable dictConfig — formatter classes unavailable in PyInstaller
    )
