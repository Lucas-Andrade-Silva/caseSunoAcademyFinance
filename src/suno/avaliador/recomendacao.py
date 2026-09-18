"""Recomendação detectada por Léxico (pode / não pode) mais padrão sintático sobre POS
tagging do spaCy (`pt_core_news_sm`, offline). Nunca por LLM. O canary set em
data/canary/ é a regressão contra paráfrase.

ADR 0012.

As duas camadas somam, não se substituem:

- **Léxico** (`data/canary/padroes.yaml`, bloco ``nao_pode``): expressões literais, com
  o bloco ``pode`` funcionando como allowlist. Pega a Recomendação escrita com todas as
  letras e, principalmente, as fórmulas fixas ("é hora de", "oportunidade de compra")
  que nenhuma análise sintática reconheceria como direção de ação.
- **Sintaxe** (mesmo arquivo, bloco ``sintaxe``): sujeito dirigido ao leitor + modal de
  obrigação ou conveniência + verbo de ação financeira, sobre ``pos_``, ``dep_``,
  ``lemma_`` e ``morph``. É o que pega a paráfrase — "seria prudente considerar reduzir
  posição" não tem uma palavra proibida.

Nada aqui depende de rede: o modelo do spaCy vem instalado como wheel (ver
pyproject.toml) e é carregado uma vez, em cache de módulo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal

import spacy
import yaml
from spacy.language import Language
from spacy.tokens import Span, Token

RAIZ = Path(__file__).resolve().parents[3]
PASTA_DO_CANARY = RAIZ / "data" / "canary"
ARQUIVO_DE_PADROES = PASTA_DO_CANARY / "padroes.yaml"
ARQUIVO_DO_CANARY = PASTA_DO_CANARY / "canary.yaml"

NOME_DO_MODELO = "pt_core_news_sm"
"""O único modelo. Wheel fixada no pyproject.toml; `spacy.load` não vai à rede."""

Camada = Literal["lexico", "sintaxe"]

_VERBAIS = frozenset({"VERB", "AUX"})
_NOMINAIS = frozenset({"NOUN", "PROPN"})
_ANTES_QUE_NOMINALIZA = frozenset({"DET", "ADP", "NUM"})
"""Palavra anterior que transforma imperativo em substantivo: "a venda", "de resgate"."""

_LETRA = r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]"


@dataclass(frozen=True)
class Ocorrencia:
    """Uma Recomendação encontrada: onde, por qual padrão, e em que camada.

    ``padrao`` é o nome do bloco em padroes.yaml, para o Laudo dizer o que reprovou e
    para o canary contar fuga por padrão.
    """

    frase: str
    padrao: str
    trecho: str
    camada: Camada = "lexico"


@dataclass(frozen=True)
class CasoDoCanary:
    """Uma linha de data/canary/canary.yaml."""

    texto: str
    deve_acusar: bool
    por_que: str
    sem_cobertura: str | None = None


# ---------------------------------------------------------------------------
# Carga do Léxico e dos padrões
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Expressao:
    """Uma entrada do Léxico já compilada."""

    padrao: str
    texto: str
    regex: re.Pattern[str]
    palavra_unica: bool


@dataclass(frozen=True)
class _Padroes:
    """padroes.yaml em memória. Imutável: a detecção precisa ser determinística."""

    proibidas: tuple[_Expressao, ...]
    permitidas: tuple[_Expressao, ...]
    conveniencia: tuple[_Expressao, ...]
    lemas_acao: frozenset[str]
    sintagmas: tuple[tuple[str, str], ...]
    lemas_de_movimentacao: frozenset[str]
    modais: frozenset[str]
    favorecimento: frozenset[str]
    pronomes: frozenset[str]
    relativos: frozenset[str]
    substantivos_de_sujeito: frozenset[str]
    possessivos: frozenset[str]
    patrimonio: frozenset[str]
    bruto: dict[str, Any] = field(default_factory=dict, repr=False)


def _compilar(expressao: str) -> re.Pattern[str]:
    """Casa palavra inteira, sem diferenciar caixa, com espaço flexível.

    O espaço vira ``\\s+`` porque a Ata sai do PDF com a frase partida em duas linhas.
    Acento é significativo: sem ele, "é hora de" casaria com "data e hora de".
    """
    corpo = r"\s+".join(re.escape(parte) for parte in expressao.split())
    return re.compile(rf"(?<!{_LETRA}){corpo}(?!{_LETRA})", re.IGNORECASE)


def _expressoes(bloco: dict[str, Any]) -> tuple[_Expressao, ...]:
    achadas: list[_Expressao] = []
    for nome, corpo in bloco.items():
        for texto in corpo.get("expressoes", ()):
            achadas.append(
                _Expressao(
                    padrao=nome,
                    texto=texto,
                    regex=_compilar(texto),
                    palavra_unica=len(texto.split()) == 1,
                )
            )
    return tuple(achadas)


@lru_cache(maxsize=1)
def _padroes() -> _Padroes:
    bruto = yaml.safe_load(ARQUIVO_DE_PADROES.read_text(encoding="utf-8"))
    gatilhos = bruto["gatilhos"]
    sujeito = bruto["sujeito_dirigido"]
    conveniencia = tuple(
        _Expressao(
            padrao="conveniencia_impessoal",
            texto=texto,
            regex=_compilar(texto),
            palavra_unica=len(texto.split()) == 1,
        )
        for texto in gatilhos["conveniencia_impessoal"]
    )
    return _Padroes(
        proibidas=_expressoes(bruto["nao_pode"]),
        permitidas=_expressoes(bruto["pode"]),
        conveniencia=conveniencia,
        lemas_acao=frozenset(bruto["lemas_acao"]),
        sintagmas=tuple((s["verbo"], s["nucleo"]) for s in bruto["sintagmas_acao"]),
        lemas_de_movimentacao=frozenset(bruto["lemas_de_movimentacao"]),
        modais=frozenset(gatilhos["modais_por_lema"]),
        favorecimento=frozenset(gatilhos["verbos_de_favorecimento"]),
        pronomes=frozenset(sujeito["pronomes"]),
        relativos=frozenset(sujeito["relativo"]),
        substantivos_de_sujeito=frozenset(sujeito["substantivos"]),
        possessivos=frozenset(sujeito["possessivos"]),
        patrimonio=frozenset(bruto["substantivos_de_patrimonio"]),
        bruto=bruto,
    )


@lru_cache(maxsize=1)
def _modelo() -> Language:
    """Carregado uma vez por processo. Offline: a wheel do modelo já está instalada."""
    return spacy.load(NOME_DO_MODELO)


def carregar_padroes() -> dict[str, Any]:
    """padroes.yaml cru, para quem precisa documentar ou conferir o Léxico."""
    return _padroes().bruto


def casos_do_canary() -> list[CasoDoCanary]:
    """As armadilhas e as neutras, na ordem do arquivo."""
    bruto = yaml.safe_load(ARQUIVO_DO_CANARY.read_text(encoding="utf-8"))
    casos: list[CasoDoCanary] = []
    for chave in ("armadilhas", "neutras"):
        for linha in bruto.get(chave, ()):
            casos.append(
                CasoDoCanary(
                    texto=linha["texto"],
                    deve_acusar=bool(linha["deve_acusar"]),
                    por_que=linha["por_que"],
                    sem_cobertura=linha.get("sem_cobertura"),
                )
            )
    return casos


# ---------------------------------------------------------------------------
# Camada 1 — Léxico
# ---------------------------------------------------------------------------


def _e_substantivo_ali(frase: Span, inicio: int, fim: int) -> bool:
    """"a venda de ativos" não é imperativo de venda; "venda agora" é.

    O pt_core_news_sm erra muito o imperativo — chega a marcar "Venda" como NOUN e
    "Mantenha" como PROPN —, então não dá para exigir ``Mood=Imp``. O que separa os dois
    casos com segurança é o determinante à esquerda.
    """
    doc = frase.doc
    span = doc.char_span(inicio, fim, alignment_mode="expand")
    if span is None or len(span) == 0:
        return False
    alvo = span[0]
    anterior = doc[alvo.i - 1] if alvo.i > frase.start else None
    if anterior is not None and anterior.pos_ in _ANTES_QUE_NOMINALIZA:
        return True
    if alvo.pos_ in _NOMINAIS:
        return any(filho.dep_ == "det" and filho.i < alvo.i for filho in alvo.children)
    return False


def _achados_do_lexico(frase: Span, padroes: _Padroes) -> Iterator[tuple[int, int, str]]:
    deslocamento = frase.start_char
    for expressao in padroes.proibidas:
        for casado in expressao.regex.finditer(frase.text):
            inicio = deslocamento + casado.start()
            fim = deslocamento + casado.end()
            if expressao.palavra_unica and _e_substantivo_ali(frase, inicio, fim):
                continue
            yield inicio, fim, expressao.padrao


def _spans_permitidos(frase: Span, padroes: _Padroes) -> list[tuple[int, int]]:
    """O bloco ``pode``: trecho que cai aqui dentro não vira Ocorrência."""
    deslocamento = frase.start_char
    return [
        (deslocamento + casado.start(), deslocamento + casado.end())
        for expressao in padroes.permitidas
        for casado in expressao.regex.finditer(frase.text)
    ]


# ---------------------------------------------------------------------------
# Camada 2 — padrões sintáticos
# ---------------------------------------------------------------------------


def _e_infinitivo(token: Token) -> bool:
    return "Inf" in token.morph.get("VerbForm")


def _acoes_no_infinitivo(frase: Span, padroes: _Padroes) -> list[Token]:
    return [
        token
        for token in frase
        if token.pos_ in _VERBAIS
        and _e_infinitivo(token)
        and token.lemma_.lower() in padroes.lemas_acao
    ]


def _sintagmas_de_acao(frase: Span, padroes: _Padroes) -> list[Token]:
    """Verbo genérico só conta com o núcleo certo: "ter" não é ação, "ter na carteira" é."""
    achados: list[Token] = []
    for token in frase:
        if token.pos_ not in _VERBAIS:
            continue
        lema = token.lemma_.lower()
        for verbo, nucleo in padroes.sintagmas:
            if lema != verbo:
                continue
            if any(f.lemma_.lower() == nucleo for f in token.subtree if f is not token):
                achados.append(token)
                break
    return achados


def _acoes(frase: Span, padroes: _Padroes) -> list[Token]:
    achados = {t.i: t for t in _acoes_no_infinitivo(frase, padroes)}
    achados.update({t.i: t for t in _sintagmas_de_acao(frase, padroes)})
    return [achados[i] for i in sorted(achados)]


def _sujeitos_dirigidos(frase: Span, padroes: _Padroes) -> list[Token]:
    """Onde o leitor aparece como quem age: "você", "quem investe", "o investidor", "sua carteira"."""
    achados: list[Token] = []
    for token in frase:
        lema = token.lemma_.lower()
        if token.pos_ == "PRON" and lema in padroes.pronomes:
            achados.append(token)
        elif token.pos_ == "PRON" and lema in padroes.relativos and token.dep_.startswith("nsubj"):
            achados.append(token)
        elif (
            token.pos_ in _NOMINAIS
            and lema in padroes.substantivos_de_sujeito
            and token.dep_.startswith("nsubj")
        ):
            achados.append(token)
        elif (
            token.pos_ == "DET"
            and lema in padroes.possessivos
            and token.head.lemma_.lower() in padroes.patrimonio
        ):
            achados.append(token)
    return achados


def _limites(tokens: Iterable[Token]) -> tuple[int, int]:
    tokens = list(tokens)
    return min(t.idx for t in tokens), max(t.idx + len(t.text) for t in tokens)


def _modal_com_sujeito_dirigido(
    frase: Span, padroes: _Padroes
) -> Iterator[tuple[int, int, str]]:
    """O padrão central do ADR 0012: leitor no sujeito + modal + ação financeira."""
    sujeitos = _sujeitos_dirigidos(frase, padroes)
    if not sujeitos:
        return
    modais = [
        t for t in frase if t.pos_ in _VERBAIS and t.lemma_.lower() in padroes.modais
    ]
    if not modais:
        return
    acoes = [t for t in _acoes(frase, padroes) if t.lemma_.lower() not in padroes.modais]
    if not acoes:
        return
    inicio, fim = _limites([sujeitos[0], modais[0], acoes[0]])
    yield inicio, fim, "modal_com_sujeito_dirigido"


def _conveniencia_impessoal(frase: Span, padroes: _Padroes) -> Iterator[tuple[int, int, str]]:
    """Sem sujeito escrito: "seria prudente considerar reduzir posição" é sobre o leitor."""
    acoes = _acoes(frase, padroes)
    if not acoes:
        return
    deslocamento = frase.start_char
    for expressao in padroes.conveniencia:
        casado = expressao.regex.search(frase.text)
        if casado is None:
            continue
        inicio = deslocamento + casado.start()
        fim = deslocamento + casado.end()
        depois = [t for t in acoes if t.idx >= fim]
        if not depois:
            continue
        yield inicio, depois[0].idx + len(depois[0].text), "conveniencia_impessoal"
        return


def _imperativo_sobre_patrimonio(
    frase: Span, padroes: _Padroes
) -> Iterator[tuple[int, int, str]]:
    """Verbo finito sem sujeito mandando mexer no que é do leitor."""
    for token in frase:
        if token.pos_ not in _VERBAIS or "Fin" not in token.morph.get("VerbForm"):
            continue
        if not set(token.morph.get("Mood")) & {"Imp", "Sub"}:
            continue
        if any(filho.dep_.startswith("nsubj") for filho in token.children):
            continue
        lema = token.lemma_.lower()
        if lema not in padroes.lemas_acao and lema not in padroes.lemas_de_movimentacao:
            continue
        for filho in token.subtree:
            if (
                filho.pos_ == "DET"
                and filho.lemma_.lower() in padroes.possessivos
                and filho.head.lemma_.lower() in padroes.patrimonio
            ):
                inicio, fim = _limites([token, filho.head])
                yield inicio, fim, "imperativo_sobre_patrimonio"
                return


def _voz_editorial_com_acao(frase: Span, padroes: _Padroes) -> Iterator[tuple[int, int, str]]:
    """Primeira pessoa do plural assinando a direção: "nossa posição é comprar"."""
    marcas = [
        token
        for token in frase
        if (token.pos_ == "DET" and token.lemma_.lower() == "nosso")
        or (
            token.pos_ in _VERBAIS
            and "1" in token.morph.get("Person")
            and "Plur" in token.morph.get("Number")
        )
    ]
    if not marcas:
        return
    acoes = _acoes(frase, padroes)
    if not acoes:
        return
    inicio, fim = _limites([marcas[0], acoes[0]])
    yield inicio, fim, "voz_editorial_com_acao"


def _favorecimento_de_quem_age(
    frase: Span, padroes: _Padroes
) -> Iterator[tuple[int, int, str]]:
    """"O cenário favorece quem se posiciona": a direção vai para o cenário, o leitor fica."""
    for token in frase:
        if token.pos_ not in _VERBAIS or token.lemma_.lower() not in padroes.favorecimento:
            continue
        for filho in token.subtree:
            if not (filho.lemma_.lower() in padroes.relativos and filho.dep_.startswith("nsubj")):
                continue
            alvo = filho.head
            if alvo.lemma_.lower() in padroes.lemas_acao:
                inicio, fim = _limites([token, alvo])
                yield inicio, fim, "favorecimento_de_quem_age"
                return


_PADROES_SINTATICOS = (
    _modal_com_sujeito_dirigido,
    _conveniencia_impessoal,
    _imperativo_sobre_patrimonio,
    _voz_editorial_com_acao,
    _favorecimento_de_quem_age,
)


def _achados_da_sintaxe(frase: Span, padroes: _Padroes) -> Iterator[tuple[int, int, str]]:
    for padrao in _PADROES_SINTATICOS:
        yield from padrao(frase, padroes)


# ---------------------------------------------------------------------------
# A porta de entrada
# ---------------------------------------------------------------------------


def _permitido(inicio: int, fim: int, permitidos: list[tuple[int, int]]) -> bool:
    return any(inicio < f and i < fim for i, f in permitidos)


def detectar_recomendacao(texto: str) -> list[Ocorrencia]:
    """Lista vazia = sem Recomendação. Qualquer ocorrência reprova a Célula."""
    if not texto or not texto.strip():
        return []
    padroes = _padroes()
    doc = _modelo()(texto)
    vistos: set[tuple[int, str, str]] = set()
    achadas: list[tuple[int, Ocorrencia]] = []
    for frase in doc.sents:
        permitidos = _spans_permitidos(frase, padroes)
        candidatos = [
            (inicio, fim, padrao, camada)
            for camada, gerador in (
                ("lexico", _achados_do_lexico),
                ("sintaxe", _achados_da_sintaxe),
            )
            for inicio, fim, padrao in gerador(frase, padroes)
        ]
        for inicio, fim, padrao, camada in candidatos:
            if _permitido(inicio, fim, permitidos):
                continue
            trecho = doc.text[inicio:fim]
            chave = (inicio, padrao, trecho)
            if chave in vistos:
                continue
            vistos.add(chave)
            achadas.append(
                (
                    inicio,
                    Ocorrencia(
                        frase=frase.text.strip(),
                        padrao=padrao,
                        trecho=trecho,
                        camada=camada,  # type: ignore[arg-type]
                    ),
                )
            )
    achadas.sort(key=lambda par: (par[0], par[1].padrao))
    return [ocorrencia for _, ocorrencia in achadas]


def ha_recomendacao(texto: str) -> bool:
    """Atalho para o Laudo: a métrica Recomendação é binária."""
    return bool(detectar_recomendacao(texto))
