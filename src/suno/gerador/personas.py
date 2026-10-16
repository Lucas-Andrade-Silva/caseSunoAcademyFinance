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
from suno.gerador.ciclo import Andou, rodar_ciclo
from suno.gerador.curador import DossieCurado
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.avaliador.fidelidade import VerificadorDeFidelidade
    from suno.avaliador.qualidade import AvaliadorDeQualidade


@dataclass(frozen=True, slots=True)
class AgenteGeradorPersona:
    """Gera somente uma persona; quantidade e Formatos continuam fixos por código."""

    audiencia: Audiencia

    def gerar(
        self,
        dossie: DossieCurado,
        provedor: Provedor,
        *,
        qualidade: "AvaliadorDeQualidade | None" = None,
        fidelidade: "VerificadorDeFidelidade | None" = None,
        ao_andar: Andou | None = None,
    ) -> list[HistoricoCelula]:
        return self.gerar_formatos(
            dossie,
            provedor,
            list(Formato),
            qualidade=qualidade,
            fidelidade=fidelidade,
            ao_andar=ao_andar,
        )

    def gerar_formatos(
        self,
        dossie: DossieCurado,
        provedor: Provedor,
        formatos: list[Formato],
        *,
        qualidade: "AvaliadorDeQualidade | None" = None,
        fidelidade: "VerificadorDeFidelidade | None" = None,
        ao_andar: Andou | None = None,
    ) -> list[HistoricoCelula]:
        """Gera os Formatos pedidos, sempre pelas regras fixas."""
        escolhidos = [formato for formato in Formato if formato in set(formatos)]
        if not escolhidos:
            return []
        with ThreadPoolExecutor(max_workers=len(escolhidos)) as executor:
            futuros = {
                formato: executor.submit(
                    rodar_ciclo,
                    dossie.ata,
                    dossie.ancoras,
                    self.audiencia,
                    formato,
                    provedor,
                    qualidade=qualidade,
                    fidelidade=fidelidade,
                    ao_andar=ao_andar,
                    duracao=dossie.duracao,
                )
                for formato in escolhidos
            }
            return [futuros[formato].result() for formato in escolhidos]


AGENTES_GERADORES: tuple[AgenteGeradorPersona, ...] = tuple(
    AgenteGeradorPersona(audiencia) for audiencia in Audiencia
)
"""Exatamente Iniciante, Intermediário e Avançado, na ordem da Matriz."""
