"""Ciclo de correção: no máximo duas rodadas; o feedback é o valor medido. Falha de extração
nem tenta: vai direto à fila humana (H4).

ADR 0013.
"""

from __future__ import annotations

from suno.dominio import Ancoras, Ata, Audiencia, Formato, HistoricoCelula
from suno.provedores.base import Provedor


def rodar_ciclo(
    ata: Ata, ancoras: Ancoras, audiencia: Audiencia, formato: Formato, provedor: Provedor
) -> HistoricoCelula:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0013")
