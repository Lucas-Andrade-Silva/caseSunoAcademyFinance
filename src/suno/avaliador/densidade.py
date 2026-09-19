"""Densidade: proporção de termos do Léxico na Célula e se vieram explicados na primeira
ocorrência quando a Audiência exigia. O Léxico vive em data/lexico/.

ADR 0012.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from suno.dominio import ExigenciaDeExplicacao

CAMINHO_LEXICO = Path(__file__).resolve().parents[3] / "data" / "lexico" / "lexico.yaml"


@dataclass(frozen=True)
class Termo:
    """Uma entrada do Léxico: o nome canônico, formas alternativas e onde ela pesa."""

    termo: str
    variantes: tuple[str, ...]
    nucleo: bool
    area: str
    origem: str


@dataclass(frozen=True)
class TermoEncontrado:
    termo: str
    posicao: int
    explicado: bool
    nucleo: bool


@dataclass(frozen=True)
class ResultadoDensidade:
    proporcao: float | None
    termos: list[TermoEncontrado] = field(default_factory=list)
    sem_explicacao: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Carregamento do Léxico (cache de módulo — carrega o YAML uma vez só)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _carregar_bruto() -> tuple[Termo, ...]:
    with CAMINHO_LEXICO.open("r", encoding="utf-8") as arquivo:
        bruto: dict[str, Any] = yaml.safe_load(arquivo)

    termos: list[Termo] = []
    vistos: set[str] = set()
    for registro in bruto["termos"]:
        termo = Termo(
            termo=str(registro["termo"]),
            variantes=tuple(registro.get("variantes") or []),
            nucleo=bool(registro["nucleo"]),
            area=str(registro["area"]),
            origem=str(registro["origem"]),
        )
        chave = _normalizar(termo.termo)
        if chave in vistos:
            raise ValueError(f"termo duplicado no Léxico após normalização: {termo.termo!r}")
        vistos.add(chave)
        termos.append(termo)
    return tuple(termos)


def carregar_lexico() -> list[Termo]:
    """O Léxico inteiro. Carrega o YAML uma única vez por processo (cache de módulo)."""
    return list(_carregar_bruto())


def termos_do_nucleo() -> set[str]:
    """Os nomes canônicos marcados ``nucleo: true`` — vocabulário que o Intermediário já conhece."""
    return {termo.termo for termo in carregar_lexico() if termo.nucleo}


# ---------------------------------------------------------------------------
# Normalização: mesma comparação para "SELIC"/"selic" e para acento presente/ausente
# ---------------------------------------------------------------------------

# Só letras latinas acentuadas de um único code point: preserva o tamanho da string
# (ao contrário de NFKD, que decompõe "ç" em dois code points), então uma posição no
# texto normalizado é sempre a mesma posição no texto original.
_MAPA_ACENTOS = str.maketrans(
    "áàãâäéèêëíìîïóòõôöúùûüç",
    "aaaaaeeeeiiiiooooouuuuc",
)


def _normalizar(texto: str) -> str:
    return texto.lower().translate(_MAPA_ACENTOS)


def _minusculo_com_acento(texto: str) -> str:
    """Só ``lower()``, sem tirar acento — mesma contagem de caracteres que ``_normalizar``,
    então os spans de frase calculados numa servem na outra. Usado só nas marcas de
    explicação: "é a"/"são" sem acento colidem com "e a" (conjunção) e "São" (o santo de
    nome de cidade), o que marcava frase inteira como explicada por acidente (achado do
    revisor de erros, 2026-09-19). Marca de explicação é sempre acentuada em português
    correto; perder o acento é o que cria a ambiguidade, não o que a resolve.
    """
    return texto.lower()


# ---------------------------------------------------------------------------
# Construção dos padrões de casamento: limite de palavra + plural simples
# ---------------------------------------------------------------------------


def _padrao_palavra(palavra_normalizada: str) -> str:
    """Uma palavra, com o plural simples que o brief pede: -s, -es, -ões/-ão."""
    escapada = re.escape(palavra_normalizada)
    if palavra_normalizada.endswith("ao") and len(palavra_normalizada) > 2:
        raiz = re.escape(palavra_normalizada[:-2])
        return f"{raiz}(?:ao|oes)"
    if palavra_normalizada.endswith(("r", "s", "z")):
        return f"{escapada}(?:es)?"
    return f"{escapada}s?"


def _padrao_forma(forma: str) -> str:
    """Uma forma do termo (canônico ou variante), já normalizada.

    Termo de uma palavra só ganha a flexão de plural; termo multi-palavra casa literal
    (o plural de composto em português muda por concordância, não por sufixo simples —
    fora do escopo pedido). Sempre com limite de palavra nas duas pontas, para não achar
    "ação" dentro de "reação" ou "aplicação".
    """
    palavras = forma.split()
    if len(palavras) == 1:
        nucleo_regex = _padrao_palavra(palavras[0])
    else:
        nucleo_regex = r"\s+".join(re.escape(p) for p in palavras)
    return rf"\b{nucleo_regex}\b"


@lru_cache(maxsize=1)
def _padroes_compilados() -> tuple[tuple[re.Pattern[str], str, bool], ...]:
    padroes: list[tuple[re.Pattern[str], str, bool]] = []
    for termo in carregar_lexico():
        formas = {termo.termo, *termo.variantes}
        for forma in formas:
            padrao = _padrao_forma(_normalizar(forma))
            padroes.append((re.compile(padrao, re.IGNORECASE), termo.termo, termo.nucleo))
    return tuple(padroes)


# ---------------------------------------------------------------------------
# Sentenças: para decidir "mesma frase ou frase seguinte"
# ---------------------------------------------------------------------------

_QUEBRA_DE_FRASE = re.compile(r"(?<=[.!?])\s+|\n[ \t]*\n\s*")
"""Pontuação normal, mais linha em branco. `Conteudo.texto_avaliavel()` junta os slides do
Carrossel com uma linha em branco (sem `.`/`!`/`?` no meio) — sem o segundo ramo, o título
do slide seguinte contava como "frase seguinte ao termo" e virava explicação por acidente
(achado do revisor de erros, 2026-09-19)."""


def _dividir_frases(texto: str) -> list[tuple[int, int]]:
    """Spans (início, fim) contíguos cobrindo o texto inteiro, um por frase."""
    frases: list[tuple[int, int]] = []
    posicao = 0
    for m in _QUEBRA_DE_FRASE.finditer(texto):
        frases.append((posicao, m.start()))
        posicao = m.end()
    frases.append((posicao, len(texto)))
    return frases


def _indice_da_frase(inicios: list[int], posicao: int) -> int:
    i = bisect.bisect_right(inicios, posicao) - 1
    return max(0, min(i, len(inicios) - 1))


# ---------------------------------------------------------------------------
# Marcas de explicação (ADR 0012 / brief do Agente 2)
# ---------------------------------------------------------------------------

_MARCAS_IMEDIATAS = ("(", ":", "—", "-")
"""Parêntese, dois-pontos ou travessão logo após o termo — checado sem espaço de sobra."""

_FRASES_DE_EXPLICACAO = (
    "ou seja",
    "isto é",
    "em outras palavras",
    "quer dizer",
    "é a",
    "é o",
    "é uma",
    "é um",
    "são",
    "significa",
    "funciona como",
    "é como",
    "pense em",
    "imagine",
    "parecido com",
    "uma espécie de",
    "chamado de",
    "conhecido como",
    "que é",
    "que são",
)
"""Só minúsculas, acento preservado (achado do revisor de erros, 2026-09-19: sem acento,
"é a"/"são" colidem com a conjunção "e a" e com "São" de topônimo, e quase toda frase com
dois termos do Léxico marcava o primeiro como explicado por acaso)."""


def _padrao_de_marca(marca: str) -> str:
    # Escapa palavra por palavra: escapar a frase inteira de uma vez escaparia também o
    # espaço (re.escape trata ' ' como caractere a escapar nesta versão do Python), o que
    # quebraria o \s+ que devia ficar no lugar dele.
    palavras = marca.split(" ")
    return r"\b" + r"\s+".join(re.escape(p) for p in palavras) + r"\b"


_MARCA_DE_FRASE_REGEX = re.compile("|".join(_padrao_de_marca(m) for m in _FRASES_DE_EXPLICACAO))


def _tem_marca_imediata(resto_da_frase: str) -> bool:
    resto = resto_da_frase.lstrip()
    return bool(resto) and resto[0] in _MARCAS_IMEDIATAS


def _explicado(
    texto_com_acento: str,
    frases: list[tuple[int, int]],
    indice_frase: int,
    fim_do_termo: int,
) -> bool:
    """Mesma frase (depois do termo) ou frase seguinte têm marca de explicação.

    A explicação de uma frase anterior nunca conta — só o que vem depois do termo.
    ``texto_com_acento`` é minúsculo mas com acento — as marcas de explicação dependem
    disso para não colidir com palavras comuns (ver ``_minusculo_com_acento``); os spans
    de frase vêm de ``_normalizar``, mas as duas versões têm o mesmo tamanho, então servem
    nas duas.
    """
    _, fim_frase = frases[indice_frase]
    resto_mesma_frase = texto_com_acento[fim_do_termo:fim_frase]
    if _tem_marca_imediata(resto_mesma_frase):
        return True
    if _MARCA_DE_FRASE_REGEX.search(resto_mesma_frase):
        return True
    if indice_frase + 1 < len(frases):
        inicio_prox, fim_prox = frases[indice_frase + 1]
        proxima_frase = texto_com_acento[inicio_prox:fim_prox]
        if _MARCA_DE_FRASE_REGEX.search(proxima_frase):
            return True
    return False


# ---------------------------------------------------------------------------
# Resolução de sobreposição: termo multi-palavra conta uma vez, não como N palavras
# ---------------------------------------------------------------------------

_Ocorrencia = tuple[int, int, str, bool]  # (inicio, fim, termo canônico, núcleo)


def _resolver_sobreposicoes(candidatos: list[_Ocorrencia]) -> list[_Ocorrencia]:
    """Casamento mais longo vence quando dois padrões disputam o mesmo trecho."""
    ordenados = sorted(candidatos, key=lambda c: (-(c[1] - c[0]), c[0]))
    ocupados: list[tuple[int, int]] = []
    aceitos: list[_Ocorrencia] = []
    for candidato in ordenados:
        inicio, fim = candidato[0], candidato[1]
        if any(inicio < o_fim and fim > o_inicio for o_inicio, o_fim in ocupados):
            continue
        ocupados.append((inicio, fim))
        aceitos.append(candidato)
    aceitos.sort(key=lambda c: c[0])
    return aceitos


def _exige_explicacao(exigencia: ExigenciaDeExplicacao, nucleo: bool) -> bool:
    if exigencia is ExigenciaDeExplicacao.NUNCA:
        return False
    if exigencia is ExigenciaDeExplicacao.SEMPRE:
        return True
    return not nucleo  # FORA_DO_NUCLEO


# ---------------------------------------------------------------------------
# A medição
# ---------------------------------------------------------------------------

_PALAVRA_RE = re.compile(r"\w+", re.UNICODE)


def medir_densidade(texto: str, exigencia: ExigenciaDeExplicacao) -> ResultadoDensidade:
    """Proporção de termos do Léxico no texto e quais violam a Exigência de explicação.

    ``proporcao`` é ``None`` quando o texto não tem palavras — nunca zero por falta de
    base (o Laudo não pode confundir "sem base" com "densidade zero"). Para cada termo
    distinto, só a primeira ocorrência decide ``sem_explicacao``: uma segunda ocorrência
    sem marca não acusa se a primeira já veio explicada.
    """
    total_palavras = len(_PALAVRA_RE.findall(texto))
    if total_palavras == 0:
        return ResultadoDensidade(proporcao=None)

    texto_normalizado = _normalizar(texto)
    texto_com_acento = _minusculo_com_acento(texto)
    frases = _dividir_frases(texto_normalizado)
    inicios_de_frase = [inicio for inicio, _ in frases]

    candidatos: list[_Ocorrencia] = []
    for regex, nome_termo, nucleo in _padroes_compilados():
        for m in regex.finditer(texto_normalizado):
            candidatos.append((m.start(), m.end(), nome_termo, nucleo))

    ocorrencias_aceitas = _resolver_sobreposicoes(candidatos)

    termos_encontrados: list[TermoEncontrado] = []
    primeira_ocorrencia: dict[str, TermoEncontrado] = {}
    ordem_de_aparicao: list[str] = []

    for inicio, fim, nome_termo, nucleo in ocorrencias_aceitas:
        indice_frase = _indice_da_frase(inicios_de_frase, inicio)
        explicado = _explicado(texto_com_acento, frases, indice_frase, fim)
        encontrado = TermoEncontrado(
            termo=nome_termo, posicao=inicio, explicado=explicado, nucleo=nucleo
        )
        termos_encontrados.append(encontrado)
        if nome_termo not in primeira_ocorrencia:
            primeira_ocorrencia[nome_termo] = encontrado
            ordem_de_aparicao.append(nome_termo)

    sem_explicacao = [
        nome_termo
        for nome_termo in ordem_de_aparicao
        if _exige_explicacao(exigencia, primeira_ocorrencia[nome_termo].nucleo)
        and not primeira_ocorrencia[nome_termo].explicado
    ]

    proporcao = len(termos_encontrados) / total_palavras
    return ResultadoDensidade(
        proporcao=proporcao, termos=termos_encontrados, sem_explicacao=sem_explicacao
    )
