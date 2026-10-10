"""A decisão humana sobre uma Célula: aprovar ou reprovar, e quando isso é proibido.

Compliance é métrica do Laudo (CLAUDE.md): a Célula cujo Laudo final carrega
``MotivoReprovacao.RECOMENDACAO`` não pode ser aprovada por ninguém. A regra mora aqui, e não
na tela, para que a API a imponha mesmo a quem chamar a rota sem passar pela interface.
"""

from __future__ import annotations

from suno.dominio import (
    Audiencia,
    DecisaoHumana,
    Destino,
    EstadoDecisao,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    MotivoReprovacao,
)


class CelulaNaoEncontrada(LookupError):
    """A posição não existe nesta execução."""


class DecisaoInvalida(ValueError):
    """O pedido não faz sentido para esta Célula: sem conteúdo, em correção ou sem motivo."""


class DecisaoBloqueada(Exception):
    """O Laudo proíbe a decisão: a Célula cruzou a linha da Recomendação."""


def celula_bloqueada(historico: HistoricoCelula) -> bool:
    """O Laudo final detectou Recomendação: esta Célula não pode ser aprovada."""
    laudo = historico.laudo_final
    return laudo is not None and MotivoReprovacao.RECOMENDACAO in laudo.motivos


def decidir(
    execucao: Execucao,
    audiencia: Audiencia,
    formato: Formato,
    estado: EstadoDecisao,
    *,
    motivo: str | None = None,
    revisor: str | None = None,
) -> DecisaoHumana:
    """Registra a decisão em ``execucao.decisoes`` e resolve a Pendência H4 da posição.

    Muda o objeto em memória; quem chama grava em disco. Uma decisão nova na mesma posição
    substitui a anterior.
    """
    historico = execucao.historico(audiencia, formato)
    if historico is None:
        raise CelulaNaoEncontrada("Célula não encontrada nesta execução")
    if historico.celula_final is None:
        raise DecisaoInvalida("a Célula não tem conteúdo gerado: não há o que decidir")

    motivo_limpo = (motivo or "").strip() or None
    if estado is EstadoDecisao.REPROVADA and motivo_limpo is None:
        raise DecisaoInvalida("reprovar exige motivo")

    if estado is EstadoDecisao.APROVADA:
        if celula_bloqueada(historico):
            raise DecisaoBloqueada(
                "o Laudo detectou Recomendação: esta Célula não pode ser aprovada"
            )
        if historico.destino_final is Destino.REPROVADO_CORRIGIVEL:
            raise DecisaoInvalida("a Célula ainda está em correção: espere o Ciclo terminar")

    decisao = DecisaoHumana(
        audiencia=audiencia,
        formato=formato,
        estado=estado,
        motivo=motivo_limpo,
        revisor=(revisor or "").strip() or None,
    )
    execucao.decisoes = [
        anterior
        for anterior in execucao.decisoes
        if (anterior.audiencia, anterior.formato) != (audiencia, formato)
    ] + [decisao]

    resumo_da_decisao = estado.value if motivo_limpo is None else f"{estado.value}: {motivo_limpo}"
    for pendencia in execucao.pendencias:
        if (
            pendencia.fila is FilaHumana.H4_REVISAO
            and (pendencia.audiencia, pendencia.formato) == (audiencia, formato)
            and not pendencia.resolvida
        ):
            pendencia.resolvida = True
            pendencia.decisao = resumo_da_decisao
    return decisao
