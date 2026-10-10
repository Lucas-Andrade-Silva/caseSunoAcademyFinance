"""O que a lista de Saídas e a Matriz precisam saber de cada Célula, sem abrir o Laudo inteiro.

A regra do status vive aqui, no servidor, para que a lista, o contador do menu e a Saída
aberta concordem. Uma Célula bloqueada por Compliance ou sem conteúdo gerado não tem o que
um humano decida, então não segura a Saída em "aguardando revisão".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from suno.dominio import Audiencia, Destino, EstadoDecisao, EstadoMedida, Execucao, Formato
from suno.revisao import celula_bloqueada

StatusSaida = Literal["aguardando_revisao", "concluida"]


class PosicaoResumo(BaseModel):
    """Uma posição da Matriz, no mínimo que a tela precisa para colorir e rotular."""

    audiencia: Audiencia
    formato: Formato
    destino: Destino
    decisao: EstadoDecisao | None
    bloqueada: bool
    sem_conteudo: bool
    revisao_comite: bool


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
