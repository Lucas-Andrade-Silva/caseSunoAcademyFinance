"""Integridade da extração: se as Âncoras numéricas essenciais faltam, a Célula reprova por
`falha de extração` e vai direto à revisão humana, sem Ciclo de correção.

ADR 0013.

A medida olha a **tabela de Âncoras**, não a Célula: é a leitura da Ata que está sob
suspeita, e reescrever a Célula não conserta documento mal lido. Por isso a reprovação
daqui não aciona o Ciclo de correção.

Âncora textual não substitui um número do Copom: ``CHAVES_ESSENCIAIS`` é um conjunto de chaves
de Âncora numérica. A única exceção é o ``numero_principal`` das demais categorias: um
comunicado sem valor nenhum tem o fato central numa afirmação em prosa conferida contra o texto
(ADR 0034), e essa Âncora textual o substitui. Na Visão unida a regra vale por parte
(``a2_numero_principal`` aceita uma Âncora textual ``a2_...``).

``ancoras_com_trecho_vazio`` é sinal de extração degradada — Âncora sem o trecho literal da
Ata de onde o número veio não é conferível por um humano — mas é informativo: não entra em
``completa``, porque o valor pode estar certo mesmo sem o trecho.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from suno.dominio import (
    CHAVE_NUMERO_PRINCIPAL,
    CHAVES_ESSENCIAIS,
    Ancora,
    AncoraNumerica,
    AncoraTextual,
    ChaveAncora,
)

_PREFIXO_DA_PARTE = re.compile(r"^(a\d+_)")


@dataclass(frozen=True)
class ResultadoIntegridade:
    """``completa`` é o que vira ``MotivoReprovacao.FALHA_DE_EXTRACAO`` quando falso."""

    completa: bool
    faltantes: list[str] = field(default_factory=list)
    ancoras_com_trecho_vazio: list[str] = field(default_factory=list)


def _sem_numero_mas_com_afirmacao(chave: str, textuais: Sequence[AncoraTextual]) -> bool:
    """``numero_principal`` (ou ``aN_numero_principal``) vale com uma Âncora textual da mesma parte."""
    prefixo = _PREFIXO_DA_PARTE.match(chave)
    if prefixo is not None:
        if chave != f"{prefixo.group(1)}{CHAVE_NUMERO_PRINCIPAL}":
            return False
        return any(t.identificador.startswith(prefixo.group(1)) for t in textuais)
    return chave == CHAVE_NUMERO_PRINCIPAL and bool(textuais)


def _ordem_estavel(essenciais: frozenset[str]) -> list[str]:
    """As chaves essenciais na ordem em que ``ChaveAncora`` as declara, e o resto ordenado.

    Ordem estável importa: ``faltantes`` entra no Laudo e no relatório, e comparação de
    execuções não pode depender da ordem de iteração de um conjunto.
    """
    declaradas = [c.value for c in ChaveAncora if c.value in essenciais]
    sobras = sorted(str(c) for c in essenciais if str(c) not in declaradas)
    return [*declaradas, *sobras]


def medir_integridade(
    ancoras: Sequence[Ancora],
    chaves_essenciais: frozenset[str] = CHAVES_ESSENCIAIS,
) -> ResultadoIntegridade:
    """A extração está completa? Sem LLM e sem rede (ADR 0013).

    ``chaves_essenciais`` é o conjunto da categoria da Ata: o do Copom por padrão.

    Sequência vazia devolve incompleta com todas as chaves essenciais faltando — é o caso
    da Ata fora do padrão que o ADR 0013 descreve, e o silêncio é o modo de falha.
    """
    numericas = [a for a in ancoras if isinstance(a, AncoraNumerica)]
    textuais = [a for a in ancoras if isinstance(a, AncoraTextual) and a.trecho.strip()]
    presentes = {a.chave for a in numericas}
    for chave in chaves_essenciais:
        if _sem_numero_mas_com_afirmacao(str(chave), textuais):
            presentes.add(str(chave))
    faltantes = [chave for chave in _ordem_estavel(chaves_essenciais) if chave not in presentes]
    sem_trecho = [a.chave for a in numericas if not a.trecho.strip()]
    return ResultadoIntegridade(
        completa=not faltantes,
        faltantes=faltantes,
        ancoras_com_trecho_vazio=sem_trecho,
    )
