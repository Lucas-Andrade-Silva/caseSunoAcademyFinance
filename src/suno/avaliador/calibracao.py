"""Calibração (H2): o formato do arquivo de Células rotuladas à mão, o Kappa de Cohen e a
matriz de confusão por Audiência. Não inventa rótulo humano.

ADR 0002, 0003.
"""

from __future__ import annotations

from pathlib import Path


def kappa_cohen(rotulos_a: list[str], rotulos_b: list[str]) -> float:
    raise NotImplementedError("Etapa 2, agente 10 — ADR 0002, 0003")


def matriz_de_confusao(caminho: Path) -> dict[str, dict[str, int]]:
    raise NotImplementedError("Etapa 2, agente 10 — ADR 0002, 0003")
