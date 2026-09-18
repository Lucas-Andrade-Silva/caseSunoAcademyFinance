"""As convenções de silabação do ADR 0002, uma a uma.

Cada caso aqui é uma decisão registrada, não um acaso da implementação: mexer no
separador e ver um destes quebrar significa que a convenção mudou, e o ADR também
tem que mudar. Roda offline, sem LLM (ADR 0001).
"""

from __future__ import annotations

import pytest

from suno.avaliador.silabas import contar_silabas, separar

# O bug do NILC: 'ideia' produzia sílaba vazia e contava 4.
CASOS_DITONGO_MAIS_VOGAL = [("ideia", 3)]

# Hiato com i/u tônico marcado.
CASOS_HIATO_MARCADO = [("saúde", 3), ("país", 2), ("baú", 2), ("saída", 3)]

# Ditongo decrescente não separa.
CASOS_DITONGO_DECRESCENTE = [("mãe", 1), ("pau", 1), ("lei", 1), ("causa", 2), ("ouro", 2)]

# -ia átono final é hiato; o resto do vocabulário básico da Ata.
CASOS_IA_FINAL = [("economia", 5), ("taxa", 2), ("juros", 2), ("Selic", 2)]

# As que a pyphen erra (pesquisa §2): subcontagem sistemática em palavra de finanças.
CASOS_QUE_A_PYPHEN_ERRA = [
    ("inflação", 3),
    ("ação", 2),
    ("ações", 2),
    ("ativo", 3),
    ("ágio", 2),
    ("água", 2),
    ("aplicação", 4),
]

CASOS_DE_FINANCAS = [
    ("dividendos", 4),
    ("liquidez", 3),
    ("título", 3),
    ("rendimento", 4),
    ("carteira", 3),
    ("tesouro", 3),
    ("pessoa", 3),
    ("juro", 2),
    ("real", 2),
    ("reais", 2),
]

CASOS_DE_DIGRAFO = [
    ("queijo", 2),
    ("guerra", 2),
    ("linguiça", 3),
    ("aquático", 4),
    ("chuva", 2),
    ("filho", 2),
    ("banho", 2),
]

CASOS_DE_ENCONTRO_CONSONANTAL = [
    ("prato", 2),
    ("blusa", 2),
    ("abstrato", 3),
    ("pneu", 1),
    ("psicologia", 5),
    ("ritmo", 2),
    ("obstáculo", 4),
]

# Siglas: bcb e CDI não têm vogal-núcleo suficiente para mais de uma sílaba.
CASOS_DE_SIGLA = [("copom", 2), ("bcb", 1), ("IPCA", 2), ("CDI", 1), ("selic", 2)]

TODOS_OS_CASOS = (
    CASOS_DITONGO_MAIS_VOGAL
    + CASOS_HIATO_MARCADO
    + CASOS_DITONGO_DECRESCENTE
    + CASOS_IA_FINAL
    + CASOS_QUE_A_PYPHEN_ERRA
    + CASOS_DE_FINANCAS
    + CASOS_DE_DIGRAFO
    + CASOS_DE_ENCONTRO_CONSONANTAL
    + CASOS_DE_SIGLA
)


@pytest.mark.parametrize("palavra, esperado", TODOS_OS_CASOS)
def test_contagem_das_convencoes_do_adr(palavra: str, esperado: int) -> None:
    assert contar_silabas(palavra) == esperado, separar(palavra)


@pytest.mark.parametrize("palavra, _esperado", TODOS_OS_CASOS)
def test_nenhuma_silaba_vazia(palavra: str, _esperado: int) -> None:
    """O bug do NILC em 'ideia' era exatamente este: uma sílaba vazia no meio."""
    silabas = separar(palavra)
    assert all(silabas), silabas
    assert "".join(silabas) == palavra


@pytest.mark.parametrize(
    "palavra, esperado",
    [
        ("ideia", ["i", "dei", "a"]),
        ("saúde", ["sa", "ú", "de"]),
        ("país", ["pa", "ís"]),
        ("baú", ["ba", "ú"]),
        ("saída", ["sa", "í", "da"]),
        ("economia", ["e", "co", "no", "mi", "a"]),
        ("ágio", ["á", "gio"]),
        ("água", ["á", "gua"]),
        ("causa", ["cau", "sa"]),
        ("Selic", ["Se", "lic"]),
    ],
)
def test_recorte_exato_das_convencoes_escritas_no_adr(palavra: str, esperado: list[str]) -> None:
    assert separar(palavra) == esperado


@pytest.mark.parametrize(
    "palavra, esperado",
    [
        ("rainha", ["ra", "i", "nha"]),  # i antes de nh abre hiato
        ("ruim", ["ru", "im"]),  # i com coda nasal abre hiato
        ("ainda", ["a", "in", "da"]),
        ("reino", ["rei", "no"]),  # ...mas n seguido de vogal não fecha sílaba
        ("moinho", ["mo", "i", "nho"]),
    ],
)
def test_hiato_diante_de_nh_e_de_coda_nasal(palavra: str, esperado: list[str]) -> None:
    assert separar(palavra) == esperado


@pytest.mark.parametrize(
    "palavra, esperado",
    [
        ("ciência", 3),  # crescente com tônica marcada abre: ci-ên-cia
        ("influência", 4),
        ("viagem", 3),  # crescente fora do fim da palavra abre: vi-a-gem
        ("convergência", 4),  # ...mas -ia final de palavra acentuada fecha
        ("família", 3),
        ("cenário", 3),
        ("psicologia", 5),  # e -ia final de palavra sem acento abre
    ],
)
def test_ditongo_crescente_depende_do_acento_e_da_posicao(palavra: str, esperado: int) -> None:
    assert contar_silabas(palavra) == esperado, separar(palavra)


@pytest.mark.parametrize(
    "palavra, esperado",
    [
        ("carro", ["car", "ro"]),
        ("pessoa", ["pes", "so", "a"]),
        ("nascer", ["nas", "cer"]),
        ("exceção", ["ex", "ce", "ção"]),
        ("desço", ["des", "ço"]),
    ],
)
def test_digrafo_separavel_sempre_parte_a_silaba(palavra: str, esperado: list[str]) -> None:
    assert separar(palavra) == esperado


def test_palavra_com_hifen_separa_cada_parte() -> None:
    assert separar("bem-vindo") == ["bem", "vin", "do"]
    assert contar_silabas("come-cotas") == 4


@pytest.mark.parametrize("entrada", ["", "   ", "%", "—", "14", "•"])
def test_entrada_sem_letra_devolve_lista_vazia(entrada: str) -> None:
    """Zero sílabas, nunca uma string vazia dentro da lista."""
    assert separar(entrada) == []
    assert contar_silabas(entrada) == 0


def test_maiusculas_preservadas_no_recorte() -> None:
    assert separar("IPCA") == ["IP", "CA"]
    assert separar("Copom") == ["Co", "pom"]
