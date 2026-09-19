"""Vídeo fora do grafo: consome Roteiros já aprovados. Um mp4 só, 9:16, dois destinos.
Nenhum LLM olha o mp4.

ADR 0004.
"""

from __future__ import annotations

from suno.video.render import compor_quadro, medir_video, renderizar_video

__all__ = ["compor_quadro", "medir_video", "renderizar_video"]
