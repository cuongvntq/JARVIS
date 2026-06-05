# jarvis_server.spec — PyInstaller build spec for JARVIS backend
# Build: cd backend && pyinstaller jarvis_server.spec

from PyInstaller.utils.hooks import collect_all, collect_data_files

# Collect all litellm submodules — it has many dynamic imports
litellm_datas, litellm_binaries, litellm_hiddenimports = collect_all("litellm")
# tiktoken needs its BPE encoding data files and the openai_public registry
tiktoken_datas, tiktoken_binaries, tiktoken_hiddenimports = collect_all("tiktoken")

a = Analysis(
    ["jarvis_server.py"],
    pathex=["."],
    datas=[
        ("app/vi_time_dict.json", "app"),
        ("alembic.ini", "."),
        ("migrations/", "migrations/"),  # script_location = migrations (not alembic/)
        # litellm JSON data files not always caught by collect_all
        (".venv/Lib/site-packages/litellm/model_prices_and_context_window_backup.json", "litellm"),
        (".venv/Lib/site-packages/litellm/policy_templates_backup.json", "litellm"),
        (".venv/Lib/site-packages/litellm/provider_endpoints_support_backup.json", "litellm"),
        (".venv/Lib/site-packages/litellm/anthropic_beta_headers_config.json", "litellm"),
        (".venv/Lib/site-packages/litellm/cost.json", "litellm"),
        *litellm_datas,
        *tiktoken_datas,
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
        *litellm_hiddenimports,
        *tiktoken_hiddenimports,
    ],
    binaries=[*litellm_binaries, *tiktoken_binaries],
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
