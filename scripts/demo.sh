#!/usr/bin/env sh
# Demo ponta a ponta sem rede: executa a Ata versionada com o LLM falso e monta o Pacote.
set -eu
cd "$(dirname "$0")/.."
saida="$(uv run python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor falso)"
echo "$saida"
id="$(echo "$saida" | sed -n 's/.*execucao=\([^ ]*\).*/\1/p' | tail -n 1)"
[ -n "$id" ] && uv run python -m suno.cli pacote --execucao "$id"
