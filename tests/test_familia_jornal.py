"""Família Jornal (Suno Notícias): manifesto e render dos três layouts com o texto real do Gerador.

Os testes de render pulam sem Node/Puppeteer, como os de ``test_familias``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

from suno.dominio import (
    ALTURA_SLIDE,
    LARGURA_SLIDE,
    Audiencia,
    ComposicaoCarrossel,
    EscolhaDeLayout,
    FamiliaVisual,
    ImagemSlide,
    Slide,
    TipoSlide,
)
from suno.pacote import carrossel_html, familias
from suno.pacote.visual import conferir_imagens
from tests.test_familias import _slides_reais
from tests.test_pacote import ancoras  # noqa: F401 - fixture

RAIZ = Path(__file__).resolve().parents[1]
FOTO = RAIZ / "data" / "imagens" / "bcb-sede.jpg"

CAPA = ComposicaoCarrossel.JORNAL_CAPA
ITEM = ComposicaoCarrossel.JORNAL_ITEM_NUMERADO
TEXTO = ComposicaoCarrossel.JORNAL_TEXTO

requer_navegador = pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)


def _layouts() -> dict[ComposicaoCarrossel, familias.LayoutDeFamilia]:
    return {c: l for c, l in familias.carregar_layouts().items() if l.familia is FamiliaVisual.JORNAL}


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------


def test_a_familia_jornal_tem_os_tres_layouts_e_cobre_os_quatro_papeis() -> None:
    layouts = _layouts()
    assert set(layouts) == {CAPA, ITEM, TEXTO}
    assert set().union(*(l.papeis for l in layouts.values())) == set(TipoSlide)
    assert layouts[CAPA].papeis == {TipoSlide.HOOK}
    assert layouts[ITEM].papeis == {TipoSlide.PONTO}
    assert layouts[TEXTO].papeis == {TipoSlide.CITACAO, TipoSlide.CTA, TipoSlide.PONTO}


def test_o_perfil_e_fixo_e_nenhum_numero_esta_escrito_no_layout() -> None:
    for composicao, layout in _layouts().items():
        assert layout.slots["nome_perfil"].fonte == "fixo:Suno Notícias"
        assert layout.slots["arroba"].fonte == "fixo:@sunonoticias"
        assert layout.referencia is not None, composicao
        assert not layout.exige_dado


def test_cada_papel_tem_um_layout_favorito_na_familia() -> None:
    layouts = _layouts()
    assert layouts[CAPA].pontos_por_papel[TipoSlide.HOOK] > 0
    assert layouts[ITEM].pontos_por_papel[TipoSlide.PONTO] > layouts[TEXTO].pontos_por_papel[TipoSlide.PONTO]
    assert layouts[TEXTO].pontos_por_papel[TipoSlide.CITACAO] > 0
    assert layouts[TEXTO].pontos_por_papel[TipoSlide.CTA] > 0


def test_html_sem_recorte_de_pixels_e_com_selo_fora_do_slot_do_nome() -> None:
    for layout in _layouts().values():
        html = (familias.PASTA_DOS_TEMPLATES / layout.arquivo).read_text(encoding="utf-8")
        assert "data:image" not in html and "{{IMG:" not in html
        assert re.search(r'<span data-slot="nome_perfil">Suno Notícias</span> <svg', html)
        assert 'data-ajustar data-caixa="area"' in html


# ---------------------------------------------------------------------------
# Render com o texto real
# ---------------------------------------------------------------------------


def _renderizar(slides: list[Slide], composicoes, tmp_path: Path, ancoras, fotos: bool):
    plano = tuple(EscolhaDeLayout(indice=i, composicao=c, pontuacao=0) for i, c in enumerate(composicoes))
    imagens = {i: FOTO for i in range(len(slides))} if fotos else None
    caminhos = carrossel_html.renderizar(
        slides, Audiencia.INICIANTE, ancoras, tmp_path, plano_direcao=plano, imagens=imagens
    )
    imagens_slide = []
    for i, caminho in enumerate(caminhos):
        with Image.open(caminho) as aberta:
            assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
        imagens_slide.append(ImagemSlide(indice=i, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE))
    return [m for m in conferir_imagens(imagens_slide, ancoras).medicoes if m.defeito is not None]


@requer_navegador
@pytest.mark.parametrize("fotos", [True, False], ids=["com_foto", "sem_foto"])
def test_cada_layout_renderiza_1080x1350_sem_defeito(fotos: bool, tmp_path: Path, ancoras) -> None:  # noqa: F811
    hook, ponto, citacao, cta = _slides_reais()
    slides = [hook, ponto, ponto, citacao, cta]
    composicoes = [CAPA, ITEM, TEXTO, TEXTO, TEXTO]
    assert _renderizar(slides, composicoes, tmp_path, ancoras, fotos) == []


@requer_navegador
def test_sem_foto_a_classe_de_degradacao_vai_no_body(tmp_path: Path, ancoras) -> None:  # noqa: F811
    hook = _slides_reais()[0]
    layout = _layouts()[CAPA]
    sem, _ = familias.preencher_layout(layout, hook, ancoras=ancoras, indice=0, total=1, imagem_uri=None)
    com, _ = familias.preencher_layout(layout, hook, ancoras=ancoras, indice=0, total=1, imagem_uri="file:///f.jpg")
    assert '<body class="sem-imagem"' in sem
    assert "<body data-fundo" in com and 'src="file:///f.jpg"' in com


@requer_navegador
@pytest.mark.parametrize("fotos", [True, False], ids=["com_foto", "sem_foto"])
def test_texto_longo_encolhe_ate_caber_em_vez_de_estourar(fotos: bool, tmp_path: Path, ancoras) -> None:  # noqa: F811
    titulo = "Por que a decisão de juros do Banco Central muda o custo do crédito para as famílias"
    corpo = (
        "O Copom (o grupo que decide os juros, ou seja, o custo de pegar dinheiro emprestado) definiu a Selic "
        "(o juro básico da economia) em 13,75% a.a. Essa taxa guia todos os outros juros do país e muda o preço "
        "do crédito, dos financiamentos e dos investimentos de renda fixa para as famílias."
    )
    slides = [
        Slide(tipo=TipoSlide.HOOK, titulo=titulo, corpo=corpo),
        Slide(tipo=TipoSlide.PONTO, titulo=titulo, corpo=corpo),
        Slide(tipo=TipoSlide.CITACAO, titulo=titulo, corpo=corpo),
    ]
    assert _renderizar(slides, [CAPA, ITEM, TEXTO], tmp_path, ancoras, fotos) == []
