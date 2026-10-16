"""`executar` com um subconjunto da Matriz, ponta a ponta, com o LLM falso da demo.

A Ata do repositório tem respostas prontas para as nove posições: sete aprovam na rodada 0,
`iniciante × texto analítico` aprova depois de uma correção e `intermediário × roteiro` é a que
cai na fila humana. Escolher posições dá cenários diferentes sem escrever resposta nova.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from suno.dominio import (
    MATRIZ,
    Audiencia,
    Destino,
    EstadoAvaliacaoTransversal,
    EtapaDaCelula,
    FaseDaExecucao,
    FilaHumana,
    Formato,
)
from suno.gerador.execucao import carregar_execucao, executar

CARROSSEL_INICIANTE = (Audiencia.INICIANTE, Formato.CARROSSEL)
ROTEIRO_INICIANTE = (Audiencia.INICIANTE, Formato.ROTEIRO)
ROTEIRO_INTERMEDIARIO = (Audiencia.INTERMEDIARIO, Formato.ROTEIRO)
TEXTO_INICIANTE = (Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)


def test_uma_celula_so_nao_roda_a_conferencia_da_matriz(caminho_ata: Path, tmp_path: Path):
    execucao = executar(caminho_ata, "falso", tmp_path, pedido=[CARROSSEL_INICIANTE])

    assert [(h.audiencia, h.formato) for h in execucao.celulas] == [CARROSSEL_INICIANTE]
    assert execucao.posicoes_pedidas() == (CARROSSEL_INICIANTE,)
    assert execucao.avaliacao_transversal is None
    assert execucao.pendencias == []
    assert execucao.celulas[0].destino_final is Destino.APROVADO


def test_duas_celulas_aprovadas_passam_pela_conferencia_da_matriz(caminho_ata: Path, tmp_path: Path):
    execucao = executar(
        caminho_ata, "falso", tmp_path, pedido=[CARROSSEL_INICIANTE, ROTEIRO_INICIANTE]
    )

    assert len(execucao.celulas) == 2
    assert execucao.avaliacao_transversal is not None
    assert execucao.avaliacao_transversal.total_esperado == 2
    assert execucao.avaliacao_transversal.estado is EstadoAvaliacaoTransversal.APROVADA
    assert execucao.pendencias == []


def test_a_celula_teimosa_continua_indo_para_a_fila_humana(caminho_ata: Path, tmp_path: Path):
    execucao = executar(
        caminho_ata, "falso", tmp_path, pedido=[CARROSSEL_INICIANTE, ROTEIRO_INTERMEDIARIO]
    )

    h4 = [p for p in execucao.pendencias if p.fila is FilaHumana.H4_REVISAO]
    assert [(p.audiencia, p.formato) for p in h4] == [ROTEIRO_INTERMEDIARIO]
    assert execucao.avaliacao_transversal.estado is EstadoAvaliacaoTransversal.REVISAO_HUMANA


def test_a_correcao_da_rodada_um_acontece_na_posicao_pedida(caminho_ata: Path, tmp_path: Path):
    execucao = executar(caminho_ata, "falso", tmp_path, pedido=[TEXTO_INICIANTE])

    historico = execucao.celulas[0]
    assert len(historico.tentativas) == 2
    assert historico.destino_final is Destino.APROVADO


def test_sem_pedido_grava_as_nove_no_pedido(caminho_ata: Path, tmp_path: Path):
    execucao = executar(caminho_ata, "falso", tmp_path)

    assert [p.como_tupla() for p in execucao.pedido] == list(MATRIZ)
    assert len(execucao.celulas) == 9


def test_o_pedido_e_o_nome_vao_para_o_disco(caminho_ata: Path, tmp_path: Path):
    executar(
        caminho_ata,
        "falso",
        tmp_path,
        pedido=[ROTEIRO_INICIANTE, CARROSSEL_INICIANTE],
        nome="Revisão da semana",
        identificador="saida-parcial",
    )

    lida = carregar_execucao("saida-parcial", tmp_path)
    assert lida.nome == "Revisão da semana"
    assert lida.posicoes_pedidas() == (CARROSSEL_INICIANTE, ROTEIRO_INICIANTE)


def test_as_fases_avisam_na_ordem(caminho_ata: Path, tmp_path: Path):
    fases: list[FaseDaExecucao] = []

    executar(
        caminho_ata,
        "falso",
        tmp_path,
        pedido=[CARROSSEL_INICIANTE, ROTEIRO_INICIANTE],
        ao_mudar_fase=fases.append,
    )

    assert fases == [
        FaseDaExecucao.EXTRAINDO_ANCORAS,
        FaseDaExecucao.GERANDO_CELULAS,
        FaseDaExecucao.AVALIANDO_MATRIZ,
        FaseDaExecucao.GRAVANDO,
    ]


def test_com_uma_celula_a_fase_de_avaliar_a_matriz_nao_aparece(caminho_ata: Path, tmp_path: Path):
    fases: list[FaseDaExecucao] = []

    executar(
        caminho_ata, "falso", tmp_path, pedido=[CARROSSEL_INICIANTE], ao_mudar_fase=fases.append
    )

    assert FaseDaExecucao.AVALIANDO_MATRIZ not in fases


def test_o_andamento_so_avisa_das_celulas_pedidas(caminho_ata: Path, tmp_path: Path):
    avisos: list[tuple[Audiencia, Formato, EtapaDaCelula, int]] = []

    executar(
        caminho_ata,
        "falso",
        tmp_path,
        pedido=[CARROSSEL_INICIANTE, ROTEIRO_INICIANTE],
        ao_andar=lambda a, f, e, r: avisos.append((a, f, e, r)),
    )

    assert {(a, f) for a, f, _, _ in avisos} == {CARROSSEL_INICIANTE, ROTEIRO_INICIANTE}
    assert {e for _, _, e, _ in avisos} == {
        EtapaDaCelula.GERANDO,
        EtapaDaCelula.AVALIANDO_DETERMINISTICA,
        EtapaDaCelula.APROVADA,
    }


@pytest.mark.parametrize("pedido", [[], [CARROSSEL_INICIANTE, CARROSSEL_INICIANTE]])
def test_pedido_vazio_ou_repetido_e_recusado_antes_de_gastar_chamada(
    caminho_ata: Path, tmp_path: Path, pedido
):
    with pytest.raises(ValueError):
        executar(caminho_ata, "falso", tmp_path, pedido=pedido)
