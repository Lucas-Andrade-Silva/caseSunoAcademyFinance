"""Separador de sílabas do português, reimplementado a partir de Silva (2011).

Não copia o código do NILC (GPL-3.0). As convenções para `ideia`, hiatos, ditongos
decrescentes e `-ia` final ficam documentadas aqui e cobertas por teste.

ADR 0002.
"""

from __future__ import annotations

def separar(palavra: str) -> list[str]:
    """Devolve as sílabas de uma palavra, sem strings vazias."""
    raise NotImplementedError("Etapa 1, agente 1 — ADR 0002")


def contar_silabas(palavra: str) -> int:
    raise NotImplementedError("Etapa 1, agente 1 — ADR 0002")
