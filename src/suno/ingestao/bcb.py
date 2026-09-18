"""Busca de Atas na API não documentada do BCB. Nunca roda no meio de uma execução.
User-Agent identificado (SUNO_CONTATO), cerca de uma requisição por segundo.

ADR 0006.
"""

from __future__ import annotations

from pathlib import Path

from suno.dominio import Ata


def listar_atas(quantidade: int = 10) -> list[dict]:
    raise NotImplementedError("Etapa 1, agente 5 — ADR 0006")


def buscar_ata(destino: Path, reuniao: int | None = None) -> Ata:
    """Baixa o arquivo da reunião pedida (ou da mais recente) e grava PDF, texto e metadados ao lado."""
    raise NotImplementedError("Etapa 1, agente 5 — ADR 0006")
