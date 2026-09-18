"""O Avaliador: recebe ``(Conteúdo, Âncora[], Audiência)`` e devolve um Laudo (ADR 0001).

Roda sem LLM e sem rede por padrão. As cinco medidas determinísticas vivem em módulos
irmãos; ``laudo.py`` as junta e aplica os Limiares. O comitê de juízes-LLM (ADR 0008) é
uma camada opcional, injetada por quem chama, e nasce desligado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from suno.dominio import Ancora, Audiencia, Conteudo, Laudo, Limiares

if TYPE_CHECKING:
    from suno.comite import Comite


def avaliar(
    conteudo: Conteudo,
    ancoras: Sequence[Ancora],
    audiencia: Audiencia,
    *,
    limiares: Limiares | None = None,
    comite: "Comite | None" = None,
) -> Laudo:
    """A única assinatura que atravessa a costura entre Gerador e Avaliador.

    ``limiares`` cai em ``LIMIARES_PROVISORIOS[audiencia]`` quando não informado.
    ``comite`` é ``None`` por padrão: o Laudo sai com ``comite=None``, nunca com nota zero.
    """
    from suno.avaliador.laudo import avaliar as _avaliar

    return _avaliar(conteudo, ancoras, audiencia, limiares=limiares, comite=comite)


__all__ = ["avaliar"]
