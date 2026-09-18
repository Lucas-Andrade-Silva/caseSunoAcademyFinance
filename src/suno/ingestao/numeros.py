"""Extração determinística de números do texto em português: vírgula decimal, ponto de
milhar, por extenso (text2num), `p.p.` diferente de `%`, `CDI+2%` diferente de
`110% do CDI`, datas (dateparser, pt).

ADR 0011.
"""

from __future__ import annotations

from dataclasses import dataclass

from suno.dominio import Unidade


@dataclass(frozen=True)
class NumeroEncontrado:
    literal: str
    valor: float | None
    unidade: Unidade
    inicio: int
    fim: int
    trecho: str


def extrair_numeros(texto: str) -> list[NumeroEncontrado]:
    raise NotImplementedError("Etapa 1, agente 4 — ADR 0011")
