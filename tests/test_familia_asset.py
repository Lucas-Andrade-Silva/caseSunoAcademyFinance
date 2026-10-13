"""Família Asset (Suno Asset): capa vermelha e aviso legal, renderizados com texto real do Gerador.

A família tem marca própria (gestora de fundos): só entra por escolha explícita. O texto jurídico
do aviso é fixo e é o da Suno Asset para fundos; os demais textos fixos são neutros.
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
from tests.test_pacote import ancoras  # noqa: F401 - fixture

RAIZ = Path(__file__).resolve().parents[1]
FOTO = RAIZ / "data" / "imagens" / "bcb-sede.jpg"

TEXTO_JURIDICO = (
    "O PRESENTE MATERIAL DE DIVULGAÇÃO NÃO CONSTITUI OFERTA E/OU RECOMENDAÇÃO PARA COMPRA DE "
    "QUAISQUER VALORES MOBILIÁRIOS. LEIA O PROSPECTO E O REGULAMENTO ANTES DE INVESTIR, EM ESPECIAL "
    "A SEÇÃO DE FATORES DE RISCO. A isenção do imposto de renda é aplicável apenas para pessoa "
    "física e está sujeita às condições legais. Avalie a adequação do investimento ao seu perfil. "
    "Os fundos de investimento não contam com garantia do administrador do fundo, do gestor da "
    "carteira, de qualquer mecanismo de seguro ou do Fundo Garantidor de Crédito (FGC). A "
    "rentabilidade obtida no passado não representa garantia de resultados futuros. A EXPECTATIVA "
    "DE RETORNO PROJETADA NÃO REPRESENTA PROMESSA DE RENTABILIDADE. Saiba mais em: "
    "https://www.suno.com.br/asset/fundos/"
)

LAYOUTS = [ComposicaoCarrossel.ASSET_CAPA, ComposicaoCarrossel.ASSET_AVISO]


def _layouts_da_familia() -> dict[ComposicaoCarrossel, familias.LayoutDeFamilia]:
    return {c: l for c, l in familias.carregar_layouts().items() if l.familia is FamiliaVisual.ASSET}


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------


def test_a_familia_asset_so_abre_e_encerra_e_nao_cobre_o_miolo() -> None:
    """Capa e aviso são as bordas do carrossel. Sem layout de texto, o miolo (ponto, citação)
    não tem onde cair, e repetir o aviso legal em todo slide seria um defeito, não um layout."""
    layouts = _layouts_da_familia()
    assert set(layouts) == set(LAYOUTS)
    assert layouts[ComposicaoCarrossel.ASSET_CAPA].papeis == {TipoSlide.HOOK}
    assert layouts[ComposicaoCarrossel.ASSET_AVISO].papeis == {TipoSlide.CTA}
    assert set().union(*(l.papeis for l in layouts.values())) == {TipoSlide.HOOK, TipoSlide.CTA}


def test_o_manifesto_avisa_que_o_texto_juridico_e_da_gestora_e_pede_compliance() -> None:
    aviso = _layouts_da_familia()[ComposicaoCarrossel.ASSET_AVISO]
    assert "Suno Asset" in aviso.descricao
    assert "fundos de investimento" in aviso.descricao
    assert "compliance" in aviso.descricao


def test_a_capa_tem_um_unico_slot_de_titulo_e_foto_opcional() -> None:
    capa = _layouts_da_familia()[ComposicaoCarrossel.ASSET_CAPA]
    assert capa.usa_imagem
    assert "titulo" in capa.slots and not any(n.startswith("titulo_linha") for n in capa.slots)
    assert capa.slots["imagem"].obrigatorio is False


# ---------------------------------------------------------------------------
# Textos fixos: neutros, sem promessa nem número
# ---------------------------------------------------------------------------


def _textos_fixos(layout: familias.LayoutDeFamilia) -> list[str]:
    fixos: list[str] = []
    for slot in layout.slots.values():
        if slot.fonte.startswith("fixo:"):
            fixos.append(slot.fonte.removeprefix("fixo:"))
        elif slot.fonte == "por_papel":
            fixos.extend(slot.por_papel.values())
    return fixos


def test_nenhum_texto_fixo_da_capa_promete_nem_traz_numero() -> None:
    capa = _layouts_da_familia()[ComposicaoCarrossel.ASSET_CAPA]
    fixos = _textos_fixos(capa)
    assert fixos, "a capa deveria ter sobretítulo e botão fixos"
    for texto in fixos:
        assert "garantid" not in texto.lower(), texto
        assert "rendimentos do mês" not in texto.lower(), texto
        assert not re.search(r"\d", texto), texto
    html = (familias.PASTA_DOS_TEMPLATES / capa.arquivo).read_text(encoding="utf-8")
    texto_do_html = re.sub(r"<style>.*?</style>|<[^>]+>", " ", html, flags=re.S)
    assert "garantid" not in texto_do_html.lower()
    assert "DATACOM" not in html


def test_o_aviso_so_tem_o_texto_juridico_original_como_texto_fixo() -> None:
    aviso = _layouts_da_familia()[ComposicaoCarrossel.ASSET_AVISO]
    assert _textos_fixos(aviso) == []
    html = (familias.PASTA_DOS_TEMPLATES / aviso.arquivo).read_text(encoding="utf-8")
    bloco = re.search(r'data-slot="texto_juridico"[^>]*>(.*?)</div>', html, flags=re.S)
    assert bloco is not None
    texto = re.sub(r"<[^>]+>", "", bloco.group(1))
    assert " ".join(texto.split()) == TEXTO_JURIDICO
    # Fora do bloco jurídico e do título, o aviso não tem número de dado.
    resto = html.replace(bloco.group(0), "")
    resto = re.sub(r"<style>.*?</style>|<!--.*?-->", " ", resto, flags=re.S)
    resto = re.sub(r"<[^>]+>", " ", resto)
    assert not re.search(r"\d", resto), resto
    assert "garantid" not in resto.lower()


# ---------------------------------------------------------------------------
# Render com o texto real do Gerador
# ---------------------------------------------------------------------------

requer_navegador = pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)


def _hook() -> Slide:
    return Slide(
        tipo=TipoSlide.HOOK,
        titulo="Juros em 13,75% a.a.: qual o próximo passo?",
        corpo="A 281ª reunião do Copom trouxe ajustes na Selic. O mercado observa a inflação.",
        destaque="próximo passo",
        imagem="banco central",
    )


def _aviso(tipo: TipoSlide) -> Slide:
    return Slide(
        tipo=tipo,
        titulo="Leia a Ata completa",
        corpo="Veja o documento no site do Banco Central. Ele explica a decisão em detalhes.",
    )


def _renderizar(
    slide: Slide, composicao: ComposicaoCarrossel, pasta: Path, ancoras, *, foto: Path | None
) -> tuple[Path, list]:
    plano = (EscolhaDeLayout(indice=0, composicao=composicao, pontuacao=0),)
    [png] = carrossel_html.renderizar(
        [slide], Audiencia.INICIANTE, ancoras, pasta, plano_direcao=plano,
        imagens={0: foto} if foto else None,
    )
    with Image.open(png) as aberta:
        assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
    imagem = ImagemSlide(indice=0, caminho=png, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE)
    medicoes = conferir_imagens([imagem], ancoras).medicoes
    return png, [m for m in medicoes if m.defeito is not None]


@requer_navegador
def test_capa_com_foto_renderiza_1080x1350_sem_defeito(tmp_path: Path, ancoras) -> None:  # noqa: F811
    _, defeitos = _renderizar(_hook(), ComposicaoCarrossel.ASSET_CAPA, tmp_path, ancoras, foto=FOTO)
    assert defeitos == [], defeitos


@requer_navegador
def test_capa_sem_foto_degrada_sem_defeito(tmp_path: Path, ancoras) -> None:  # noqa: F811
    _, defeitos = _renderizar(_hook(), ComposicaoCarrossel.ASSET_CAPA, tmp_path, ancoras, foto=None)
    assert defeitos == [], defeitos


@requer_navegador
@pytest.mark.parametrize("tipo", [TipoSlide.CTA, TipoSlide.PONTO, TipoSlide.CITACAO])
def test_aviso_renderiza_1080x1350_sem_defeito_em_cada_papel(
    tipo: TipoSlide, tmp_path: Path, ancoras  # noqa: F811
) -> None:
    _, defeitos = _renderizar(_aviso(tipo), ComposicaoCarrossel.ASSET_AVISO, tmp_path, ancoras, foto=None)
    assert defeitos == [], defeitos


@requer_navegador
@pytest.mark.parametrize("foto", [FOTO, None], ids=["com_foto", "sem_foto"])
def test_capa_com_texto_longo_encolhe_em_vez_de_estourar(foto, tmp_path: Path, ancoras) -> None:  # noqa: F811
    longo = Slide(
        tipo=TipoSlide.HOOK,
        titulo="Por que a decisão de juros do Banco Central muda o custo do crédito",  # 63+ caracteres
        corpo=" ".join(
            ["O Comitê avalia o balanço de riscos com cautela e serenidade para decidir os juros."] * 3
        ),  # ~250 caracteres, o máximo real
    )
    _, defeitos = _renderizar(longo, ComposicaoCarrossel.ASSET_CAPA, tmp_path, ancoras, foto=foto)
    assert defeitos == [], defeitos


@requer_navegador
def test_aviso_com_titulo_longo_encolhe_em_vez_de_estourar(tmp_path: Path, ancoras) -> None:  # noqa: F811
    longo = Slide(
        tipo=TipoSlide.CTA,
        titulo="Por que a decisão de juros do Banco Central muda o custo do crédito para as famílias",
        corpo="Veja o documento no site do Banco Central.",
    )
    _, defeitos = _renderizar(longo, ComposicaoCarrossel.ASSET_AVISO, tmp_path, ancoras, foto=None)
    assert defeitos == [], defeitos
