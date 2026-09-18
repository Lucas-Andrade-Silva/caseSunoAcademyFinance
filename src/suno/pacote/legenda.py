"""Legenda e hashtags do Pacote. O número da legenda vem das Âncoras, da mesma origem única.

ADR 0011.

A legenda tem três partes fixas, nesta ordem:

1. a decisão, com a Selic citada por ``AncoraNumerica.citacao()`` — nunca ``str(valor)``;
2. as duas primeiras frases do texto avaliável da Célula, que já passou pelo Avaliador;
3. o aviso de que isto não é Recomendação, que é a linha que o sistema não cruza.

Nenhum número é escrito aqui: os da parte 1 saem das Âncoras e os da parte 2 vêm de uma Célula
cuja Aderência já foi medida contra as mesmas Âncoras. Não existe segundo caminho pelo qual um
número chegue à legenda.
"""

from __future__ import annotations

import re

from suno.dominio import Ancoras, Audiencia, Celula, ChaveAncora

AVISO_DE_NAO_RECOMENDACAO = "Conteúdo informativo. Não é recomendação de investimento."
"""A linha que não se cruza, escrita por extenso no que o humano publica."""

MAXIMO_DE_HASHTAGS = 8

HASHTAGS_COMUNS = ("#copom", "#selic", "#juros", "#bancocentral")

HASHTAGS_DA_AUDIENCIA: dict[Audiencia, tuple[str, ...]] = {
    Audiencia.INICIANTE: ("#educacaofinanceira", "#investirdozero", "#dinheiro"),
    Audiencia.INTERMEDIARIO: ("#rendafixa", "#macroeconomia", "#investimentos"),
    Audiencia.AVANCADO: ("#politicamonetaria", "#macro", "#rendafixa"),
}

FRASES_NA_LEGENDA = 2

_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+|\n+")


def primeiras_frases(texto: str, quantas: int = FRASES_NA_LEGENDA) -> list[str]:
    """As primeiras frases do texto avaliável. Quebra de linha também termina frase.

    O título de um Slide e a rubrica de cena não trazem ponto final; sem tratar a quebra de
    linha como fim de frase, título e corpo virariam uma frase só.
    """
    frases = [trecho.strip() for trecho in _FIM_DE_FRASE.split(texto) if trecho.strip()]
    return frases[:quantas]


def hashtags_da_audiencia(audiencia: Audiencia) -> list[str]:
    """Fixas por Audiência, sem repetição e no teto de oito."""
    escolhidas: list[str] = []
    for etiqueta in (*HASHTAGS_COMUNS, *HASHTAGS_DA_AUDIENCIA[audiencia]):
        if etiqueta not in escolhidas:
            escolhidas.append(etiqueta)
    return escolhidas[:MAXIMO_DE_HASHTAGS]


def _abertura(ancoras: Ancoras) -> str:
    """A decisão, citada. Sem a Âncora da Selic decidida, a legenda abre sem número."""
    decidida = ancoras.numerica(ChaveAncora.SELIC_DECIDIDA.value)
    if decidida is None:
        return "O Copom decidiu a taxa básica de juros nesta reunião."
    citacao = decidida.citacao()
    # ``14,00% a.a.`` já termina em ponto: a citação é literal e não ganha pontuação nova.
    ponto = "" if citacao.endswith(".") else "."
    return f"O Copom definiu a Selic em {citacao}{ponto}"


def montar_legenda(celula: Celula, ancoras: Ancoras) -> tuple[str, list[str]]:
    """A legenda e as hashtags de uma Célula aprovada, prontas para um humano publicar."""
    partes = [_abertura(ancoras)]
    partes.extend(primeiras_frases(celula.conteudo.texto_avaliavel()))
    partes.append(AVISO_DE_NAO_RECOMENDACAO)
    return "\n\n".join(partes), hashtags_da_audiencia(celula.audiencia)
