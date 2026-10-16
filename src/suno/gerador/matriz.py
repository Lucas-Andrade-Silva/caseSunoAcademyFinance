"""Três geradores de persona produzem as nove Células em paralelo.

ADR 0010, 0015.

Paralelismo aqui é um ``ThreadPoolExecutor`` e nada mais: as nove posições da Matriz são
independentes — nenhuma lê o resultado da outra — então não há sequência a decidir, e sim
nove transformações que rodam ao mesmo tempo. A espera é de rede, não de CPU, e por isso
thread basta.

O retorno é o **histórico** de cada posição, não só a Célula: o Ciclo de correção pode ter
gerado até três, e a reprovação consertada é entregável do case tanto quanto a aprovação.
A ordem do resultado é a de ``MATRIZ``, sempre, qualquer que tenha sido a ordem de término.

``posicoes`` é o pedido: o padrão são as nove, mas a interface pode pedir de uma a nove
Células. Cada Audiência vira um trabalhador que gera só os Formatos pedidos para ela.
"""

from __future__ import annotations

from collections.abc import Sequence
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
from suno.gerador.ciclo import Andou
from suno.gerador.curador import DossieCurado
from suno.gerador.personas import AGENTES_GERADORES
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.avaliador.fidelidade import VerificadorDeFidelidade
    from suno.avaliador.qualidade import AvaliadorDeQualidade

TRABALHADORES = len(AGENTES_GERADORES)
"""Um trabalhador por gerador especializado: três."""


def gerar_matriz(
    ata: Ata,
    ancoras: Ancoras,
    provedor: Provedor,
    *,
    qualidade: "AvaliadorDeQualidade | None" = None,
    fidelidade: "VerificadorDeFidelidade | None" = None,
) -> list[HistoricoCelula]:
    """Compatibilidade: monta um dossiê de fonte única e gera a Matriz."""
    dossie = DossieCurado(
        ata=ata,
        ancoras=ancoras,
        selecao=SelecaoCuradoria(modo=ModoSelecao.SEPARADA, itens=[ata.identificador]),
    )
    return gerar_matriz_do_dossie(
        dossie, provedor, qualidade=qualidade, fidelidade=fidelidade
    )


def gerar_matriz_do_dossie(
    dossie: DossieCurado,
    provedor: Provedor,
    *,
    qualidade: "AvaliadorDeQualidade | None" = None,
    fidelidade: "VerificadorDeFidelidade | None" = None,
    posicoes: Sequence[tuple[Audiencia, Formato]] = MATRIZ,
    ao_andar: Andou | None = None,
) -> list[HistoricoCelula]:
    """Os geradores recebem o mesmo dossiê e devolvem as Células pedidas na ordem fixa."""
    pedidas = set(posicoes)
    prontos: dict[tuple[Audiencia, Formato], HistoricoCelula] = {}
    with ThreadPoolExecutor(max_workers=TRABALHADORES) as executor:
        futuros = [
            executor.submit(
                agente.gerar_formatos,
                dossie,
                provedor,
                [
                    formato
                    for audiencia, formato in MATRIZ
                    if audiencia is agente.audiencia and (audiencia, formato) in pedidas
                ],
                qualidade=qualidade,
                fidelidade=fidelidade,
                ao_andar=ao_andar,
            )
            for agente in AGENTES_GERADORES
        ]
        for futuro in futuros:
            for historico in futuro.result():
                prontos[(historico.audiencia, historico.formato)] = historico
    return [prontos[posicao] for posicao in MATRIZ if posicao in pedidas]
