"""Família Notícia: capa escura e slide de foto, com o texto real do Gerador e a degradação sem foto."""

from __future__ import annotations

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
from tests.test_pacote import ancoras  # noqa: F401 - fixture

requer_navegador = pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)

FOTO = Path(__file__).resolve().parents[1] / "data" / "imagens" / "bolsa-sp.jpg"

HOOK = Slide(
    tipo=TipoSlide.HOOK,
    titulo="Juros em 13,75% a.a.: qual o próximo passo?",
    corpo="A 281ª reunião do Copom trouxe ajustes na Selic. O mercado observa a inflação.",
    destaque="próximo passo",
)
PONTO = Slide(
    tipo=TipoSlide.PONTO,
    titulo="A decisão da 281ª reunião",
    corpo=(
        "O Copom (o grupo que decide os juros) definiu a Selic (o juro básico da economia) "
        "em 13,75% a.a. Isso guia todos os outros juros do país."
    ),
    dado="selic_decidida",
)
CTA = Slide(
    tipo=TipoSlide.CTA,
    titulo="Leia a Ata completa",
    corpo="Veja o documento no site do Banco Central.",
)
LONGO = Slide(
    tipo=TipoSlide.PONTO,
    titulo="Por que a decisão de juros do Banco Central muda o custo do crédito para as famílias",
    corpo=(
        "O Copom (o grupo que decide os juros, ou seja, o custo de pegar dinheiro emprestado) "
        "definiu a Selic (o juro básico da economia) em 13,75% a.a. Essa taxa guia todos os outros "
        "juros do país e muda o preço do crédito, dos financiamentos e dos investimentos de renda "
        "fixa para as famílias."
    ),
    destaque="famílias",
)


def _renderizar(slide: Slide, composicao: ComposicaoCarrossel, tmp_path: Path, ancoras, foto=None):  # noqa: F811
    plano = (EscolhaDeLayout(indice=0, composicao=composicao, pontuacao=0),)
    [caminho] = carrossel_html.renderizar(
        [slide],
        Audiencia.INICIANTE,
        ancoras,
        tmp_path,
        plano_direcao=plano,
        imagens={0: foto} if foto else None,
    )
    with Image.open(caminho) as aberta:
        assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
    imagem = ImagemSlide(indice=0, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE)
    return [m for m in conferir_imagens([imagem], ancoras).medicoes if m.defeito is not None]


def test_a_familia_noticia_cobre_os_quatro_papeis_com_dois_layouts() -> None:
    layouts = familias.layouts_da_familia(FamiliaVisual.NOTICIA)
    assert {layout.composicao for layout in layouts} == {
        ComposicaoCarrossel.NOTICIA_CAPA,
        ComposicaoCarrossel.NOTICIA_FOTO,
    }
    assert set().union(*(layout.papeis for layout in layouts)) == set(TipoSlide)


def test_chamada_da_capa_muda_com_o_papel(ancoras) -> None:  # noqa: F811
    layout = familias.carregar_layouts()[ComposicaoCarrossel.NOTICIA_CAPA]

    def chamada(slide: Slide):
        return familias.valores_do_slide(
            layout, slide, ancoras=ancoras, indice=0, total=1, imagem_uri=None
        )[0]["chamada"]

    assert chamada(HOOK) == "ARRASTE E CONFIRA"
    assert chamada(CTA) == "LEIA A ATA COMPLETA"


def test_destaque_so_existe_quando_e_o_final_literal_do_titulo(ancoras) -> None:  # noqa: F811
    layout = familias.carregar_layouts()[ComposicaoCarrossel.NOTICIA_CAPA]

    def valores(slide: Slide):
        return familias.valores_do_slide(
            layout, slide, ancoras=ancoras, indice=0, total=1, imagem_uri=None
        )[0]

    com = valores(HOOK.model_copy(update={"titulo": "Juros caem: qual o próximo passo?"}))
    assert com["destaque"] == "próximo passo"
    assert com["titulo"] == "Juros caem: qual o"
    sem = valores(HOOK.model_copy(update={"destaque": "juros"}))
    assert sem["destaque"] is None
    assert sem["titulo"] == HOOK.titulo


@requer_navegador
@pytest.mark.parametrize(
    ("slide", "composicao", "foto"),
    [
        (HOOK, ComposicaoCarrossel.NOTICIA_CAPA, None),
        (CTA, ComposicaoCarrossel.NOTICIA_CAPA, None),
        (PONTO, ComposicaoCarrossel.NOTICIA_FOTO, FOTO),
    ],
)
def test_layout_noticia_renderiza_1080x1350_sem_defeito(
    slide: Slide, composicao: ComposicaoCarrossel, foto, tmp_path: Path, ancoras  # noqa: F811
) -> None:
    assert _renderizar(slide, composicao, tmp_path, ancoras, foto) == []


@requer_navegador
def test_capa_sem_destaque_mostra_o_titulo_inteiro(tmp_path: Path, ancoras) -> None:  # noqa: F811
    slide = HOOK.model_copy(update={"destaque": "juros"})
    assert _renderizar(slide, ComposicaoCarrossel.NOTICIA_CAPA, tmp_path, ancoras) == []


@requer_navegador
def test_slide_de_foto_sem_foto_degrada_sem_defeito(tmp_path: Path, ancoras) -> None:  # noqa: F811
    assert _renderizar(PONTO, ComposicaoCarrossel.NOTICIA_FOTO, tmp_path, ancoras) == []


def test_sem_foto_o_motor_marca_o_body_e_tira_a_imagem(ancoras) -> None:  # noqa: F811
    layout = familias.carregar_layouts()[ComposicaoCarrossel.NOTICIA_FOTO]
    html, _ = familias.preencher_layout(
        layout, PONTO, ancoras=ancoras, indice=0, total=1, imagem_uri=None
    )
    assert '<body class="sem-imagem"' in html
    assert 'data-slot="imagem"' not in html


@requer_navegador
@pytest.mark.parametrize(
    ("composicao", "foto"),
    [
        (ComposicaoCarrossel.NOTICIA_CAPA, None),
        (ComposicaoCarrossel.NOTICIA_FOTO, FOTO),
        (ComposicaoCarrossel.NOTICIA_FOTO, None),
    ],
)
def test_texto_longo_encolhe_ate_caber_em_vez_de_estourar(
    composicao: ComposicaoCarrossel, foto, tmp_path: Path, ancoras  # noqa: F811
) -> None:
    assert _renderizar(LONGO, composicao, tmp_path, ancoras, foto) == []
