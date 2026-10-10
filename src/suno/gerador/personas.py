"""Três geradores especializados, um por Audiência.

Cada gerador recebe o mesmo dossiê e produz os três Formatos da sua persona. Os
Formatos continuam independentes e rodam em paralelo; o papel especializado fica na
instrução de Audiência usada por ``rodar_ciclo``.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from suno.dominio import Audiencia, Formato, HistoricoCelula
from suno.gerador.ciclo import rodar_ciclo
from suno.gerador.curador import DossieCurado
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.comite import Comite


@dataclass(frozen=True, slots=True)
class AgenteGeradorPersona:
    """Gera somente uma persona; quantidade e Formatos continuam fixos por código."""

    audiencia: Audiencia

    def gerar(
        self,
        dossie: DossieCurado,
        provedor: Provedor,
        *,
        comite: "Comite | None" = None,
    ) -> list[HistoricoCelula]:
        return self.gerar_formatos(dossie, provedor, list(Formato), comite=comite)

    def gerar_formatos(
        self,
        dossie: DossieCurado,
        provedor: Provedor,
        formatos: list[Formato],
        *,
        comite: "Comite | None" = None,
        orientacoes: dict[Formato, list[str]] | None = None,
    ) -> list[HistoricoCelula]:
        """Regenera somente os Formatos apontados pelo Judge, sempre pelas regras fixas."""
        escolhidos = [formato for formato in Formato if formato in set(formatos)]
        if not escolhidos:
            return []
        orientacoes = orientacoes or {}
        with ThreadPoolExecutor(max_workers=len(escolhidos)) as executor:
            futuros = {
                formato: executor.submit(
                    rodar_ciclo,
                    dossie.ata,
                    dossie.ancoras,
                    self.audiencia,
                    formato,
                    provedor,
                    comite=comite,
                    orientacoes_transversais=orientacoes.get(formato),
                )
                for formato in escolhidos
            }
            return [futuros[formato].result() for formato in escolhidos]


AGENTES_GERADORES: tuple[AgenteGeradorPersona, ...] = tuple(
    AgenteGeradorPersona(audiencia) for audiencia in Audiencia
)
"""Exatamente Iniciante, Intermediário e Avançado, na ordem da Matriz."""
