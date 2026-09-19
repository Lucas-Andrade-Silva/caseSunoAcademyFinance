#!/usr/bin/env bash
# Gera web/openapi.json a partir da API e o cliente TypeScript a partir dele (ADR 0005).
# Precisa de rede uma vez, para baixar o pacote `openapi-typescript` via npx; nada disso
# entra no pytest, que roda inteiramente offline.
#
#   bash scripts/gerar-cliente.sh

set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

export PYTHONIOENCODING=utf-8  # acentos do schema (Windows abre console em cp1252)

echo "Gerando web/openapi.json..."
uv run python -m suno.api.openapi > web/openapi.json

mkdir -p web/src/api

echo "Gerando web/src/api/schema.d.ts..."
npx --yes openapi-typescript web/openapi.json -o web/src/api/schema.d.ts

echo "Cliente gerado."
