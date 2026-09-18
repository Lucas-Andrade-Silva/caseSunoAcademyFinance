"""O Flesch-BR e as convenções de contagem do ADR 0002.

O texto de referência é deste teste, escrito aqui: a pesquisa cita o valor 34,4 mas não
preservou o texto que o produziu. As 45 palavras, 4 frases e 108 sílabas foram contadas
à mão, palavra a palavra, na lista ``CONTAGEM_A_MAO`` abaixo — que também é conferida
contra o separador de sílabas, para o teste falhar se as duas contas divergirem.

Roda offline, sem LLM e sem chave (ADR 0001).
"""

from __future__ import annotations

import pytest

from suno.avaliador.flesch_br import Contagens, contar, faixa_nilc, flesch_br
from suno.avaliador.silabas import contar_silabas

TEXTO_DE_REFERENCIA = (
    "O Copom decidiu reduzir a taxa básica de juros da economia brasileira. "
    "A decisão considerou a desaceleração da atividade e o comportamento das "
    "expectativas de inflação. O Comitê avaliou os riscos do cenário externo. "
    "O objetivo principal segue a convergência da inflação para a meta."
)

# Contagem à mão, palavra a palavra, na ordem do texto. 45 palavras, 108 sílabas.
CONTAGEM_A_MAO: tuple[tuple[str, int], ...] = (
    # 1ª frase — 12 palavras, 28 sílabas
    ("O", 1),
    ("Copom", 2),  # Co-pom
    ("decidiu", 3),  # de-ci-diu
    ("reduzir", 3),  # re-du-zir
    ("a", 1),
    ("taxa", 2),  # ta-xa
    ("básica", 3),  # bá-si-ca
    ("de", 1),
    ("juros", 2),  # ju-ros
    ("da", 1),
    ("economia", 5),  # e-co-no-mi-a
    ("brasileira", 4),  # bra-si-lei-ra
    # 2ª frase — 14 palavras, 38 sílabas
    ("A", 1),
    ("decisão", 3),  # de-ci-são
    ("considerou", 4),  # con-si-de-rou
    ("a", 1),
    ("desaceleração", 6),  # de-sa-ce-le-ra-ção
    ("da", 1),
    ("atividade", 5),  # a-ti-vi-da-de
    ("e", 1),
    ("o", 1),
    ("comportamento", 5),  # com-por-ta-men-to
    ("das", 1),
    ("expectativas", 5),  # ex-pec-ta-ti-vas
    ("de", 1),
    ("inflação", 3),  # in-fla-ção
    # 3ª frase — 8 palavras, 18 sílabas
    ("O", 1),
    ("Comitê", 3),  # Co-mi-tê
    ("avaliou", 4),  # a-va-li-ou
    ("os", 1),
    ("riscos", 2),  # ris-cos
    ("do", 1),
    ("cenário", 3),  # ce-ná-rio
    ("externo", 3),  # ex-ter-no
    # 4ª frase — 11 palavras, 24 sílabas
    ("O", 1),
    ("objetivo", 4),  # ob-je-ti-vo
    ("principal", 3),  # prin-ci-pal
    ("segue", 2),  # se-gue
    ("a", 1),
    ("convergência", 4),  # con-ver-gên-cia
    ("da", 1),
    ("inflação", 3),  # in-fla-ção
    ("para", 2),  # pa-ra
    ("a", 1),
    ("meta", 2),  # me-ta
)

TEXTO_FACIL = "O juro caiu. A bolsa subiu. O real ficou firme."


def _paragrafo_da_decisao(texto_ata: str) -> str:
    """O parágrafo 17 da Ata 280: a decisão de política monetária."""
    inicio = texto_ata.index("17. O Copom decidiu")
    fim = texto_ata.index("18. O cenário atual")
    return texto_ata[inicio:fim].strip()


# ---------------------------------------------------------------------------
# O texto de referência
# ---------------------------------------------------------------------------


def test_contagem_a_mao_bate_com_o_texto_de_referencia() -> None:
    """A lista à mão é o texto: mesma ordem, mesmas palavras."""
    assert len(CONTAGEM_A_MAO) == 45
    assert sum(silabas for _, silabas in CONTAGEM_A_MAO) == 108
    assert " ".join(palavra for palavra, _ in CONTAGEM_A_MAO) == TEXTO_DE_REFERENCIA.replace(
        ".", ""
    )


@pytest.mark.parametrize("palavra, esperado", CONTAGEM_A_MAO)
def test_cada_palavra_do_texto_de_referencia(palavra: str, esperado: int) -> None:
    assert contar_silabas(palavra) == esperado


def test_texto_de_referencia_tem_45_palavras_4_frases_108_silabas() -> None:
    assert contar(TEXTO_DE_REFERENCIA) == Contagens(45, 4, 108)


def test_texto_de_referencia_da_34_4() -> None:
    indice = flesch_br(TEXTO_DE_REFERENCIA)
    assert indice is not None
    assert round(indice, 1) == 34.4
    assert faixa_nilc(indice) == "difícil"


# ---------------------------------------------------------------------------
# Faixas
# ---------------------------------------------------------------------------


def test_texto_facil_passa_de_50() -> None:
    indice = flesch_br(TEXTO_FACIL)
    assert indice is not None
    assert indice >= 50


def test_paragrafo_da_ata_fica_abaixo_de_50(texto_ata: str) -> None:
    indice = flesch_br(_paragrafo_da_decisao(texto_ata))
    assert indice is not None
    assert indice < 50


def test_paragrafo_da_ata_nao_quebra_frase_no_a_a(texto_ata: str) -> None:
    """'14,00% a.a.,' está no meio da primeira frase do parágrafo 17."""
    contagens = contar(_paragrafo_da_decisao(texto_ata))
    assert contagens.frases == 2


@pytest.mark.parametrize(
    "indice, esperado",
    [
        (100.0, "muito fácil"),
        (75.0, "muito fácil"),
        (74.9, "fácil"),
        (50.0, "fácil"),
        (49.9, "difícil"),
        (25.0, "difícil"),
        (24.9, "muito difícil"),
        (-10.0, "muito difícil"),
    ],
)
def test_faixas_publicadas_pelo_nilc(indice: float, esperado: str) -> None:
    assert faixa_nilc(indice) == esperado


# ---------------------------------------------------------------------------
# Sem base para calcular
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("texto", ["", "   ", "%%% — • -", "\n\n"])
def test_texto_sem_palavra_devolve_none_e_nunca_zero(texto: str) -> None:
    assert flesch_br(texto) is None
    assert contar(texto) == Contagens(0, 0, 0)


def test_uma_palavra_so_nao_quebra() -> None:
    assert contar("Selic") == Contagens(1, 1, 2)
    indice = flesch_br("Selic")
    assert indice is not None
    assert indice == pytest.approx(248.835 - 1.015 - 84.6 * 2)


# ---------------------------------------------------------------------------
# Frases: o que termina e o que não termina
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, frases",
    [
        # Termina: a abreviação é seguida de maiúscula, de quebra de linha ou do fim.
        ("O Copom levou a Selic para 14,00% a.a. O Comitê seguiu cauteloso.", 2),
        ("A taxa fechou em 14,00% a.a.\nO Comitê seguiu cauteloso.", 2),
        ("Juros, câmbio, inflação, etc. O Comitê decidiu.", 2),
        ("O ciclo terminou. A Selic ficou em 14,00% a.a.", 2),
        ("A Selic ficou em 14,00% a.a.", 1),  # fim de texto não abre frase vazia
        # Não termina: minúscula, pontuação ou outro número depois.
        ("O Copom levou a Selic para 14,00% a.a. pelo segundo mês seguido.", 1),
        ("O Copom levou a Selic para 14,00% a.a., e entende que basta.", 1),
        ("O juro real ficou em 9,00% a.a. contra 8,50% a.a. no trimestre.", 1),
        ("O spread subiu 0,50 p.p. ante o mês anterior.", 1),
        # Tratamento fica fora da regra: o que vem depois é nome próprio.
        ("O Sr. Silva e o Dr. Souza votaram com o presidente.", 1),
        ("O Sr. Silva votou. O Dr. Souza também.", 2),
    ],
)
def test_abreviacao_termina_frase_so_diante_de_frase_nova(texto: str, frases: int) -> None:
    """A Célula fecha frase na Selic: '…para 14,00% a.a. O Comitê…' são duas frases."""
    assert contar(texto).frases == frases


def test_abreviacao_diante_de_minuscula_e_ponto_de_milhar_nao_terminam_frase() -> None:
    texto = (
        "A taxa Selic ficou em 14,00% a.a. pelo Copom. "
        "O Sr. Dr. Silva citou 1.234 pontos e p.p. adicionais."
    )
    contagens = contar(texto)
    assert contagens.frases == 2
    assert contagens.palavras == 19  # 14,00 / a.a. / 1.234 / p.p. contam uma cada


@pytest.mark.parametrize(
    "texto, frases",
    [
        ("Uma frase só", 1),  # sem terminador ainda é uma frase
        ("Uma. Duas! Três? Quatro…", 4),
        ("Isso... aquilo?! Fim.", 3),  # sequência de terminadores termina uma frase só
        ("Fim do texto.", 1),  # terminador no fim não abre frase vazia
        ("Primeira linha\n\nSegunda linha", 2),  # quebra dupla termina frase
        ("Primeira linha\nmesma frase", 1),  # quebra simples, não
        ("14,00% a.a. e 3,25% a.a.", 1),  # a do fim termina, mas não abre frase vazia
    ],
)
def test_contagem_de_frases(texto: str, frases: int) -> None:
    assert contar(texto).frases == frases


# ---------------------------------------------------------------------------
# Palavras, números e Markdown
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "texto, palavras",
    [
        ("Selic a 14,00% a.a.", 4),  # % não é palavra
        ("O Copom — reunião 280 — decidiu", 5),  # travessão não é palavra
        ("marcação a mercado", 3),
        ("bem-vindo", 1),  # hífen interno não parte a palavra
        ("• um • dois", 2),  # marcador de lista também não
    ],
)
def test_contagem_de_palavras(texto: str, palavras: int) -> None:
    assert contar(texto).palavras == palavras


@pytest.mark.parametrize(
    "texto, silabas",
    [
        ("7", 1),  # um dígito, uma sílaba
        ("2026", 4),
        ("14,00", 7),  # 4 dígitos + as 3 sílabas de vír-gu-la
        ("1.234", 4),  # ponto de milhar não soma
    ],
)
def test_convencao_de_silabas_para_numero(texto: str, silabas: int) -> None:
    assert contar(texto) == Contagens(1, 1, silabas)


def test_markdown_sai_da_contagem() -> None:
    texto = "# Título\n\n- Um ponto\n- Outro ponto\n\n1. Primeiro\n2. Segundo\n"
    # 7 palavras: Título, Um, ponto, Outro, ponto, Primeiro, Segundo
    assert contar(texto) == Contagens(palavras=7, frases=3, silabas=16)


def test_enfase_de_markdown_nao_vira_palavra() -> None:
    assert contar("**Selic** a _14,00_%") == contar("Selic a 14,00%")


def test_paragrafo_numerado_nao_termina_frase_no_marcador(texto_ata: str) -> None:
    """'17.' abrindo o parágrafo da Ata é marcador de lista, não fim de frase."""
    assert contar("17. O Copom decidiu reduzir a taxa.").frases == 1
    assert _paragrafo_da_decisao(texto_ata).startswith("17.")
