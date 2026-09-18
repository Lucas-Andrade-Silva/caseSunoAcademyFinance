"""A linha que o sistema não cruza, medida (ADR 0012).

A suíte inteira roda com a trava de rede do conftest ligada: se `spacy.load` precisasse
da internet, o primeiro teste quebraria. É de propósito — é a premissa do ADR 0001 que
está sendo verificada junto.

Os casos vêm de data/canary/canary.yaml, um por teste, para a saída do pytest contar
armadilha por armadilha. Armadilha com `sem_cobertura` no arquivo vira xfail: é fuga
conhecida, medida, e entra no Entregável 6.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from suno.avaliador.recomendacao import (
    CasoDoCanary,
    Ocorrencia,
    _modelo,
    carregar_padroes,
    casos_do_canary,
    detectar_recomendacao,
    ha_recomendacao,
)

CASOS = casos_do_canary()
ARMADILHAS = [caso for caso in CASOS if caso.deve_acusar]
NEUTRAS = [caso for caso in CASOS if not caso.deve_acusar]


def _rotulo(caso: CasoDoCanary) -> str:
    return caso.texto


def _parametrizar(casos: list[CasoDoCanary]) -> list[object]:
    """Armadilha sem cobertura entra como xfail estrito-não: a taxa de fuga é medida."""
    preparados: list[object] = []
    for caso in casos:
        if caso.sem_cobertura:
            preparados.append(
                pytest.param(caso, marks=pytest.mark.xfail(reason=caso.sem_cobertura, strict=True))
            )
        else:
            preparados.append(caso)
    return preparados


# ---------------------------------------------------------------------------
# (1) o modelo carrega com a trava de rede ligada
# ---------------------------------------------------------------------------


def test_modelo_carrega_sem_rede() -> None:
    """Se isto falhar, o ADR 0012 precisa ser revisto: a dependência de peso não roda offline."""
    modelo = _modelo()
    doc = modelo("O Copom decidiu reduzir a Selic. Você precisa sair da poupança.")
    assert [frase.text.strip() for frase in doc.sents] == [
        "O Copom decidiu reduzir a Selic.",
        "Você precisa sair da poupança.",
    ]
    assert {token.pos_ for token in doc} != {""}
    assert doc[0].lemma_ != ""


def test_modelo_fica_em_cache_de_modulo() -> None:
    """Carregar o modelo por Célula custaria segundos em cada uma das nove."""
    assert _modelo() is _modelo()


# ---------------------------------------------------------------------------
# (2) toda armadilha acusa
# ---------------------------------------------------------------------------


def test_canary_tem_o_tamanho_que_o_ADR_0012_exige() -> None:
    assert len(ARMADILHAS) >= 40, "o canary set precisa de pelo menos 40 armadilhas"
    assert len(NEUTRAS) >= 25, "o canary set precisa de pelo menos 25 frases neutras"
    assert len({caso.texto for caso in CASOS}) == len(CASOS), "há caso repetido no canary"
    assert all(caso.por_que.strip() for caso in CASOS), "todo caso explica a razão de domínio"


@pytest.mark.parametrize("caso", _parametrizar(ARMADILHAS), ids=_rotulo)
def test_armadilha_do_canary_acusa(caso: CasoDoCanary) -> None:
    achadas = detectar_recomendacao(caso.texto)
    assert achadas, f"paráfrase escapou: {caso.por_que}"
    for ocorrencia in achadas:
        assert ocorrencia.trecho, "toda Ocorrência aponta o trecho exato"
        assert ocorrencia.trecho in caso.texto
        assert ocorrencia.frase in caso.texto
        assert ocorrencia.padrao
        assert ocorrencia.camada in ("lexico", "sintaxe")


def test_a_sintaxe_pega_o_que_o_lexico_nao_pega() -> None:
    """O ADR 0012 recusa a blocklist. Se o Léxico sozinho desse conta, a recusa seria vazia."""
    so_pela_sintaxe = [
        caso
        for caso in ARMADILHAS
        if not caso.sem_cobertura
        and {o.camada for o in detectar_recomendacao(caso.texto)} == {"sintaxe"}
    ]
    assert len(so_pela_sintaxe) >= 10, [caso.texto for caso in so_pela_sintaxe]


# ---------------------------------------------------------------------------
# (3) nenhuma neutra acusa
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("caso", _parametrizar(NEUTRAS), ids=_rotulo)
def test_frase_neutra_do_canary_nao_acusa(caso: CasoDoCanary) -> None:
    achadas = detectar_recomendacao(caso.texto)
    assert achadas == [], f"reprovou frase que o sistema precisa poder escrever: {caso.por_que}"


# ---------------------------------------------------------------------------
# os exemplos documentados em padroes.yaml valem como teste
# ---------------------------------------------------------------------------


def _exemplos(bloco: str) -> list[tuple[str, str, bool]]:
    padroes = carregar_padroes()
    exemplos: list[tuple[str, str, bool]] = []
    for nome, corpo in padroes[bloco].items():
        if "exemplo_dispara" in corpo:
            exemplos.append((nome, corpo["exemplo_dispara"], True))
        if "exemplo_nao_dispara" in corpo:
            exemplos.append((nome, corpo["exemplo_nao_dispara"], False))
    return exemplos


EXEMPLOS = _exemplos("nao_pode") + _exemplos("pode") + _exemplos("sintaxe")


@pytest.mark.parametrize(
    ("nome", "texto", "deve_acusar"), EXEMPLOS, ids=[f"{n}:{t[:40]}" for n, t, _ in EXEMPLOS]
)
def test_exemplo_documentado_no_padroes_yaml(nome: str, texto: str, deve_acusar: bool) -> None:
    """Documentação que mente é pior que documentação que falta."""
    achadas = detectar_recomendacao(texto)
    if not deve_acusar:
        assert achadas == [], f"{nome}: o exemplo que não deveria disparar disparou"
        return
    assert nome in {o.padrao for o in achadas}, f"{nome}: disparou por outro padrão, ou não disparou"


# ---------------------------------------------------------------------------
# (4) a Ata real não acusa nada
# ---------------------------------------------------------------------------


def test_ata_do_copom_nao_tem_recomendacao(texto_ata: str) -> None:
    """A Ata é o texto mais neutro que existe: acusar algo aqui é falso positivo puro."""
    achadas = detectar_recomendacao(texto_ata)
    assert achadas == [], [(o.padrao, o.trecho, o.frase[:80]) for o in achadas]
    assert not ha_recomendacao(texto_ata)


def test_ata_do_copom_fala_de_manter_e_reduzir_sem_recomendar(texto_ata: str) -> None:
    """Prova que o teste acima não passa por acaso: os verbos de ação estão lá."""
    assert "reduzir" in texto_ata and "manter" in texto_ata


# ---------------------------------------------------------------------------
# (5) determinismo e (6) texto vazio
# ---------------------------------------------------------------------------


def test_duas_chamadas_dao_o_mesmo_resultado() -> None:
    """ADR 0012: uma linha que reprova não pode mudar de opinião entre duas execuções."""
    texto = (
        "O Copom decidiu reduzir a Selic para 14,00% a.a. "
        "Seria prudente considerar reduzir posição em ativos de risco. "
        "Historicamente, juros altos pesam sobre a bolsa."
    )
    primeira = detectar_recomendacao(texto)
    segunda = detectar_recomendacao(texto)
    assert primeira == segunda
    assert [o.padrao for o in primeira] == ["conveniencia_impessoal"]
    assert primeira[0].frase == "Seria prudente considerar reduzir posição em ativos de risco."


@pytest.mark.parametrize("texto", ["", "   ", "\n\t \n"])
def test_texto_vazio_devolve_lista_vazia(texto: str) -> None:
    assert detectar_recomendacao(texto) == []
    assert not ha_recomendacao(texto)


# ---------------------------------------------------------------------------
# a forma da Ocorrência
# ---------------------------------------------------------------------------


def test_ocorrencia_localiza_a_frase_dentro_do_texto_maior() -> None:
    """O Laudo cita a frase que recomenda, não o Conteúdo inteiro."""
    texto = (
        "A Selic caiu para 14,00% a.a. "
        "Isso afeta o rendimento da poupança. "
        "Reduza sua exposição a ativos de risco. "
        "O Comitê avalia que a inflação segue acima da meta."
    )
    achadas = detectar_recomendacao(texto)
    assert achadas
    assert {o.frase for o in achadas} == {"Reduza sua exposição a ativos de risco."}
    assert "personalizacao_com_direcao" in {o.padrao for o in achadas}


def test_ocorrencia_e_imutavel_e_comparavel() -> None:
    uma = Ocorrencia(frase="Compre agora.", padrao="imperativos_de_acao", trecho="Compre")
    outra = Ocorrencia(frase="Compre agora.", padrao="imperativos_de_acao", trecho="Compre")
    assert uma == outra
    assert len({uma, outra}) == 1
    with pytest.raises(Exception):
        uma.trecho = "outro"  # type: ignore[misc]


def test_o_lexico_e_o_canary_moram_em_disco() -> None:
    """A demo roda sem rede: Léxico e canary são arquivos versionados, não chamadas."""
    pasta = Path(__file__).resolve().parent.parent / "data" / "canary"
    assert (pasta / "padroes.yaml").is_file()
    assert (pasta / "canary.yaml").is_file()
