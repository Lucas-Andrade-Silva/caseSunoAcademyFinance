"""O bloco de créditos que o chamador anexa à legenda do post."""

from __future__ import annotations

from collections.abc import Sequence

from suno.imagens.modelos import ImagemResolvida


def bloco_de_creditos(imagens: Sequence[ImagemResolvida]) -> str:
    """Uma linha ``Foto: autor / licença / url`` por foto, sem repetir, na ordem de entrada.

    Vazio quando não há foto. Domínio público e CC0 também saem: o crédito é opcional, mas
    custa uma linha e deixa a origem rastreável.
    """
    linhas: dict[str, None] = {}
    for imagem in imagens:
        linhas.setdefault(imagem.credito(), None)
    return "\n".join(linhas)
