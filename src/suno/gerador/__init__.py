"""Curador, três geradores, regras fixas e LLM Judge transversal.

ADR 0010, 0015, 0016.

O caminho é sempre o mesmo, sem decisão dinâmica em nenhum ponto::

    carregar_ata → AgenteCurador → 3 Geradores de persona → Matriz 3×3
                 → regras individuais → LLM Judge transversal → gravar_execucao

O Avaliador de Célula entra em ``rodar_ciclo``. O Judge confere o conjunto e devolve
correções seletivas. Entre geração e regras individuais passa
``(Conteúdo, Âncora[], Audiência) → Laudo`` (ADR 0001).
"""

from __future__ import annotations

from suno.gerador.ciclo import rodar_ciclo
from suno.gerador.curador import AgenteCurador, DossieCurado
from suno.gerador.execucao import (
    carregar_execucao,
    executar,
    gravar_execucao,
    listar_execucoes,
)
from suno.gerador.extracao import extrair_ancoras
from suno.gerador.matriz import gerar_matriz, gerar_matriz_do_dossie
from suno.gerador.moldes import montar_conteudo, montar_pedido, preencher
from suno.gerador.orquestracao import rodar_ciclo_transversal
from suno.gerador.personas import AGENTES_GERADORES, AgenteGeradorPersona

__all__ = [
    "AGENTES_GERADORES",
    "AgenteCurador",
    "AgenteGeradorPersona",
    "DossieCurado",
    "carregar_execucao",
    "executar",
    "extrair_ancoras",
    "gerar_matriz",
    "gerar_matriz_do_dossie",
    "gravar_execucao",
    "listar_execucoes",
    "montar_conteudo",
    "montar_pedido",
    "preencher",
    "rodar_ciclo",
    "rodar_ciclo_transversal",
]
