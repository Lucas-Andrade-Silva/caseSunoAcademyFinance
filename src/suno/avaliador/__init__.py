"""O Avaliador: recebe ``(Conteúdo, Âncora[], Audiência)`` e devolve um Laudo (ADR 0001).

Roda sem LLM e sem rede por padrão. As cinco medidas determinísticas vivem em módulos
irmãos; ``laudo.py`` as junta e aplica os Limiares. O comitê de juízes-LLM (ADR 0008) é
uma camada opcional, injetada por quem chama, e nasce desligado.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from suno.dominio import Ancora, Audiencia, Conteudo, Laudo, Limiares
from suno.avaliador.juiz_transversal import AgenteAvaliadorTransversal
from suno.avaliador.transversal import avaliar_matriz

if TYPE_CHECKING:
    from suno.comite import Comite


def avaliar(
    conteudo: Conteudo,
    ancoras: Sequence[Ancora],
    audiencia: Audiencia,
    *,
    limiares: Limiares | None = None,
    comite: "Comite | None" = None,
    chaves_essenciais: frozenset[str] | None = None,
) -> Laudo:
    """A única assinatura que atravessa a costura entre Gerador e Avaliador.

    ``limiares`` cai em ``LIMIARES_PROVISORIOS[audiencia]`` quando não informado.
    ``comite`` é ``None`` por padrão: o Laudo sai com ``comite=None``, nunca com nota zero.
    ``chaves_essenciais`` é ``None`` por padrão e então vale o conjunto do Copom; só uma Ata de
    outra categoria passa o conjunto genérico (``suno.dominio.chaves_essenciais_da``).
    """
    from suno.avaliador.laudo import avaliar as _avaliar

    if chaves_essenciais is None:
        return _avaliar(conteudo, ancoras, audiencia, limiares=limiares, comite=comite)
    return _avaliar(
        conteudo,
        ancoras,
        audiencia,
        limiares=limiares,
        comite=comite,
        chaves_essenciais=chaves_essenciais,
    )


__all__ = ["AgenteAvaliadorTransversal", "avaliar", "avaliar_matriz"]
