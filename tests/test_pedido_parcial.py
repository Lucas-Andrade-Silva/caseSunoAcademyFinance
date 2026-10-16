"""O pipeline com um subconjunto da Matriz: 1, 5 ou 9 Células (spec do front, seção 6.1, achado 2).

Os testes trocam `gerar_celula` e `avaliar` do Ciclo por fakes que respondem na hora: o que se
confere aqui é a orquestração (quais posições, em que ordem, que avisos de andamento), não o
texto nem o Laudo.
"""

from __future__ import annotations

import threading

import pytest

from suno.avaliador import avaliar_matriz
from suno.dominio import (
    MATRIZ,
    Audiencia,
    Celula,
    Destino,
    EstadoAvaliacaoTransversal,
    EtapaDaCelula,
    Formato,
    Laudo,
    MotivoReprovacao,
)
from suno.gerador.matriz import gerar_matriz_do_dossie
from suno.provedores.falso import ProvedorFalso
from tests.test_curador_e_matriz import _ancoras, _conteudo, _dossie, _historico

UMA = MATRIZ[:1]
CINCO = (MATRIZ[0], MATRIZ[2], MATRIZ[4], MATRIZ[6], MATRIZ[8])


def _historicos(posicoes):
    return [_historico(audiencia, formato) for audiencia, formato in posicoes]


# ---------------------------------------------------------------------------
# A avaliação da Matriz é relativa ao pedido
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("posicoes", [UMA, CINCO, MATRIZ], ids=["1", "5", "9"])
def test_matriz_completa_para_o_pedido_aprova(posicoes):
    veredito = avaliar_matriz(_historicos(posicoes), _ancoras(), posicoes=posicoes)

    assert veredito.estado is EstadoAvaliacaoTransversal.APROVADA
    assert veredito.total_esperado == len(posicoes)
    assert veredito.total_recebido == len(posicoes)
    assert veredito.posicoes_faltantes == []
    assert veredito.posicoes_inesperadas == []


def test_falta_so_o_que_o_pedido_exigia():
    pedido = CINCO
    recebidas = _historicos(pedido[:-1])

    veredito = avaliar_matriz(recebidas, _ancoras(), posicoes=pedido)

    assert veredito.estado is EstadoAvaliacaoTransversal.REVISAO_HUMANA
    audiencia, formato = pedido[-1]
    assert veredito.posicoes_faltantes == [f"{audiencia.value}:{formato.value}"]


def test_celula_fora_do_pedido_reprova_a_matriz():
    pedido = UMA
    fora = MATRIZ[1]
    recebidas = _historicos([*pedido, fora])

    veredito = avaliar_matriz(recebidas, _ancoras(), posicoes=pedido)

    assert veredito.estado is EstadoAvaliacaoTransversal.REVISAO_HUMANA
    assert veredito.posicoes_inesperadas == [f"{fora[0].value}:{fora[1].value}"]


def test_sem_pedido_o_avaliador_continua_exigindo_as_nove():
    veredito = avaliar_matriz(_historicos(CINCO), _ancoras())

    assert veredito.estado is EstadoAvaliacaoTransversal.REVISAO_HUMANA
    assert veredito.total_esperado == 9
    assert len(veredito.posicoes_faltantes) == 4


# ---------------------------------------------------------------------------
# A geração
# ---------------------------------------------------------------------------


@pytest.fixture
def ciclo_rapido(monkeypatch):
    """`gerar_celula` e `avaliar` sem LLM. Devolve a lista de posições geradas, com a rodada."""
    geradas: list[tuple[Audiencia, Formato, int]] = []
    trava = threading.Lock()

    def gerar(ata, ancoras, audiencia, formato, provedor, rodada=0, correcoes=None, orientacoes_transversais=None, duracao=None, rascunho=None):
        with trava:
            geradas.append((audiencia, formato, rodada))
        return Celula(
            audiencia=audiencia, formato=formato, conteudo=_conteudo(formato), rodada=rodada
        )

    def aprovar(conteudo, ancoras, audiencia, *, limiares=None, ao_etapa=None):
        return Laudo(
            audiencia=audiencia, formato=conteudo.formato, medidas=[], destino=Destino.APROVADO
        )

    monkeypatch.setattr("suno.gerador.ciclo.gerar_celula", gerar)
    monkeypatch.setattr("suno.gerador.ciclo.avaliar", aprovar)
    return geradas


@pytest.mark.parametrize("posicoes", [UMA, CINCO, MATRIZ], ids=["1", "5", "9"])
def test_so_as_posicoes_pedidas_sao_geradas_e_na_ordem_da_matriz(ciclo_rapido, posicoes):
    historicos = gerar_matriz_do_dossie(_dossie(), ProvedorFalso(), posicoes=posicoes)

    assert [(h.audiencia, h.formato) for h in historicos] == list(posicoes)
    assert sorted((a, f) for a, f, _ in ciclo_rapido) == sorted(posicoes)


def test_posicoes_em_desordem_saem_na_ordem_da_matriz(ciclo_rapido):
    desordenadas = (MATRIZ[8], MATRIZ[0], MATRIZ[4])

    historicos = gerar_matriz_do_dossie(_dossie(), ProvedorFalso(), posicoes=desordenadas)

    assert [(h.audiencia, h.formato) for h in historicos] == [MATRIZ[0], MATRIZ[4], MATRIZ[8]]


def test_sem_posicoes_a_geracao_continua_sendo_as_nove(ciclo_rapido):
    historicos = gerar_matriz_do_dossie(_dossie(), ProvedorFalso())

    assert [(h.audiencia, h.formato) for h in historicos] == list(MATRIZ)


def test_o_andamento_avisa_gerando_e_depois_aprovada(ciclo_rapido):
    avisos: list[tuple[Audiencia, Formato, EtapaDaCelula, int]] = []
    trava = threading.Lock()

    def ao_andar(audiencia, formato, etapa, rodada):
        with trava:
            avisos.append((audiencia, formato, etapa, rodada))

    gerar_matriz_do_dossie(_dossie(), ProvedorFalso(), posicoes=CINCO, ao_andar=ao_andar)

    for audiencia, formato in CINCO:
        etapas = [e for a, f, e, _ in avisos if (a, f) == (audiencia, formato)]
        assert etapas == [EtapaDaCelula.GERANDO, EtapaDaCelula.APROVADA]


def test_a_rodada_de_correcao_aparece_como_corrigindo(monkeypatch):
    posicao = MATRIZ[0]

    def gerar(ata, ancoras, audiencia, formato, provedor, rodada=0, correcoes=None, orientacoes_transversais=None, duracao=None, rascunho=None):
        return Celula(
            audiencia=audiencia, formato=formato, conteudo=_conteudo(formato), rodada=rodada
        )

    def avaliar_na_segunda(conteudo, ancoras, audiencia, *, limiares=None, ao_etapa=None):
        primeira = not chamadas_do_avaliador
        chamadas_do_avaliador.append(1)
        if primeira:
            return Laudo(
                audiencia=audiencia,
                formato=conteudo.formato,
                medidas=[],
                destino=Destino.REPROVADO_CORRIGIVEL,
                motivos=[MotivoReprovacao.FLESCH_BR],
            )
        return Laudo(
            audiencia=audiencia, formato=conteudo.formato, medidas=[], destino=Destino.APROVADO
        )

    chamadas_do_avaliador: list[int] = []
    monkeypatch.setattr("suno.gerador.ciclo.gerar_celula", gerar)
    monkeypatch.setattr("suno.gerador.ciclo.avaliar", avaliar_na_segunda)
    avisos: list[tuple[EtapaDaCelula, int]] = []

    gerar_matriz_do_dossie(
        _dossie(),
        ProvedorFalso(),
        posicoes=(posicao,),
        ao_andar=lambda a, f, etapa, rodada: avisos.append((etapa, rodada)),
    )

    assert avisos == [
        (EtapaDaCelula.GERANDO, 0),
        (EtapaDaCelula.CORRIGINDO, 1),
        (EtapaDaCelula.APROVADA, 1),
    ]


def test_callback_que_levanta_nao_derruba_o_ciclo(ciclo_rapido):
    def estragado(audiencia, formato, etapa, rodada):
        raise RuntimeError("a tela caiu")

    historicos = gerar_matriz_do_dossie(
        _dossie(), ProvedorFalso(), posicoes=UMA, ao_andar=estragado
    )

    assert historicos[0].destino_final is Destino.APROVADO


def test_avaliar_avisa_a_camada_deterministica_ao_comecar() -> None:
    from suno.avaliador import avaliar
    from suno.dominio import Conteudo

    camadas: list[str] = []
    avaliar(
        Conteudo(formato=Formato.TEXTO_ANALITICO, texto="Texto curto."),
        [],
        Audiencia.INICIANTE,
        ao_etapa=camadas.append,
    )

    assert camadas == ["deterministica"]
