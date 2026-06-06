# build-sidecar.ps1 — Build PyInstaller backend exe and stage it for Tauri
#
# Run from repo root:
#   .\scripts\build-sidecar.ps1
#
# Prerequisites (fresh clone):
#   cd backend
#   uv sync --extra dev   # installs pyinstaller + all dev deps
#   cd ..
#   .\scripts\build-sidecar.ps1
#
# This script must be run before `tauri build` because
# frontend/src-tauri/binaries/*.exe is git-ignored (106 MB binary).
# CI should run `uv sync --extra dev` then this script before the Tauri build step.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot    = $PSScriptRoot | Split-Path -Parent
$BackendDir  = Join-Path $RepoRoot "backend"
$BinariesDir = Join-Path $RepoRoot "frontend" "src-tauri" "binaries"

# Detect the Rust target triple so the binary is named correctly for Tauri
$TargetTriple = (rustc -Vv | Select-String "host:").ToString().Split()[1].Trim()
if (-not $TargetTriple) {
    Write-Error "Could not detect Rust target triple. Is rustc installed?"
    exit 1
}

Write-Host "==> Target triple: $TargetTriple"
Write-Host "==> Building PyInstaller sidecar (via uv run)..."

Push-Location $BackendDir
try {
    # --extra dev ensures pyinstaller (dev-only dep) is included in the resolved env
    uv run --extra dev pyinstaller jarvis_server.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

$SrcExe  = Join-Path $BackendDir "dist" "jarvis-server.exe"
$DestExe = Join-Path $BinariesDir "jarvis-server-$TargetTriple.exe"

if (-not (Test-Path $SrcExe)) {
    Write-Error "Build succeeded but $SrcExe not found."
    exit 1
}

New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null
Copy-Item -Force $SrcExe $DestExe
Write-Host "==> Staged: $DestExe"
Write-Host "==> Done. You can now run: cd frontend; pnpm tauri build"
