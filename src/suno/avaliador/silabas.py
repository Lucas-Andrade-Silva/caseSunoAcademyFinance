"""Separador de sílabas do português, reimplementado a partir de Silva (2011).

Não copia o código do NILC (GPL-3.0): é uma reescrita a partir da descrição do
algoritmo — classificar cada letra, achar os núcleos vocálicos e só então repartir os
grupos consonantais entre coda e ataque. ADR 0002 (atualização de 18/09/2026).

As convenções abaixo foram escolhidas onde o artigo é ambíguo. Cada uma tem teste em
``tests/test_silabas.py``; quem "corrigir" uma delas quebra o teste de propósito.

- ``ideia`` → ``i-dei-a``: depois de um ditongo decrescente, a vogal seguinte abre
  sílaba nova. O bug de sílaba vazia do NILC não existe aqui.
- ``i``/``u`` com acento marcado sempre abrem hiato: ``sa-ú-de``, ``pa-ís``, ``ba-ú``,
  ``sa-í-da``.
- Ditongo decrescente não separa: ``mãe``, ``pau``, ``lei``, ``cau-sa``, ``ou-ro``.
  Separa, porém, quando o ``i``/``u`` é seguido de ``nh`` ou de coda nasal:
  ``ra-i-nha``, ``ru-im``, ``a-in-da``.
- Ditongo crescente (``i``/``u`` + vogal forte) é hiato, exceto quando é o último grupo
  vocálico de uma palavra que já tem acento escrito noutro lugar: por isso ``á-gio`` e
  ``con-ver-gên-cia`` fecham, e ``e-co-no-mi-a`` e ``vi-a-gem`` abrem. É a aproximação
  ortográfica do que, de fato, é posição de tônica, e é onde este separador mais erra
  (``juiz`` sai como uma sílaba só, em vez de ``ju-iz``).
- ``qu`` e ``gu`` diante de vogal são dígrafos: o ``u`` não é núcleo (``quei-jo``,
  ``á-gua``, ``lin-gui-ça``, ``a-quá-ti-co``).
- Palavra sem nenhuma vogal é uma sílaba: siglas como ``bcb`` contam 1.
- Hífen e apóstrofo repartem a palavra: cada parte é separada por si.
- Entrada sem letra nenhuma devolve lista vazia — nunca uma string vazia.
"""

from __future__ import annotations

import re

VOGAIS_FORTES = frozenset("aeoáéóâêôãõà")
VOGAIS_FRACAS = frozenset("iuíúü")
VOGAIS = VOGAIS_FORTES | VOGAIS_FRACAS

ACENTUADAS = frozenset("áéíóúâêôãõ")
"""Acento escrito que marca tônica. ``à`` fica de fora: crase não marca tônica."""

FRACAS_ACENTUADAS = frozenset("íú")
NASAIS = frozenset("ãõ")

DITONGOS_NASAIS = frozenset({"ão", "ãe", "ãi", "ãu", "õe", "õi"})

TRITONGOS = frozenset({"uai", "uei", "uou"})
"""Só sobrevivem fora de ``qu``/``gu``; em ``sa-guão`` o dígrafo já resolveu."""

ONSETS_VALIDOS = frozenset(
    {
        "ch", "lh", "nh", "qu", "gu",
        "bl", "cl", "fl", "gl", "pl",
        "br", "cr", "dr", "fr", "gr", "pr", "tr", "vr",
    }
)
"""Dígrafos inseparáveis e encontros consonantais com ``l``/``r``: abrem sílaba."""

DIGRAFOS_SEPARAVEIS = frozenset({"rr", "ss", "sc", "sç", "xc"})
"""Sempre partem a sílaba: ``car-ro``, ``pes-so-a``, ``nas-cer``, ``ex-ce-ção``."""

_NAO_LETRA = re.compile(r"[^A-Za-zÀ-ÖØ-öø-ÿ]+")
_DIVISORES = re.compile(r"[-‐‑–—'’]+")


def separar(palavra: str) -> list[str]:
    """Devolve as sílabas de uma palavra, sem strings vazias."""
    silabas: list[str] = []
    for pedaco in _DIVISORES.split(palavra):
        limpo = _NAO_LETRA.sub("", pedaco)
        if limpo:
            silabas.extend(_separar_pedaco(limpo))
    return silabas


def contar_silabas(palavra: str) -> int:
    """Quantas sílabas a palavra tem. Zero só quando não sobrou letra nenhuma."""
    return len(separar(palavra))


# ---------------------------------------------------------------------------
# Implementação
# ---------------------------------------------------------------------------


def _separar_pedaco(palavra: str) -> list[str]:
    baixa = palavra.lower()
    consonantal = _us_de_digrafo(baixa)
    nucleos = _nucleos(baixa, consonantal)
    if not nucleos:
        return [palavra]  # sigla sem vogal: bcb é uma sílaba

    silabas: list[str] = []
    inicio = 0
    for ordem, (_, fim) in enumerate(nucleos):
        if ordem + 1 == len(nucleos):
            silabas.append(palavra[inicio:])
            break
        proximo = nucleos[ordem + 1][0]
        coda, _ataque = _repartir_consoantes(baixa[fim:proximo])
        limite = fim + len(coda)
        silabas.append(palavra[inicio:limite])
        inicio = limite
    return silabas


def _us_de_digrafo(baixa: str) -> list[bool]:
    """Marca o ``u`` de ``qu``/``gu`` diante de vogal: ele é consoante, não núcleo."""
    marcas = [False] * len(baixa)
    for pos, letra in enumerate(baixa):
        if (
            letra in ("u", "ü")
            and pos > 0
            and baixa[pos - 1] in ("q", "g")
            and pos + 1 < len(baixa)
            and baixa[pos + 1] in VOGAIS
        ):
            marcas[pos] = True
    return marcas


def _nucleos(baixa: str, consonantal: list[bool]) -> list[tuple[int, int]]:
    """Os núcleos vocálicos da palavra, como intervalos ``[inicio, fim)``."""

    def eh_nucleo(pos: int) -> bool:
        return baixa[pos] in VOGAIS and not consonantal[pos]

    grupos: list[tuple[int, int]] = []
    pos = 0
    while pos < len(baixa):
        if eh_nucleo(pos):
            fim = pos
            while fim < len(baixa) and eh_nucleo(fim):
                fim += 1
            grupos.append((pos, fim))
            pos = fim
        else:
            pos += 1

    acentuada = any(letra in ACENTUADAS for letra in baixa)
    nucleos: list[tuple[int, int]] = []
    for ordem, (inicio, fim) in enumerate(grupos):
        final = ordem + 1 == len(grupos)
        nucleos.extend(_repartir_grupo(baixa, inicio, fim, acentuada, final))
    return nucleos


def _repartir_grupo(
    baixa: str, inicio: int, fim: int, acentuada: bool, final: bool
) -> list[tuple[int, int]]:
    """Quebra um grupo de vogais contíguas em um ou mais núcleos."""
    nucleos: list[tuple[int, int]] = []
    abertura = inicio
    pos = inicio + 1
    while pos < fim:
        tamanho = pos - abertura
        if tamanho >= 2:
            # núcleo já fechado com ditongo: só cresce se virar tritongo (u-ai, u-ei)
            if tamanho == 2 and baixa[abertura : pos + 1] in TRITONGOS:
                pos += 1
                continue
            nucleos.append((abertura, pos))
            abertura = pos
            pos += 1
            continue
        if _mesma_silaba(baixa, pos - 1, pos, acentuada, final):
            pos += 1
            continue
        nucleos.append((abertura, pos))
        abertura = pos
        pos += 1
    nucleos.append((abertura, fim))
    return nucleos


def _mesma_silaba(baixa: str, antes: int, depois: int, acentuada: bool, final: bool) -> bool:
    """Duas vogais vizinhas ficam na mesma sílaba?"""
    primeira, segunda = baixa[antes], baixa[depois]

    if primeira in NASAIS:
        return primeira + segunda in DITONGOS_NASAIS  # a-ção, mãe, a-ções
    if primeira in FRACAS_ACENTUADAS or segunda in FRACAS_ACENTUADAS:
        return False  # sa-í-da, sa-ú-de, pa-ís, ba-ú
    if segunda in VOGAIS_FRACAS:
        # decrescente: lei, pau, cau-sa — salvo ra-i-nha e ru-im
        return not _fecha_silaba(baixa, depois)
    if primeira in VOGAIS_FRACAS:
        # crescente: fecha só no fim de palavra já acentuada (á-gio, sé-rio)
        if segunda in ACENTUADAS:
            return False  # in-flu-ên-cia, di-á-rio
        return final and acentuada
    return False  # forte + forte é sempre hiato: pes-so-a, re-al, mo-e-da


def _fecha_silaba(baixa: str, pos: int) -> bool:
    """O ``i``/``u`` em ``pos`` é seguido de ``nh`` ou de coda nasal?"""
    if baixa[pos + 1 : pos + 3] == "nh":
        return True  # ra-i-nha, mo-i-nho
    if baixa[pos + 1 : pos + 2] in ("m", "n"):
        seguinte = baixa[pos + 2 : pos + 3]
        return seguinte == "" or seguinte not in VOGAIS  # ru-im, a-in-da; rei-no não
    return False


def _repartir_consoantes(grupo: str) -> tuple[str, str]:
    """Reparte as consoantes entre duas vogais em (coda da anterior, ataque da próxima)."""
    if len(grupo) < 2:
        return "", grupo
    dois = grupo[-2:]
    if dois in ONSETS_VALIDOS and dois not in DIGRAFOS_SEPARAVEIS:
        return grupo[:-2], dois  # in-fla-ção, abs-tra-to, fi-lho
    return grupo[:-1], grupo[-1:]  # car-tei-ra, rit-mo, obs-tá-cu-lo, guer-ra
