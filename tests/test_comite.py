"""O comitê de juízes-LLM: dois juízes, um julgamento por dimensão, seis chamadas por Célula.

Tudo com ``ProvedorFalso``: o comitê é a exceção deliberada do ADR 0001, mas a suíte
continua rodando offline e sem ``.env``.
"""

from __future__ import annotations

import logging

import pytest

from suno.comite import Comite, NotaDoJuiz
from suno.comite.rubricas import RUBRICAS, rubrica
from suno.dominio import (
    Audiencia,
    BlocoFala,
    Conteudo,
    DimensaoSubjetiva,
    EstadoMedida,
    Formato,
    PapelLLM,
    Slide,
)
from suno.provedores.falso import ProvedorFalso

NOMES_DE_PROVEDOR = ("gemini", "groq", "sambanova", "falso")
"""O prompt do juiz não pode citar nenhum deles: viés de reputação (ADR 0008)."""

TEXTO = (
    "A Selic (a taxa básica de juros do país) não mudou. "
    "O Banco Central: é a casa que cuida do valor do dinheiro."
)


def _juiz(nome: str, *notas: int) -> ProvedorFalso:
    """Um ``ProvedorFalso`` com nome próprio: os dois juízes nunca são o mesmo provedor."""
    provedor = ProvedorFalso(
        {"*": [{"nota": nota, "justificativa": "as ideias se encadeiam"} for nota in notas]}
    )
    provedor.nome = nome
    return provedor


def _analitico(texto: str = TEXTO) -> Conteudo:
    return Conteudo(formato=Formato.TEXTO_ANALITICO, texto=texto)


# ---------------------------------------------------------------------------
# Consenso e discordância
# ---------------------------------------------------------------------------


def test_notas_iguais_viram_consenso_medido() -> None:
    primeiro, segundo = _juiz("juiz-a", 4, 4, 4), _juiz("juiz-b", 4, 4, 4)
    comite = Comite((primeiro, segundo))

    resultado = comite.julgar(_analitico(), Audiencia.INICIANTE)

    assert resultado is not None
    assert [d.dimensao for d in resultado.dimensoes] == list(DimensaoSubjetiva)
    for dimensao in resultado.dimensoes:
        assert dimensao.estado is EstadoMedida.MEDIDA
        assert dimensao.consenso == 4
        assert [v.provedor for v in dimensao.votos] == ["juiz-a", "juiz-b"]
    assert resultado.provedores == ["juiz-a", "juiz-b"]


def test_notas_a_um_ponto_de_distancia_ainda_sao_consenso() -> None:
    comite = Comite((_juiz("juiz-a", 3, 3, 3), _juiz("juiz-b", 4, 4, 4)))

    resultado = comite.julgar(_analitico(), Audiencia.INICIANTE)

    assert resultado is not None
    for dimensao in resultado.dimensoes:
        assert dimensao.estado is EstadoMedida.MEDIDA
        # round() do Python arredonda 3,5 para o par mais próximo, que aqui é 4.
        assert dimensao.consenso == 4


def test_consenso_de_2_e_3_arredonda_para_o_par_mais_proximo() -> None:
    comite = Comite((_juiz("juiz-a", 2, 2, 2), _juiz("juiz-b", 3, 3, 3)))

    resultado = comite.julgar(_analitico(), Audiencia.INICIANTE)

    assert resultado is not None
    assert all(d.consenso == 2 for d in resultado.dimensoes)


def test_discordancia_vai_a_revisao_humana_sem_uma_terceira_chamada() -> None:
    primeiro, segundo = _juiz("juiz-a", 2, 2, 2), _juiz("juiz-b", 5, 5, 5)
    comite = Comite((primeiro, segundo))

    resultado = comite.julgar(_analitico(), Audiencia.INICIANTE)

    assert resultado is not None
    for dimensao in resultado.dimensoes:
        assert dimensao.estado is EstadoMedida.REVISAO_HUMANA
        assert dimensao.consenso is None
        assert len(dimensao.votos) == 2
    # 3 dimensões × 2 juízes = 6 chamadas por Célula. Nunca uma sétima para desempatar.
    assert len(primeiro.pedidos) + len(segundo.pedidos) == 6


def test_sao_seis_chamadas_por_celula_tambem_quando_todos_concordam() -> None:
    primeiro, segundo = _juiz("juiz-a", 5, 5, 5), _juiz("juiz-b", 5, 5, 5)

    Comite((primeiro, segundo)).julgar(_analitico(), Audiencia.AVANCADO)

    assert len(primeiro.pedidos) == 3
    assert len(segundo.pedidos) == 3


# ---------------------------------------------------------------------------
# O juiz nunca é quem gerou
# ---------------------------------------------------------------------------


def test_juiz_com_o_nome_do_provedor_gerador_nao_monta_comite() -> None:
    with pytest.raises(ValueError, match="autopreferência"):
        Comite((_juiz("gemini", 4), _juiz("groq", 4)), provedor_gerador="gemini")


def test_o_segundo_juiz_tambem_e_conferido_contra_o_provedor_gerador() -> None:
    with pytest.raises(ValueError):
        Comite((_juiz("groq", 4), _juiz("gemini", 4)), provedor_gerador="gemini")


def test_dois_juizes_no_mesmo_provedor_nao_montam_comite() -> None:
    with pytest.raises(ValueError, match="distintos"):
        Comite((_juiz("groq", 4), _juiz("groq", 4)), provedor_gerador="gemini")


def test_comite_sem_provedor_gerador_declarado_e_permitido() -> None:
    comite = Comite((_juiz("juiz-a", 4, 4, 4), _juiz("juiz-b", 4, 4, 4)))

    assert comite.provedor_gerador is None
    assert comite.julgar(_analitico(), Audiencia.INICIANTE) is not None


# ---------------------------------------------------------------------------
# O juiz é cego quanto a quem gerou
# ---------------------------------------------------------------------------


def test_nenhum_pedido_menciona_provedor_ou_modelo() -> None:
    primeiro, segundo = _juiz("juiz-a", 4, 4, 4), _juiz("juiz-b", 4, 4, 4)

    Comite((primeiro, segundo), provedor_gerador="gemini").julgar(
        _analitico(), Audiencia.INTERMEDIARIO
    )

    pedidos = [*primeiro.pedidos, *segundo.pedidos]
    assert len(pedidos) == 6
    for pedido in pedidos:
        inteiro = " ".join(m.texto for m in pedido.mensagens).lower()
        for nome in NOMES_DE_PROVEDOR:
            assert nome not in inteiro, f"o prompt do juiz citou {nome!r}"


def test_o_pedido_do_juiz_carrega_papel_rotulo_e_schema() -> None:
    primeiro, segundo = _juiz("juiz-a", 4, 4, 4), _juiz("juiz-b", 4, 4, 4)

    Comite((primeiro, segundo)).julgar(_analitico(), Audiencia.INICIANTE)

    rotulos = primeiro.rotulos_pedidos()
    assert rotulos == [
        "juiz:tom:iniciante:texto_analitico",
        "juiz:clareza:iniciante:texto_analitico",
        "juiz:coerencia:iniciante:texto_analitico",
    ]
    for pedido in primeiro.pedidos:
        assert pedido.papel is PapelLLM.JUIZ
        # O schema viaja no pedido, nunca fica no cliente (ADR 0007).
        assert pedido.schema_saida == NotaDoJuiz.model_json_schema()
        assert TEXTO in pedido.mensagens[-1].texto


def test_a_rubrica_de_coerencia_pergunta_pelo_texto_picado() -> None:
    texto_da_rubrica = RUBRICAS[DimensaoSubjetiva.COERENCIA].lower()

    assert "cortado artificialmente" in texto_da_rubrica
    assert "curtas e desconexas" in texto_da_rubrica


_SEM_ACENTO = str.maketrans("áàãâéêíóôõúç", "aaaaeeiooouc")


def test_toda_dimensao_tem_rubrica_propria_e_nenhuma_cita_provedor() -> None:
    assert set(RUBRICAS) == set(DimensaoSubjetiva)
    for dimensao in DimensaoSubjetiva:
        inteira = rubrica(dimensao).lower().translate(_SEM_ACENTO)
        assert str(dimensao) in inteira
        for nome in NOMES_DE_PROVEDOR:
            assert nome not in inteira


# ---------------------------------------------------------------------------
# Resposta malformada: ausente, nunca nota zero
# ---------------------------------------------------------------------------


def test_resposta_fora_do_schema_deixa_so_aquela_dimensao_ausente() -> None:
    primeiro = ProvedorFalso(
        {
            "juiz:tom:iniciante:texto_analitico": ["isto aqui não é JSON nenhum"],
            "*": [{"nota": 4, "justificativa": "claro"} for _ in range(2)],
        }
    )
    primeiro.nome = "juiz-a"
    segundo = _juiz("juiz-b", 4, 4, 4)

    resultado = Comite((primeiro, segundo)).julgar(_analitico(), Audiencia.INICIANTE)

    assert resultado is not None
    julgamentos = {d.dimensao: d for d in resultado.dimensoes}
    tom = julgamentos[DimensaoSubjetiva.TOM]
    assert tom.estado is EstadoMedida.AUSENTE
    assert tom.consenso is None
    # O voto que existe fica registrado; o que faltou não vira zero (ADR 0008).
    assert [v.provedor for v in tom.votos] == ["juiz-b"]
    for outra in (DimensaoSubjetiva.CLAREZA, DimensaoSubjetiva.COERENCIA):
        assert julgamentos[outra].estado is EstadoMedida.MEDIDA
        assert julgamentos[outra].consenso == 4


def test_nota_fora_da_escala_conta_como_resposta_malformada() -> None:
    primeiro = ProvedorFalso({"*": [{"nota": 9, "justificativa": "nota impossível"}] * 3})
    primeiro.nome = "juiz-a"
    segundo = _juiz("juiz-b", 4, 4, 4)

    resultado = Comite((primeiro, segundo)).julgar(_analitico(), Audiencia.INICIANTE)

    assert resultado is not None
    assert all(d.estado is EstadoMedida.AUSENTE for d in resultado.dimensoes)
    assert all(len(d.votos) == 1 for d in resultado.dimensoes)


# ---------------------------------------------------------------------------
# Formato: o Roteiro não passa pelo comitê
# ---------------------------------------------------------------------------


def test_roteiro_devolve_none_sem_gastar_chamada() -> None:
    primeiro, segundo = _juiz("juiz-a", 4, 4, 4), _juiz("juiz-b", 4, 4, 4)
    conteudo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[BlocoFala(inicio_s=0, fim_s=8, fala=TEXTO)],
    )

    assert Comite((primeiro, segundo)).julgar(conteudo, Audiencia.INICIANTE) is None
    assert primeiro.pedidos == []
    assert segundo.pedidos == []


def test_carrossel_e_julgado_pelo_texto_dos_slides() -> None:
    primeiro, segundo = _juiz("juiz-a", 4, 4, 4), _juiz("juiz-b", 4, 4, 4)
    conteudo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[Slide(titulo="A Selic parada", corpo=TEXTO)],
    )

    resultado = Comite((primeiro, segundo)).julgar(conteudo, Audiencia.AVANCADO)

    assert resultado is not None
    assert "A Selic parada" in primeiro.pedidos[0].mensagens[-1].texto
    assert primeiro.rotulos_pedidos()[0] == "juiz:tom:avancado:carrossel"


# ---------------------------------------------------------------------------
# Montagem a partir do ambiente: nasce desligado
# ---------------------------------------------------------------------------


def test_de_ambiente_desligado_devolve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUNO_COMITE", "0")

    assert Comite.de_ambiente("gemini") is None


def test_de_ambiente_sem_a_variavel_devolve_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUNO_COMITE", raising=False)

    assert Comite.de_ambiente("gemini") is None


def test_de_ambiente_ligado_sem_chave_no_ambiente_devolve_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sem provedor disponível o comitê não existe — e não derruba a execução (ADR 0008)."""
    monkeypatch.setenv("SUNO_COMITE", "1")

    assert Comite.de_ambiente("gemini") is None


def test_ligado_true_sobrepoe_a_variavel_desligada(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """É por aqui que ``--comite`` liga o comitê sem ninguém exportar ``SUNO_COMITE``."""
    monkeypatch.setenv("SUNO_COMITE", "0")
    caplog.set_level(logging.WARNING, logger="suno.comite")

    assert Comite.de_ambiente("gemini", ligado=True) is None
    # Tentou montar e explicou o que falta, em vez de sair calado como quando está desligado.
    assert "comitê pedido mas não montado" in caplog.text


def test_o_aviso_nomeia_as_variaveis_que_faltam_e_poupa_o_provedor_gerador(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SUNO_COMITE", "0")
    caplog.set_level(logging.WARNING, logger="suno.comite")

    assert Comite.de_ambiente("gemini", ligado=True) is None

    # A lista do que falta vem depois desta marca; antes dela vem a queixa do roteador, que
    # é genérica e cita os três provedores.
    _, _, faltando = caplog.text.partition("Falta preencher no .env:")
    assert "GROQ_API_KEY" in faltando
    assert "GROQ_MODELO" in faltando
    assert "SAMBANOVA_API_KEY" in faltando
    assert "SAMBANOVA_MODELO" in faltando
    # O Gerador está fora por princípio, não por falta de chave: não peça a chave dele.
    assert "GEMINI" not in faltando


def test_ligado_false_sobrepoe_a_variavel_ligada(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SUNO_COMITE", "1")
    caplog.set_level(logging.WARNING, logger="suno.comite")

    assert Comite.de_ambiente("gemini", ligado=False) is None
    # Desligado de propósito não é falha: nada a avisar.
    assert caplog.text == ""


def test_ligado_none_obedece_a_variavel_ligada(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SUNO_COMITE", "1")
    caplog.set_level(logging.WARNING, logger="suno.comite")

    assert Comite.de_ambiente("gemini", ligado=None) is None
    assert "comitê pedido mas não montado" in caplog.text


def test_ligado_none_com_a_variavel_desligada_nem_tenta(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SUNO_COMITE", "0")
    caplog.set_level(logging.WARNING, logger="suno.comite")

    assert Comite.de_ambiente("gemini", ligado=None) is None
    assert caplog.text == ""
