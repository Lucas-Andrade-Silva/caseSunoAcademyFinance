"""Ciclo transversal: regras fixas, LLM Judge e retorno seletivo às personas."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Sequence

from suno.avaliador.juiz_transversal import AgenteAvaliadorTransversal
from suno.avaliador.transversal import avaliar_matriz
from suno.dominio import (
    MATRIZ,
    Audiencia,
    CorrecaoTransversalAplicada,
    ErroProvedor,
    EstadoAvaliacaoTransversal,
    EstadoJulgamentoTransversal,
    Formato,
    HistoricoCelula,
    JulgamentoTransversal,
    ResultadoCicloTransversal,
)
from suno.gerador.ciclo import sem_credencial
from suno.gerador.curador import DossieCurado
from suno.gerador.personas import AGENTES_GERADORES, AgenteGeradorPersona
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.comite import Comite

TETO_DE_CORRECOES_TRANSVERSAIS = 2
"""Duas correções seletivas; depois, o impasse vai para revisão humana."""


def _ordenar(celulas: Sequence[HistoricoCelula]) -> list[HistoricoCelula]:
    por_posicao = {(celula.audiencia, celula.formato): celula for celula in celulas}
    return [por_posicao[posicao] for posicao in MATRIZ if posicao in por_posicao]


def _regenerar_afetadas(
    dossie: DossieCurado,
    atuais: list[HistoricoCelula],
    julgamento: JulgamentoTransversal,
    provedor: Provedor,
    *,
    comite: "Comite | None",
) -> tuple[list[HistoricoCelula], list[CorrecaoTransversalAplicada]]:
    por_posicao = {(celula.audiencia, celula.formato): celula for celula in atuais}
    instrucoes: dict[tuple[Audiencia, Formato], list[str]] = {}
    for problema in julgamento.problemas:
        posicao = (problema.audiencia, problema.formato)
        instrucao = (
            f"[{problema.criterio.value}] {problema.correcao} "
            f"Evidência observada: {problema.evidencia}"
        )
        if instrucao not in instrucoes.setdefault(posicao, []):
            instrucoes[posicao].append(instrucao)

    agentes: dict[Audiencia, AgenteGeradorPersona] = {
        agente.audiencia: agente for agente in AGENTES_GERADORES
    }
    por_audiencia: dict[Audiencia, dict[Formato, list[str]]] = {}
    for (audiencia, formato), orientacoes in instrucoes.items():
        por_audiencia.setdefault(audiencia, {})[formato] = orientacoes

    novos: list[HistoricoCelula] = []
    with ThreadPoolExecutor(max_workers=len(por_audiencia)) as executor:
        futuros = [
            executor.submit(
                agentes[audiencia].gerar_formatos,
                dossie,
                provedor,
                list(por_formato),
                comite=comite,
                orientacoes=por_formato,
            )
            for audiencia, por_formato in por_audiencia.items()
        ]
        for futuro in futuros:
            novos.extend(futuro.result())

    correcoes: list[CorrecaoTransversalAplicada] = []
    for novo in novos:
        posicao = (novo.audiencia, novo.formato)
        anterior = por_posicao[posicao]
        correcoes.append(
            CorrecaoTransversalAplicada(
                rodada=julgamento.rodada,
                audiencia=novo.audiencia,
                formato=novo.formato,
                instrucoes=instrucoes[posicao],
                historico_anterior=anterior,
            )
        )
        por_posicao[posicao] = novo
    return _ordenar(list(por_posicao.values())), correcoes


def rodar_ciclo_transversal(
    dossie: DossieCurado,
    celulas: Sequence[HistoricoCelula],
    provedor: Provedor,
    *,
    comite: "Comite | None" = None,
) -> tuple[list[HistoricoCelula], ResultadoCicloTransversal]:
    """Aprova a Matriz ou termina em revisão humana com todo o histórico preservado."""
    atuais = _ordenar(celulas)
    julgamentos: list[JulgamentoTransversal] = []
    correcoes: list[CorrecaoTransversalAplicada] = []
    juiz = AgenteAvaliadorTransversal(provedor)

    for rodada in range(TETO_DE_CORRECOES_TRANSVERSAIS + 1):
        deterministica = avaliar_matriz(atuais, dossie.ancoras)
        if deterministica.estado is not EstadoAvaliacaoTransversal.APROVADA:
            return atuais, ResultadoCicloTransversal(
                estado=EstadoAvaliacaoTransversal.REVISAO_HUMANA,
                avaliacao_deterministica=deterministica,
                julgamentos=julgamentos,
                correcoes_aplicadas=correcoes,
                motivo_final="a Matriz não passou pela avaliação determinística",
            )

        try:
            julgamento = juiz.julgar(
                dossie.ata, dossie.ancoras, atuais, rodada=rodada
            )
        except ErroProvedor as erro:
            julgamento = JulgamentoTransversal(
                rodada=rodada,
                estado=EstadoJulgamentoTransversal.FALHA,
                provedor=getattr(provedor, "nome", "desconhecido"),
                falha=sem_credencial(str(erro)),
            )
        except Exception as erro:  # noqa: BLE001 - a Matriz precisa chegar à revisão humana
            julgamento = JulgamentoTransversal(
                rodada=rodada,
                estado=EstadoJulgamentoTransversal.FALHA,
                provedor=getattr(provedor, "nome", "desconhecido"),
                falha=f"erro inesperado no Judge: {sem_credencial(str(erro))}",
            )
        julgamentos.append(julgamento)

        if julgamento.estado is EstadoJulgamentoTransversal.APROVADO:
            return atuais, ResultadoCicloTransversal(
                estado=EstadoAvaliacaoTransversal.APROVADA,
                avaliacao_deterministica=deterministica,
                julgamentos=julgamentos,
                correcoes_aplicadas=correcoes,
                motivo_final="regras determinísticas e LLM Judge aprovaram a Matriz",
            )
        if julgamento.estado is EstadoJulgamentoTransversal.FALHA:
            return atuais, ResultadoCicloTransversal(
                estado=EstadoAvaliacaoTransversal.REVISAO_HUMANA,
                avaliacao_deterministica=deterministica,
                julgamentos=julgamentos,
                correcoes_aplicadas=correcoes,
                motivo_final="o LLM Judge falhou; nenhuma aprovação foi presumida",
            )
        if julgamento.estado is EstadoJulgamentoTransversal.GRAVE:
            return atuais, ResultadoCicloTransversal(
                estado=EstadoAvaliacaoTransversal.REVISAO_HUMANA,
                avaliacao_deterministica=deterministica,
                julgamentos=julgamentos,
                correcoes_aplicadas=correcoes,
                motivo_final="o LLM Judge encontrou problema grave",
            )
        if rodada >= TETO_DE_CORRECOES_TRANSVERSAIS:
            return atuais, ResultadoCicloTransversal(
                estado=EstadoAvaliacaoTransversal.REVISAO_HUMANA,
                avaliacao_deterministica=deterministica,
                julgamentos=julgamentos,
                correcoes_aplicadas=correcoes,
                motivo_final="o ciclo transversal esgotou duas correções",
            )

        atuais, aplicadas = _regenerar_afetadas(
            dossie, atuais, julgamento, provedor, comite=comite
        )
        correcoes.extend(aplicadas)

    raise AssertionError("ciclo transversal saiu do limite sem resultado")


__all__ = ["TETO_DE_CORRECOES_TRANSVERSAIS", "rodar_ciclo_transversal"]
