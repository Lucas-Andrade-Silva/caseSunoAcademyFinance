"""Integridade da extração: se as Âncoras numéricas essenciais faltam, a Célula reprova por
`falha de extração` e vai direto à revisão humana, sem Ciclo de correção.

ADR 0013.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from suno.dominio import Ancora


@dataclass(frozen=True)
class ResultadoIntegridade:
    completa: bool
    faltantes: list[str] = field(default_factory=list)


def medir_integridade(ancoras: Sequence[Ancora]) -> ResultadoIntegridade:
    raise NotImplementedError("Etapa 1, agente 4 — ADR 0013")
