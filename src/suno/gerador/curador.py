"""Curador: prepara um dossiê factual único antes dos três geradores de persona.

O papel é limitado. O LLM rotula candidatos e afirmações; regras determinísticas
preservam os valores e conferem os trechos. O curador não gera Células nem as aprova.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from suno.dominio import (
    Ancoras,
    Ata,
    CategoriaDaAta,
    DuracaoDoVideo,
    ModoSelecao,
    SelecaoCuradoria,
)
from suno.gerador.extracao import extrair_ancoras, extrair_ancoras_da_uniao
from suno.provedores.base import Provedor

MINIMO_DE_PARTES = 2
MAXIMO_DE_PARTES = 5
TITULO_MAXIMO_DA_UNIAO = 200


@dataclass(frozen=True, slots=True)
class DossieCurado:
    """Fonte e evidências compartilhadas por todas as personas."""

    ata: Ata
    ancoras: Ancoras
    selecao: SelecaoCuradoria
    duracao: DuracaoDoVideo = DuracaoDoVideo.S60
    """A duração escolhida para o Roteiro; as outras duas formas não a leem."""


def compor_uniao(atas: Sequence[Ata]) -> Ata:
    """A Ata composta da Visão unida: os textos sob cabeçalhos ``[a1]``, ``[a2]``…, na ordem dada.

    O identificador vem dos identificadores das partes (estável, curto, serve de nome de pasta).
    A data de referência é a mais recente.
    """
    if not MINIMO_DE_PARTES <= len(atas) <= MAXIMO_DE_PARTES:
        raise ValueError(
            f"a Visão unida junta de {MINIMO_DE_PARTES} a {MAXIMO_DE_PARTES} Atas, "
            f"recebeu {len(atas)}"
        )
    identificadores = [ata.identificador for ata in atas]
    if len(set(identificadores)) != len(identificadores):
        raise ValueError("a Visão unida não aceita Ata repetida")
    digest = hashlib.sha1("|".join(identificadores).encode("utf-8")).hexdigest()[:8]
    titulo = "Visão unida: " + " + ".join(ata.titulo for ata in atas)
    if len(titulo) > TITULO_MAXIMO_DA_UNIAO:
        titulo = titulo[: TITULO_MAXIMO_DA_UNIAO - 1].rstrip() + "…"
    blocos = [
        f"[a{posicao}] {ata.titulo} ({ata.data_referencia:%d/%m/%Y})\n{ata.texto}"
        for posicao, ata in enumerate(atas, start=1)
    ]
    return Ata(
        identificador=f"uniao-{digest}",
        titulo=titulo,
        data_referencia=max(ata.data_referencia for ata in atas),
        texto="\n\n".join(blocos),
        categoria=CategoriaDaAta.UNIDA,
        origem="uniao",
        partes=identificadores,
    )


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

    def preparar_uniao(self, atas: Sequence[Ata]) -> DossieCurado:
        """O dossiê da Visão unida: uma extração por parte, chaves prefixadas por parte."""
        uniao = compor_uniao(atas)
        return DossieCurado(
            ata=uniao,
            ancoras=extrair_ancoras_da_uniao(atas, uniao, self.provedor),
            selecao=SelecaoCuradoria(
                modo=ModoSelecao.UNIDA, itens=[ata.identificador for ata in atas]
            ),
        )
