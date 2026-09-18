"""Junta as cinco medidas num Laudo com três destinos. Métrica sem base sai `ausente`,
nunca zero. O comitê é opcional e roda depois das medidas determinísticas, nunca antes.

ADR 0001, 0008, 0013.
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
    raise NotImplementedError("Etapa 2, agente 7 — ADR 0001, 0008, 0013")
