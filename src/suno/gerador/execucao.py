"""Uma execução ponta a ponta: lê a Ata do disco, extrai Âncoras, gera a Matriz, avalia,
corrige e grava `data/execucoes/<id>/execucao.json`, o mesmo arquivo que a API e o pytest leem.

ADR 0001, 0006.
"""

from __future__ import annotations

from pathlib import Path

from suno.dominio import Execucao


def executar(caminho_ata: Path, provedor: str, pasta_execucoes: Path, *, comite: bool = False) -> Execucao:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0001, 0006")


def carregar_execucao(identificador: str, pasta_execucoes: Path) -> Execucao:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0001, 0006")


def gravar_execucao(execucao: Execucao, pasta_execucoes: Path) -> Path:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0001, 0006")
