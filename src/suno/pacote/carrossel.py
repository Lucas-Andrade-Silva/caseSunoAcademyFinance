"""Renderização determinística do Carrossel: matplotlib desenha o gráfico a partir das Âncoras
numéricas, Pillow compõe. PNG 1080x1350 em todos os slides.

ADR 0009.

## O que garante o determinismo

Nenhuma data, nenhum aleatório, nenhuma medida que dependa da máquina: as letras são as DejaVu
que o próprio matplotlib embute (nada é baixado), o gráfico sai num ``BytesIO`` pelo backend Agg
com ``metadata={"Software": None}`` e só os pixels são colados. Duas renderizações da mesma Célula
produzem o mesmo PNG.

## O manifesto do render

Ao lado de cada ``slide-<nn>.png`` é gravado um ``slide-<nn>.json`` com as caixas de texto
(retângulo reservado, texto já quebrado, letra, tamanho, cor e cor de fundo) e os números
desenhados (chave da Âncora e a ``citacao()`` que apareceu). É o que ``visual.py`` mede — sem ele
a conferência teria de fazer OCR. ``ImagemSlide`` não muda por causa disso.

O texto é desenhado inteiro mesmo quando não cabe no retângulo reservado: estouro é defeito de
render que o H5 precisa ver (ADR 0014), não algo a esconder encolhendo a letra.
"""

from __future__ import annotations

import io
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image, ImageDraw, ImageFont

from suno.dominio import (
    ALTURA_SLIDE,
    LARGURA_SLIDE,
    AncoraNumerica,
    Ancoras,
    Audiencia,
    Celula,
    ChaveAncora,
    Formato,
    ImagemSlide,
    Slide,
)

# ---------------------------------------------------------------------------
# Identidade visual: fixa, simples, e a mesma nas nove Células
# ---------------------------------------------------------------------------

PASTA_DE_LETRAS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
"""As DejaVu que vêm dentro do matplotlib. Baixar letra é proibido (ADR 0009)."""

LETRA_FORTE = "DejaVuSans-Bold.ttf"
LETRA_COMUM = "DejaVuSans.ttf"

COR_FUNDO = "#0E1420"
COR_TEXTO = "#F2F5FA"
COR_APOIO = "#B9C7DA"
COR_DESTAQUE = "#F0B429"
"""Razões de contraste sobre o fundo: 16,9 · 10,7 · 9,9. Todas acima de CONTRASTE_MINIMO."""

SELO_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "Iniciante",
    Audiencia.INTERMEDIARIO: "Intermediário",
    Audiencia.AVANCADO: "Avançado",
}
"""A Audiência muda só o selo de canto; o resto do template é idêntico."""

MARGEM = 84
LARGURA_UTIL = LARGURA_SLIDE - 2 * MARGEM

TAMANHO_SELO = 30
TAMANHO_TITULO = 62
TAMANHO_CORPO = 38
TAMANHO_RODAPE = 28

ENTRELINHA_TITULO = 16
ENTRELINHA_CORPO = 14

LINHAS_DO_TITULO = 3
LINHAS_DO_CORPO_COM_GRAFICO = 4
LINHAS_DO_CORPO_SEM_GRAFICO = 9

Y_SELO = 70
Y_TITULO = 190
Y_CORPO = 490
Y_GRAFICO = 750
ALTURA_GRAFICO = 420
Y_RODAPE = 1240

RECUO_DO_SELO = 24
RECUO_VERTICAL_DO_SELO = 14

COLUNAS_DA_FOLHA = 3
LARGURA_DA_MINIATURA = 360
MARGEM_DA_FOLHA = 24

# Uma superfície de 1x1 só para medir texto: ``ImageDraw.textbbox`` precisa de um desenho.
_REGUA_DE_TEXTO = ImageDraw.Draw(Image.new("RGB", (1, 1)))


@lru_cache(maxsize=32)
def tipografia(nome: str, tamanho: int) -> ImageFont.FreeTypeFont:
    """A letra pelo nome do arquivo DejaVu (ou por caminho absoluto, vindo do manifesto)."""
    caminho = Path(nome)
    if not caminho.is_absolute():
        caminho = PASTA_DE_LETRAS / nome
    return ImageFont.truetype(str(caminho), tamanho)


def medir_largura(texto: str, letra: ImageFont.FreeTypeFont) -> int:
    """Largura em pixels de uma linha, pelo ``textbbox`` — a mesma medida que a conferência usa."""
    return int(math.ceil(_REGUA_DE_TEXTO.textbbox((0, 0), texto, font=letra)[2]))


def altura_da_linha(letra: ImageFont.FreeTypeFont) -> int:
    """Subida + descida: o passo vertical entre duas linhas, sem a entrelinha."""
    subida, descida = letra.getmetrics()
    return subida + descida


def altura_reservada(letra: ImageFont.FreeTypeFont, linhas: int, entrelinha: int) -> int:
    return linhas * altura_da_linha(letra) + max(linhas - 1, 0) * entrelinha


def quebrar_linhas(texto: str, letra: ImageFont.FreeTypeFont, largura_maxima: int) -> list[str]:
    """Quebra por largura medida. Palavra maior que a caixa fica sozinha e estoura — de propósito."""
    quebradas: list[str] = []
    for paragrafo in texto.splitlines() or [""]:
        palavras = paragrafo.split()
        if not palavras:
            continue
        atual = palavras[0]
        for palavra in palavras[1:]:
            tentativa = f"{atual} {palavra}"
            if medir_largura(tentativa, letra) > largura_maxima:
                quebradas.append(atual)
                atual = palavra
            else:
                atual = tentativa
        quebradas.append(atual)
    return quebradas or [""]


# ---------------------------------------------------------------------------
# As caixas de texto
# ---------------------------------------------------------------------------


def _escrever_caixa(
    desenho: ImageDraw.ImageDraw,
    *,
    nome: str,
    texto: str,
    letra_nome: str,
    tamanho: int,
    cor: str,
    cor_atras: str,
    x: int,
    y: int,
    largura: int,
    linhas_reservadas: int,
    entrelinha: int,
    centralizado: bool = False,
) -> dict[str, Any]:
    """Desenha o texto quebrado e devolve o registro dele para o manifesto do render."""
    letra = tipografia(letra_nome, tamanho)
    linhas = quebrar_linhas(texto, letra, largura)
    passo = altura_da_linha(letra) + entrelinha
    for ordem, linha in enumerate(linhas):
        posicao_x = x
        if centralizado:
            posicao_x = x + (largura - medir_largura(linha, letra)) // 2
        desenho.text((posicao_x, y + ordem * passo), linha, font=letra, fill=cor)
    return {
        "nome": nome,
        "retangulo": [x, y, x + largura, y + altura_reservada(letra, linhas_reservadas, entrelinha)],
        "texto": "\n".join(linhas),
        "fonte": letra_nome,
        "tamanho": tamanho,
        "entrelinha": entrelinha,
        "cor": cor,
        "cor_fundo": cor_atras,
    }


def _escrever_selo(desenho: ImageDraw.ImageDraw, audiencia: Audiencia) -> dict[str, Any]:
    """O selo de canto: a única coisa que a Audiência muda no template."""
    rotulo = SELO_DA_AUDIENCIA[audiencia]
    letra = tipografia(LETRA_FORTE, TAMANHO_SELO)
    largura = medir_largura(rotulo, letra) + 2 * RECUO_DO_SELO
    altura = altura_da_linha(letra) + 2 * RECUO_VERTICAL_DO_SELO
    desenho.rounded_rectangle(
        [MARGEM, Y_SELO, MARGEM + largura, Y_SELO + altura], radius=12, fill=COR_DESTAQUE
    )
    return _escrever_caixa(
        desenho,
        nome="selo",
        texto=rotulo,
        letra_nome=LETRA_FORTE,
        tamanho=TAMANHO_SELO,
        cor=COR_FUNDO,
        cor_atras=COR_DESTAQUE,
        x=MARGEM + RECUO_DO_SELO,
        y=Y_SELO + RECUO_VERTICAL_DO_SELO,
        largura=largura - 2 * RECUO_DO_SELO,
        linhas_reservadas=1,
        entrelinha=0,
    )


# ---------------------------------------------------------------------------
# O gráfico: matplotlib, a partir das Âncoras numéricas (ADR 0011)
# ---------------------------------------------------------------------------

_CHAVES_DA_SELIC = (ChaveAncora.SELIC_ANTERIOR.value, ChaveAncora.SELIC_DECIDIDA.value)

_AJUSTE_DO_MATPLOTLIB = {
    "font.family": "DejaVu Sans",
    "text.usetex": False,
    "axes.unicode_minus": False,
    "svg.hashsalt": "suno",
}


def _figura_em_imagem(figura: Figure, largura: int, altura: int) -> Image.Image:
    """Agg em memória: nada vai a disco e nada além dos pixels entra no slide."""
    FigureCanvasAgg(figura)
    memoria = io.BytesIO()
    figura.savefig(
        memoria,
        format="png",
        dpi=100,
        facecolor=COR_FUNDO,
        metadata={"Software": None},
    )
    memoria.seek(0)
    with Image.open(memoria) as aberta:
        return aberta.convert("RGB").resize((largura, altura), Image.LANCZOS)


def _barras_antes_e_depois(
    anterior: AncoraNumerica, decidida: AncoraNumerica, largura: int, altura: int
) -> tuple[Image.Image, list[dict[str, str]]]:
    with matplotlib.rc_context(_AJUSTE_DO_MATPLOTLIB):
        figura = Figure(figsize=(largura / 100, altura / 100), dpi=100, facecolor=COR_FUNDO)
        eixo = figura.add_subplot(111)
        eixo.set_facecolor(COR_FUNDO)
        alturas = [float(anterior.valor or 0.0), float(decidida.valor or 0.0)]
        barras = eixo.bar(
            ["Antes", "Depois"], alturas, color=[COR_APOIO, COR_DESTAQUE], width=0.45
        )
        for barra, ancora in zip(barras, (anterior, decidida)):
            eixo.text(
                barra.get_x() + barra.get_width() / 2,
                barra.get_height(),
                ancora.citacao(),
                ha="center",
                va="bottom",
                color=COR_TEXTO,
                fontsize=22,
                fontweight="bold",
            )
        eixo.set_ylim(0, max(alturas) * 1.3 if max(alturas) else 1.0)
        eixo.set_yticks([])
        eixo.tick_params(axis="x", colors=COR_TEXTO, labelsize=20, length=0)
        for lado in eixo.spines.values():
            lado.set_visible(False)
        figura.subplots_adjust(left=0.06, right=0.94, top=0.94, bottom=0.14)
        imagem = _figura_em_imagem(figura, largura, altura)
    numeros = [
        {"chave": anterior.chave, "texto": anterior.citacao()},
        {"chave": decidida.chave, "texto": decidida.citacao()},
    ]
    return imagem, numeros


def _numero_grande(
    ancora: AncoraNumerica, largura: int, altura: int
) -> tuple[Image.Image, list[dict[str, str]]]:
    with matplotlib.rc_context(_AJUSTE_DO_MATPLOTLIB):
        figura = Figure(figsize=(largura / 100, altura / 100), dpi=100, facecolor=COR_FUNDO)
        eixo = figura.add_subplot(111)
        eixo.set_facecolor(COR_FUNDO)
        eixo.axis("off")
        eixo.text(
            0.5,
            0.60,
            ancora.citacao(),
            ha="center",
            va="center",
            color=COR_DESTAQUE,
            fontsize=76,
            fontweight="bold",
            transform=eixo.transAxes,
        )
        eixo.text(
            0.5,
            0.28,
            ancora.rotulo,
            ha="center",
            va="center",
            color=COR_TEXTO,
            fontsize=26,
            transform=eixo.transAxes,
        )
        imagem = _figura_em_imagem(figura, largura, altura)
    return imagem, [{"chave": ancora.chave, "texto": ancora.citacao()}]


def _grafico_do_slide(
    chave: str, ancoras: Ancoras, largura: int, altura: int
) -> tuple[Image.Image, list[dict[str, str]]] | None:
    """Barras quando a chave é uma das duas Selic e as duas existem; senão, número grande.

    Devolve ``None`` quando a chave declarada no Slide não tem Âncora: melhor um slide sem
    gráfico do que um número inventado (ADR 0011).
    """
    ancora = ancoras.numerica(chave)
    if ancora is None:
        return None
    anterior = ancoras.numerica(ChaveAncora.SELIC_ANTERIOR.value)
    decidida = ancoras.numerica(ChaveAncora.SELIC_DECIDIDA.value)
    sao_comparaveis = (
        chave in _CHAVES_DA_SELIC
        and anterior is not None
        and decidida is not None
        and anterior.valor is not None
        and decidida.valor is not None
    )
    if sao_comparaveis:
        assert anterior is not None and decidida is not None  # já checado acima
        return _barras_antes_e_depois(anterior, decidida, largura, altura)
    return _numero_grande(ancora, largura, altura)


# ---------------------------------------------------------------------------
# O slide inteiro
# ---------------------------------------------------------------------------


def _desenhar_slide(
    slide: Slide, audiencia: Audiencia, indice: int, total: int, ancoras: Ancoras
) -> tuple[Image.Image, dict[str, Any]]:
    imagem = Image.new("RGB", (LARGURA_SLIDE, ALTURA_SLIDE), COR_FUNDO)
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle([0, 0, LARGURA_SLIDE, 10], fill=COR_DESTAQUE)

    caixas = [_escrever_selo(desenho, audiencia)]
    caixas.append(
        _escrever_caixa(
            desenho,
            nome="titulo",
            texto=slide.titulo,
            letra_nome=LETRA_FORTE,
            tamanho=TAMANHO_TITULO,
            cor=COR_TEXTO,
            cor_atras=COR_FUNDO,
            x=MARGEM,
            y=Y_TITULO,
            largura=LARGURA_UTIL,
            linhas_reservadas=LINHAS_DO_TITULO,
            entrelinha=ENTRELINHA_TITULO,
        )
    )

    numeros: list[dict[str, str]] = []
    grafico = _grafico_do_slide(slide.dado, ancoras, LARGURA_UTIL, ALTURA_GRAFICO) if slide.dado else None
    if grafico is not None:
        imagem.paste(grafico[0], (MARGEM, Y_GRAFICO))
        numeros = grafico[1]

    caixas.append(
        _escrever_caixa(
            desenho,
            nome="corpo",
            texto=slide.corpo,
            letra_nome=LETRA_COMUM,
            tamanho=TAMANHO_CORPO,
            cor=COR_APOIO,
            cor_atras=COR_FUNDO,
            x=MARGEM,
            y=Y_CORPO,
            largura=LARGURA_UTIL,
            linhas_reservadas=(
                LINHAS_DO_CORPO_COM_GRAFICO if grafico is not None else LINHAS_DO_CORPO_SEM_GRAFICO
            ),
            entrelinha=ENTRELINHA_CORPO,
        )
    )
    caixas.append(
        _escrever_caixa(
            desenho,
            nome="rodape",
            texto=f"{indice + 1}/{total}",
            letra_nome=LETRA_COMUM,
            tamanho=TAMANHO_RODAPE,
            cor=COR_APOIO,
            cor_atras=COR_FUNDO,
            x=MARGEM,
            y=Y_RODAPE,
            largura=LARGURA_UTIL,
            linhas_reservadas=1,
            entrelinha=0,
            centralizado=True,
        )
    )

    manifesto = {
        "slide": indice + 1,
        "total": total,
        "audiencia": audiencia.value,
        "largura": LARGURA_SLIDE,
        "altura": ALTURA_SLIDE,
        "caixas": caixas,
        "numeros": numeros,
    }
    return imagem, manifesto


def renderizar_carrossel(celula: Celula, ancoras: Ancoras, pasta: Path) -> list[ImagemSlide]:
    """Um PNG 1080x1350 por Slide em ``<pasta>/slide-<nn>.png``, mais o manifesto ao lado.

    ``nn`` começa em 01 e acompanha o "n/total" do rodapé; ``ImagemSlide.indice`` continua
    em base zero, como a posição na lista de Slides.
    """
    if celula.formato is not Formato.CARROSSEL:
        raise ValueError(f"renderizar_carrossel só aceita o Formato Carrossel, não {celula.formato}")
    slides = celula.conteudo.slides or []
    pasta.mkdir(parents=True, exist_ok=True)
    imagens: list[ImagemSlide] = []
    for indice, slide in enumerate(slides):
        imagem, manifesto = _desenhar_slide(slide, celula.audiencia, indice, len(slides), ancoras)
        caminho = pasta / f"slide-{indice + 1:02d}.png"
        imagem.save(caminho, format="PNG")
        caminho.with_suffix(".json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        imagens.append(
            ImagemSlide(
                indice=indice, caminho=caminho, largura=LARGURA_SLIDE, altura=ALTURA_SLIDE
            )
        )
    return imagens


def folha_de_contato(imagens: list[ImagemSlide], destino: Path) -> Path:
    """Todos os slides da Célula numa imagem só, em três colunas (ADR 0014).

    É o que vai ao juiz de visão — três chamadas por Ata em vez de dezoito — e o que o H5 olha
    primeiro, porque inconsistência entre slides só aparece quando eles estão lado a lado.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    quantidade = max(len(imagens), 1)
    fileiras = math.ceil(quantidade / COLUNAS_DA_FOLHA)
    altura_da_miniatura = round(LARGURA_DA_MINIATURA * ALTURA_SLIDE / LARGURA_SLIDE)

    largura = COLUNAS_DA_FOLHA * LARGURA_DA_MINIATURA + (COLUNAS_DA_FOLHA + 1) * MARGEM_DA_FOLHA
    altura = fileiras * altura_da_miniatura + (fileiras + 1) * MARGEM_DA_FOLHA
    folha = Image.new("RGB", (largura, altura), COR_FUNDO)

    for ordem, imagem_slide in enumerate(imagens):
        with Image.open(imagem_slide.caminho) as aberta:
            proporcional = aberta.convert("RGB")
            nova_altura = round(LARGURA_DA_MINIATURA * proporcional.height / proporcional.width)
            miniatura = proporcional.resize((LARGURA_DA_MINIATURA, nova_altura), Image.LANCZOS)
        coluna = ordem % COLUNAS_DA_FOLHA
        fileira = ordem // COLUNAS_DA_FOLHA
        folha.paste(
            miniatura,
            (
                MARGEM_DA_FOLHA + coluna * (LARGURA_DA_MINIATURA + MARGEM_DA_FOLHA),
                MARGEM_DA_FOLHA + fileira * (altura_da_miniatura + MARGEM_DA_FOLHA),
            ),
        )
    folha.save(destino, format="PNG")
    return destino
