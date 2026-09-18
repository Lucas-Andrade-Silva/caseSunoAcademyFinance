"""Leitura do arquivo da Ata. PDF é reconhecido pelos primeiros bytes (`%PDF`), nunca pelo
cabeçalho HTTP, que mente. Extração com pypdf (BSD-3).

ADR 0006.
"""

from __future__ import annotations

from pathlib import Path

from suno.dominio import Ata


def eh_pdf(caminho_ou_bytes: Path | bytes) -> bool:
    raise NotImplementedError("Etapa 1, agente 5 — ADR 0006")


def extrair_texto(caminho: Path) -> str:
    raise NotImplementedError("Etapa 1, agente 5 — ADR 0006")


def carregar_ata(caminho: Path) -> Ata:
    """Lê o .pdf (ou o .txt já extraído ao lado) e o .json de metadados; devolve a Ata."""
    raise NotImplementedError("Etapa 1, agente 5 — ADR 0006")
