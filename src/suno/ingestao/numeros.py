"""Extração determinística de números do texto em português: vírgula decimal, ponto de
milhar, por extenso (text2num), `p.p.` diferente de `%`, `CDI+2%` diferente de
`110% do CDI`, datas (dateparser, pt).

ADR 0011.

A varredura é uma sequência fixa de regras, da mais específica para a mais genérica. Cada
regra consome o trecho que casou, e nenhuma regra posterior volta a olhar para dentro dele:
é o que garante que ``14,00% a.a.`` saia uma vez como ``% a.a.``, e não também como ``%``,
e que o ``2026`` de ``4 e 5 de agosto de 2026`` não vire um ano solto.

## A fronteira (leia antes de supor cobertura)

Este é o lugar onde alguém vai supor cobertura que não existe. O que **não** é extraído:

- **Número por extenso sem unidade.** Só há extração por extenso quando a palavra vem
  seguida de unidade — ``por cento``, ``ponto(s) percentual(is)``, ``pontos-base``,
  ``reais``, ``milhões``, ``bilhões``. "três Formatos", "nove Células" e "duas rodadas"
  não viram números; se virassem, toda Célula reprovaria por contar coisas.
- **Número relativo.** "acima do projetado", "o dobro do trimestre anterior" não entram
  (ADR 0011): não há valor a conferir contra Âncora.
- **Decimal solto, sem unidade.** ``5,1`` sozinho — como nas células da tabela de
  projeções da Ata — não é extraído. Os mesmos valores aparecem no corpo do texto com
  ``%`` e são extraídos lá. Extrair decimal nu faria página, horário e numeração de
  parágrafo virarem número fora das Âncoras.
- **Inteiro solto.** Só dois casos de inteiro sem unidade entram: o ordinal feminino
  (``280ª``, porque a Reunião é feminina) e o ano de quatro dígitos entre 1900 e 2099.
  Ordinal masculino (``8º andar``) fica de fora de propósito: é andar, não medida.
- **Moeda estrangeira.** ``US$2`` não é extraído; só ``R$``.
- **Escala sem moeda.** ``300 milhões`` sem ``R$`` e sem ``reais`` sai como
  ``Unidade.NUMERO`` com o valor já multiplicado (3e8), nunca como ``R$``.

## Qualificador

``CDI+2%`` e ``110% do CDI`` carregam ``qualificador`` (``"CDI+"`` e ``"do CDI"``). Um
número qualificado nunca é igual a outro qualificado diferente, nem ao mesmo número sem
qualificador: são taxas distintas, e a Aderência trata essa diferença como divergência.

## Datas

``data_iso`` sai do ``dateparser`` travado em ``languages=["pt"]``. Quando a expressão
traz mais de um dia ("4 e 5 de agosto de 2026"), vale o **último** — é o dia da decisão do
Copom. Sem ano no texto ("28 de janeiro"), vale ``ano_padrao``; sem ``ano_padrao``, o ano
corrente do relógio, e aí o resultado deixa de ser determinístico — por isso a Aderência
sempre passa o ano das Âncoras. Ano solto ("2026") sai como ``Unidade.DATA`` com
``data_iso`` nulo e ``ano`` preenchido.

## Votos

``7 a 0``, ``7 votos a 0`` e ``por 7 votos a 2`` saem com ``literal`` igual ao trecho
exato do texto (sem o "por"), ``valor`` igual aos votos a favor e ``placar`` com o par.
A comparação na Aderência normaliza o literal, então as três formas casam com a Âncora
``7 a 0``.
"""

from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Callable

import dateparser
from babel.numbers import NumberFormatError, parse_decimal
from text_to_num import text2num

from suno.dominio import Unidade


@dataclass(frozen=True)
class NumeroEncontrado:
    """Um número achado no texto, já normalizado, com de onde ele veio.

    ``texto[inicio:fim] == literal`` sempre: a posição delimita o número como escrito,
    não a unidade que vem depois.
    """

    literal: str
    valor: float | None
    unidade: Unidade
    inicio: int
    fim: int
    trecho: str
    qualificador: str | None = None
    data_iso: date | None = None
    ano: int | None = None
    placar: tuple[float, float] | None = None


# ---------------------------------------------------------------------------
# Peças das regras
# ---------------------------------------------------------------------------

_DIGITOS = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"

_PALAVRAS_DE_NUMERO = (
    "zero", "um", "uma", "dois", "duas", "três", "tres", "quatro", "cinco", "seis",
    "sete", "oito", "nove", "dez", "onze", "doze", "treze", "catorze", "quatorze",
    "quinze", "dezesseis", "dezasseis", "dezessete", "dezoito", "dezenove", "vinte",
    "trinta", "quarenta", "cinquenta", "cinqüenta", "sessenta", "setenta", "oitenta",
    "noventa", "cem", "cento", "duzentos", "duzentas", "trezentos", "trezentas",
    "quatrocentos", "quatrocentas", "quinhentos", "quinhentas", "seiscentos",
    "seiscentas", "setecentos", "setecentas", "oitocentos", "oitocentas", "novecentos",
    "novecentas", "mil", "milhão", "milhao", "milhões", "milhoes", "bilhão", "bilhao",
    "bilhões", "bilhoes", "trilhão", "trilhao", "trilhões", "trilhoes", "meio", "meia",
)
# As mais longas primeiro: senão "dez" casaria dentro de "dezessete".
_UMA_PALAVRA = "(?:" + "|".join(sorted(_PALAVRAS_DE_NUMERO, key=len, reverse=True)) + ")"
_EXTENSO = rf"\b{_UMA_PALAVRA}(?:[ \t-]+(?:e[ \t]+)?{_UMA_PALAVRA})*\b"

_NUMERO = rf"(?:{_DIGITOS}|{_EXTENSO})"

_ESCALAS: dict[str, float] = {
    "mil": 1e3,
    "milhao": 1e6, "milhão": 1e6, "milhoes": 1e6, "milhões": 1e6,
    "bilhao": 1e9, "bilhão": 1e9, "bilhoes": 1e9, "bilhões": 1e9,
    "trilhao": 1e12, "trilhão": 1e12, "trilhoes": 1e12, "trilhões": 1e12,
}
# As longas primeiro: "mil" antes de "milhões" casaria só o prefixo.
_RE_ESCALA = r"milh(?:ão|ao|ões|oes)|bilh(?:ão|ao|ões|oes)|trilh(?:ão|ao|ões|oes)|mil"
_RE_ESCALA_GRANDE = r"milh(?:ão|ao|ões|oes)|bilh(?:ão|ao|ões|oes)|trilh(?:ão|ao|ões|oes)"

# O índice do qualificador começa com maiúscula mesmo quando a regra é case-insensitive.
_INDICE = r"(?-i:[A-ZÀ-Ý][A-Za-zÀ-ÿ0-9\-]{0,15})"

_MESES: dict[str, int] = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5,
    "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12,
}
_RE_MES = "|".join(sorted(_MESES, key=len, reverse=True))

# text2num só aceita a grafia acentuada; texto de PDF às vezes perde o acento.
_ACENTOS_DE_NUMERO = {
    "tres": "três", "milhao": "milhão", "milhoes": "milhões", "bilhao": "bilhão",
    "bilhoes": "bilhões", "trilhao": "trilhão", "trilhoes": "trilhões",
}

_VOTOS_MAXIMOS = 11
"""Teto de votos num colegiado do Copom. Acima disso, ``7 a 0`` seria outra coisa."""


# ---------------------------------------------------------------------------
# Normalização de valor
# ---------------------------------------------------------------------------


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def _valor_por_extenso(frase: str) -> float | None:
    """``quinze`` → 15.0. ``meio`` → 0.5, que o text2num não conhece."""
    limpa = re.sub(r"[\s-]+", " ", frase.strip().lower())
    sobra = 0.0
    if limpa in {"meio", "meia"}:
        return 0.5
    if limpa.endswith(" e meio") or limpa.endswith(" e meia"):
        limpa, sobra = limpa[: -len(" e meio")], 0.5
    for errado, certo in _ACENTOS_DE_NUMERO.items():
        limpa = re.sub(rf"\b{errado}\b", certo, limpa)
    try:
        return float(text2num(limpa, "pt")) + sobra
    except ValueError:
        return None


def _valor_do_literal(bruto: str) -> float | None:
    """Vírgula decimal e ponto de milhar pelo Babel; o resto por extenso."""
    bruto = bruto.strip()
    if re.fullmatch(r"[\d.,]+", bruto):
        try:
            return float(parse_decimal(bruto, locale="pt_BR"))
        except (NumberFormatError, ValueError):
            return None
    return _valor_por_extenso(bruto)


def _com_escala(valor: float | None, escala: str | None) -> float | None:
    if valor is None or not escala:
        return valor
    return valor * _ESCALAS[escala.strip().lower()]


# ---------------------------------------------------------------------------
# A frase de onde o número veio
# ---------------------------------------------------------------------------

_FIM_DE_FRASE = re.compile(
    r"(?<=[.!?:;])\s+(?=[A-ZÀ-Ý0-9(\"“])"  # pontuação seguida de começo de frase
    r"|\n[ \t]*\n\s*"  # linha em branco
)


def _limites_das_frases(texto: str) -> list[tuple[int, int]]:
    limites: list[tuple[int, int]] = []
    inicio = 0
    for separador in _FIM_DE_FRASE.finditer(texto):
        limites.append((inicio, separador.start()))
        inicio = separador.end()
    limites.append((inicio, len(texto)))
    return [(a, b) for a, b in limites if b > a]


def _frase_em(limites: list[tuple[int, int]], comecos: list[int], texto: str, posicao: int) -> str:
    indice = max(0, bisect_right(comecos, posicao) - 1)
    a, b = limites[indice]
    return re.sub(r"\s+", " ", texto[a:b]).strip()


# ---------------------------------------------------------------------------
# As regras, da mais específica para a mais genérica
# ---------------------------------------------------------------------------

_Regra = tuple[re.Pattern[str], Callable[[re.Match[str], int | None], "NumeroEncontrado | None"]]


def _simples(unidade: Unidade, escalar: bool = False) -> Callable[..., NumeroEncontrado | None]:
    """Fábrica das regras em que só o grupo ``numero`` (mais escala e sinal) interessa.

    O grupo ``sinal`` é opcional e só existe nos padrões que o declaram (p.p. e pb — onde a
    direção da mudança é o que a Aderência precisa distinguir); nos outros, ``groupdict``
    simplesmente não tem a chave, e o comportamento é o de sempre.
    """

    def regra(achado: re.Match[str], _ano_padrao: int | None) -> NumeroEncontrado | None:
        escala = achado.groupdict().get("escala") if escalar else None
        valor = _com_escala(_valor_do_literal(achado.group("numero")), escala)
        if valor is None:
            return None
        sinal = achado.groupdict().get("sinal")
        if sinal == "-":
            valor = -valor
        inicio = achado.start("sinal") if sinal else achado.start("numero")
        fim = achado.end("escala") if escala else achado.end("numero")
        return NumeroEncontrado(
            literal=achado.string[inicio:fim],
            valor=valor,
            unidade=unidade,
            inicio=inicio,
            fim=fim,
            trecho="",
        )

    return regra


def _regra_data(achado: re.Match[str], ano_padrao: int | None) -> NumeroEncontrado | None:
    dias = re.findall(r"\d{1,2}", achado.group("dias"))
    mes = achado.group("mes").lower()
    ano_texto = achado.group("ano")
    ano = int(ano_texto) if ano_texto else (ano_padrao or datetime.now().year)
    # O dateparser resolve mês por extenso; o dia sai da regra, porque em "4 e 5 de
    # agosto" a biblioteca ora devolve o primeiro, ora o último (verificado em 1.4.3).
    resolvida = dateparser.parse(
        f"{dias[-1]} de {mes} de {ano}",
        languages=["pt"],
        settings={"RELATIVE_BASE": datetime(ano, 1, 1)},
    )
    if resolvida is None:
        return None
    return NumeroEncontrado(
        literal=achado.group(0),
        valor=None,
        unidade=Unidade.DATA,
        inicio=achado.start(0),
        fim=achado.end(0),
        trecho="",
        data_iso=resolvida.date(),
        ano=resolvida.year,
    )


def _regra_votos(achado: re.Match[str], _ano_padrao: int | None) -> NumeroEncontrado | None:
    favor, contra = int(achado.group("favor")), int(achado.group("contra"))
    if favor > _VOTOS_MAXIMOS or contra > _VOTOS_MAXIMOS:
        return None
    return NumeroEncontrado(
        literal=achado.group(0),
        valor=float(favor),
        unidade=Unidade.VOTOS,
        inicio=achado.start(0),
        fim=achado.end(0),
        trecho="",
        placar=(float(favor), float(contra)),
    )


def _regra_ano(achado: re.Match[str], _ano_padrao: int | None) -> NumeroEncontrado | None:
    ano = int(achado.group("numero"))
    return NumeroEncontrado(
        literal=achado.group("numero"),
        valor=float(ano),
        unidade=Unidade.DATA,
        inicio=achado.start("numero"),
        fim=achado.end("numero"),
        trecho="",
        ano=ano,
    )


def _com_qualificador(
    unidade: Unidade, monta: Callable[[re.Match[str]], str]
) -> Callable[..., NumeroEncontrado | None]:
    def regra(achado: re.Match[str], _ano_padrao: int | None) -> NumeroEncontrado | None:
        valor = _valor_do_literal(achado.group("numero"))
        if valor is None:
            return None
        return NumeroEncontrado(
            literal=achado.group("numero"),
            valor=valor,
            unidade=unidade,
            inicio=achado.start("numero"),
            fim=achado.end("numero"),
            trecho="",
            qualificador=monta(achado),
        )

    return regra


_REGRAS: tuple[_Regra, ...] = (
    # Data primeiro: "4 de agosto de 2026" não pode virar um placar de votação nem um ano solto.
    (
        re.compile(
            rf"\b(?P<dias>\d{{1,2}}(?:\s*(?:,|e|a)\s*\d{{1,2}})*)\s+de\s+(?P<mes>{_RE_MES})"
            rf"(?:\s+de\s+(?P<ano>\d{{4}}))?",
            re.IGNORECASE,
        ),
        _regra_data,
    ),
    # Os dois qualificadores (CDI+2% / 110% do CDI) vêm antes de qualquer regra de "%" nua:
    # cada uma reivindica o `%` primeiro, senão a regra genérica consome o número e o
    # sinal "+"/o "do CDI" nunca chega a ser lido — achado do revisor de erros, 2026-09-19
    # ("o CDI+2% ao ano" perdia o qualificador para a regra de "% a.a.").
    (
        re.compile(rf"\b(?P<indice>{_INDICE})\s*\+\s*(?P<numero>{_NUMERO})\s*%", re.IGNORECASE),
        _com_qualificador(Unidade.PERCENTUAL, lambda a: f"{a.group('indice')}+"),
    ),
    (
        re.compile(
            rf"(?P<numero>{_NUMERO})\s*%\s+(?P<preposicao>do|da|dos|das)\s+(?P<indice>{_INDICE})\b",
            re.IGNORECASE,
        ),
        _com_qualificador(
            Unidade.PERCENTUAL, lambda a: f"{a.group('preposicao').lower()} {a.group('indice')}"
        ),
    ),
    (
        re.compile(
            rf"(?P<numero>{_NUMERO})\s*(?:%|por\s+cento)\s*(?:a\.\s?a\.|ao\s+ano)", re.IGNORECASE
        ),
        _simples(Unidade.PERCENTUAL_AO_ANO),
    ),
    # `pp`/`pb`/`bps` costumam vir colados ao número ("50pb", "0,25pp"), sem espaço — entre um
    # dígito e uma letra não há `\b` (os dois são caractere de palavra), então o `\b` à
    # esquerda destas abreviações nunca casava esse caso (achado do revisor de erros,
    # 2026-09-19; `\b` continua à direita, para não engolir o começo de outra palavra). O
    # sinal opcional na frente ("+0,25 p.p." ≠ "-0,25 p.p.") é o que separa alta de corte.
    (
        re.compile(
            rf"(?:(?P<sinal>[+-])\s*)?(?P<numero>{_NUMERO})\s*"
            r"(?:p\.\s?p\.?|pp\b|pontos?\s+percentua(?:l|is))",
            re.IGNORECASE,
        ),
        _simples(Unidade.PONTO_PERCENTUAL),
    ),
    (
        re.compile(
            rf"(?:(?P<sinal>[+-])\s*)?(?P<numero>{_NUMERO})\s*"
            r"(?:pontos?[-\s]+base|pb\b|p\.b\.|bps\b)",
            re.IGNORECASE,
        ),
        _simples(Unidade.PONTOS_BASE),
    ),
    (
        re.compile(
            rf"R\$\s*(?P<numero>{_NUMERO})(?:\s*(?P<escala>{_RE_ESCALA})\b)?", re.IGNORECASE
        ),
        _simples(Unidade.REAIS, escalar=True),
    ),
    (
        re.compile(
            rf"(?P<numero>{_NUMERO})(?:\s*(?P<escala>{_RE_ESCALA})\b)?\s+(?:de\s+)?reais\b",
            re.IGNORECASE,
        ),
        _simples(Unidade.REAIS, escalar=True),
    ),
    (
        re.compile(rf"(?P<numero>{_NUMERO})\s*(?:%|por\s+cento)", re.IGNORECASE),
        _simples(Unidade.PERCENTUAL),
    ),
    # Votos por último entre os numéricos: "de 2 a 3 anos" e "3 a 4 pontos percentuais" têm a
    # forma `N a M` que a regra de votos casava cega, antes de pp/%/ano — a que reclama a
    # unidade certa primeiro fica com o número, e "N a M" sem unidade nenhuma depois (o
    # placar de verdade, "7 a 0") é o que sobra (achado do revisor de erros, 2026-09-19).
    (
        re.compile(
            r"\b(?P<favor>\d{1,2})\s+(?:votos?\s+)?a\s+(?P<contra>\d{1,2})\b"
            # "2 a 3 anos"/"3 a 4 pontos" não são placar: um intervalo de verdade é seguido de
            # unidade, um placar não é seguido de nada (ou pontuação). A reordenação acima já
            # resolve quando a unidade casa um padrão próprio (pp/pb/%); esta negativa cobre o
            # resto ("anos", "meses", "dias" não têm regra própria neste módulo).
            r"(?!\s*(?:anos?|meses|dias|semanas|%|p\.\s?p\.?|pp\b|pontos?)\b)",
            re.IGNORECASE,
        ),
        _regra_votos,
    ),
    (
        re.compile(rf"(?P<numero>{_NUMERO})\s+(?P<escala>{_RE_ESCALA_GRANDE})\b", re.IGNORECASE),
        _simples(Unidade.NUMERO, escalar=True),
    ),
    (re.compile(r"(?P<numero>\d{1,4})ª"), _simples(Unidade.NUMERO)),
    (re.compile(r"\b(?P<numero>(?:19|20)\d{2})\b"), _regra_ano),
)


# ---------------------------------------------------------------------------
# A varredura
# ---------------------------------------------------------------------------


def extrair_numeros(texto: str, *, ano_padrao: int | None = None) -> list[NumeroEncontrado]:
    """Todos os números do texto, em ordem de posição. Sem LLM e sem rede (ADR 0011).

    ``ano_padrao`` completa data sem ano ("28 de janeiro"); passe o ano da Ata para que o
    resultado não dependa do relógio.
    """
    if not texto:
        return []
    limites = _limites_das_frases(texto)
    comecos = [a for a, _ in limites]
    ocupado: list[tuple[int, int]] = []
    achados: list[NumeroEncontrado] = []
    for padrao, monta in _REGRAS:
        for casado in padrao.finditer(texto):
            if any(casado.start(0) < fim and inicio < casado.end(0) for inicio, fim in ocupado):
                continue
            numero = monta(casado, ano_padrao)
            if numero is None:
                continue
            ocupado.append((casado.start(0), casado.end(0)))
            achados.append(
                replace(numero, trecho=_frase_em(limites, comecos, texto, numero.inicio))
            )
    achados.sort(key=lambda n: (n.inicio, n.fim))
    return achados


def normalizar_placar(literal: str) -> str:
    """``por 7 votos a 0`` → ``7 a 0``: a forma que a Aderência compara."""
    limpo = _sem_acento(literal).lower()
    limpo = re.sub(r"\b(por|votos?)\b", " ", limpo)
    return re.sub(r"\s+", " ", limpo).strip()


def mes_e_ano_no_literal(literal: str, quando: date) -> bool:
    """O literal cita o mês e o ano desta data? É como uma data casa sem ``data_iso``."""
    limpo = _sem_acento(literal).lower()
    nomes = {_sem_acento(nome) for nome, indice in _MESES.items() if indice == quando.month}
    return str(quando.year) in limpo and any(nome in limpo for nome in nomes)
