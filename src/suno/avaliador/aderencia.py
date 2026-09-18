"""Aderência: cada número na Célula conferido por igualdade exata de valor e unidade contra
as Âncoras numéricas; afirmações conferidas contra as Âncoras textuais. Sem LLM.

ADR 0011.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from suno.dominio import Ancora


@dataclass(frozen=True)
class ResultadoAderencia:
    proporcao: float | None
    numeros_conferidos: list[str] = field(default_factory=list)
    numeros_fora_das_ancoras: list[str] = field(default_factory=list)
    ancoras_citadas: list[str] = field(default_factory=list)


def medir_aderencia(texto: str, ancoras: Sequence[Ancora]) -> ResultadoAderencia:
    raise NotImplementedError("Etapa 1, agente 4 — ADR 0011")
