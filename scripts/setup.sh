#!/usr/bin/env sh
# Prepara o ambiente numa máquina limpa (sh). Precisa só de Python 3.12+ e uv.
set -eu
cd "$(dirname "$0")/.."
if ! command -v uv >/dev/null 2>&1; then
  echo "uv não encontrado. Instale com: curl -LsSf https://astral.sh/uv/install.sh | sh  (ou pip install uv)"
  exit 1
fi
# --extra video inclui o Entregável 5 (imageio-ffmpeg, edge-tts) no ambiente padrão.
# `set -e` já aborta o script se uv sync sair com erro; nada extra a conferir aqui.
uv sync --extra video
[ -f .env ] || cp .env.example .env
echo "Pronto. Rode scripts/test.sh para a suíte e scripts/demo.sh para a demo sem rede."
