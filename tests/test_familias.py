"""Famílias visuais: manifesto, motor de slots e render com o texto real do Gerador.

Cada família vive em ``src/suno/pacote/templates/familias/<familia>/`` com um ``familia.json`` e um
HTML por layout. O HTML marca os slots com ``data-slot``; o motor troca o conteúdo sem tocar no
resto. Os testes de render pulam sem Node/Puppeteer, como os de ``test_carrossel_html``.
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
    FamiliaVisual,
    ImagemSlide,
    Slide,
    TipoSlide,
)
from suno.pacote import carrossel_html, familias
from suno.pacote.familias import SlotObrigatorioAusente
from suno.pacote.visual import conferir_imagens
from tests.test_pacote import ancoras  # noqa: F401 - fixture


# ---------------------------------------------------------------------------
# Corpo em frases: a "frase em vermelho" sai da última frase, não de um parágrafo
# ---------------------------------------------------------------------------


def test_corpo_de_um_paragrafo_so_vira_corpo_e_ultima_frase() -> None:
    corpo, ultima = familias.separar_ultima_frase(
        "O Copom definiu a Selic em 13,75% a.a. Isso guia todos os outros juros do país."
    )
    assert corpo == "O Copom definiu a Selic em 13,75% a.a."
    assert ultima == "Isso guia todos os outros juros do país."


def test_corpo_com_uma_frase_nao_tem_ultima_frase() -> None:
    corpo, ultima = familias.separar_ultima_frase("Leia a Ata completa.")
    assert corpo == "Leia a Ata completa."
    assert ultima is None


def test_paragrafos_explicitos_mandam_na_divisao() -> None:
    corpo, ultima = familias.separar_ultima_frase("Primeiro.\n\nSegundo bloco. Com duas frases.")
    assert corpo == "Primeiro."
    assert ultima == "Segundo bloco. Com duas frases."


# ---------------------------------------------------------------------------
# O motor de slots
# ---------------------------------------------------------------------------

MODELO = (
    '<div class="a" data-slot="titulo">exemplo</div>'
    '<p data-slot="corpo">outro <b>exemplo</b></p>'
    '<img data-slot="imagem" src="x.jpg">'
    '<div data-slot="opcional"><i>sobra</i></div>'
)


def _especificacao(**sobrescrita):
    base = {
        "titulo": familias.SlotDoLayout("titulo", "titulo"),
        "corpo": familias.SlotDoLayout("corpo", "corpo"),
        "imagem": familias.SlotDoLayout("imagem", "imagem", tipo="imagem"),
        "opcional": familias.SlotDoLayout("opcional", "ultima_frase", obrigatorio=False),
    }
    base.update(sobrescrita)
    return base


def test_troca_o_conteudo_do_slot_e_escapa_o_texto() -> None:
    saida = familias.preencher_slots(
        MODELO,
        _especificacao(),
        {"titulo": "Selic & <juros>", "corpo": "Texto", "imagem": "file:///foto.jpg", "opcional": None},
    )
    assert 'data-slot="titulo"' in saida and "Selic &amp; &lt;juros&gt;" in saida
    assert "outro" not in saida and "exemplo" not in saida
    assert 'src="file:///foto.jpg"' in saida


def test_slot_opcional_sem_valor_sai_do_html_inteiro() -> None:
    saida = familias.preencher_slots(
        MODELO,
        _especificacao(),
        {"titulo": "T", "corpo": "C", "imagem": "file:///f.jpg", "opcional": None},
    )
    assert "sobra" not in saida
    assert 'data-slot="opcional"' not in saida


def test_slot_obrigatorio_sem_valor_e_erro() -> None:
    with pytest.raises(SlotObrigatorioAusente, match="titulo"):
        familias.preencher_slots(
            MODELO, _especificacao(), {"titulo": None, "corpo": "C", "imagem": "f", "opcional": None}
        )


def test_texto_marcado_como_caixa_para_a_conferencia_visual() -> None:
    saida = familias.preencher_slots(
        MODELO,
        _especificacao(),
        {"titulo": "T", "corpo": "C", "imagem": "f", "opcional": None},
    )
    assert re.search(r'<div class="a" data-slot="titulo" data-caixa="titulo">T</div>', saida)


def test_com_contenedor_medido_o_slot_so_entra_no_contraste() -> None:
    modelo = '<div data-ajustar data-caixa="area"><p data-slot="corpo">x</p></div>'
    saida = familias.preencher_slots(
        modelo, {"corpo": familias.SlotDoLayout("corpo", "corpo")}, {"corpo": "texto"}
    )
    assert 'data-contraste="corpo"' in saida
    assert saida.count("data-caixa") == 1


def test_numeracao_de_item_nao_conta_a_capa(ancoras) -> None:  # noqa: F811
    slot = familias.SlotDoLayout("numero_item", "ordem_sem_capa")
    layout = familias.LayoutDeFamilia(
        composicao=ComposicaoCarrossel.JORNAL_ITEM_NUMERADO,
        familia=FamiliaVisual.JORNAL,
        arquivo="x",
        descricao="",
        papeis=frozenset(TipoSlide),
        slots={"numero_item": slot},
    )

    def numero(indice: int) -> object:
        slide = Slide(tipo=TipoSlide.PONTO, titulo="T", corpo="C")
        return familias.valores_do_slide(
            layout, slide, ancoras=ancoras, indice=indice, total=5, imagem_uri=None
        )[0]["numero_item"]

    assert numero(1) == "1", "o primeiro slide depois da capa é o item 1"
    assert numero(3) == "3"
    assert numero(0) == "1", "nunca abaixo de 1, mesmo sem capa"


def test_texto_fixo_por_papel_muda_com_o_papel_do_slide(ancoras) -> None:  # noqa: F811
    slot = familias.SlotDoLayout(
        "chamada",
        "por_papel",
        obrigatorio=False,
        por_papel={TipoSlide.HOOK: "ARRASTE E CONFIRA", TipoSlide.CTA: "LEIA A ATA"},
    )
    layout = familias.LayoutDeFamilia(
        composicao=ComposicaoCarrossel.EXPLICATIVO_CAPA,
        familia=FamiliaVisual.EXPLICATIVO,
        arquivo="x",
        descricao="",
        papeis=frozenset(TipoSlide),
        slots={"chamada": slot},
    )

    def valor(tipo: TipoSlide):
        slide = Slide(tipo=tipo, titulo="T", corpo="C")
        return familias.valores_do_slide(
            layout, slide, ancoras=ancoras, indice=0, total=1, imagem_uri=None
        )[0]["chamada"]

    assert valor(TipoSlide.HOOK) == "ARRASTE E CONFIRA"
    assert valor(TipoSlide.CTA) == "LEIA A ATA"
    assert valor(TipoSlide.PONTO) is None


# ---------------------------------------------------------------------------
# O manifesto casa com o HTML
# ---------------------------------------------------------------------------


def test_cada_layout_declarado_tem_html_e_os_slots_do_html_sao_os_do_manifesto() -> None:
    layouts = familias.carregar_layouts()
    assert layouts, "nenhuma família carregada"
    for composicao, layout in layouts.items():
        caminho = familias.PASTA_DOS_TEMPLATES / layout.arquivo
        assert caminho.is_file(), f"{composicao}: falta {layout.arquivo}"
        html = caminho.read_text(encoding="utf-8")
        no_html = set(re.findall(r'data-slot="([\w-]+)"', html))
        assert no_html == set(layout.slots), f"{composicao}: slots do HTML != manifesto"
        assert html.count("</style>") == 1, f"{composicao}: precisa de um único <style>"
        assert "{{FONTES}}" in html


def test_toda_composicao_nova_do_enum_tem_layout_e_vice_versa() -> None:
    layouts = familias.carregar_layouts()
    do_enum = {c for c in ComposicaoCarrossel if familias.familia_da_composicao(c) is not FamiliaVisual.SUNO_ESCURO}
    assert set(layouts) == do_enum


def test_a_familia_explicativo_cobre_os_quatro_papeis() -> None:
    layouts = {
        c: layout for c, layout in familias.carregar_layouts().items() if layout.familia is FamiliaVisual.EXPLICATIVO
    }
    papeis = set().union(*(layout.papeis for layout in layouts.values()))
    assert papeis == set(TipoSlide)
    assert {c.value for c in layouts} == {
        "explicativo_capa",
        "explicativo_texto_imagem",
        "explicativo_texto",
        "explicativo_texto_ilustracao",
    }


# ---------------------------------------------------------------------------
# Render com o texto real do Gerador (execução copom-281, 12/10)
# ---------------------------------------------------------------------------

requer_navegador = pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)


def _slides_reais() -> list[Slide]:
    """Textos no tamanho que o Gerador produz: título mediano de 35 caracteres, corpo de 150."""
    return [
        Slide(
            tipo=TipoSlide.HOOK,
            titulo="Juros em 13,75% a.a.: qual o próximo passo?",
            corpo="A 281ª reunião do Copom trouxe ajustes na Selic. O mercado observa a inflação.",
            destaque="próximo passo",
        ),
        Slide(
            tipo=TipoSlide.PONTO,
            titulo="A decisão da 281ª reunião",
            corpo=(
                "O Copom (o grupo que decide os juros) definiu a Selic (o juro básico da economia) "
                "em 13,75% a.a. Isso guia todos os outros juros do país."
            ),
            destaque="decisão",
            dado="selic_decidida",
        ),
        Slide(
            tipo=TipoSlide.CITACAO,
            titulo="O cenário atual exige cautela",
            corpo=(
                "O Comitê destaca que a incerteza (a falta de clareza sobre o futuro) segue alta. "
                "Por isso, a política monetária precisa ser firme."
            ),
        ),
        Slide(
            tipo=TipoSlide.CTA,
            titulo="Leia a Ata completa",
            corpo="Veja o documento no site do Banco Central.",
        ),
    ]


@requer_navegador
@pytest.mark.parametrize(
    "composicao",
    [
        ComposicaoCarrossel.EXPLICATIVO_CAPA,
        ComposicaoCarrossel.EXPLICATIVO_TEXTO_IMAGEM,
        ComposicaoCarrossel.EXPLICATIVO_TEXTO,
        ComposicaoCarrossel.EXPLICATIVO_TEXTO_ILUSTRACAO,
    ],
)
def test_layout_explicativo_renderiza_1080x1350_sem_defeito(
    composicao: ComposicaoCarrossel, tmp_path: Path, ancoras  # noqa: F811
) -> None:
    from suno.dominio import EscolhaDeLayout

    slides = _slides_reais()
    plano = tuple(
        EscolhaDeLayout(indice=i, composicao=composicao, pontuacao=0) for i, _ in enumerate(slides)
    )
    caminhos = carrossel_html.renderizar(
        slides, Audiencia.INICIANTE, ancoras, tmp_path, plano_direcao=plano
    )
    imagens = []
    for i, caminho in enumerate(caminhos):
        with Image.open(caminho) as aberta:
            assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
        imagens.append(ImagemSlide(indice=i, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE))
    defeitos = [m for m in conferir_imagens(imagens, ancoras).medicoes if m.defeito is not None]
    assert defeitos == [], defeitos


@requer_navegador
def test_texto_longo_encolhe_ate_caber_em_vez_de_estourar(tmp_path: Path, ancoras) -> None:  # noqa: F811
    from suno.dominio import EscolhaDeLayout

    longo = Slide(
        tipo=TipoSlide.PONTO,
        titulo="Por que a decisão de juros do Banco Central muda o custo do crédito para as famílias",
        corpo=" ".join(["O Comitê avalia o balanço de riscos com cautela e serenidade."] * 5),
    )
    plano = (
        EscolhaDeLayout(indice=0, composicao=ComposicaoCarrossel.EXPLICATIVO_TEXTO, pontuacao=0),
    )
    [caminho] = carrossel_html.renderizar(
        [longo], Audiencia.INICIANTE, ancoras, tmp_path, plano_direcao=plano
    )
    imagem = ImagemSlide(indice=0, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE)
    medicoes = conferir_imagens([imagem], ancoras).medicoes
    assert [m for m in medicoes if m.defeito is not None] == []
