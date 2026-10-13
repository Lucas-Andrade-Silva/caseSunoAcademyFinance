"""Família Dados (carrossel4 da Suno): manifesto, render com texto real e Âncora no número gigante.

O texto de cada caso tem o tamanho que o Gerador produz (título mediano de 35 caracteres, corpo de
150) e a variante LONGA o maior que o Gerador chega a escrever. Os testes de render pulam sem
Node/Puppeteer, como os de ``test_familias``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from PIL import Image

from suno.dominio import (
    ALTURA_SLIDE,
    LARGURA_SLIDE,
    Audiencia,
    ComposicaoCarrossel,
    DefeitoRender,
    EscolhaDeLayout,
    FamiliaVisual,
    ImagemSlide,
    Slide,
    TipoSlide,
)
from suno.pacote import carrossel_html, familias
from suno.pacote.visual import conferir_imagens
from tests.test_pacote import CITACAO_DA_SELIC, ancoras  # noqa: F401 - fixture

FOTO = Path(__file__).resolve().parents[1] / "data" / "imagens" / "bolsa-sp.jpg"

COMPOSICOES = [
    ComposicaoCarrossel.DADOS_TEXTO_GRANDE,
    ComposicaoCarrossel.DADOS_FOTO_NO_MEIO,
    ComposicaoCarrossel.DADOS_TEXTO_FOTO_EMBAIXO,
    ComposicaoCarrossel.DADOS_TEXTO_DUPLO_FOTO,
    ComposicaoCarrossel.DADOS_NUMERO_GIGANTE,
    ComposicaoCarrossel.DADOS_CTA,
]

requer_navegador = pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)


def _layouts() -> dict[ComposicaoCarrossel, familias.LayoutDeFamilia]:
    return {c: l for c, l in familias.carregar_layouts().items() if l.familia is FamiliaVisual.DADOS}


# ---------------------------------------------------------------------------
# O manifesto
# ---------------------------------------------------------------------------


def test_a_familia_dados_tem_os_seis_layouts_e_cobre_os_quatro_papeis() -> None:
    layouts = _layouts()
    assert set(layouts) == set(COMPOSICOES)
    assert set().union(*(l.papeis for l in layouts.values())) == set(TipoSlide)
    assert layouts[ComposicaoCarrossel.DADOS_TEXTO_GRANDE].papeis == {TipoSlide.HOOK, TipoSlide.PONTO}
    assert layouts[ComposicaoCarrossel.DADOS_CTA].papeis == {TipoSlide.CTA}


def test_so_o_numero_gigante_exige_dado_e_o_numero_vem_da_ancora() -> None:
    layouts = _layouts()
    exigem = {c for c, l in layouts.items() if l.exige_dado}
    assert exigem == {ComposicaoCarrossel.DADOS_NUMERO_GIGANTE}
    gigante = layouts[ComposicaoCarrossel.DADOS_NUMERO_GIGANTE]
    assert gigante.orientado_a_dados
    assert gigante.slots["numero"].fonte == "numero"
    assert gigante.slots["complemento"].fonte == "titulo"
    assert gigante.slots["nota"].fonte == "corpo"


def test_a_pilula_do_cta_nao_usa_palavra_chave_comercial() -> None:
    cta = _layouts()[ComposicaoCarrossel.DADOS_CTA]
    assert cta.slots["chamada"].por_papel == {TipoSlide.CTA: "Leia a Ata completa"}
    html = (familias.PASTA_DOS_TEMPLATES / cta.arquivo).read_text(encoding="utf-8")
    assert "comente" not in html.casefold()


@pytest.mark.parametrize("composicao", COMPOSICOES)
def test_o_html_nao_leva_numero_fixo_nem_linguagem_de_recomendacao(composicao) -> None:
    layout = _layouts()[composicao]
    html = (familias.PASTA_DOS_TEMPLATES / layout.arquivo).read_text(encoding="utf-8")
    visivel = re.sub(r"<!--.*?-->|<style>.*?</style>|<[^>]+>", "", html, flags=re.S)
    assert not re.search(r"\d", visivel), "o layout não pode ter número fixo: número só por Âncora"
    assert not re.search(r"compr|vend|garant|invista agora", visivel, flags=re.I)


@pytest.mark.parametrize("composicao", COMPOSICOES)
def test_cada_layout_tem_referencia_visual_para_o_banco(composicao) -> None:
    ref = _layouts()[composicao].referencia
    assert ref is not None
    assert {"titulo", "tema", "descricao", "instrucao_de_design", "analise", "origem"} <= set(ref)
    assert {
        "posicao_do_titulo",
        "proeminencia_do_titulo",
        "densidade_textual",
        "uso_de_imagem",
        "tipo_de_fundo",
        "elementos_visuais",
        "estrutura_do_conteudo",
    } <= set(ref["analise"])


# ---------------------------------------------------------------------------
# Render com o texto real do Gerador
# ---------------------------------------------------------------------------

NORMAL = {
    TipoSlide.HOOK: dict(
        titulo="Juros em 13,75% a.a.: qual o próximo passo?",
        corpo="A 281ª reunião do Copom trouxe ajustes na Selic. O mercado observa a inflação.",
        destaque="próximo passo",
    ),
    TipoSlide.PONTO: dict(
        titulo="A decisão da 281ª reunião",
        corpo=(
            "O Copom (o grupo que decide os juros) definiu a Selic (o juro básico da economia) "
            "em 14,00% a.a. Isso guia todos os outros juros do país."
        ),
        destaque="decisão",
    ),
    TipoSlide.CITACAO: dict(
        titulo="O cenário atual exige cautela",
        corpo=(
            "O Comitê destaca que a incerteza (a falta de clareza sobre o futuro) segue alta. "
            "Por isso, a política monetária precisa ser firme."
        ),
    ),
    TipoSlide.CTA: dict(
        titulo="Leia a Ata completa",
        corpo="Veja o documento no site do Banco Central. Ele explica a decisão em detalhes.",
    ),
}
LONGO = dict(
    titulo="Por que a decisão de juros do Banco Central muda o custo do crédito para as famílias",
    corpo=(
        "O Copom (o grupo que decide os juros, ou seja, o custo de pegar dinheiro emprestado) definiu a "
        "Selic (o juro básico da economia) em 14,00% a.a. Essa taxa guia todos os outros juros do país e "
        "muda o preço do crédito, dos financiamentos e dos investimentos de renda fixa para as famílias."
    ),
    destaque="decisão",
)


def _slide(composicao: ComposicaoCarrossel, *, longo: bool = False, corpo: str | None = None) -> Slide:
    layout = _layouts()[composicao]
    papel = sorted(layout.papeis, key=list(TipoSlide).index)[0]
    base = dict(NORMAL[papel])
    if longo:
        base.update(LONGO)
    if corpo is not None:
        base["corpo"] = corpo
    if layout.exige_dado:
        base["dado"] = "selic_decidida"
    return Slide(tipo=papel, **base)


def _renderizar(composicao, slide, ancoras, pasta, *, foto: Path | None):  # noqa: F811
    plano = (EscolhaDeLayout(indice=0, composicao=composicao, pontuacao=0),)
    [caminho] = carrossel_html.renderizar(
        [slide],
        Audiencia.INICIANTE,
        ancoras,
        pasta,
        plano_direcao=plano,
        imagens={0: foto} if foto else None,
    )
    with Image.open(caminho) as aberta:
        assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
    imagem = ImagemSlide(indice=0, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE)
    return caminho, conferir_imagens([imagem], ancoras).medicoes


def _defeitos(medicoes):
    return [m for m in medicoes if m.defeito is not None]


@requer_navegador
@pytest.mark.parametrize("composicao", COMPOSICOES)
def test_layout_dados_renderiza_1080x1350_sem_defeito(composicao, tmp_path, ancoras) -> None:  # noqa: F811
    usa_foto = _layouts()[composicao].usa_imagem
    _, medicoes = _renderizar(
        composicao, _slide(composicao), ancoras, tmp_path, foto=FOTO if usa_foto else None
    )
    assert _defeitos(medicoes) == []


@requer_navegador
@pytest.mark.parametrize("composicao", [c for c in COMPOSICOES if _layouts()[c].usa_imagem])
def test_layout_com_foto_degrada_sem_foto_sem_defeito(composicao, tmp_path, ancoras) -> None:  # noqa: F811
    _, medicoes = _renderizar(composicao, _slide(composicao), ancoras, tmp_path, foto=None)
    assert _defeitos(medicoes) == []


@requer_navegador
@pytest.mark.parametrize("composicao", COMPOSICOES)
def test_texto_longo_encolhe_ate_caber_em_vez_de_estourar(composicao, tmp_path, ancoras) -> None:  # noqa: F811
    usa_foto = _layouts()[composicao].usa_imagem
    _, medicoes = _renderizar(
        composicao, _slide(composicao, longo=True), ancoras, tmp_path, foto=FOTO if usa_foto else None
    )
    assert _defeitos(medicoes) == []


@requer_navegador
@pytest.mark.parametrize(
    "composicao", [ComposicaoCarrossel.DADOS_TEXTO_FOTO_EMBAIXO, ComposicaoCarrossel.DADOS_TEXTO_DUPLO_FOTO]
)
def test_corpo_de_uma_frase_so_ainda_renderiza(composicao, tmp_path, ancoras) -> None:  # noqa: F811
    slide = _slide(composicao, corpo="O Copom manteve a taxa básica de juros.")
    _, medicoes = _renderizar(composicao, slide, ancoras, tmp_path, foto=FOTO)
    assert _defeitos(medicoes) == []


@requer_navegador
def test_o_numero_gigante_desenha_a_ancora_e_nada_alem_dela(tmp_path, ancoras) -> None:  # noqa: F811
    caminho, medicoes = _renderizar(
        ComposicaoCarrossel.DADOS_NUMERO_GIGANTE,
        _slide(ComposicaoCarrossel.DADOS_NUMERO_GIGANTE),
        ancoras,
        tmp_path,
        foto=None,
    )
    manifesto = json.loads(caminho.with_suffix(".json").read_text(encoding="utf-8"))
    assert manifesto["numeros"] == [{"chave": "selic_decidida", "texto": CITACAO_DA_SELIC}]
    assert not [m for m in medicoes if m.defeito is DefeitoRender.NUMERO_DIVERGENTE]
    desenhado = " ".join(c["texto"] for c in manifesto["caixas"])
    assert CITACAO_DA_SELIC in desenhado


@requer_navegador
def test_o_cta_mostra_a_chamada_fixa_e_o_texto_do_slide(tmp_path, ancoras) -> None:  # noqa: F811
    caminho, _ = _renderizar(
        ComposicaoCarrossel.DADOS_CTA, _slide(ComposicaoCarrossel.DADOS_CTA), ancoras, tmp_path, foto=None
    )
    manifesto = json.loads(caminho.with_suffix(".json").read_text(encoding="utf-8"))
    por_nome = {c["nome"]: c["texto"] for c in manifesto["caixas"]}
    assert por_nome["chamada"] == "Leia a Ata completa"
    assert "Banco Central" in por_nome["apoio"]
