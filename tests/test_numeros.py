"""O extrator de números: cada caso que a Ata do Copom exige, e a fronteira do que ele
não cobre de propósito (ADR 0011)."""

from __future__ import annotations

from datetime import date

import pytest

from suno.dominio import Unidade
from suno.ingestao.numeros import extrair_numeros

ANO_DA_ATA = 2026


def _unico(texto: str):
    achados = extrair_numeros(texto, ano_padrao=ANO_DA_ATA)
    assert len(achados) == 1, f"esperava um número em {texto!r}, achei {achados}"
    return achados[0]


# -- Percentuais ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "literal", "valor"),
    [
        ("14,00% a.a.", "14,00", 14.0),
        ("15,00% ao ano", "15,00", 15.0),
        ("a Selic foi mantida em 15% a.a. pelo Comitê", "15", 15.0),
    ],
)
def test_percentual_ao_ano(texto: str, literal: str, valor: float) -> None:
    achado = _unico(texto)
    assert (achado.literal, achado.valor, achado.unidade) == (
        literal,
        valor,
        Unidade.PERCENTUAL_AO_ANO,
    )


@pytest.mark.parametrize("texto", ["0,50 p.p.", "0,5 ponto percentual", "meio ponto percentual"])
def test_ponto_percentual_em_todas_as_grafias(texto: str) -> None:
    achado = _unico(texto)
    assert achado.valor == 0.5
    assert achado.unidade is Unidade.PONTO_PERCENTUAL


@pytest.mark.parametrize("texto", ["50 pontos-base", "50 pontos base", "50 pb", "50 bps"])
def test_pontos_base_em_todas_as_grafias(texto: str) -> None:
    achado = _unico(texto)
    assert achado.valor == 50.0
    assert achado.unidade is Unidade.PONTOS_BASE


def test_percentual_simples() -> None:
    achado = _unico("a projeção é de 5,1% no cenário de referência")
    assert (achado.literal, achado.valor, achado.unidade) == ("5,1", 5.1, Unidade.PERCENTUAL)


def test_percentual_por_extenso() -> None:
    achado = _unico("o juro chegou a quinze por cento")
    assert (achado.literal, achado.valor, achado.unidade) == ("quinze", 15.0, Unidade.PERCENTUAL)


def test_unidades_de_percentual_nao_se_confundem() -> None:
    achados = extrair_numeros("subiu 0,5 p.p., de 50 pb, para 15% a.a., com 5,1% no ano")
    assert [a.unidade for a in achados] == [
        Unidade.PONTO_PERCENTUAL,
        Unidade.PONTOS_BASE,
        Unidade.PERCENTUAL_AO_ANO,
        Unidade.PERCENTUAL,
    ]


# -- Qualificador --------------------------------------------------------------


@pytest.mark.parametrize("texto", ["CDI+2%", "CDI + 2%"])
def test_qualificador_de_prefixo(texto: str) -> None:
    achado = _unico(texto)
    assert (achado.valor, achado.unidade, achado.qualificador) == (2.0, Unidade.PERCENTUAL, "CDI+")


def test_qualificador_de_sufixo() -> None:
    achado = _unico("110% do CDI")
    assert (achado.valor, achado.unidade, achado.qualificador) == (
        110.0,
        Unidade.PERCENTUAL,
        "do CDI",
    )


def test_numero_qualificado_nunca_se_confunde_com_o_nu() -> None:
    qualificados = extrair_numeros("CDI+2% e 110% do CDI")
    nus = extrair_numeros("2% e 110%")
    assert [a.qualificador for a in qualificados] == ["CDI+", "do CDI"]
    assert [a.qualificador for a in nus] == [None, None]
    assert qualificados[0].qualificador != qualificados[1].qualificador


# -- Reais ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "valor"),
    [("R$ 1.234,56", 1234.56), ("R$ 2,5 bilhões", 2.5e9), ("R$ 300 milhões", 3e8)],
)
def test_reais_com_ponto_de_milhar_e_escala(texto: str, valor: float) -> None:
    achado = _unico(texto)
    assert achado.valor == valor
    assert achado.unidade is Unidade.REAIS


def test_escala_sem_moeda_sai_como_numero() -> None:
    """Fronteira documentada: sem ``R$`` e sem ``reais``, a escala não vira dinheiro."""
    achado = _unico("300 milhões de pessoas")
    assert (achado.valor, achado.unidade) == (3e8, Unidade.NUMERO)


# -- Votos ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "literal", "placar"),
    [
        ("7 a 0", "7 a 0", (7.0, 0.0)),
        ("7 votos a 0", "7 votos a 0", (7.0, 0.0)),
        ("por 7 votos a 2", "7 votos a 2", (7.0, 2.0)),
    ],
)
def test_placar_de_votacao(texto: str, literal: str, placar: tuple[float, float]) -> None:
    achado = _unico(texto)
    assert (achado.literal, achado.unidade, achado.placar) == (literal, Unidade.VOTOS, placar)
    assert achado.valor == placar[0]


# -- Datas ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "quando"),
    [
        ("4 e 5 de agosto de 2026", date(2026, 8, 5)),
        ("17 de setembro de 2026", date(2026, 9, 17)),
        ("28 de janeiro", date(2026, 1, 28)),
    ],
)
def test_data_em_portugues(texto: str, quando: date) -> None:
    achado = _unico(texto)
    assert achado.unidade is Unidade.DATA
    assert achado.data_iso == quando
    assert achado.literal == texto


def test_ano_solto_nao_vira_data_completa() -> None:
    achados = extrair_numeros("as projeções para 2026 e 2027", ano_padrao=ANO_DA_ATA)
    assert [(a.valor, a.ano, a.data_iso, a.unidade) for a in achados] == [
        (2026.0, 2026, None, Unidade.DATA),
        (2027.0, 2027, None, Unidade.DATA),
    ]


def test_data_nao_depende_do_relogio_quando_ha_ano_padrao() -> None:
    assert _unico("28 de janeiro").data_iso == date(ANO_DA_ATA, 1, 28)
    achado = extrair_numeros("28 de janeiro", ano_padrao=2030)[0]
    assert achado.data_iso == date(2030, 1, 28)


# -- Ordinal -------------------------------------------------------------------


@pytest.mark.parametrize("texto", ["280ª Reunião", "280ª"])
def test_ordinal_feminino_da_reuniao(texto: str) -> None:
    achado = _unico(texto)
    assert (achado.literal, achado.valor, achado.unidade) == ("280", 280.0, Unidade.NUMERO)


# -- A fronteira ---------------------------------------------------------------


@pytest.mark.parametrize(
    "texto",
    [
        "três Formatos",
        "nove Células",
        "duas rodadas",
        "o Comitê tem sete membros e meia dúzia de assessores",
    ],
)
def test_extenso_sem_unidade_nao_vira_numero(texto: str) -> None:
    assert extrair_numeros(texto) == []


@pytest.mark.parametrize(
    "texto",
    ["a inflação ficou acima do projetado", "o dobro do trimestre anterior", "menos que o esperado"],
)
def test_numero_relativo_nao_entra(texto: str) -> None:
    assert extrair_numeros(texto) == []


def test_decimal_solto_e_ordinal_masculino_ficam_de_fora() -> None:
    assert extrair_numeros("IPCA 5,1 3,8 3,2 no 8º andar") == []


def test_texto_vazio() -> None:
    assert extrair_numeros("") == []


# -- Posição e trecho ----------------------------------------------------------


def test_posicao_delimita_o_literal_no_texto() -> None:
    texto = "Em 4 e 5 de agosto de 2026 o Copom levou a Selic a 14,00% a.a., por 7 votos a 0."
    achados = extrair_numeros(texto, ano_padrao=ANO_DA_ATA)
    assert achados
    for achado in achados:
        assert texto[achado.inicio : achado.fim] == achado.literal


def test_trecho_e_a_frase_de_onde_o_numero_veio() -> None:
    texto = (
        "O Comitê analisou o cenário. O Copom decidiu reduzir a taxa para 14,00% a.a.\n"
        "Sem prejuízo, a decisão foi unânime."
    )
    achado = _unico(texto)
    assert achado.trecho == "O Copom decidiu reduzir a taxa para 14,00% a.a."


# -- A Ata de verdade ----------------------------------------------------------


def test_ata_do_copom_280(texto_ata: str) -> None:
    achados = extrair_numeros(texto_ata, ano_padrao=ANO_DA_ATA)

    frase_da_decisao = "O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a."
    selic = [
        a for a in achados if a.unidade is Unidade.PERCENTUAL_AO_ANO and a.valor == 14.0
    ]
    assert len(selic) == 1
    assert selic[0].literal == "14,00"
    assert frase_da_decisao in selic[0].trecho

    datas = [a for a in achados if a.literal == "4 e 5 de agosto de 2026"]
    assert datas and all(a.data_iso == date(2026, 8, 5) for a in datas)

    projecoes = {a.valor for a in achados if a.unidade is Unidade.PERCENTUAL}
    assert {5.1, 3.8, 3.2} <= projecoes

    assert all(texto_ata[a.inicio : a.fim] == a.literal for a in achados)


# -- Regressões do revisor de erros (2026-09-19) --------------------------------


@pytest.mark.parametrize(
    ("texto", "literal", "unidade"),
    [
        ("O Copom cortou 999pb.", "999", Unidade.PONTOS_BASE),
        ("elevou 42pp.", "42", Unidade.PONTO_PERCENTUAL),
        ("caiu 50bps.", "50", Unidade.PONTOS_BASE),
        ("subiu 0,25pp.", "0,25", Unidade.PONTO_PERCENTUAL),
    ],
)
def test_pp_pb_bps_colados_ao_numero_sem_espaco(texto: str, literal: str, unidade: Unidade) -> None:
    """Entre um dígito e uma letra não há `\\b`: o limite à esquerda destas abreviações não
    podia exigir um, senão `999pb` nunca casava (achado Crítico)."""
    achado = _unico(texto)
    assert achado.literal == literal
    assert achado.unidade is unidade


def test_intervalo_com_unidade_nao_vira_placar_de_votacao() -> None:
    """`N a M` só é VOTOS quando nada (ou pontuação) segue; um intervalo de verdade tem
    unidade depois, e a unidade certa fica com o número (achado Crítico)."""
    achados = extrair_numeros("O horizonte relevante é de 2 a 3 anos.", ano_padrao=ANO_DA_ATA)
    assert not any(a.unidade is Unidade.VOTOS for a in achados)

    achado = _unico("alta de 3 a 4 pontos percentuais")
    assert achado.unidade is Unidade.PONTO_PERCENTUAL
    assert achado.valor == 4.0

    # O placar de verdade — nada suspeito depois — continua votos.
    achado = _unico("Votaram 7 a 0 pela decisão.")
    assert achado.unidade is Unidade.VOTOS


@pytest.mark.parametrize(
    "texto",
    ["o CDI+2% ao ano", "O papel rende CDI+2% ao ano.", "O título paga CDI + 2% ao ano."],
)
def test_qualificador_cdi_nao_se_perde_para_a_regra_de_a_a(texto: str) -> None:
    """A regra de `% a.a.` rodava antes da de `CDI+` e consumia o `%` primeiro, apagando o
    qualificador (achado Crítico: `CDI+2%` virava `2%` nu, que casaria com qualquer Âncora
    de 2% a.a.)."""
    achado = _unico(texto)
    assert achado.qualificador == "CDI+"
    assert achado.unidade is Unidade.PERCENTUAL


@pytest.mark.parametrize(
    ("texto", "valor", "literal"),
    [
        ("O Copom elevou a taxa em +0,25 p.p.", 0.25, "+0,25"),
        ("O Copom reduziu a taxa em -0,25 p.p.", -0.25, "-0,25"),
        ("A taxa subiu 0,25 p.p.", 0.25, "0,25"),
    ],
)
def test_sinal_de_ponto_percentual_distingue_alta_de_reducao(
    texto: str, valor: float, literal: str
) -> None:
    """Sem capturar o sinal, `+0,25 p.p.` e `-0,25 p.p.` comparavam iguais — uma Célula que
    troca "elevou" por "reduziu" passava pela Aderência do mesmo jeito (achado Importante)."""
    achado = _unico(texto)
    assert achado.valor == valor
    assert achado.literal == literal
