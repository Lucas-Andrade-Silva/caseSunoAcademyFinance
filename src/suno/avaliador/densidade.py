"""Densidade: proporção de termos do Léxico na Célula e se vieram explicados na primeira
ocorrência quando a Audiência exigia. O Léxico vive em data/lexico/.

ADR 0012.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from suno.dominio import ExigenciaDeExplicacao


@dataclass(frozen=True)
class TermoEncontrado:
    termo: str
    posicao: int
    explicado: bool
    nucleo: bool


@dataclass(frozen=True)
class ResultadoDensidade:
    proporcao: float | None
    termos: list[TermoEncontrado] = field(default_factory=list)
    sem_explicacao: list[str] = field(default_factory=list)


def medir_densidade(texto: str, exigencia: ExigenciaDeExplicacao) -> ResultadoDensidade:
    raise NotImplementedError("Etapa 1, agente 2 — ADR 0012")
