# jarvis_server.spec — PyInstaller build spec for JARVIS backend
# Build: cd backend && pyinstaller jarvis_server.spec

import importlib.util
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files

# Collect all litellm submodules — it has many dynamic imports
litellm_datas, litellm_binaries, litellm_hiddenimports = collect_all("litellm")
# tiktoken needs its BPE encoding data files and the openai_public registry
tiktoken_datas, tiktoken_binaries, tiktoken_hiddenimports = collect_all("tiktoken")
# keyring discovers backends via entry points (dist-info) — collect_all pulls the
# metadata + backend modules so the packaged sidecar can use WinVaultKeyring.
# win32ctypes is the Windows backend's dependency (win32ctypes.pywin32.win32cred).
keyring_datas, keyring_binaries, keyring_hiddenimports = collect_all("keyring")
win32ctypes_datas, win32ctypes_binaries, win32ctypes_hiddenimports = collect_all("win32ctypes")
# Alembic runs on startup (auto-migrate). It loads templates/migration scripts and
# the psycopg2 sync dialect dynamically — neither is reliably found by static analysis.
alembic_datas, alembic_binaries, alembic_hiddenimports = collect_all("alembic")

# Resolve litellm package directory dynamically (cross-platform, venv-agnostic)
_litellm_dir = os.path.dirname(importlib.util.find_spec("litellm").origin)

def _litellm_json(filename):
    """Return (src, dest) tuple for a litellm JSON file, or None if not found."""
    src = os.path.join(_litellm_dir, filename)
    return (src, "litellm") if os.path.exists(src) else None

_extra_litellm_jsons = [
    r for f in [
        "model_prices_and_context_window_backup.json",
        "policy_templates_backup.json",
        "provider_endpoints_support_backup.json",
        "anthropic_beta_headers_config.json",
        "cost.json",
    ]
    if (r := _litellm_json(f))
]

a = Analysis(
    ["jarvis_server.py"],
    pathex=["."],
    datas=[
        ("app/vi_time_dict.json", "app"),
        ("alembic.ini", "."),
        ("migrations/", "migrations/"),  # script_location = migrations (not alembic/)
        # litellm JSON data files not always caught by collect_all (resolved dynamically)
        *_extra_litellm_jsons,
        *litellm_datas,
        *tiktoken_datas,
        *keyring_datas,
        *win32ctypes_datas,
        *alembic_datas,
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "passlib.handlers.bcrypt",
        "apscheduler.schedulers.asyncio",
        "apscheduler.triggers.interval",
        "apscheduler.triggers.date",
        "asyncpg",
        "asyncpg.pgproto.pgproto",
        "tiktoken_ext",
        "tiktoken_ext.openai_public",
        "win32ctypes.pywin32.win32cred",
        "psycopg2",
        *litellm_hiddenimports,
        *tiktoken_hiddenimports,
        *keyring_hiddenimports,
        *win32ctypes_hiddenimports,
        *alembic_hiddenimports,
    ],
    binaries=[
        *litellm_binaries,
        *tiktoken_binaries,
        *keyring_binaries,
        *win32ctypes_binaries,
        *alembic_binaries,
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # required — contains litellm native deps
    a.datas,
    name="jarvis-server",
    debug=False,
    console=False,
    onefile=True,
)
