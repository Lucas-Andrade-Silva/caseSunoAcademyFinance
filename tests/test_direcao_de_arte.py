"""Biblioteca de layouts e seleção determinística da direção de arte."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from suno.dominio import Audiencia, ImagemSlide, Slide, TipoSlide
from suno.pacote import carrossel_html
from suno.pacote.direcao_de_arte import (
    CATALOGO_DE_LAYOUTS,
    ComposicaoCarrossel,
    planejar_direcao_de_arte,
    resumir_direcao_renderizada,
)
from suno.pacote.familias import COMPOSICOES_LEGADAS
from suno.pacote.visual import conferir_imagens
from suno.pacote.referencias_visuais import REFERENCIAS_INICIAIS
from tests.test_pacote import ancoras  # noqa: F401 - fixture


def _slides_representativos() -> list[Slide]:
    return [
        Slide(
            tipo=TipoSlide.HOOK,
            titulo="O que mudou agora?",
            corpo="Entenda a decisão em cinco passos.",
        ),
        Slide(
            tipo=TipoSlide.PONTO,
            titulo="O número central",
            corpo="A taxa definida nesta reunião.",
            dado="selic_decidida",
        ),
        Slide(
            tipo=TipoSlide.PONTO,
            titulo="Antes e depois",
            corpo="A taxa anterior e a nova taxa, lado a lado.",
            dado="selic_decidida",
        ),
        Slide(
            tipo=TipoSlide.PONTO,
            titulo="O primeiro efeito",
            corpo=(
                "A decisão altera o custo do dinheiro e muda gradualmente as condições "
                "financeiras para famílias e empresas."
            ),
        ),
        Slide(
            tipo=TipoSlide.CITACAO,
            titulo="O que o comitê sinalizou",
            corpo="O balanço de riscos segue com fatores nos dois sentidos.",
        ),
        Slide(
            tipo=TipoSlide.PONTO,
            titulo="Decisão unânime",
            corpo="O placar confirmou consenso.",
            dado="placar_votacao",
        ),
        Slide(
            tipo=TipoSlide.CTA,
            titulo="Continue acompanhando",
            corpo="Leia a Ata completa.",
        ),
    ]


def test_catalogo_cobre_todas_as_composicoes_e_cada_uma_tem_template() -> None:
    assert set(CATALOGO_DE_LAYOUTS) == set(ComposicaoCarrossel)
    for layout in CATALOGO_DE_LAYOUTS.values():
        assert (carrossel_html.PASTA_DOS_TEMPLATES / layout.arquivo).is_file()


def test_plano_considera_conteudo_e_usa_as_seis_composicoes() -> None:
    plano = planejar_direcao_de_arte(_slides_representativos())
    composicoes = [escolha.composicao for escolha in plano]

    assert composicoes[0] is ComposicaoCarrossel.EDITORIAL
    assert composicoes[1] is ComposicaoCarrossel.ESTATISTICO
    assert composicoes[2] is ComposicaoCarrossel.COMPARATIVO
    assert set(composicoes) == COMPOSICOES_LEGADAS
    assert all(atual is not anterior for anterior, atual in zip(composicoes, composicoes[1:]))


def test_historico_recente_penaliza_repeticao() -> None:
    slide = _slides_representativos()[0]
    sem_historico = planejar_direcao_de_arte([slide])[0]
    com_historico = planejar_direcao_de_arte(
        [slide], historico_recente=[ComposicaoCarrossel.EDITORIAL]
    )[0]

    assert sem_historico.composicao is ComposicaoCarrossel.EDITORIAL
    assert com_historico.composicao is not sem_historico.composicao


def test_cta_com_dado_pode_encerrar_com_layout_estatistico() -> None:
    slide = Slide(
        tipo=TipoSlide.CTA,
        titulo="Acompanhe a decisão",
        corpo="Consulte a ata completa.",
        dado="selic_decidida",
    )

    escolha = planejar_direcao_de_arte([slide])[0]

    assert escolha.composicao is ComposicaoCarrossel.ESTATISTICO


def test_referencia_escolhida_orienta_sem_congelar_o_layout() -> None:
    referencia = next(
        item
        for item in REFERENCIAS_INICIAIS
        if item.composicao is ComposicaoCarrossel.MINIMALISTA
    )

    plano = planejar_direcao_de_arte(
        _slides_representativos(),
        referencias_aprovadas=REFERENCIAS_INICIAIS,
        referencia_preferida=referencia,
    )

    composicoes = [item.composicao for item in plano]
    assert ComposicaoCarrossel.MINIMALISTA in composicoes
    assert len(set(composicoes)) > 1
    assert all(atual is not anterior for anterior, atual in zip(composicoes, composicoes[1:]))
    escolhidas = [
        item
        for item in plano
        if item.composicao is ComposicaoCarrossel.MINIMALISTA
    ]
    assert {item.referencia_visual for item in escolhidas} == {referencia.identificador}
    assert all(
        any("linguagem visual escolhida" in motivo for motivo in item.motivos)
        for item in escolhidas
    )


@pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)
def test_as_seis_composicoes_renderizam_sem_defeito(tmp_path: Path, ancoras) -> None:  # noqa: F811
    caminhos = carrossel_html.renderizar(
        _slides_representativos(),
        Audiencia.INICIANTE,
        ancoras,
        tmp_path,
        referencias_aprovadas=REFERENCIAS_INICIAIS,
    )
    manifestos = [
        json.loads(caminho.with_suffix(".json").read_text(encoding="utf-8"))
        for caminho in caminhos
    ]
    imagens = [
        ImagemSlide(indice=i, caminho=caminho, largura=1080, altura=1350)
        for i, caminho in enumerate(caminhos)
    ]

    assert {item["layout"] for item in manifestos} == {
        composicao.value for composicao in COMPOSICOES_LEGADAS
    }
    assert all(item["direcao_de_arte"]["motivos"] for item in manifestos)
    assert all(item["direcao_de_arte"]["referencia_visual"] for item in manifestos)
    assert conferir_imagens(imagens, ancoras).defeitos == []
    resumo = resumir_direcao_renderizada(
        [caminho.with_suffix(".json") for caminho in caminhos],
        [ComposicaoCarrossel.EDITORIAL],
    )
    assert resumo is not None
    assert sum(resumo.distribuicao.values()) == len(caminhos)
    assert resumo.repeticoes_consecutivas == 0
    assert resumo.historico_considerado == [ComposicaoCarrossel.EDITORIAL]
    assert all(escolha.referencia_visual for escolha in resumo.escolhas)
