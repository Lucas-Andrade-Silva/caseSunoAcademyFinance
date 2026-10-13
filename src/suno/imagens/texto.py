"""Normalização de texto para a busca: casefold, sem acento, sem stopwords."""

from __future__ import annotations

import re
import unicodedata

_PALAVRA = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset(
    """a o as os um uma uns umas de do da dos das em no na nos nas por para pra com sem sob sobre
    e ou mas que se ao aos ate entre como mais menos muito ja nao sim ser foi tem ter the of and in
    to for on at by with from""".split()
)


def sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def _singular(termo: str) -> str:
    """Tira o plural simples ('acoes' -> 'acoe', 'precos' -> 'preco') nos dois lados da busca."""
    return termo[:-1] if len(termo) > 3 and termo.endswith("s") else termo


def termos(texto: str) -> list[str]:
    """Os termos normalizados do texto, na ordem, sem repetição e sem stopwords."""
    vistos: dict[str, None] = {}
    for palavra in _PALAVRA.findall(sem_acento(texto)):
        if palavra in STOPWORDS:
            continue
        vistos.setdefault(_singular(palavra), None)
    return list(vistos)
