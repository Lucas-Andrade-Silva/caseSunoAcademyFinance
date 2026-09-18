"""Flesch-BR: 248.835 - 1.015 x (palavras/frases) - 84.6 x (sílabas/palavras).
Martins, Ghiraldelo, Nunes & Oliveira Jr. (1996), NILC/USP.

`textstat` está proibida: cai no inglês em silêncio, com 20 pontos de erro.

ADR 0002.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Contagens:
    palavras: int
    frases: int
    silabas: int


def contar(texto: str) -> Contagens:
    raise NotImplementedError("Etapa 1, agente 1 — ADR 0002")


def flesch_br(texto: str) -> float | None:
    """O índice. ``None`` quando não há base (texto sem palavras): nunca zero."""
    raise NotImplementedError("Etapa 1, agente 1 — ADR 0002")
