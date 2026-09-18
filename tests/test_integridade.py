"""A integridade da extração: sem as chaves essenciais, a Célula reprova por falha de
extração e vai direto à revisão humana (ADR 0013)."""

from __future__ import annotations

from datetime import date

from suno.avaliador.integridade import medir_integridade
from suno.dominio import (
    CHAVES_ESSENCIAIS,
    AncoraNumerica,
    AncoraTextual,
    ChaveAncora,
    Unidade,
)


def _selic(trecho: str = "O Copom decidiu reduzir a taxa para 14,00% a.a.") -> AncoraNumerica:
    return AncoraNumerica(
        chave=ChaveAncora.SELIC_DECIDIDA,
        rotulo="Selic decidida",
        valor_literal="14,00",
        valor=14.0,
        unidade=Unidade.PERCENTUAL_AO_ANO,
        trecho=trecho,
    )


def _reuniao() -> AncoraNumerica:
    return AncoraNumerica(
        chave=ChaveAncora.DATA_REUNIAO,
        rotulo="Data da reunião",
        valor_literal="4 e 5 de agosto de 2026",
        valor=None,
        unidade=Unidade.DATA,
        trecho="Data: 4 e 5 de agosto de 2026",
        data_iso=date(2026, 8, 5),
    )


def _placar() -> AncoraNumerica:
    return AncoraNumerica(
        chave=ChaveAncora.PLACAR_VOTACAO,
        rotulo="Placar da votação",
        valor_literal="7 a 0",
        valor=None,
        unidade=Unidade.VOTOS,
        trecho="A decisão foi tomada por 7 votos a 0.",
    )


def test_extracao_completa() -> None:
    medida = medir_integridade([_selic(), _reuniao(), _placar()])
    assert medida.completa
    assert medida.faltantes == []
    assert medida.ancoras_com_trecho_vazio == []


def test_chave_faltando_reprova_a_extracao() -> None:
    medida = medir_integridade([_selic(), _reuniao()])
    assert not medida.completa
    assert medida.faltantes == [ChaveAncora.PLACAR_VOTACAO]


def test_sequencia_vazia_e_incompleta_com_todas_as_chaves_faltando() -> None:
    medida = medir_integridade([])
    assert not medida.completa
    assert set(medida.faltantes) == set(CHAVES_ESSENCIAIS)
    assert len(medida.faltantes) == len(CHAVES_ESSENCIAIS)


def test_ordem_das_faltantes_e_estavel() -> None:
    """``faltantes`` entra no Laudo: comparar execuções exige ordem previsível."""
    primeira = medir_integridade([])
    segunda = medir_integridade([])
    assert primeira.faltantes == segunda.faltantes
    assert primeira.faltantes == [
        ChaveAncora.SELIC_DECIDIDA,
        ChaveAncora.PLACAR_VOTACAO,
        ChaveAncora.DATA_REUNIAO,
    ]


def test_ancora_textual_nao_cobre_chave_essencial() -> None:
    textual = AncoraTextual(
        identificador="decisao",
        afirmacao="O Copom decidiu reduzir a taxa básica de juros",
        trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
    )
    medida = medir_integridade([_selic(), _reuniao(), textual])
    assert not medida.completa
    assert medida.faltantes == [ChaveAncora.PLACAR_VOTACAO]


def test_chave_fora_do_enum_nao_conta_para_integridade() -> None:
    livre = AncoraNumerica(
        chave="cambio_de_referencia",
        rotulo="Câmbio de referência",
        valor_literal="5,10",
        valor=5.1,
        unidade=Unidade.REAIS,
        trecho="a taxa de câmbio parte de R$5,10/US$",
    )
    medida = medir_integridade([_selic(), _reuniao(), livre])
    assert medida.faltantes == [ChaveAncora.PLACAR_VOTACAO]


def test_trecho_vazio_e_sinal_de_extracao_degradada_mas_nao_reprova() -> None:
    medida = medir_integridade([_selic(trecho="   "), _reuniao(), _placar()])
    assert medida.completa
    assert medida.ancoras_com_trecho_vazio == [ChaveAncora.SELIC_DECIDIDA]
