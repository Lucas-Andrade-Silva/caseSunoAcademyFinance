"""O pedido (quais Células da Matriz foram pedidas) e o andamento de uma geração em segundo plano.

Execução antiga não tem ``pedido``: significa as nove, e continua carregando.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from suno.dominio import (
    MATRIZ,
    Andamento,
    AndamentoDaCelula,
    Audiencia,
    EstadoDoAndamento,
    EtapaDaCelula,
    Execucao,
    FaseDaExecucao,
    Formato,
    PosicaoDaMatriz,
)
from tests.construtores_de_execucao import execucao_de_teste


def _posicao(audiencia: Audiencia, formato: Formato) -> PosicaoDaMatriz:
    return PosicaoDaMatriz(audiencia=audiencia, formato=formato)


def test_sem_pedido_a_execucao_vale_as_nove_posicoes():
    execucao = execucao_de_teste()
    assert execucao.pedido == []
    assert execucao.posicoes_pedidas() == MATRIZ


def test_o_pedido_sai_na_ordem_da_matriz_qualquer_que_seja_a_de_entrada():
    execucao = execucao_de_teste()
    desordenado = [
        _posicao(Audiencia.AVANCADO, Formato.ROTEIRO),
        _posicao(Audiencia.INICIANTE, Formato.CARROSSEL),
    ]
    com_pedido = Execucao.model_validate(
        {**execucao.model_dump(mode="json"), "pedido": [p.model_dump(mode="json") for p in desordenado]}
    )
    assert com_pedido.posicoes_pedidas() == (
        (Audiencia.INICIANTE, Formato.CARROSSEL),
        (Audiencia.AVANCADO, Formato.ROTEIRO),
    )


def test_posicao_repetida_no_pedido_e_recusada():
    execucao = execucao_de_teste()
    repetido = [
        {"audiencia": "iniciante", "formato": "carrossel"},
        {"audiencia": "iniciante", "formato": "carrossel"},
    ]
    with pytest.raises(ValidationError):
        Execucao.model_validate({**execucao.model_dump(mode="json"), "pedido": repetido})


def test_execucao_gravada_antes_do_pedido_continua_carregando():
    bruto = json.loads(execucao_de_teste().model_dump_json())
    bruto.pop("pedido")
    antiga = Execucao.model_validate(bruto)
    assert antiga.posicoes_pedidas() == MATRIZ


def test_a_posicao_vira_tupla():
    assert _posicao(Audiencia.INTERMEDIARIO, Formato.TEXTO_ANALITICO).como_tupla() == (
        Audiencia.INTERMEDIARIO,
        Formato.TEXTO_ANALITICO,
    )


def test_o_andamento_faz_ida_e_volta_em_json():
    agora = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    andamento = Andamento(
        identificador="saida-1",
        nome="Minha Saída",
        ata="copom-280-2026-08-05",
        provedor="falso",
        estado=EstadoDoAndamento.GERANDO,
        fase=FaseDaExecucao.GERANDO_CELULAS,
        celulas=[
            AndamentoDaCelula(
                audiencia=Audiencia.INICIANTE,
                formato=Formato.CARROSSEL,
                etapa=EtapaDaCelula.CORRIGINDO,
                rodada=1,
            )
        ],
        criado_em=agora,
        atualizado_em=agora,
    )
    de_volta = Andamento.model_validate_json(andamento.model_dump_json())
    assert de_volta == andamento
    assert de_volta.celulas[0].etapa is EtapaDaCelula.CORRIGINDO
    assert de_volta.erro is None
    assert de_volta.concluido_em is None


def test_a_celula_do_andamento_comeca_aguardando_na_rodada_zero():
    celula = AndamentoDaCelula(audiencia=Audiencia.AVANCADO, formato=Formato.ROTEIRO)
    assert celula.etapa is EtapaDaCelula.AGUARDANDO
    assert celula.rodada == 0
