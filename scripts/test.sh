#!/usr/bin/env sh
export PYTHONIOENCODING=utf-8
# Suíte completa: verde sem internet e sem .env.
set -eu
cd "$(dirname "$0")/.."
uv run --offline pytest -q "$@"
