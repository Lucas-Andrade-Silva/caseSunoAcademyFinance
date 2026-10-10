"""O resumo por posição: o que a lista de Saídas e a Matriz precisam saber de cada Célula."""

from __future__ import annotations

from suno.api.resumo import montar_posicoes, status_da_saida
from suno.dominio import (
    Audiencia,
    Destino,
    DimensaoSubjetiva,
    EstadoDecisao,
    EstadoMedida,
    Formato,
    HistoricoCelula,
    JulgamentoDimensao,
    MotivoReprovacao,
    ResultadoComite,
)
from suno.revisao import decidir
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto

TEXTO = Formato.TEXTO_ANALITICO


def test_posicao_sem_decisao_vem_pendente() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))

    (posicao,) = montar_posicoes(execucao)

    assert posicao.audiencia is Audiencia.INICIANTE
    assert posicao.formato is TEXTO
    assert posicao.destino is Destino.APROVADO
    assert posicao.decisao is None
    assert posicao.bloqueada is False
    assert posicao.sem_conteudo is False
    assert posicao.revisao_comite is False


def test_decisao_humana_aparece_na_posicao() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)

    (posicao,) = montar_posicoes(execucao)

    assert posicao.decisao is EstadoDecisao.APROVADA


def test_recomendacao_no_laudo_marca_a_posicao_como_bloqueada() -> None:
    historico = historico_de_texto(
        Audiencia.AVANCADO, Destino.REPROVADO_REVISAO_HUMANA, (MotivoReprovacao.RECOMENDACAO,)
    )

    (posicao,) = montar_posicoes(execucao_de_teste(historico))

    assert posicao.bloqueada is True


def test_posicao_sem_tentativa_e_sem_conteudo() -> None:
    historico = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=TEXTO,
        tentativas=[],
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
        falha="provedor sem cota",
    )

    (posicao,) = montar_posicoes(execucao_de_teste(historico))

    assert posicao.sem_conteudo is True
    assert posicao.destino is Destino.REPROVADO_REVISAO_HUMANA


def test_dimensao_do_comite_em_revisao_humana_marca_a_posicao() -> None:
    historico = historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO)
    historico.tentativas[0].laudo.comite = ResultadoComite(
        dimensoes=[
            JulgamentoDimensao(
                dimensao=DimensaoSubjetiva.TOM, estado=EstadoMedida.REVISAO_HUMANA
            )
        ],
        provedores=["groq", "sambanova"],
    )

    (posicao,) = montar_posicoes(execucao_de_teste(historico))

    assert posicao.revisao_comite is True
    assert posicao.destino is Destino.APROVADO


def test_status_aguarda_revisao_enquanto_alguma_celula_espera_decisao() -> None:
    execucao = execucao_de_teste(
        historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO),
        historico_de_texto(Audiencia.INTERMEDIARIO, Destino.APROVADO),
    )
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)

    assert status_da_saida(montar_posicoes(execucao)) == "aguardando_revisao"


def test_status_conclui_quando_tudo_foi_decidido_ou_nao_pode_ser() -> None:
    execucao = execucao_de_teste(
        historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO),
        historico_de_texto(
            Audiencia.AVANCADO, Destino.REPROVADO_REVISAO_HUMANA, (MotivoReprovacao.RECOMENDACAO,)
        ),
    )
    decidir(execucao, Audiencia.INICIANTE, TEXTO, EstadoDecisao.APROVADA)

    assert status_da_saida(montar_posicoes(execucao)) == "concluida"
