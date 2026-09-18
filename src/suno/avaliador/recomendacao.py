"""Recomendação detectada por Léxico (pode / não pode) mais padrão sintático sobre POS
tagging do spaCy (`pt_core_news_sm`, offline). Nunca por LLM. O canary set em
data/canary/ é a regressão contra paráfrase.

ADR 0012.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ocorrencia:
    frase: str
    padrao: str
    trecho: str


def detectar_recomendacao(texto: str) -> list[Ocorrencia]:
    """Lista vazia = sem Recomendação. Qualquer ocorrência reprova a Célula."""
    raise NotImplementedError("Etapa 1, agente 3 — ADR 0012")
