"""Extração das Âncoras: roda uma vez por Ata, antes da Matriz. As Âncoras numéricas saem do
extrator determinístico de ingestao/numeros.py; o LLM só localiza e rotula, nunca reescreve valor.

ADR 0011.
"""

from __future__ import annotations

from suno.dominio import Ancoras, Ata
from suno.provedores.base import Provedor


def extrair_ancoras(ata: Ata, provedor: Provedor) -> Ancoras:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0011")
