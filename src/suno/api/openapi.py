"""Imprime o schema OpenAPI da API, para o cliente TypeScript gerado (ADR 0005).

    python -m suno.api.openapi > web/openapi.json

A pasta de execuções passada a ``criar_app`` aqui não precisa existir: o schema sai das
assinaturas das rotas, não de uma execução real em disco.
"""

from __future__ import annotations

import json
from pathlib import Path

from suno.api.app import criar_app


def gerar_schema() -> dict:
    app = criar_app(Path("data/execucoes"))
    return app.openapi()


def main() -> int:
    print(json.dumps(gerar_schema(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
