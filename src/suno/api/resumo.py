"""O que a lista de Saídas e a Matriz precisam saber de cada Célula, sem abrir o Laudo inteiro.

A regra do status vive aqui, no servidor, para que a lista, o contador do menu e a Saída
aberta concordem. Uma Célula bloqueada por Compliance ou sem conteúdo gerado não tem o que
um humano decida, então não segura a Saída em "aguardando revisão".

Uma Saída que ainda está sendo gerada (ou que parou antes de gravar o ``execucao.json``) só
tem ``andamento.json``: as posições dela vêm daí, com a ``etapa`` de cada Célula e sem Laudo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from suno.dominio import (
    Andamento,
    Audiencia,
    Destino,
    EstadoDecisao,
    EstadoDoAndamento,
    EstadoMedida,
    EtapaDaCelula,
    Execucao,
    Formato,
)
from suno.revisao import celula_bloqueada

StatusSaida = Literal[
    "na_fila", "gerando", "aguardando_revisao", "concluida", "interrompida", "falhou"
]


class PosicaoResumo(BaseModel):
    """Uma posição da Matriz, no mínimo que a tela precisa para colorir e rotular."""

    audiencia: Audiencia
    formato: Formato
    destino: Destino | None
    """``None`` enquanto a Célula não tem Laudo (ainda está sendo gerada)."""
    decisao: EstadoDecisao | None
    bloqueada: bool
    sem_conteudo: bool
    revisao_comite: bool
    etapa: EtapaDaCelula | None = None
    """Só para Saída em geração ou que parou antes de gravar a execução."""


def montar_posicoes(execucao: Execucao) -> list[PosicaoResumo]:
    """Uma entrada por Célula pedida, na ordem em que estão em ``execucao.celulas``."""
    posicoes: list[PosicaoResumo] = []
    for historico in execucao.celulas:
        decisao = execucao.decisao_de(historico.audiencia, historico.formato)
        laudo = historico.laudo_final
        revisao_comite = (
            laudo is not None
            and laudo.comite is not None
            and any(d.estado is EstadoMedida.REVISAO_HUMANA for d in laudo.comite.dimensoes)
        )
        posicoes.append(
            PosicaoResumo(
                audiencia=historico.audiencia,
                formato=historico.formato,
                destino=historico.destino_final,
                decisao=decisao.estado if decisao is not None else None,
                bloqueada=celula_bloqueada(historico),
                sem_conteudo=historico.celula_final is None,
                revisao_comite=revisao_comite,
            )
        )
    return posicoes


def status_da_saida(posicoes: list[PosicaoResumo]) -> StatusSaida:
    for posicao in posicoes:
        if posicao.decisao is None and not posicao.bloqueada and not posicao.sem_conteudo:
            return "aguardando_revisao"
    return "concluida"


def montar_posicoes_do_andamento(andamento: Andamento) -> list[PosicaoResumo]:
    """As Células de uma Saída que ainda não tem ``execucao.json``, na ordem do pedido."""
    return [
        PosicaoResumo(
            audiencia=celula.audiencia,
            formato=celula.formato,
            destino=None,
            decisao=None,
            bloqueada=False,
            sem_conteudo=True,
            revisao_comite=False,
            etapa=celula.etapa,
        )
        for celula in andamento.celulas
    ]


def status_do_andamento(andamento: Andamento) -> StatusSaida:
    """O status de uma Saída sem ``execucao.json``.

    ``concluida`` sem execução gravada é um job que acabou mal: aparece como ``falhou``.
    """
    return {
        EstadoDoAndamento.NA_FILA: "na_fila",
        EstadoDoAndamento.GERANDO: "gerando",
        EstadoDoAndamento.INTERROMPIDA: "interrompida",
        EstadoDoAndamento.FALHOU: "falhou",
        EstadoDoAndamento.CONCLUIDA: "falhou",
    }[andamento.estado]
