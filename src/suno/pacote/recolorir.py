"""Recolore um Layout de família visual com a paleta escolhida no editor.

As famílias foram recriadas dos posts reais da Suno com as cores escritas no HTML. Para trocar a
paleta sem reescrever cada template, cada cor do CSS vira um papel pelo que ela é, não pelo valor:

- **neutra** (branco, cinza, preto) desliza entre o ``fundo`` e o ``texto`` da paleta conforme a
  distância dela até o fundo do Layout (``data-fundo-cor``). O fundo vira fundo, o texto vira texto,
  e a hierarquia dos cinzas se mantém. Num Layout claro o branco é fundo; num escuro, o preto.
- **com cor** (o vermelho da Suno, o verde do botão) vira ``destaque`` quando é viva e ``apoio``
  quando é escura; um tom pastel fica entre o destaque e o fundo.

Só cores de CSS mudam: dentro de ``<style>`` e dos atributos de estilo e de SVG. O texto do slide e
as fotos ficam como estão. Sem paleta, ou num documento sem fundo declarado, o HTML sai igual.
"""

from __future__ import annotations

import base64
import mimetypes
import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from suno.dominio import PaletaVisual

Rgb = tuple[float, float, float]

_FUNDO_DECLARADO = re.compile(r'data-fundo-cor="(#[0-9a-fA-F]{3,8})"')
_BLOCO_DE_ESTILO = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.DOTALL | re.IGNORECASE)
_ATRIBUTO_DE_COR = re.compile(
    r'(\s(?:style|fill|stroke|stop-color|flood-color|lighting-color|color)=")([^"]*)(")',
    re.IGNORECASE,
)
# A cor não pode vir logo depois de ``url(``: ``url(#abc)`` é referência a um id do SVG.
_COR = re.compile(
    r"(?<!url\()#(?P<hex>[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
    r"|rgba?\(\s*(?P<r>\d+)\s*,\s*(?P<g>\d+)\s*,\s*(?P<b>\d+)\s*(?:,\s*(?P<a>[\d.]+%?)\s*)?\)",
    re.IGNORECASE,
)

CROMA_NEUTRO = 0.12
"""Abaixo desta diferença entre o maior e o menor canal, a cor conta como cinza."""


def _rgb(hexadecimal: str) -> Rgb:
    valor = hexadecimal.lstrip("#")
    if len(valor) == 3:
        valor = "".join(c * 2 for c in valor)
    return tuple(int(valor[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _hex(cor: Rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in cor)


def _misturar(a: Rgb, b: Rgb, t: float) -> Rgb:
    t = max(0.0, min(1.0, t))
    return tuple(x + (y - x) * t for x, y in zip(a, b))  # type: ignore[return-value]


def _luminancia(cor: Rgb) -> float:
    def canal(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in cor)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


class _Mapa:
    def __init__(self, paleta: PaletaVisual, fundo_do_layout: Rgb) -> None:
        self.fundo = _rgb(paleta.fundo)
        self.texto = _rgb(paleta.texto)
        self.destaque = _rgb(paleta.destaque)
        self.apoio = _rgb(paleta.apoio)
        self.layout_claro = _luminancia(fundo_do_layout) > 0.5

    def _neutra(self, claridade: float) -> Rgb:
        distancia_do_fundo = 1 - claridade if self.layout_claro else claridade
        return _misturar(self.fundo, self.texto, distancia_do_fundo)

    def __call__(self, cor: Rgb) -> Rgb:
        maior, menor = max(cor), min(cor)
        claridade = (maior + menor) / 2
        if maior - menor < CROMA_NEUTRO:
            return self._neutra(claridade)
        if claridade > 0.7:
            return _misturar(self.destaque, self._neutra(claridade), (claridade - 0.7) / 0.3)
        return _misturar(self.apoio, self.destaque, (claridade - 0.15) / 0.2)


def _trocar_cores(texto: str, mapa: _Mapa) -> str:
    def trocar(achado: re.Match[str]) -> str:
        if achado["hex"]:
            original = achado["hex"]
            alfa = original[6:] if len(original) == 8 else ""
            return _hex(mapa(_rgb(original[:6] if len(original) == 8 else original))) + alfa
        nova = mapa((int(achado["r"]) / 255, int(achado["g"]) / 255, int(achado["b"]) / 255))
        r, g, b = (round(c * 255) for c in nova)
        if achado["a"] is None:
            return f"rgb({r},{g},{b})"
        alfa = achado["a"]
        alfa = alfa if alfa.endswith("%") else f"{float(alfa):g}"
        return f"rgba({r},{g},{b},{alfa})"

    return _COR.sub(trocar, texto)


def recolorir(html: str, paleta: PaletaVisual | None) -> str:
    """O mesmo documento com as cores de CSS trocadas pelas da paleta (ver o docstring do módulo)."""
    if paleta is None:
        return html
    declarado = _FUNDO_DECLARADO.search(html)
    if declarado is None:
        return html
    mapa = _Mapa(paleta, _rgb(declarado.group(1)))
    html = _BLOCO_DE_ESTILO.sub(
        lambda a: a.group(1) + _trocar_cores(a.group(2), mapa) + a.group(3), html
    )
    return _ATRIBUTO_DE_COR.sub(
        lambda a: a.group(1) + _trocar_cores(a.group(2), mapa) + a.group(3), html
    )


# ---------------------------------------------------------------------------
# Documento autossuficiente, para o navegador do editor
# ---------------------------------------------------------------------------

_ARQUIVO_LOCAL = re.compile(r"file:///[^\"')\s]+")
_TIPOS_EXTRAS = {".woff2": "font/woff2", ".woff": "font/woff", ".webp": "image/webp"}


def _caminho_do_uri(uri: str) -> Path:
    return Path(url2pathname(unquote(urlparse(uri).path)))


def embutir_arquivos(html: str, permitidas: Iterable[Path]) -> str:
    """Troca cada ``file://`` (fontes, foto) por um ``data:`` URI, para o navegador abrir o HTML.

    O render grava os arquivos como ``file://`` porque o Puppeteer roda na mesma máquina. Só entram
    arquivos dentro das pastas ``permitidas``; o resto some do documento.
    """
    raizes = [raiz.resolve() for raiz in permitidas]

    def embutir(achado: re.Match[str]) -> str:
        caminho = _caminho_do_uri(achado.group(0)).resolve()
        if not caminho.is_file() or not any(caminho.is_relative_to(raiz) for raiz in raizes):
            return ""
        tipo = _TIPOS_EXTRAS.get(caminho.suffix.lower()) or mimetypes.guess_type(caminho.name)[0]
        dados = base64.b64encode(caminho.read_bytes()).decode("ascii")
        return f"data:{tipo or 'application/octet-stream'};base64,{dados}"

    return _ARQUIVO_LOCAL.sub(embutir, html)
