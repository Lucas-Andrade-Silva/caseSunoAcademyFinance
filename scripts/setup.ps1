# Prepara o ambiente numa máquina limpa (Windows / PowerShell). Precisa só de Python 3.12+ e uv.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv não encontrado. Instale com: winget install astral-sh.uv  (ou pip install uv)"
    exit 1
}
# --extra video inclui o Entregável 5 (imageio-ffmpeg, edge-tts) no ambiente padrão.
# $ErrorActionPreference não pega falha de um executável nativo: o código de saída
# precisa ser conferido à mão, senão "Pronto." sai mesmo com o uv sync quebrado.
uv sync --extra video
if ($LASTEXITCODE -ne 0) {
    Write-Host "uv sync falhou (código $LASTEXITCODE). Veja a mensagem acima antes de continuar."
    exit $LASTEXITCODE
}
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Write-Host "Pronto. Rode scripts\test.ps1 para a suíte e scripts\demo.ps1 para a demo sem rede."
