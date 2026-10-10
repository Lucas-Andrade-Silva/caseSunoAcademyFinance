"""O nome da Saída e a decisão humana no domínio: valores padrão, validação e compatibilidade
com execucao.json gravado antes do front novo."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from suno.dominio import Audiencia, DecisaoHumana, Destino, EstadoDecisao, Execucao, Formato
from tests.construtores_de_execucao import IDENTIFICADOR, execucao_de_teste, historico_de_texto


def test_nome_vazio_vira_o_identificador() -> None:
    assert execucao_de_teste().nome == IDENTIFICADOR


def test_nome_dado_pelo_usuario_e_preservado() -> None:
    assert execucao_de_teste(nome="Copom 280 · pauta juros").nome == "Copom 280 · pauta juros"


def test_execucao_gravada_antes_do_front_novo_continua_carregando() -> None:
    dados = json.loads(execucao_de_teste().model_dump_json())
    del dados["nome"]
    del dados["decisoes"]

    reconstruida = Execucao.model_validate(dados)

    assert reconstruida.nome == IDENTIFICADOR
    assert reconstruida.decisoes == []


def test_decisao_reprovada_exige_motivo() -> None:
    with pytest.raises(ValidationError, match="motivo"):
        DecisaoHumana(
            audiencia=Audiencia.INICIANTE,
            formato=Formato.TEXTO_ANALITICO,
            estado=EstadoDecisao.REPROVADA,
            motivo="   ",
        )


def test_decisao_aprovada_nao_exige_motivo() -> None:
    decisao = DecisaoHumana(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.TEXTO_ANALITICO,
        estado=EstadoDecisao.APROVADA,
    )
    assert decisao.motivo is None
    assert decisao.revisor is None


def test_decisao_de_acha_a_decisao_da_posicao() -> None:
    execucao = execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO))
    decisao = DecisaoHumana(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.TEXTO_ANALITICO,
        estado=EstadoDecisao.APROVADA,
    )
    execucao.decisoes.append(decisao)

    assert execucao.decisao_de(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO) is decisao
    assert execucao.decisao_de(Audiencia.AVANCADO, Formato.TEXTO_ANALITICO) is None
