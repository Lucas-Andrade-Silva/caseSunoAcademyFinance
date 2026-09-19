# Demo ponta a ponta sem rede: executa a Ata versionada com o LLM falso e monta o Pacote.
# Identificador fixo: rodar de novo regrava a mesma pasta em vez de acumular execuções, e
# nunca toca em data/execucoes/demo-copom-280/, que é a demo já versionada no repositório.
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
Set-Location (Join-Path $PSScriptRoot "..")
$saida = uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor falso --identificador demo-ao-vivo
$saida
$id = ($saida | Select-String -Pattern "execucao=(\S+)" | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -Last 1)
if ($id) { uv run --offline python -m suno.cli pacote --execucao $id }
