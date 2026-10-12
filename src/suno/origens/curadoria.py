"""As sugestões da curadoria: qual Ata, ou quais, valem uma Saída agora. Determinístico, sem LLM.

Sugere pauta de conteúdo, nunca um ativo para comprar ou vender (a linha que não se cruza). O
ranking é: quem consegue gerar, a recência, o número de Âncoras e o peso da Origem (``catalogo``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from suno.origens.catalogo import PESO_DA_CATEGORIA, Origem
from suno.origens.resumo import ResumoDaAta

TAMANHO_DA_VISAO_UNIDA = 3


class Sugestao(BaseModel):
    itens: list[ResumoDaAta]
    motivo: str


def _ranqueadas(
    origens: Sequence[Origem], itens_por_origem: Mapping[str, Sequence[ResumoDaAta]]
) -> list[ResumoDaAta]:
    """As Atas das Origens ligadas, da melhor para a pior.

    Quem não consegue gerar (a extração vai falhar) só aparece depois de todo mundo que consegue.
    """
    ligadas = {o.id for o in origens if o.ativa and o.disponivel}
    candidatas = [
        ata for origem, atas in itens_por_origem.items() if origem in ligadas for ata in atas
    ]
    return sorted(
        candidatas,
        key=lambda i: (
            i.extracao_completa,
            i.data_referencia,
            i.total_ancoras,
            PESO_DA_CATEGORIA[i.categoria],
        ),
        reverse=True,
    )


def sugerir(
    origens: Sequence[Origem], itens_por_origem: Mapping[str, Sequence[ResumoDaAta]]
) -> Sugestao | None:
    """O Destaque único: a Ata mais recente entre as Origens ligadas, ou ``None`` sem nenhuma."""
    ordenadas = _ranqueadas(origens, itens_por_origem)
    if not ordenadas:
        return None
    escolhido = ordenadas[0]
    mais_ancoras = max(i.total_ancoras for i in ordenadas)
    if escolhido.total_ancoras == mais_ancoras and escolhido.total_ancoras > 0:
        motivo = (
            "O item mais recente e com mais Âncoras: "
            f"{escolhido.total_ancoras} números e datas conferidos contra o texto."
        )
    else:
        motivo = (
            f"O item mais recente: {escolhido.total_ancoras} números e datas conferidos "
            "contra o texto."
        )
    if not escolhido.extracao_completa:
        motivo += (
            " Atenção: sem uma data e um número com unidade no texto, a geração reprovaria "
            "toda Célula por falha de extração."
        )
    if not escolhido.calibrada:
        motivo += (
            " Fora do Copom: ainda não calibrado (Limiares e Léxico foram medidos só com "
            "Atas do Copom)."
        )
    return Sugestao(itens=[escolhido], motivo=motivo)


def sugerir_visao_unida(
    origens: Sequence[Origem], itens_por_origem: Mapping[str, Sequence[ResumoDaAta]]
) -> Sugestao | None:
    """A Visão unida: as três Atas mais bem colocadas que conseguem gerar, ou ``None``.

    Precisa de ao menos duas: uma só é o Destaque único.
    """
    geraveis = [a for a in _ranqueadas(origens, itens_por_origem) if a.extracao_completa]
    escolhidas = geraveis[:TAMANHO_DA_VISAO_UNIDA]
    if len(escolhidas) < 2:
        return None
    motivo = (
        f"Junta os {len(escolhidas)} itens mais relevantes num só conteúdo. "
        "Cada número cita o comunicado de onde vem."
    )
    if any(not ata.calibrada for ata in escolhidas):
        motivo += (
            " Inclui item não calibrado (Limiares e Léxico foram medidos só com Atas do Copom)."
        )
    return Sugestao(itens=escolhidas, motivo=motivo)
