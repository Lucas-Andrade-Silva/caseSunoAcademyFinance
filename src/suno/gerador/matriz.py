"""As nove Células geram em paralelo. Em sequência, uma Ata leva minutos e a demo morre esperando.

ADR 0010.
"""

from __future__ import annotations

from suno.dominio import Ancoras, Ata, Celula
from suno.provedores.base import Provedor


def gerar_matriz(ata: Ata, ancoras: Ancoras, provedor: Provedor) -> list[Celula]:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0010")
