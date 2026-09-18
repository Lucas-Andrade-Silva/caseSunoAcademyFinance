"""O Gerador: sequência fixa de chamadas estruturadas. Não é agente, não usa ferramentas,
não usa LangGraph nem MCP.

ADR 0010.

O caminho é sempre o mesmo, sem decisão dinâmica em nenhum ponto::

    carregar_ata → extrair_ancoras (1× por Ata) → gerar_matriz (9 em paralelo)
                 → rodar_ciclo (até 3 gerações por Célula) → gravar_execucao

O Avaliador entra dentro de ``rodar_ciclo`` e é o único a dizer se uma Célula está pronta.
Entre os dois módulos passa só ``(Conteúdo, Âncora[], Audiência) → Laudo`` (ADR 0001).
"""

from __future__ import annotations

from suno.gerador.ciclo import rodar_ciclo
from suno.gerador.execucao import (
    carregar_execucao,
    executar,
    gravar_execucao,
    listar_execucoes,
)
from suno.gerador.extracao import extrair_ancoras
from suno.gerador.matriz import gerar_matriz
from suno.gerador.moldes import montar_conteudo, montar_pedido, preencher

__all__ = [
    "carregar_execucao",
    "executar",
    "extrair_ancoras",
    "gerar_matriz",
    "gravar_execucao",
    "listar_execucoes",
    "montar_conteudo",
    "montar_pedido",
    "preencher",
    "rodar_ciclo",
]
