"""A foto de cada slide do Carrossel: resolvida antes do plano de arte e do render.

O Gerador sugere só o assunto (``Slide.imagem``). Aqui esse assunto vira um arquivo real, com
licença que permite reuso e o crédito que a acompanha (``suno.imagens``). A demo roda sem rede:
por padrão só a biblioteca local, em ``data/imagens/``, é consultada; ir ao Wikimedia Commons é
decisão explícita (``permitir_rede``) e exige validação de relevância por visão.

Slide sem assunto, ou com assunto sem foto aprovada, fica sem foto. O layout da família degrada
sozinho, então nada quebra e nenhuma foto é inventada.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import httpx

from suno.dominio import Slide
from suno.imagens import BibliotecaDeImagens, ImagemResolvida, resolver_imagem

if TYPE_CHECKING:  # pragma: no cover
    from suno.provedores.base import Provedor

PASTA_PADRAO_DAS_FOTOS = Path(__file__).resolve().parents[3] / "data" / "imagens"


@dataclass(frozen=True)
class FotoDoSlide:
    imagem: ImagemResolvida
    caminho: Path  # absoluto, pronto para o render

    def credito(self) -> str:
        return self.imagem.credito()


def biblioteca_padrao() -> BibliotecaDeImagens:
    return BibliotecaDeImagens(PASTA_PADRAO_DAS_FOTOS)


def resolver_fotos(
    slides: Iterable[Slide],
    biblioteca: BibliotecaDeImagens | None = None,
    *,
    permitir_rede: bool = False,
    provedor_visao: Provedor | None = None,
    cliente: httpx.Client | None = None,
) -> dict[int, FotoDoSlide]:
    """Índice do slide → foto. Só entra quem pediu foto e teve uma aprovada."""
    biblioteca = biblioteca or biblioteca_padrao()
    fotos: dict[int, FotoDoSlide] = {}
    usadas: set[str] = set()
    for indice, slide in enumerate(slides):
        assunto = (slide.imagem or "").strip()
        if not assunto:
            continue
        imagem = resolver_imagem(
            assunto,
            biblioteca,
            contexto=slide.titulo,
            permitir_rede=permitir_rede,
            cliente=cliente,
            provedor_visao=provedor_visao,
        )
        if imagem is None:
            continue
        caminho = (biblioteca.pasta / imagem.arquivo).resolve()
        # A mesma foto em dois slides do mesmo carrossel parece erro, não identidade visual.
        if str(caminho) in usadas or not caminho.is_file():
            continue
        usadas.add(str(caminho))
        fotos[indice] = FotoDoSlide(imagem=imagem, caminho=caminho)
    return fotos


__all__ = ["FotoDoSlide", "biblioteca_padrao", "resolver_fotos"]
