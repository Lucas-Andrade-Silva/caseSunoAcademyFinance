"""Comitê de juízes-LLM: um juiz por dimensão subjetiva (tom, clareza, coerência), dois
provedores, nunca o do Gerador. Só Texto analítico e Carrossel. Nasce desligado.

ADR 0008.
"""

from __future__ import annotations

from suno.dominio import Celula, ResultadoComite
from suno.provedores.base import Provedor


class Comite:
    def __init__(self, juizes: tuple[Provedor, Provedor], provedor_gerador: str | None = None) -> None:
        raise NotImplementedError("Etapa 2, agente 7 — ADR 0008")

    def julgar(self, celula: Celula) -> ResultadoComite | None:
        """None para o Roteiro: ele não passa pelo comitê."""
        raise NotImplementedError("Etapa 2, agente 7 — ADR 0008")
