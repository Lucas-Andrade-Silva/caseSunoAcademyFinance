"""Renderização determinística do Carrossel: matplotlib desenha o gráfico a partir das Âncoras
numéricas, Pillow compõe. PNG 1080x1350 em todos os slides.

ADR 0009.
"""

from __future__ import annotations

from pathlib import Path

from suno.dominio import Ancoras, Celula, ImagemSlide


def renderizar_carrossel(celula: Celula, ancoras: Ancoras, pasta: Path) -> list[ImagemSlide]:
    raise NotImplementedError("Etapa 2, agente 9 — ADR 0009")


def folha_de_contato(imagens: list[ImagemSlide], destino: Path) -> Path:
    raise NotImplementedError("Etapa 2, agente 9 — ADR 0014")
