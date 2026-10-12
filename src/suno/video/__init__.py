"""Vídeo fora do grafo: consome Roteiros já aprovados. Um mp4 só, 9:16, dois destinos.
Nenhum LLM olha o mp4.

ADR 0004.

Os três nomes do render são resolvidos sob demanda: ``suno.video.design`` (o design system) é
importado pelo Gerador, e o render importa o Gerador de volta — carregar o render junto
fecharia um ciclo.
"""

from __future__ import annotations

from typing import Any

__all__ = ["compor_quadro", "medir_video", "renderizar_video"]


def __getattr__(nome: str) -> Any:
    if nome in __all__:
        from suno.video import render

        return getattr(render, nome)
    raise AttributeError(f"module 'suno.video' has no attribute {nome!r}")
