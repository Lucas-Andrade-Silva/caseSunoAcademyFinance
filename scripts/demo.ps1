# Demo ponta a ponta sem rede: executa a Ata versionada com o LLM falso e monta o Pacote.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$saida = uv run python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor falso
$saida
$id = ($saida | Select-String -Pattern "execucao=(\S+)" | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -Last 1)
if ($id) { uv run python -m suno.cli pacote --execucao $id }
