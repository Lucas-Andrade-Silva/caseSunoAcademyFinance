"""A foto de cada slide do Carrossel: resolvida antes do plano de arte e do render.

O Gerador sugere só o assunto (``Slide.imagem``). Aqui esse assunto vira um arquivo real, com
o crédito que a acompanha (``suno.imagens``). A demo roda sem rede:
por padrão só a biblioteca local, em ``data/imagens/``, é consultada; ir à busca de imagens na web é
decisão explícita (``permitir_rede``) e exige validação de relevância por visão.

Slide sem assunto, ou com assunto sem foto aprovada, fica sem foto: o plano de arte escolhe, para
ele, um layout que não precisa de imagem. E foto achada que o plano não consegue usar no slide
que a pediu (um slide de gráfico, o CTA) é realocada para outro slide que comporte foto
(``acomodar_fotos``); se nenhum comportar, a foto é descartada, e com ela o crédito na legenda.
Nada quebra e nenhuma foto é inventada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Protocol

import httpx

from suno.dominio import FamiliaVisual, Slide
from suno.imagens import BibliotecaDeImagens, ImagemResolvida, resolver_imagem
from suno.pacote.direcao_de_arte import CATALOGO_DE_LAYOUTS, EscolhaDeLayout, composicoes_compativeis

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


class _ComEscolhas(Protocol):
    escolhas: list[EscolhaDeLayout]


@dataclass
class FotosAcomodadas:
    """O que sobrou do pedido de fotos depois de o plano de arte decidir onde elas cabem."""

    slides: list[Slide]  # os slides do plano: ``imagem`` só onde há foto de fato
    fotos: dict[int, FotoDoSlide]  # índice do slide onde a foto foi desenhada → foto
    plano: _ComEscolhas
    movidas: list[tuple[int, int]] = field(default_factory=list)  # (slide que pediu, slide que recebeu)
    descartadas: list[int] = field(default_factory=list)  # slides que pediram e cuja foto não coube em lugar nenhum


def _layout_usa_foto(escolha: EscolhaDeLayout) -> bool:
    return CATALOGO_DE_LAYOUTS[escolha.composicao].usa_imagem


def _aceita_foto(slide: Slide, familia: FamiliaVisual) -> bool:
    """O slide teria algum layout de foto se recebesse uma? (``imagem`` vazia esconde esses layouts.)"""
    com_foto = slide.model_copy(update={"imagem": slide.imagem or "foto"})
    return any(CATALOGO_DE_LAYOUTS[c].usa_imagem for c in composicoes_compativeis(com_foto, familia))


def acomodar_fotos(
    slides: list[Slide],
    fotos: dict[int, FotoDoSlide],
    familia: FamiliaVisual,
    planejar: Callable[[list[Slide]], _ComEscolhas],
) -> FotosAcomodadas:
    """Garante que toda foto resolvida aparece num slide cujo layout tem espaço para ela.

    O plano só vê ``Slide.imagem`` nos slides com foto. Se mesmo assim ele escolhe, para o slide
    da foto, um layout sem espaço de imagem (slide com gráfico, CTA), a foto vai para o slide
    mais próximo que ainda não tem foto e aceita um layout de foto; o plano é refeito. Sem
    destino, a foto é descartada. Cada foto tenta cada slide no máximo uma vez, então o laço acaba.
    """
    fotos = dict(fotos)
    do_plano = [s if i in fotos else s.model_copy(update={"imagem": None}) for i, s in enumerate(slides)]
    pediu = {i: i for i in fotos}  # slide onde a foto está agora → slide que a pediu
    tentados: dict[int, set[int]] = {i: {i} for i in fotos}  # slide que pediu → destinos já tentados
    movidas: list[tuple[int, int]] = []
    descartadas: list[int] = []

    for _ in range(len(slides) * 2 + 1):
        plano = planejar(do_plano)
        orfas = [i for i in sorted(fotos) if not _layout_usa_foto(plano.escolhas[i])]
        if not orfas:
            return FotosAcomodadas(do_plano, fotos, plano, movidas, descartadas)
        atual = orfas[0]
        origem = pediu[atual]
        destinos = [
            j
            for j in range(len(do_plano))
            if j not in fotos and j not in tentados[origem] and _aceita_foto(do_plano[j], familia)
        ]
        foto = fotos.pop(atual)
        assunto = do_plano[atual].imagem
        do_plano[atual] = do_plano[atual].model_copy(update={"imagem": None})
        del pediu[atual]
        if not destinos:
            descartadas.append(origem)
            continue
        destino = min(destinos, key=lambda j: (abs(j - origem), j))
        tentados[origem].add(destino)
        fotos[destino] = foto
        pediu[destino] = origem
        do_plano[destino] = do_plano[destino].model_copy(update={"imagem": assunto})
        movidas.append((origem, destino))

    # Sem convergir (o plano insiste num layout sem foto): o que sobrou como órfã não é desenhado.
    plano = planejar(do_plano)
    for i in [i for i in sorted(fotos) if not _layout_usa_foto(plano.escolhas[i])]:
        descartadas.append(pediu[i])
        fotos.pop(i)
        do_plano[i] = do_plano[i].model_copy(update={"imagem": None})
    return FotosAcomodadas(do_plano, fotos, planejar(do_plano), movidas, descartadas)


__all__ = ["FotoDoSlide", "FotosAcomodadas", "acomodar_fotos", "biblioteca_padrao", "resolver_fotos"]
