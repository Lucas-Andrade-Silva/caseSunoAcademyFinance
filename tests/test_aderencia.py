"""A Aderência: número da Célula conferido contra as Âncoras por igualdade exata de valor
e unidade (ADR 0011). Sem LLM, sem rede."""

from __future__ import annotations

from datetime import date

import pytest

from suno.avaliador.aderencia import medir_aderencia
from suno.dominio import AncoraNumerica, AncoraTextual, ChaveAncora, Unidade

SELIC = AncoraNumerica(
    chave=ChaveAncora.SELIC_DECIDIDA,
    rotulo="Selic decidida",
    valor_literal="14,00",
    valor=14.0,
    unidade=Unidade.PERCENTUAL_AO_ANO,
    trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
)
VARIACAO = AncoraNumerica(
    chave=ChaveAncora.VARIACAO_PB,
    rotulo="Variação da Selic",
    valor_literal="50",
    valor=50.0,
    unidade=Unidade.PONTOS_BASE,
    trecho="redução de 50 pontos-base",
)
PLACAR = AncoraNumerica(
    chave=ChaveAncora.PLACAR_VOTACAO,
    rotulo="Placar da votação",
    valor_literal="7 a 0",
    valor=None,
    unidade=Unidade.VOTOS,
    trecho="Votaram por essa decisão sete membros.",
)
REUNIAO = AncoraNumerica(
    chave=ChaveAncora.DATA_REUNIAO,
    rotulo="Data da reunião",
    valor_literal="4 e 5 de agosto de 2026",
    valor=None,
    unidade=Unidade.DATA,
    trecho="Data: 4 e 5 de agosto de 2026",
    data_iso=date(2026, 8, 5),
)
PROXIMA = AncoraNumerica(
    chave=ChaveAncora.DATA_PROXIMA_REUNIAO,
    rotulo="Próxima reunião",
    valor_literal="16 e 17 de setembro de 2026",
    valor=None,
    unidade=Unidade.DATA,
    trecho="A próxima reunião será em 16 e 17 de setembro de 2026",
    data_iso=date(2026, 9, 17),
)
IPCA = AncoraNumerica(
    chave=ChaveAncora.IPCA_PROJECAO_ANO_CORRENTE,
    rotulo="IPCA projetado para 2026",
    valor_literal="5,1",
    valor=5.1,
    unidade=Unidade.PERCENTUAL,
    trecho="as projeções são, respectivamente, 5,1%, 3,8%, e 3,2%.",
)

ANCORAS = [SELIC, VARIACAO, PLACAR, REUNIAO, PROXIMA, IPCA]


# -- O caso que aprova e o caso que reprova ------------------------------------


def test_celula_que_so_cita_ancoras_tem_proporcao_um() -> None:
    texto = (
        "Em 4 e 5 de agosto de 2026 o Copom levou a Selic a 14,00% a.a., "
        "uma redução de 50 pb decidida por 7 votos a 0. O IPCA projetado é de 5,1%."
    )
    medida = medir_aderencia(texto, ANCORAS)
    assert medida.proporcao == 1.0
    assert medida.numeros_fora_das_ancoras == []
    assert medida.ancoras_citadas == [
        ChaveAncora.DATA_REUNIAO,
        ChaveAncora.SELIC_DECIDIDA,
        ChaveAncora.VARIACAO_PB,
        ChaveAncora.PLACAR_VOTACAO,
        ChaveAncora.IPCA_PROJECAO_ANO_CORRENTE,
    ]


def test_numero_fora_das_ancoras_derruba_a_proporcao() -> None:
    """O caso do ADR 0011: número que a Célula inventou não está na tabela de Âncoras."""
    medida = medir_aderencia("A Selic foi a 14,00% a.a., o maior nível em 13,75% a.a.", ANCORAS)
    assert medida.numeros_fora_das_ancoras == ["13,75"]
    assert medida.numeros_conferidos == ["14,00"]
    assert medida.proporcao == 0.5


def test_sem_numero_a_proporcao_e_nula_e_nunca_zero() -> None:
    medida = medir_aderencia("O Copom manteve o tom cauteloso e seguiu atento ao cenário.", ANCORAS)
    assert medida.proporcao is None
    assert medida.numeros_conferidos == []
    assert medida.numeros_fora_das_ancoras == []


# -- Tolerância só de representação --------------------------------------------


@pytest.mark.parametrize("escrita", ["14% a.a.", "14,0% a.a.", "14,00% a.a.", "14,00% ao ano"])
def test_mesma_taxa_escrita_de_jeitos_diferentes_confere(escrita: str) -> None:
    medida = medir_aderencia(f"A taxa ficou em {escrita}.", [SELIC])
    assert medida.proporcao == 1.0


def test_meio_ponto_percentual_confere_com_zero_virgula_cinquenta() -> None:
    ancora = AncoraNumerica(
        chave="variacao_pp",
        rotulo="Variação em p.p.",
        valor_literal="0,50",
        valor=0.5,
        unidade=Unidade.PONTO_PERCENTUAL,
        trecho="corte de 0,50 p.p.",
    )
    assert medir_aderencia("um corte de 0,5 p.p.", [ancora]).proporcao == 1.0
    assert medir_aderencia("um corte de meio ponto percentual", [ancora]).proporcao == 1.0


@pytest.mark.parametrize("texto", ["a variação foi de 50%", "a variação foi de 50 p.p."])
def test_unidade_diferente_nunca_confere(texto: str) -> None:
    """``p.p.`` ≠ ``%`` ≠ ``pb``: a Âncora de 50 pb não cobre nenhum dos dois."""
    medida = medir_aderencia(texto, [VARIACAO])
    assert medida.proporcao == 0.0
    assert medida.ancoras_citadas == []


def test_qualificador_precisa_bater() -> None:
    ancora = AncoraNumerica(
        chave="premio",
        rotulo="Prêmio sobre o CDI",
        valor_literal="2",
        valor=2.0,
        unidade=Unidade.PERCENTUAL,
        trecho="o papel paga 2% de prêmio",
    )
    assert medir_aderencia("o papel paga 2%", [ancora]).proporcao == 1.0
    assert medir_aderencia("o papel paga CDI+2%", [ancora]).proporcao == 0.0
    assert medir_aderencia("o papel paga 110% do CDI", [ancora]).proporcao == 0.0


def test_ancora_com_qualificador_confere_e_so_com_o_mesmo() -> None:
    ancora = AncoraNumerica(
        chave="premio",
        rotulo="Prêmio sobre o CDI",
        valor_literal="2",
        valor=2.0,
        unidade=Unidade.PERCENTUAL,
        trecho="o papel paga CDI+2%",
        qualificador="CDI+",
    )
    assert ancora.citacao() == "CDI+2%"
    assert medir_aderencia("o papel paga CDI+2%", [ancora]).proporcao == 1.0
    assert medir_aderencia("o papel paga 2%", [ancora]).proporcao == 0.0


def test_ancora_com_qualificador_de_sufixo_confere() -> None:
    ancora = AncoraNumerica(
        chave="premio",
        rotulo="Percentual do CDI",
        valor_literal="110",
        valor=110.0,
        unidade=Unidade.PERCENTUAL,
        trecho="o papel paga 110% do CDI",
        qualificador="do CDI",
    )
    assert ancora.citacao() == "110% do CDI"
    assert medir_aderencia("o papel paga 110% do CDI", [ancora]).proporcao == 1.0
    assert medir_aderencia("o papel paga 110%", [ancora]).proporcao == 0.0
    assert medir_aderencia("o papel paga CDI+110%", [ancora]).proporcao == 0.0


# -- Datas e votos -------------------------------------------------------------


@pytest.mark.parametrize(
    "escrita",
    ["4 e 5 de agosto de 2026", "5 de agosto de 2026", "em 2026"],
)
def test_data_confere_por_data_iso_por_mes_e_ano_ou_por_ano_solto(escrita: str) -> None:
    medida = medir_aderencia(f"A reunião foi em {escrita}.", [REUNIAO])
    assert medida.proporcao == 1.0
    assert medida.ancoras_citadas == [ChaveAncora.DATA_REUNIAO]


def test_data_de_outro_mes_nao_confere_com_a_reuniao() -> None:
    medida = medir_aderencia("A reunião foi em 17 de setembro de 2026.", [REUNIAO])
    assert medida.proporcao == 0.0
    assert medida.numeros_fora_das_ancoras == ["17 de setembro de 2026"]


def test_data_sem_ano_no_texto_usa_o_ano_das_ancoras() -> None:
    proxima = AncoraNumerica(
        chave=ChaveAncora.DATA_PROXIMA_REUNIAO,
        rotulo="Próxima reunião",
        valor_literal="28 de janeiro de 2026",
        valor=None,
        unidade=Unidade.DATA,
        trecho="28 de janeiro de 2026",
        data_iso=date(2026, 1, 28),
    )
    assert medir_aderencia("a próxima é em 28 de janeiro", [REUNIAO, proxima]).proporcao == 1.0


@pytest.mark.parametrize("escrita", ["7 a 0", "7 votos a 0", "por 7 votos a 0"])
def test_placar_confere_em_qualquer_grafia(escrita: str) -> None:
    medida = medir_aderencia(f"A decisão saiu {escrita}.", [PLACAR])
    assert medida.proporcao == 1.0
    assert medida.ancoras_citadas == [ChaveAncora.PLACAR_VOTACAO]


def test_placar_diferente_reprova() -> None:
    assert medir_aderencia("A decisão saiu por 5 votos a 2.", [PLACAR]).proporcao == 0.0


# -- Âncoras textuais: informativas, nunca reprovam ----------------------------


def test_cobertura_textual_e_informativa_e_nao_entra_na_proporcao() -> None:
    afirmacao = AncoraTextual(
        identificador="decisao",
        afirmacao="O Copom decidiu reduzir a taxa básica de juros",
        trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
    )
    medida = medir_aderencia("O Copom decidiu reduzir a taxa básica de juros.", [SELIC, afirmacao])
    assert medida.cobertura_textual["decisao"] == 1.0
    assert medida.proporcao is None  # nenhum número no texto: Medida ausente, não zero

    magra = medir_aderencia("O Comitê seguiu atento.", [afirmacao])
    assert magra.cobertura_textual["decisao"] < 1.0
    assert magra.proporcao is None


def test_ancora_textual_nao_vira_numero_conferido() -> None:
    afirmacao = AncoraTextual(
        identificador="riscos",
        afirmacao="O balanço de riscos segue assimétrico para cima",
        trecho="Os riscos permanecem mais elevados que o usual, com assimetria altista.",
    )
    medida = medir_aderencia("A Selic ficou em 14,00% a.a.", [afirmacao])
    assert medida.proporcao == 0.0
    assert medida.numeros_fora_das_ancoras == ["14,00"]


def test_sem_ancora_nenhuma_todo_numero_fica_fora() -> None:
    medida = medir_aderencia("A Selic ficou em 14,00% a.a.", [])
    assert medida.proporcao == 0.0
    assert medida.cobertura_textual == {}


# -- O número fora das Âncoras, legível para a Correção ------------------------


def test_numero_fora_com_unidade_mostra_a_unidade() -> None:
    """A Correção precisa dizer "15%" e "0,75 p.p.", não "15" e "0,75"."""
    texto = "subiu 15%, ou 0,75 p.p., ou 75 pb, indo a 15,00% a.a., custando R$ 1.234,56"
    medida = medir_aderencia(texto, [])
    assert medida.numeros_fora_das_ancoras == ["15", "0,75", "75", "15,00", "1.234,56"]
    assert medida.numeros_fora_com_unidade == [
        "15%",
        "0,75 p.p.",
        "75 pb",
        "15,00% a.a.",
        "R$ 1.234,56",
    ]


def test_numero_fora_com_unidade_carrega_o_qualificador() -> None:
    medida = medir_aderencia("o papel paga CDI+2% e o outro paga 110% do CDI", [])
    assert medida.numeros_fora_das_ancoras == ["2", "110"]
    assert medida.numeros_fora_com_unidade == ["CDI+2%", "110% do CDI"]


def test_data_voto_e_numero_solto_ficam_so_com_o_literal() -> None:
    texto = "Na 280ª reunião, em 4 e 5 de agosto de 2026, a decisão saiu por 7 votos a 0."
    medida = medir_aderencia(texto, [])
    assert medida.numeros_fora_com_unidade == [
        "280",
        "4 e 5 de agosto de 2026",
        "7 votos a 0",
    ]
    assert medida.numeros_fora_com_unidade == medida.numeros_fora_das_ancoras


def test_as_duas_listas_de_fora_andam_juntas() -> None:
    """Mesma ordem e mesmo tamanho: o índice de uma vale na outra."""
    texto = "subiu 15% em 4 e 5 de agosto de 2026, com a Selic em 14,00% a.a."
    medida = medir_aderencia(texto, [SELIC])
    assert medida.numeros_conferidos == ["14,00"]
    assert len(medida.numeros_fora_com_unidade) == len(medida.numeros_fora_das_ancoras)
    assert medida.numeros_fora_das_ancoras == ["15", "4 e 5 de agosto de 2026"]
    assert medida.numeros_fora_com_unidade == ["15%", "4 e 5 de agosto de 2026"]
