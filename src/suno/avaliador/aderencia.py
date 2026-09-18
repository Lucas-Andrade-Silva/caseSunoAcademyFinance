"""Aderência: cada número na Célula conferido por igualdade exata de valor e unidade contra
as Âncoras numéricas; afirmações conferidas contra as Âncoras textuais. Sem LLM.

ADR 0011.

**Quem reprova é o número.** ``cobertura_textual`` é informativa e não entra no cálculo de
``proporcao``: medir prosa contra prosa sem LLM é contagem de palavra, e contagem de
palavra não sustenta um veredito. A Âncora textual serve para o humano da fila de revisão
enxergar o que a Célula deixou de dizer, não para reprovar.

A igualdade é exata em valor e unidade, com tolerância só de representação: ``14`` = ``14,0``
= ``14,00`` porque a comparação é feita sobre o valor normalizado, e ``0,5 p.p.`` = ``0,50 p.p.``
pelo mesmo motivo. O que **não** é tolerância de representação:

- ``%``, ``% a.a.``, ``p.p.`` e ``pb`` são unidades distintas e nunca casam entre si
  (pesquisa §3): ``0,5 p.p.`` não é ``0,5%``, e ``50 pb`` não é ``50%``.
- ``CDI+2%`` não é ``2%``, e ``110% do CDI`` não é ``110%``. O qualificador tem que bater.

Data casa quando ``data_iso`` coincide, quando o literal cita o mês e o ano da Âncora, ou
— para ano solto — quando o ano bate com o de qualquer Âncora de data. Votos casam pelo
literal normalizado: ``por 7 votos a 0`` é o mesmo placar que ``7 a 0``.

``proporcao`` é ``None`` quando não há número no texto. Nunca zero por falta de base: Célula
sem número é Medida ausente no Laudo (``EstadoMedida.AUSENTE``), não reprovação.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Sequence

from suno.dominio import Ancora, AncoraNumerica, AncoraTextual, Unidade
from suno.ingestao.numeros import (
    NumeroEncontrado,
    extrair_numeros,
    mes_e_ano_no_literal,
    normalizar_placar,
)


@dataclass(frozen=True)
class ResultadoAderencia:
    """O que a Aderência mediu. ``proporcao`` é o que o Laudo compara com o Limiar."""

    proporcao: float | None
    numeros_conferidos: list[str] = field(default_factory=list)
    numeros_fora_das_ancoras: list[str] = field(default_factory=list)
    ancoras_citadas: list[str] = field(default_factory=list)
    cobertura_textual: dict[str, float] = field(default_factory=dict)
    numeros_fora_com_unidade: list[str] = field(default_factory=list)
    """Os mesmos números de ``numeros_fora_das_ancoras``, na mesma ordem, legíveis.

    ``numeros_fora_das_ancoras`` traz o literal cru (``"15"``), que é o que casa com o
    texto; a Correção do Laudo precisa mostrar ``"15%"`` e ``"0,75 p.p."``, senão a
    instrução não diz qual número está errado.
    """


# Preposições, artigos e verbos de ligação: presença delas não diz nada sobre cobertura.
_PALAVRAS_VAZIAS = frozenset(
    """
    a as o os um uma uns umas de do da dos das em no na nos nas por pelo pela pelos pelas
    para com sem sob sobre ao aos à às e ou mas que se como quando onde entre ate ja mais
    menos muito pouco tambem nao sim seu sua seus suas este esta estes estas esse essa
    esses essas aquele aquela isso isto aquilo ser sao foi foram era eram tem tem ter teve
    havia ha esta estao estar estava estavam sua deve devem pode podem foi apos qual quais
    """.split()
)

_MINIMO_DE_LETRAS = 3
"""Palavra de conteúdo tem pelo menos três letras: "pib" conta, "de" não."""

def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _palavras_de_conteudo(frase: str) -> list[str]:
    limpa = _sem_acento(frase).lower()
    return [
        palavra
        for palavra in re.findall(r"[a-z0-9]+", limpa)
        if len(palavra) >= _MINIMO_DE_LETRAS and palavra not in _PALAVRAS_VAZIAS
    ]


def _mesmo_qualificador(achado: NumeroEncontrado, ancora: AncoraNumerica) -> bool:
    """Estrito: Âncora sem qualificador só casa com número sem qualificador, e vice-versa."""

    def chave(bruto: str | None) -> str:
        return re.sub(r"\s+", " ", _sem_acento(bruto or "").lower()).strip()

    return chave(achado.qualificador) == chave(ancora.qualificador)


def _mesmo_valor(esquerda: float | None, direita: float | None) -> bool:
    if esquerda is None or direita is None:
        return False
    return math.isclose(esquerda, direita, rel_tol=1e-9, abs_tol=1e-9)


def _literal_normalizado(bruto: str) -> str:
    return re.sub(r"\s+", " ", _sem_acento(bruto).lower()).strip()


def _casa_data(achado: NumeroEncontrado, ancora: AncoraNumerica) -> bool:
    if ancora.data_iso is None:
        # Âncora de data sem ``data_iso`` só pode ser conferida pelo literal.
        return _literal_normalizado(achado.literal) == _literal_normalizado(ancora.valor_literal)
    if achado.data_iso is not None:
        if achado.data_iso == ancora.data_iso:
            return True
        return mes_e_ano_no_literal(achado.literal, ancora.data_iso)
    # Ano solto: casa com qualquer Âncora de data do mesmo ano.
    return achado.ano == ancora.data_iso.year


def _casa(achado: NumeroEncontrado, ancora: AncoraNumerica) -> bool:
    if achado.unidade is not ancora.unidade:
        return False
    if not _mesmo_qualificador(achado, ancora):
        return False
    if achado.unidade is Unidade.DATA:
        return _casa_data(achado, ancora)
    if achado.unidade is Unidade.VOTOS:
        return normalizar_placar(achado.literal) == normalizar_placar(ancora.valor_literal)
    if _mesmo_valor(achado.valor, ancora.valor):
        return True
    return achado.literal.strip() == ancora.valor_literal.strip()


def _com_unidade(achado: NumeroEncontrado) -> str:
    """Como o número aparece para um humano: ``"15%"``, ``"0,75 p.p."``, ``"CDI+2%"``.

    A regra de formatação é uma só e mora em ``AncoraNumerica.citacao()``. Em vez de
    copiá-la — a cópia já divergiu uma vez, no espaço antes do ``%`` de ``% a.a.`` —, monta
    uma Âncora de mentira com o que o número tem e chama o próprio ``citacao()``. Custo:
    um modelo Pydantic por número fora das Âncoras, que é o caso raro.

    Data, votos e número solto saem só com o literal ("4 e 5 de agosto de 2026", "7 a 0",
    "280"), porque é o que ``citacao()`` faz com essas unidades: grudar a unidade neles só
    atrapalharia a leitura da Correção.
    """
    return AncoraNumerica(
        chave="",
        rotulo="",
        valor_literal=achado.literal,
        valor=achado.valor,
        unidade=achado.unidade,
        trecho=achado.trecho,
        data_iso=achado.data_iso,
        qualificador=achado.qualificador,
    ).citacao()


def _ano_das_ancoras(numericas: Sequence[AncoraNumerica]) -> int | None:
    """O ano da Ata, para resolver data sem ano no texto sem depender do relógio."""
    for ancora in numericas:
        if ancora.data_iso is not None:
            return ancora.data_iso.year
    return None


def medir_aderencia(texto: str, ancoras: Sequence[Ancora]) -> ResultadoAderencia:
    """Confere cada número do texto contra as Âncoras numéricas. Sem LLM e sem rede.

    Número que aparece na Célula e não está nas Âncoras cai em
    ``numeros_fora_das_ancoras`` e derruba a ``proporcao`` — é a reprovação que o ADR 0011
    pede.
    """
    numericas = [a for a in ancoras if isinstance(a, AncoraNumerica)]
    textuais = [a for a in ancoras if isinstance(a, AncoraTextual)]

    achados = extrair_numeros(texto, ano_padrao=_ano_das_ancoras(numericas))
    conferidos: list[str] = []
    fora: list[str] = []
    fora_legivel: list[str] = []
    citadas: list[str] = []
    for achado in achados:
        casada = next((ancora for ancora in numericas if _casa(achado, ancora)), None)
        if casada is None:
            fora.append(achado.literal)
            fora_legivel.append(_com_unidade(achado))
            continue
        conferidos.append(achado.literal)
        if casada.chave not in citadas:
            citadas.append(casada.chave)

    total = len(conferidos) + len(fora)
    proporcao = len(conferidos) / total if total else None

    presentes = set(_palavras_de_conteudo(texto))
    cobertura = {
        ancora.identificador: _cobertura_da_afirmacao(ancora.afirmacao, presentes)
        for ancora in textuais
    }
    return ResultadoAderencia(
        proporcao=proporcao,
        numeros_conferidos=conferidos,
        numeros_fora_das_ancoras=fora,
        ancoras_citadas=citadas,
        cobertura_textual=cobertura,
        numeros_fora_com_unidade=fora_legivel,
    )


def _cobertura_da_afirmacao(afirmacao: str, presentes: set[str]) -> float:
    palavras = _palavras_de_conteudo(afirmacao)
    if not palavras:
        return 1.0
    return sum(1 for palavra in palavras if palavra in presentes) / len(palavras)
