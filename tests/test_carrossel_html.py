"""O render por templates HTML + Puppeteer (ADR 0020). Pula sem Node/Puppeteer instalado."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from suno.dominio import (
    ALTURA_SLIDE,
    LARGURA_SLIDE,
    Audiencia,
    Celula,
    Conteudo,
    Formato,
    ImagemSlide,
    Slide,
    TipoSlide,
)
from suno.pacote import carrossel_html
from suno.pacote.visual import conferir_imagens
from tests.test_pacote import ancoras  # noqa: F401 - fixture

pytestmark = pytest.mark.skipif(
    not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado (npm install em render/)"
)


def _slides() -> list[Slide]:
    return [
        Slide(tipo=TipoSlide.HOOK, titulo="O Copom mexeu na Selic. E agora?", corpo="Veja em 4 passos.", destaque="Selic"),
        Slide(tipo=TipoSlide.PONTO, titulo="A decisão em números", corpo="Antes e depois.", dado="selic_decidida"),
        Slide(tipo=TipoSlide.CITACAO, titulo="O que a Ata diz", corpo="O comitê vê riscos nos dois sentidos."),
        Slide(tipo=TipoSlide.CTA, titulo="Quer ir além?", corpo="Leia a Ata completa."),
    ]


def test_comparacao_respeita_conector_sem_cortar_uma_ideia_ao_meio() -> None:
    texto = (
        "A demanda apresenta uma desaceleração gradual em setores cíclicos, conquanto "
        "o mercado de trabalho ainda apresente resiliência."
    )

    esquerda, direita = carrossel_html._partes_da_comparacao(texto)

    assert esquerda == "A demanda apresenta uma desaceleração gradual em setores cíclicos"
    assert direita == "Conquanto o mercado de trabalho ainda apresente resiliência."


def test_cada_tipo_vira_png_1080x1350_sem_defeito(tmp_path: Path, ancoras) -> None:  # noqa: F811
    caminhos = carrossel_html.renderizar(_slides(), Audiencia.INICIANTE, ancoras, tmp_path)
    assert len(caminhos) == 4
    for caminho in caminhos:
        with Image.open(caminho) as aberta:
            assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
    imagens = [
        ImagemSlide(indice=i, caminho=c, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE)
        for i, c in enumerate(caminhos)
    ]
    defeitos = [m for m in conferir_imagens(imagens, ancoras).medicoes if m.defeito is not None]
    assert defeitos == []


def test_titulo_enorme_estoura_a_caixa(tmp_path: Path, ancoras) -> None:  # noqa: F811
    slide = Slide(tipo=TipoSlide.PONTO, titulo="palavra " * 120, corpo="x")
    (caminho,) = carrossel_html.renderizar([slide], Audiencia.AVANCADO, ancoras, tmp_path)
    imagem = ImagemSlide(indice=0, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE)
    defeitos = [m.defeito for m in conferir_imagens([imagem], ancoras).medicoes if m.defeito]
    assert defeitos, "o texto estourou e a conferência precisa ver"
