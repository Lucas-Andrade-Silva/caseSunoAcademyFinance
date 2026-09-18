"""O Pacote de publicação: só de Célula aprovada. Imagens geradas, nunca raspadas.
Conferência visual própria que não reprova a Célula.

ADR 0009, 0014.
"""

from __future__ import annotations

from pathlib import Path

from suno.dominio import PacotePublicacao


def montar_pacote(identificador_execucao: str, pasta_execucoes: Path) -> list[PacotePublicacao]:
    raise NotImplementedError("Etapa 2, agente 9 — ADR 0009, 0014")
