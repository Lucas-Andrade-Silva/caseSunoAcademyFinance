"""Flesch-BR: 248.835 - 1.015 x (palavras/frases) - 84.6 x (sílabas/palavras).
Martins, Ghiraldelo, Nunes & Oliveira Jr. (1996), NILC/USP.

`textstat` está proibida: cai no inglês em silêncio, com 20 pontos de erro.

ADR 0002.

As convenções de contagem estão fixadas aqui e cobertas por ``tests/test_flesch_br.py``.
São deliberadas — é aqui que alguém "corrige" sem saber:

- **Frase** termina em ``.``, ``!``, ``?``, ``…`` ou quebra dupla de linha. Uma sequência
  de terminadores (``...``, ``?!``) termina uma frase só, e o terminador no fim do texto
  não abre frase vazia. Trecho sem nenhuma palavra não conta como frase.
- **Ponto de milhar** (``1.234``) nunca termina frase.
- **Abreviação** de ``ABREVIACOES`` (``a.a.``, ``p.p.``, ``etc.``…) termina frase só quando
  o que vem depois parece frase nova: espaço e letra maiúscula, quebra de linha, ou fim do
  texto. Seguida de minúscula, de dígito ou de pontuação, não termina — texto financeiro é
  cheio de ``14,00% a.a. pelo Copom`` e de ``14,00% a.a., e entende que`` no meio da frase,
  e a Célula também costuma *fechar* a frase na Selic (``…para 14,00% a.a. O Comitê…``).
  O ponto interno da abreviação (o de ``a.a.``) nunca termina nada.
- **Abreviação de tratamento** (``Sr.``, ``Sra.``, ``Dr.``, ``Dra.``) fica fora dessa
  regra e nunca termina frase: o que vem depois é nome próprio, sempre maiúsculo.
- **Palavra** é uma sequência de letras com acento e hífen interno (``bem-vindo`` é uma),
  ou uma abreviação inteira (``a.a.`` é uma), ou um número (``14,00`` é uma). Símbolos
  isolados (``%``, ``—``, ``•``, ``-``) não são palavras.
- **Sílabas de número**: um dígito, uma sílaba; a vírgula decimal soma as três sílabas de
  ``vír-gu-la``, medidas pelo próprio separador; o ponto de milhar não soma nada. É uma
  aproximação grosseira da leitura por extenso, escolhida por ser estável e explicável —
  ``14,00`` conta 7. O brief sugeria 2 para a vírgula; ficou 3 para não contradizer o
  separador de sílabas do próprio projeto.
- **Markdown** (``#``, ``>``, ``*``, ``_``, marcadores de lista) sai antes da contagem: a
  Célula de Texto analítico vem em Markdown, e ``17.`` abrindo um parágrafo numerado é
  marcador, não fim de frase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from suno.avaliador.silabas import contar_silabas

COEFICIENTE_LINEAR = 248.835
COEFICIENTE_PALAVRAS_POR_FRASE = 1.015
COEFICIENTE_SILABAS_POR_PALAVRA = 84.6

ABREVIACOES_DE_TRATAMENTO: tuple[str, ...] = ("sra.", "sr.", "dra.", "dr.")
"""Nunca terminam frase: o que vem depois é nome próprio, e nome próprio é maiúsculo."""

ABREVIACOES: tuple[str, ...] = (
    "p.ex.",
    "n.º",
    "a.a.",
    "p.p.",
    "a.m.",
    "p.m.",
    "etc.",
    "vs.",
) + ABREVIACOES_DE_TRATAMENTO
"""Pontos que só terminam frase diante de maiúscula, quebra de linha ou fim de texto."""

_LETRAS = "A-Za-zÀ-ÖØ-öø-ÿ"
_MARCA = "\x00"
"""Sentinela que ocupa o lugar do ponto que não termina frase."""

_ABREVIACAO = re.compile(
    "|".join(re.escape(a) for a in sorted(ABREVIACOES, key=len, reverse=True)),
    re.IGNORECASE,
)
_PONTO_DE_MILHAR = re.compile(r"(?<=\d)\.(?=\d)")
_FRASE_NOVA_DEPOIS = re.compile(r"[ \t]*(?:\n|\Z)|[ \t]+[A-ZÀ-ÖØ-Þ]")
"""O que, depois de uma abreviação, denuncia frase nova: maiúscula, linha ou fim."""
_PREFIXO_MARKDOWN = re.compile(
    r"^[ \t]*(?:>+[ \t]*|#{1,6}[ \t]*|[-*+•][ \t]+|\d+[.)][ \t]+)+", re.MULTILINE
)
_ENFASE_MARKDOWN = re.compile(r"[*_`~]")
_FIM_DE_FRASE = re.compile(r"[.!?…]+|\n[ \t]*\n")
_TOKEN = re.compile(
    rf"[{_LETRAS}]+(?:[-\x00][{_LETRAS}]+)*\x00?|\d+(?:[.,\x00]\d+)*"
)

SILABAS_DA_VIRGULA = contar_silabas("vírgula")
"""Três, pelo separador do projeto. É o que a vírgula decimal soma num número."""


@dataclass(frozen=True)
class Contagens:
    palavras: int
    frases: int
    silabas: int


def contar(texto: str) -> Contagens:
    """Palavras, frases e sílabas de um texto, pelas convenções do módulo."""
    preparado = _mascarar(_sem_markdown(texto))
    palavras = frases = silabas = 0
    for trecho in _FIM_DE_FRASE.split(preparado):
        tokens = _TOKEN.findall(trecho)
        if not tokens:
            continue  # pontuação solta não vira frase
        frases += 1
        palavras += len(tokens)
        silabas += sum(_silabas_do_token(token) for token in tokens)
    return Contagens(palavras=palavras, frases=frases, silabas=silabas)


def flesch_br(texto: str) -> float | None:
    """O índice. ``None`` quando não há base (texto sem palavras): nunca zero."""
    contagens = contar(texto)
    if contagens.palavras == 0:
        return None
    frases = max(contagens.frases, 1)
    return (
        COEFICIENTE_LINEAR
        - COEFICIENTE_PALAVRAS_POR_FRASE * (contagens.palavras / frases)
        - COEFICIENTE_SILABAS_POR_PALAVRA * (contagens.silabas / contagens.palavras)
    )


def faixa_nilc(indice: float) -> str:
    """As quatro faixas publicadas pelo NILC (ADR 0002), para a interface mostrar."""
    if indice >= 75:
        return "muito fácil"
    if indice >= 50:
        return "fácil"
    if indice >= 25:
        return "difícil"
    return "muito difícil"


# ---------------------------------------------------------------------------
# Preparação do texto
# ---------------------------------------------------------------------------


def _sem_markdown(texto: str) -> str:
    """Tira títulos, citações, marcadores de lista e ênfase, preservando as linhas."""
    limpo = texto.replace("\r\n", "\n").replace("\r", "\n")
    limpo = _PREFIXO_MARKDOWN.sub("", limpo)
    return _ENFASE_MARKDOWN.sub("", limpo)


def _mascarar(texto: str) -> str:
    """Troca por sentinela o ponto que não termina frase: abreviação e milhar."""

    def proteger(achado: re.Match[str]) -> str:
        bruto = achado.group(0)
        if bruto.lower() in ABREVIACOES_DE_TRATAMENTO or not bruto.endswith("."):
            return bruto.replace(".", _MARCA)  # Sr. Silva, n.º 280
        miolo = bruto[:-1].replace(".", _MARCA)  # o ponto de dentro de a.a. nunca termina
        if _FRASE_NOVA_DEPOIS.match(texto, achado.end()):
            return miolo + "."  # ...14,00% a.a. O Comitê... são duas frases
        return miolo + _MARCA  # ...14,00% a.a. pelo Copom... é uma só

    return _PONTO_DE_MILHAR.sub(_MARCA, _ABREVIACAO.sub(proteger, texto))


def _silabas_do_token(token: str) -> int:
    if any(letra.isdigit() for letra in token):
        return _silabas_do_numero(token)
    partes = [parte for parte in re.split(r"[-\x00]", token) if parte]
    return sum(contar_silabas(parte) for parte in partes)


def _silabas_do_numero(token: str) -> int:
    digitos = sum(1 for letra in token if letra.isdigit())
    return digitos + SILABAS_DA_VIRGULA * token.count(",")
