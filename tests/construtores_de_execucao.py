"""Construtores pequenos de Execução para os testes da revisão humana e da exportação.

Só Texto analítico, que não pede slides nem blocos: o que importa aqui é o destino do Laudo
e os motivos, não o conteúdo.
"""

from __future__ import annotations

from datetime import datetime, timezone

from suno.dominio import (
    Ancoras,
    Audiencia,
    Celula,
    Conteudo,
    Destino,
    Execucao,
    Formato,
    HistoricoCelula,
    Laudo,
    Medida,
    Metrica,
    MotivoReprovacao,
    Pendencia,
    Tentativa,
)

IDENTIFICADOR = "exec-teste"
ATA = "copom-280-2026-08-05"


def historico_de_texto(
    audiencia: Audiencia,
    destino: Destino,
    motivos: tuple[MotivoReprovacao, ...] = (),
) -> HistoricoCelula:
    """Uma posição Audiência × Texto analítico, com uma tentativa e o destino pedido."""
    formato = Formato.TEXTO_ANALITICO
    celula = Celula(
        audiencia=audiencia,
        formato=formato,
        conteudo=Conteudo(formato=formato, texto=f"Texto de teste para {audiencia.value}."),
    )
    laudo = Laudo(
        audiencia=audiencia,
        formato=formato,
        medidas=[
            Medida(metrica=Metrica.ADERENCIA, valor=1.0, atingiu=destino is Destino.APROVADO)
        ],
        destino=destino,
        motivos=list(motivos),
    )
    return HistoricoCelula(
        audiencia=audiencia,
        formato=formato,
        tentativas=[Tentativa(rodada=0, celula=celula, laudo=laudo)],
        destino_final=destino,
    )


def execucao_de_teste(
    *historicos: HistoricoCelula,
    nome: str = "",
    pendencias: tuple[Pendencia, ...] = (),
) -> Execucao:
    return Execucao(
        identificador=IDENTIFICADOR,
        nome=nome,
        ata=ATA,
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc),
        ancoras=Ancoras(ata=ATA),
        celulas=list(historicos),
        pendencias=list(pendencias),
    )
