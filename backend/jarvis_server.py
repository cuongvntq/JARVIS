"""
PyInstaller entry point for JARVIS backend.
Resolves .env path relative to exe location when packaged.
"""

import os
import sys
from pathlib import Path

# When running as a PyInstaller exe, sys.executable points to the .exe file.
# config.py uses env_file="../.env" which only works when running from backend/.
# Override with ENV_FILE_PATH so Settings() finds the correct .env.
_exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
_env_path = _exe_dir / ".env"
if _env_path.exists():
    os.environ.setdefault("ENV_FILE_PATH", str(_env_path))

import uvicorn  # noqa: E402 — must come after ENV_FILE_PATH is set
from app.config import get_settings  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402 — import object, not string (required for PyInstaller)

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
