#!/usr/bin/env sh
# Demo ponta a ponta sem rede: executa a Ata versionada com o LLM falso e monta o Pacote.
# Identificador fixo: rodar de novo regrava a mesma pasta em vez de acumular execuções, e
# nunca toca em data/execucoes/demo-copom-280/, que é a demo já versionada no repositório.
set -eu
export PYTHONIOENCODING=utf-8
cd "$(dirname "$0")/.."
saida="$(uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor falso --identificador demo-ao-vivo)"
echo "$saida"
id="$(echo "$saida" | sed -n 's/.*execucao=\([^ ]*\).*/\1/p' | tail -n 1)"
[ -n "$id" ] && uv run --offline python -m suno.cli pacote --execucao "$id"
