"""Curador: prepara um dossiê factual único antes dos três geradores de persona.

O papel é limitado. O LLM rotula candidatos e afirmações; regras determinísticas
preservam os valores e conferem os trechos. O curador não gera Células nem as aprova.
"""

from __future__ import annotations

from dataclasses import dataclass

from suno.dominio import Ancoras, Ata, ModoSelecao, SelecaoCuradoria
from suno.gerador.extracao import extrair_ancoras
from suno.provedores.base import Provedor


@dataclass(frozen=True, slots=True)
class DossieCurado:
    """Fonte e evidências compartilhadas por todas as personas."""

    ata: Ata
    ancoras: Ancoras
    selecao: SelecaoCuradoria


@dataclass(frozen=True, slots=True)
class AgenteCurador:
    """Prepara o dossiê sem decidir linguagem, Formato ou publicação."""

    provedor: Provedor

    def preparar(self, ata: Ata) -> DossieCurado:
        return DossieCurado(
            ata=ata,
            ancoras=extrair_ancoras(ata, self.provedor),
            selecao=SelecaoCuradoria(modo=ModoSelecao.SEPARADA, itens=[ata.identificador]),
        )
