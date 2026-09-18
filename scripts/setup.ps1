# Prepara o ambiente numa máquina limpa (Windows / PowerShell). Precisa só de Python 3.12+ e uv.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv não encontrado. Instale com: winget install astral-sh.uv  (ou pip install uv)"
    exit 1
}
uv sync
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Write-Host "Pronto. Rode scripts\test.ps1 para a suíte e scripts\demo.ps1 para a demo sem rede."
