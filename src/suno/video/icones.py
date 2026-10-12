"""Os ícones do catálogo, desenhados em Pillow com formas simples.

Cada ícone cabe num quadrado de lado ``tamanho`` centrado em ``(cx, cy)`` e usa uma cor só, o
traço do design system. Nenhum arquivo de imagem é versionado: um ícone novo é uma função nova
aqui e um nome novo em ``IconeDeCena``.
"""

from __future__ import annotations

from typing import Callable

from PIL import ImageDraw

from suno.dominio import IconeDeCena
from suno.pacote.carrossel import LETRA_FORTE, tipografia

Desenhista = Callable[[ImageDraw.ImageDraw, float, float, float, str, int], None]


def _p(cx: float, cy: float, s: float, x: float, y: float) -> tuple[float, float]:
    """Ponto em coordenadas do ícone (-0.5 a 0.5) para o quadro."""
    return (cx + x * s, cy + y * s)


def _linha(d, cx, cy, s, cor, larg, *pontos) -> None:
    d.line([_p(cx, cy, s, x, y) for x, y in pontos], fill=cor, width=larg, joint="curve")


def _contorno_circulo(d, cx, cy, s, cor, larg, raio=0.46) -> None:
    caixa = [_p(cx, cy, s, -raio, -raio), _p(cx, cy, s, raio, raio)]
    d.ellipse([caixa[0], caixa[1]], outline=cor, width=larg)


def _seta(d, cx, cy, s, cor, larg, x0, y0, x1, y1) -> None:
    """Linha de (x0,y0) a (x1,y1) com ponta em (x1,y1)."""
    _linha(d, cx, cy, s, cor, larg, (x0, y0), (x1, y1))
    ponta = 0.14
    dx, dy = x1 - x0, y1 - y0
    norma = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / norma, dy / norma
    for sinal in (-1, 1):
        px = x1 - ponta * ux + sinal * ponta * 0.6 * -uy
        py = y1 - ponta * uy + sinal * ponta * 0.6 * ux
        _linha(d, cx, cy, s, cor, larg, (x1, y1), (px, py))


def _juros(d, cx, cy, s, cor, larg) -> None:
    for x, y in ((-0.22, -0.22), (0.22, 0.22)):
        caixa = [_p(cx, cy, s, x - 0.12, y - 0.12), _p(cx, cy, s, x + 0.12, y + 0.12)]
        d.ellipse(caixa, outline=cor, width=larg)
    _linha(d, cx, cy, s, cor, larg, (0.3, -0.4), (-0.3, 0.4))


def _inflacao(d, cx, cy, s, cor, larg) -> None:
    _contorno_circulo(d, cx, cy, s, cor, larg)
    _seta(d, cx, cy, s, cor, larg, 0.0, 0.25, 0.0, -0.25)


def _grafico(d, cx, cy, s, cor, larg, pontos) -> None:
    _linha(d, cx, cy, s, cor, larg, (-0.42, -0.42), (-0.42, 0.42), (0.42, 0.42))
    _linha(d, cx, cy, s, cor, larg, *pontos)
    (xa, ya), (xb, yb) = pontos[-2], pontos[-1]
    _seta(d, cx, cy, s, cor, larg, xa, ya, xb, yb)


def _grafico_alta(d, cx, cy, s, cor, larg) -> None:
    _grafico(d, cx, cy, s, cor, larg, [(-0.3, 0.25), (-0.05, 0.0), (0.1, 0.1), (0.38, -0.3)])


def _grafico_queda(d, cx, cy, s, cor, larg) -> None:
    _grafico(d, cx, cy, s, cor, larg, [(-0.3, -0.3), (-0.05, -0.05), (0.1, -0.12), (0.38, 0.28)])


def _grafico_estavel(d, cx, cy, s, cor, larg) -> None:
    _grafico(d, cx, cy, s, cor, larg, [(-0.3, 0.0), (-0.05, -0.05), (0.1, 0.03), (0.38, 0.0)])


def _calendario(d, cx, cy, s, cor, larg) -> None:
    d.rounded_rectangle(
        [_p(cx, cy, s, -0.42, -0.34), _p(cx, cy, s, 0.42, 0.44)], radius=int(s * 0.06), outline=cor, width=larg
    )
    _linha(d, cx, cy, s, cor, larg, (-0.42, -0.14), (0.42, -0.14))
    for x in (-0.22, 0.22):
        _linha(d, cx, cy, s, cor, larg, (x, -0.46), (x, -0.26))
    for x in (-0.22, 0.0, 0.22):
        for y in (0.05, 0.27):
            d.ellipse([_p(cx, cy, s, x - 0.03, y - 0.03), _p(cx, cy, s, x + 0.03, y + 0.03)], fill=cor)


def _banco(d, cx, cy, s, cor, larg) -> None:
    d.polygon([_p(cx, cy, s, 0, -0.44), _p(cx, cy, s, 0.46, -0.2), _p(cx, cy, s, -0.46, -0.2)], outline=cor, width=larg)
    for x in (-0.3, -0.1, 0.1, 0.3):
        _linha(d, cx, cy, s, cor, larg, (x, -0.1), (x, 0.3))
    _linha(d, cx, cy, s, cor, larg, (-0.46, 0.4), (0.46, 0.4))


def _bolso(d, cx, cy, s, cor, larg) -> None:
    d.rounded_rectangle(
        [_p(cx, cy, s, -0.44, -0.28), _p(cx, cy, s, 0.44, 0.36)], radius=int(s * 0.08), outline=cor, width=larg
    )
    _linha(d, cx, cy, s, cor, larg, (-0.34, -0.28), (0.1, -0.42), (0.3, -0.28))
    d.ellipse([_p(cx, cy, s, 0.2, 0.0), _p(cx, cy, s, 0.34, 0.14)], fill=cor)


def _alerta(d, cx, cy, s, cor, larg) -> None:
    d.polygon([_p(cx, cy, s, 0, -0.44), _p(cx, cy, s, 0.46, 0.38), _p(cx, cy, s, -0.46, 0.38)], outline=cor, width=larg)
    _linha(d, cx, cy, s, cor, larg, (0, -0.14), (0, 0.14))
    d.ellipse([_p(cx, cy, s, -0.03, 0.22), _p(cx, cy, s, 0.03, 0.28)], fill=cor)


def _lupa(d, cx, cy, s, cor, larg) -> None:
    d.ellipse([_p(cx, cy, s, -0.4, -0.4), _p(cx, cy, s, 0.14, 0.14)], outline=cor, width=larg)
    _linha(d, cx, cy, s, cor, larg, (0.1, 0.1), (0.42, 0.42))


def _documento(d, cx, cy, s, cor, larg) -> None:
    _linha(
        d, cx, cy, s, cor, larg,
        (-0.3, -0.44), (0.1, -0.44), (0.3, -0.24), (0.3, 0.44), (-0.3, 0.44), (-0.3, -0.44),
    )
    _linha(d, cx, cy, s, cor, larg, (0.1, -0.44), (0.1, -0.24), (0.3, -0.24))
    for y in (-0.05, 0.12, 0.29):
        _linha(d, cx, cy, s, cor, larg, (-0.17, y), (0.17, y))


def _balanca(d, cx, cy, s, cor, larg) -> None:
    _linha(d, cx, cy, s, cor, larg, (0, -0.42), (0, 0.4))
    _linha(d, cx, cy, s, cor, larg, (-0.3, 0.42), (0.3, 0.42))
    _linha(d, cx, cy, s, cor, larg, (-0.42, -0.26), (0.42, -0.26))
    for x in (-0.42, 0.42):
        _linha(d, cx, cy, s, cor, larg, (x, -0.26), (x - 0.16, 0.1), (x + 0.16, 0.1), (x, -0.26))


def _relogio(d, cx, cy, s, cor, larg) -> None:
    _contorno_circulo(d, cx, cy, s, cor, larg)
    _linha(d, cx, cy, s, cor, larg, (0, 0), (0, -0.28))
    _linha(d, cx, cy, s, cor, larg, (0, 0), (0.2, 0.1))


def _pergunta(d, cx, cy, s, cor, larg) -> None:
    _contorno_circulo(d, cx, cy, s, cor, larg)
    letra = tipografia(LETRA_FORTE, int(s * 0.62))
    d.text((cx, cy), "?", font=letra, fill=cor, anchor="mm")


def _check(d, cx, cy, s, cor, larg) -> None:
    _contorno_circulo(d, cx, cy, s, cor, larg)
    _linha(d, cx, cy, s, cor, larg, (-0.22, 0.02), (-0.06, 0.2), (0.24, -0.16))


DESENHOS: dict[IconeDeCena, Desenhista] = {
    IconeDeCena.JUROS: _juros,
    IconeDeCena.INFLACAO: _inflacao,
    IconeDeCena.GRAFICO_ALTA: _grafico_alta,
    IconeDeCena.GRAFICO_QUEDA: _grafico_queda,
    IconeDeCena.GRAFICO_ESTAVEL: _grafico_estavel,
    IconeDeCena.CALENDARIO: _calendario,
    IconeDeCena.BANCO: _banco,
    IconeDeCena.BOLSO: _bolso,
    IconeDeCena.ALERTA: _alerta,
    IconeDeCena.LUPA: _lupa,
    IconeDeCena.DOCUMENTO: _documento,
    IconeDeCena.BALANCA: _balanca,
    IconeDeCena.RELOGIO: _relogio,
    IconeDeCena.PERGUNTA: _pergunta,
    IconeDeCena.CHECK: _check,
}


def desenhar_icone(
    desenho: ImageDraw.ImageDraw, icone: IconeDeCena, cx: float, cy: float, tamanho: float, cor: str
) -> None:
    """Desenha ``icone`` centrado em ``(cx, cy)``, num quadrado de lado ``tamanho``."""
    traco = max(3, round(tamanho / 16))
    DESENHOS[icone](desenho, cx, cy, tamanho, cor, traco)
