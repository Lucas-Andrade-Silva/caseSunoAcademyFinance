"""A decisão humana sobre uma Célula, e a linha que ninguém cruza.

Compliance é métrica do Laudo (CLAUDE.md): a Célula cujo Laudo final tem Recomendação não
pode ser aprovada por rota nenhuma. Tudo aqui roda sem rede e sem LLM.
"""

from __future__ import annotations

import pytest

from suno.dominio import (
    Audiencia,
    Destino,
    EstadoDecisao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    MotivoReprovacao,
    Pendencia,
)
from suno.revisao import (
    CelulaNaoEncontrada,
    DecisaoBloqueada,
    DecisaoInvalida,
    celula_bloqueada,
    decidir,
)
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto

TEXTO = Formato.TEXTO_ANALITICO


def test_aprovar_celula_aprovada_pelo_laudo_registra_a_decisao() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    decisao = decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA, revisor=" Ana ")

    assert decisao.estado is EstadoDecisao.APROVADA
    assert decisao.revisor == "Ana"
    assert execucao.decisao_de(Audiencia.INICIANTE, TEXTO) is decisao


def test_reprovar_exige_motivo() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    with pytest.raises(DecisaoInvalida, match="motivo"):
        decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="  ")

    assert execucao.decisoes == []


def test_reprovar_com_motivo_guarda_o_motivo() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    decisao = decidir(
        execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="tom condescendente"
    )

    assert decisao.estado is EstadoDecisao.REPROVADA
    assert decisao.motivo == "tom condescendente"


def test_celula_com_recomendacao_nao_pode_ser_aprovada() -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.RECOMENDACAO,),
    )
    execucao = execucao_de_teste(historico)

    assert celula_bloqueada(historico) is True
    with pytest.raises(DecisaoBloqueada, match="Recomendação"):
        decidir(execucao, Audiencia.AVANCADO, TEXTO, EstadoDecisao.APROVADA)

    assert execucao.decisoes == []


def test_celula_com_recomendacao_pode_ser_reprovada_por_humano() -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.RECOMENDACAO,),
    )
    execucao = execucao_de_teste(historico)

    decisao = decidir(
        execucao, Audiencia.AVANCADO, TEXTO, EstadoDecisao.REPROVADA, motivo="recomenda comprar"
    )

    assert decisao.estado is EstadoDecisao.REPROVADA


def test_celula_em_revisao_humana_sem_recomendacao_pode_ser_aprovada() -> None:
    historico = historico_de_texto(
        Audiencia.INTERMEDIARIO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.FLESCH_BR,),
    )
    execucao = execucao_de_teste(historico)

    decisao = decidir(execucao, Audiencia.INTERMEDIARIO, TEXTO, EstadoDecisao.APROVADA)

    assert decisao.estado is EstadoDecisao.APROVADA


def test_celula_ainda_em_correcao_nao_pode_ser_aprovada() -> None:
    historico = historico_de_texto(
        Audiencia.INICIANTE,
        Destino.REPROVADO_CORRIGIVEL,
        (MotivoReprovacao.FLESCH_BR,),
    )
    execucao = execucao_de_teste(historico)

    with pytest.raises(DecisaoInvalida, match="correção"):
        decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)


def test_celula_inexistente_nao_e_encontrada() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    with pytest.raises(CelulaNaoEncontrada):
        decidir(execucao, Audiencia.AVANCADO, TEXTO, EstadoDecisao.APROVADA)


def test_celula_sem_conteudo_nao_tem_o_que_decidir() -> None:
    sem_conteudo = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=TEXTO,
        tentativas=[],
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
        falha="provedor sem cota",
    )
    execucao = execucao_de_teste(sem_conteudo)

    with pytest.raises(DecisaoInvalida, match="conteúdo"):
        decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="x")


def test_nova_decisao_substitui_a_anterior() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.REPROVADA, motivo="mudei de ideia")

    assert len(execucao.decisoes) == 1
    assert execucao.decisoes[0].estado is EstadoDecisao.REPROVADA


def test_decidir_resolve_a_pendencia_h4_da_celula() -> None:
    historico = historico_de_texto(
        Audiencia.INTERMEDIARIO,
        Destino.REPROVADO_REVISAO_HUMANA,
        (MotivoReprovacao.FLESCH_BR,),
    )
    pendencia = Pendencia(
        fila=FilaHumana.H4_REVISAO,
        audiencia=Audiencia.INTERMEDIARIO,
        formato=TEXTO,
        motivo="flesch_br",
    )
    execucao = execucao_de_teste(historico, pendencias=(pendencia,))

    decidir(execucao, Audiencia.INTERMEDIARIO, TEXTO, EstadoDecisao.APROVADA)

    assert execucao.pendencias[0].resolvida is True
    assert (execucao.pendencias[0].decisao or "").startswith("aprovada")
