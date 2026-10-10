"""Três geradores de persona produzem as nove Células em paralelo.

ADR 0010, 0015.

Paralelismo aqui é um ``ThreadPoolExecutor`` e nada mais: as nove posições da Matriz são
independentes — nenhuma lê o resultado da outra — então não há sequência a decidir, e sim
nove transformações que rodam ao mesmo tempo. A espera é de rede, não de CPU, e por isso
thread basta.

O retorno é o **histórico** de cada posição, não só a Célula: o Ciclo de correção pode ter
gerado até três, e a reprovação consertada é entregável do case tanto quanto a aprovação.
A ordem do resultado é a de ``MATRIZ``, sempre, qualquer que tenha sido a ordem de término.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from suno.dominio import (
    MATRIZ,
    Ancoras,
    Ata,
    Audiencia,
    Formato,
    HistoricoCelula,
    ModoSelecao,
    SelecaoCuradoria,
)
from suno.gerador.curador import DossieCurado
from suno.gerador.personas import AGENTES_GERADORES
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.comite import Comite

TRABALHADORES = len(AGENTES_GERADORES)
"""Um trabalhador por gerador especializado: três."""


def gerar_matriz(
    ata: Ata,
    ancoras: Ancoras,
    provedor: Provedor,
    *,
    comite: "Comite | None" = None,
) -> list[HistoricoCelula]:
    """Compatibilidade: monta um dossiê de fonte única e gera a Matriz."""
    dossie = DossieCurado(
        ata=ata,
        ancoras=ancoras,
        selecao=SelecaoCuradoria(modo=ModoSelecao.SEPARADA, itens=[ata.identificador]),
    )
    return gerar_matriz_do_dossie(dossie, provedor, comite=comite)


def gerar_matriz_do_dossie(
    dossie: DossieCurado,
    provedor: Provedor,
    *,
    comite: "Comite | None" = None,
) -> list[HistoricoCelula]:
    """Os três geradores recebem o mesmo dossiê e devolvem a Matriz na ordem fixa."""
    prontos: dict[tuple[Audiencia, Formato], HistoricoCelula] = {}
    with ThreadPoolExecutor(max_workers=TRABALHADORES) as executor:
        futuros = {
            executor.submit(agente.gerar, dossie, provedor, comite=comite): agente.audiencia
            for agente in AGENTES_GERADORES
        }
        for futuro in futuros:
            for historico in futuro.result():
                prontos[(historico.audiencia, historico.formato)] = historico
    return [prontos[posicao] for posicao in MATRIZ]
