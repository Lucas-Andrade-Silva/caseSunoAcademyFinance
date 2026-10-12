"""Avaliador transversal da Matriz completa, sem LLM e sem rede."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from suno.dominio import (
    MATRIZ,
    Ancoras,
    Audiencia,
    AvaliacaoTransversal,
    Destino,
    EstadoAvaliacaoTransversal,
    Formato,
    HistoricoCelula,
)


def _rotulo(posicao: tuple) -> str:
    audiencia, formato = posicao
    return f"{audiencia.value}:{formato.value}"


def avaliar_matriz(
    celulas: Sequence[HistoricoCelula],
    ancoras: Ancoras,
    *,
    posicoes: Sequence[tuple[Audiencia, Formato]] = MATRIZ,
) -> AvaliacaoTransversal:
    """Verifica quantidade, unicidade, aprovação e referências das Células pedidas.

    ``posicoes`` é o pedido: sem ele valem as nove da Matriz. Completude é relativa a ele, e
    uma Célula que chegou sem ter sido pedida reprova a Matriz.
    """
    esperadas = set(posicoes)
    recebidas = [(historico.audiencia, historico.formato) for historico in celulas]
    contagem = Counter(recebidas)
    faltantes = sorted(_rotulo(posicao) for posicao in esperadas - set(recebidas))
    inesperadas = sorted(_rotulo(posicao) for posicao in set(recebidas) - esperadas)
    duplicadas = sorted(_rotulo(posicao) for posicao, total in contagem.items() if total > 1)

    com_conteudo = [historico for historico in celulas if historico.celula_final is not None]
    reprovadas = sorted(
        _rotulo((historico.audiencia, historico.formato))
        for historico in celulas
        if historico.destino_final is not Destino.APROVADO
    )

    chaves_validas = {ancora.chave for ancora in ancoras.numericas}
    invalidas: list[str] = []
    for historico in com_conteudo:
        celula = historico.celula_final
        assert celula is not None
        for chave in celula.conteudo.ancoras_citadas:
            if chave not in chaves_validas:
                invalidas.append(
                    f"{_rotulo((historico.audiencia, historico.formato))}:{chave}"
                )
    invalidas.sort()

    observacoes: list[str] = []
    if faltantes:
        observacoes.append("faltam posições na Matriz")
    if inesperadas:
        observacoes.append("há posições que não foram pedidas")
    if duplicadas:
        observacoes.append("há posições repetidas na Matriz")
    if len(com_conteudo) != len(esperadas):
        observacoes.append("nem todas as posições produziram conteúdo")
    if reprovadas:
        observacoes.append("há Células reprovadas ou enviadas à revisão humana")
    if invalidas:
        observacoes.append("há referências a Âncoras inexistentes")

    aprovada = (
        len(celulas) == len(esperadas)
        and len(com_conteudo) == len(esperadas)
        and not faltantes
        and not inesperadas
        and not duplicadas
        and not reprovadas
        and not invalidas
    )
    return AvaliacaoTransversal(
        estado=(
            EstadoAvaliacaoTransversal.APROVADA
            if aprovada
            else EstadoAvaliacaoTransversal.REVISAO_HUMANA
        ),
        total_esperado=len(esperadas),
        total_recebido=len(celulas),
        total_com_conteudo=len(com_conteudo),
        posicoes_faltantes=faltantes,
        posicoes_inesperadas=inesperadas,
        posicoes_duplicadas=duplicadas,
        posicoes_reprovadas=reprovadas,
        referencias_invalidas=invalidas,
        observacoes=observacoes,
    )
