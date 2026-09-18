"""Calibração (H2): o formato do arquivo de Células rotuladas à mão, o Kappa de Cohen e a
matriz de confusão por Audiência. Não inventa rótulo humano.

ADR 0002, 0003.

Duas matrizes de confusão convivem aqui, e confundi-las seria o erro grave:

- ``matriz_de_confusao`` lê o CSV que as duas pessoas do time preencheram à mão. É a
  Calibração de verdade, e só existe depois que alguém rotulou. O formato está em
  ``data/calibracao/FORMATO.md``.
- ``matriz_de_confusao_da_execucao`` **não tem rótulo humano nenhum**: cruza a Audiência
  pretendida de cada Célula com a Audiência em que o Flesch-BR medido a colocaria, pelas
  faixas do NILC (``LIMIARES_PROVISORIOS``). É a matriz que o relatório mostra hoje, e ela
  sai marcada com ``ORIGEM_AUTOMATICA`` justamente para ninguém a citar como concordância
  humana.

O Kappa alvo é 0,6–0,8 (ADR 0002): abaixo disso os Limiares não estão sustentados por
rótulo, e acima de 0,8 em ~30 Células é sinal de que as duas pessoas rotularam juntas em
vez de às cegas.
"""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence

from suno.avaliador.flesch_br import faixa_nilc, flesch_br
from suno.dominio import (
    LIMIARES_PROVISORIOS,
    Audiencia,
    Execucao,
    HistoricoCelula,
    Metrica,
)

SEPARADOR = ";"
"""Ponto e vírgula: é o que o Excel em português escreve e lê sem perguntar nada."""

CODIFICACAO = "utf-8-sig"
"""Tolera o BOM que o Excel do Windows põe no começo do arquivo salvo como CSV UTF-8."""

COLUNAS: tuple[str, ...] = (
    "execucao",
    "audiencia",
    "formato",
    "rodada",
    "pessoa",
    "audiencia_percebida",
    "aprovaria",
    "motivo",
    "observacao",
)
"""O cabeçalho exato de ``data/calibracao/rotulos.csv``. Ver FORMATO.md."""

PESSOA_DE_EXEMPLO = "exemplo"
"""Linha com esta pessoa é modelo de formato, nunca Calibração. Ver FORMATO.md."""

SEM_BASE = "ausente"
"""Rótulo de linha/coluna para a Célula sem base de medida — nunca zero (ADR 0008)."""

ORIGEM_AUTOMATICA = "NILC, aguardando Calibração"
"""Carimbo da matriz derivada do Flesch-BR. Igual ao ``Limiares.origem`` do domínio."""

KAPPA_ALVO: tuple[float, float] = (0.6, 0.8)
"""Faixa de concordância que o ADR 0002 põe como alvo para as ~30 Células rotuladas."""


# ---------------------------------------------------------------------------
# Kappa de Cohen
# ---------------------------------------------------------------------------


def kappa_cohen(rotulos_a: Sequence[str], rotulos_b: Sequence[str]) -> float:
    """Concordância entre duas pessoas descontado o acaso, para categorias quaisquer.

    ``κ = (po - pe) / (1 - pe)``, com ``po`` a concordância observada e ``pe`` a esperada
    se as duas rotulassem de forma independente, com as frequências marginais de cada uma.

    Devolve ``float("nan")`` quando não há base: nenhuma Célula rotulada, ou as duas
    pessoas usaram uma categoria só — aí ``pe`` é 1, não há acaso a descontar, e a divisão
    não existe. Zero seria uma mentira confortável: diria "discordam totalmente" onde o
    certo é "não dá para dizer".
    """
    if len(rotulos_a) != len(rotulos_b):
        raise ValueError(
            f"as duas listas precisam ter o mesmo tamanho: {len(rotulos_a)} != {len(rotulos_b)}"
        )
    total = len(rotulos_a)
    if total == 0:
        return math.nan

    observada = sum(1 for a, b in zip(rotulos_a, rotulos_b) if a == b) / total

    contagem_a = Counter(rotulos_a)
    contagem_b = Counter(rotulos_b)
    categorias = set(contagem_a) | set(contagem_b)
    esperada = sum(contagem_a[c] * contagem_b[c] for c in categorias) / (total * total)

    if math.isclose(esperada, 1.0):
        return math.nan
    return (observada - esperada) / (1.0 - esperada)


def dentro_do_alvo(kappa: float) -> bool:
    """O Kappa está na faixa que o ADR 0002 pede? ``nan`` nunca está."""
    if math.isnan(kappa):
        return False
    return KAPPA_ALVO[0] <= kappa <= KAPPA_ALVO[1]


# ---------------------------------------------------------------------------
# O arquivo de rótulos
# ---------------------------------------------------------------------------


def ler_rotulos(caminho: Path, *, pessoa: str | None = None) -> list[dict[str, str]]:
    """As linhas do CSV de Calibração, na ordem do arquivo, sem nenhuma interpretação.

    ``pessoa`` filtra por quem rotulou. Linha sem ``audiencia_percebida`` preenchida fica:
    quem decide o que fazer com Célula não rotulada é quem chama.
    """
    with caminho.open("r", encoding=CODIFICACAO, newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=SEPARADOR)
        faltantes = [c for c in COLUNAS if c not in (leitor.fieldnames or [])]
        if faltantes:
            raise ValueError(f"{caminho.name} está sem as colunas {faltantes}; ver FORMATO.md")
        linhas = [
            {coluna: (linha.get(coluna) or "").strip() for coluna in COLUNAS} for linha in leitor
        ]
    if pessoa is not None:
        linhas = [linha for linha in linhas if linha["pessoa"] == pessoa]
    return linhas


def matriz_de_confusao(caminho: Path, *, pessoa: str | None = None) -> dict[str, dict[str, int]]:
    """Audiência pretendida × Audiência percebida, lida do CSV de Calibração.

    ``{pretendida: {percebida: n}}``, com as três Audiências sempre presentes e zeradas,
    para a matriz ter a mesma forma em toda execução — comparar duas rodadas de Calibração
    não pode depender de qual categoria apareceu. Sem ``pessoa``, agrega todo mundo.
    """
    return _matriz(
        (linha["audiencia"], linha["audiencia_percebida"])
        for linha in ler_rotulos(caminho, pessoa=pessoa)
    )


def kappa_do_arquivo(
    caminho: Path,
    pessoa_a: str,
    pessoa_b: str,
    *,
    coluna: str = "audiencia_percebida",
) -> float:
    """O Kappa entre duas pessoas sobre as Células que **as duas** rotularam.

    O pareamento é pela Célula — ``(execucao, audiencia, formato, rodada)`` —, nunca pela
    ordem das linhas: o arquivo é preenchido à mão e ninguém garante a mesma ordem.
    Célula rotulada por uma só das duas fica de fora, porque não há par a comparar.
    """
    de_a = {_celula(linha): linha[coluna] for linha in ler_rotulos(caminho, pessoa=pessoa_a)}
    de_b = {_celula(linha): linha[coluna] for linha in ler_rotulos(caminho, pessoa=pessoa_b)}
    comuns = sorted(set(de_a) & set(de_b))
    return kappa_cohen([de_a[c] for c in comuns], [de_b[c] for c in comuns])


def _celula(linha: dict[str, str]) -> tuple[str, str, str, str]:
    return (linha["execucao"], linha["audiencia"], linha["formato"], linha["rodada"])


# ---------------------------------------------------------------------------
# A matriz automática: sem rótulo humano
# ---------------------------------------------------------------------------


def audiencia_pelo_indice(indice: float) -> Audiencia:
    """Em que Audiência este Flesch-BR colocaria o texto, pelas faixas do NILC.

    As três faixas de ``LIMIARES_PROVISORIOS`` particionam a reta, então exatamente uma
    contém o índice. A ordem de teste é a de ``Audiencia`` e o empate não existe.
    """
    for audiencia, limiares in LIMIARES_PROVISORIOS.items():
        if limiares.flesch_br.contem(indice):
            return audiencia
    raise ValueError(f"nenhuma faixa do NILC contém {indice}")  # pragma: no cover


def matriz_de_confusao_da_execucao(execucao: Execucao) -> dict[str, dict[str, int]]:
    """Audiência pretendida × Audiência que o Flesch-BR medido colocaria. Sem humano.

    O valor sai do Laudo final da Célula quando ele está medido; só quando a Medida não
    está lá é que o índice é recalculado do texto. Recalcular por padrão faria a matriz
    discordar do Laudo que a interface mostra ao lado dela.

    Célula sem base de medida cai na coluna ``ausente``: não é "percebida como Avançada",
    é "não deu para dizer" (ADR 0008).
    """
    return _matriz(
        (str(historico.audiencia), _percebida(historico))
        for historico in execucao.celulas
        if historico.tentativas
    )


def _percebida(historico: HistoricoCelula) -> str:
    laudo = historico.laudo_final
    celula = historico.celula_final
    indice: float | None = None
    if laudo is not None:
        medida = laudo.medida(Metrica.FLESCH_BR)
        if medida is not None:
            indice = medida.valor
    if indice is None and celula is not None:
        indice = flesch_br(celula.conteudo.texto_avaliavel())
    if indice is None:
        return SEM_BASE
    return str(audiencia_pelo_indice(indice))


def _matriz(pares: Iterable[tuple[str, str]]) -> dict[str, dict[str, int]]:
    """Monta ``{pretendida: {percebida: n}}`` com as três Audiências sempre presentes."""
    observados = [(str(a or SEM_BASE), str(b or SEM_BASE)) for a, b in pares]
    conhecidas = [str(a) for a in Audiencia]
    linhas = conhecidas + sorted({a for a, _ in observados} - set(conhecidas))
    colunas = conhecidas + sorted({b for _, b in observados} - set(conhecidas))
    matriz = {linha: {coluna: 0 for coluna in colunas} for linha in linhas}
    for pretendida, percebida in observados:
        matriz[pretendida][percebida] += 1
    return matriz


# ---------------------------------------------------------------------------
# O resumo que o relatório cita
# ---------------------------------------------------------------------------


def resumo_da_execucao(execucao: Execucao) -> dict[str, Any]:
    """Tudo o que o Entregável 6 cita sobre uma execução, serializável em JSON.

    Não tem nome ``..._para_relatorio`` porque "relatório" está na lista _Avoid_ do
    CONTEXT.md e ``scripts/vocabulario.py`` reprovaria o nome.

    ``matriz_de_confusao`` aqui é sempre a automática: ``origem`` diz isso em texto, para
    ninguém a apresentar como concordância entre pessoas.
    """
    return {
        "execucao": execucao.identificador,
        "ata": execucao.ata,
        "celulas": len(execucao.celulas),
        "por_motivo": {str(motivo): n for motivo, n in execucao.contagem_por_motivo().items()},
        "rodadas_por_celula": [
            {
                "audiencia": str(historico.audiencia),
                "formato": str(historico.formato),
                "rodadas": len(historico.tentativas),
                "destino_final": str(historico.destino_final),
                "flesch_br": _indice_final(historico),
                "faixa_nilc": _faixa_final(historico),
            }
            for historico in execucao.celulas
        ],
        "matriz_de_confusao": matriz_de_confusao_da_execucao(execucao),
        "origem": ORIGEM_AUTOMATICA,
        "kappa_alvo": list(KAPPA_ALVO),
        "pendencias": len([p for p in execucao.pendencias if not p.resolvida]),
    }


def _indice_final(historico: HistoricoCelula) -> float | None:
    laudo = historico.laudo_final
    if laudo is None:
        return None
    medida = laudo.medida(Metrica.FLESCH_BR)
    return None if medida is None else medida.valor


def _faixa_final(historico: HistoricoCelula) -> str | None:
    indice = _indice_final(historico)
    return None if indice is None else faixa_nilc(indice)


__all__ = [
    "CODIFICACAO",
    "COLUNAS",
    "KAPPA_ALVO",
    "ORIGEM_AUTOMATICA",
    "PESSOA_DE_EXEMPLO",
    "SEM_BASE",
    "SEPARADOR",
    "audiencia_pelo_indice",
    "dentro_do_alvo",
    "kappa_cohen",
    "kappa_do_arquivo",
    "ler_rotulos",
    "matriz_de_confusao",
    "matriz_de_confusao_da_execucao",
    "resumo_da_execucao",
]
