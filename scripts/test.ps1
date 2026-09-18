# Suíte completa: verde sem internet e sem .env.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
uv run pytest -q @args
