"""O ``web/openapi.json`` commitado tem que ser o que a API gera hoje.

Antes deste teste, só o script ``scripts/gerar-cliente`` atualizava o arquivo e nada conferia:
o cliente TypeScript podia divergir do servidor sem aviso (ADR 0005).
"""

from __future__ import annotations

import json
from pathlib import Path

from suno.api.openapi import gerar_schema

CAMINHO = Path(__file__).resolve().parent.parent / "web" / "openapi.json"


def test_openapi_commitado_bate_com_o_que_a_api_gera() -> None:
    commitado = json.loads(CAMINHO.read_text(encoding="utf-8"))

    assert commitado == gerar_schema(), (
        "web/openapi.json está desatualizado: rode scripts/gerar-cliente.ps1 (ou .sh)"
    )
