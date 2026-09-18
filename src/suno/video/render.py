"""Composição determinística em CPU a partir do Roteiro aprovado. Medições: duração,
proporção, presença de áudio.

ADR 0004, 0014.
"""

from __future__ import annotations

from pathlib import Path

from suno.dominio import Audiencia, MedicaoVisual


def renderizar_video(identificador_execucao: str, audiencia: Audiencia, pasta_execucoes: Path) -> Path:
    raise NotImplementedError("Etapa 3, agente 13 — ADR 0004")


def medir_video(caminho: Path) -> list[MedicaoVisual]:
    raise NotImplementedError("Etapa 3, agente 13 — ADR 0014")
