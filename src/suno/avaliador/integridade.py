"""Integridade da extração: se as Âncoras numéricas essenciais faltam, a Célula reprova por
`falha de extração` e vai direto à revisão humana, sem Ciclo de correção.

ADR 0013.

A medida olha a **tabela de Âncoras**, não a Célula: é a leitura da Ata que está sob
suspeita, e reescrever a Célula não conserta documento mal lido. Por isso a reprovação
daqui não aciona o Ciclo de correção.

Âncora textual não conta: ``CHAVES_ESSENCIAIS`` é um conjunto de chaves de Âncora numérica,
e uma afirmação em prosa não substitui o número que falta.

``ancoras_com_trecho_vazio`` é sinal de extração degradada — Âncora sem o trecho literal da
Ata de onde o número veio não é conferível por um humano — mas é informativo: não entra em
``completa``, porque o valor pode estar certo mesmo sem o trecho.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from suno.dominio import CHAVES_ESSENCIAIS, Ancora, AncoraNumerica, ChaveAncora


@dataclass(frozen=True)
class ResultadoIntegridade:
    """``completa`` é o que vira ``MotivoReprovacao.FALHA_DE_EXTRACAO`` quando falso."""

    completa: bool
    faltantes: list[str] = field(default_factory=list)
    ancoras_com_trecho_vazio: list[str] = field(default_factory=list)


def _ordem_estavel() -> list[str]:
    """As chaves essenciais na ordem em que ``ChaveAncora`` as declara, e o resto ordenado.

    Ordem estável importa: ``faltantes`` entra no Laudo e no relatório, e comparação de
    execuções não pode depender da ordem de iteração de um conjunto.
    """
    declaradas = [c.value for c in ChaveAncora if c.value in CHAVES_ESSENCIAIS]
    sobras = sorted(str(c) for c in CHAVES_ESSENCIAIS if str(c) not in declaradas)
    return [*declaradas, *sobras]


def medir_integridade(ancoras: Sequence[Ancora]) -> ResultadoIntegridade:
    """A extração está completa? Sem LLM e sem rede (ADR 0013).

    Sequência vazia devolve incompleta com todas as chaves essenciais faltando — é o caso
    da Ata fora do padrão que o ADR 0013 descreve, e o silêncio é o modo de falha.
    """
    numericas = [a for a in ancoras if isinstance(a, AncoraNumerica)]
    presentes = {a.chave for a in numericas}
    faltantes = [chave for chave in _ordem_estavel() if chave not in presentes]
    sem_trecho = [a.chave for a in numericas if not a.trecho.strip()]
    return ResultadoIntegridade(
        completa=not faltantes,
        faltantes=faltantes,
        ancoras_com_trecho_vazio=sem_trecho,
    )
