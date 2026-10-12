"""Os sons de transição e de efeito, sintetizados em código.

Nenhum arquivo de áudio é versionado nem baixado: cada som do catálogo é uma função de
``math`` que gera amostras de 16 bits. Isso mantém o render sem rede e sem licença de banco de
sons, e deixa o resultado idêntico a cada rodada (o ruído usa semente fixa).

``trilha_de_efeitos`` monta uma faixa mono do tamanho do vídeo com os sons nos instantes
pedidos; quem mistura com a narração é o ffmpeg (``suno.video.render``).
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

from suno.dominio import BlocoFala, SomDeCena
from suno.video.design import SONS

TAXA = 24000
"""Amostras por segundo, a mesma da trilha de narração."""


def _envelope(i: int, n: int, ataque: float = 0.05) -> float:
    """Sobe linear até ``ataque`` (fração do som) e depois decai linear até zero."""
    posicao = i / n
    if posicao < ataque:
        return posicao / ataque
    return max(0.0, 1.0 - (posicao - ataque) / (1.0 - ataque))


def _whoosh(n: int) -> list[float]:
    """Ruído filtrado por um passa-baixa que sobe: o som de algo cruzando a tela."""
    aleatorio = random.Random(11)
    saida, filtrado = [], 0.0
    for i in range(n):
        corte = 0.05 + 0.5 * (i / n)
        filtrado += corte * (aleatorio.uniform(-1, 1) - filtrado)
        saida.append(filtrado * math.sin(math.pi * i / n))
    return saida


def _pop(n: int) -> list[float]:
    return [math.sin(2 * math.pi * (900 - 600 * i / n) * i / TAXA) * (1 - i / n) ** 2 for i in range(n)]


def _clique(n: int) -> list[float]:
    aleatorio = random.Random(5)
    return [aleatorio.uniform(-1, 1) * (1 - i / n) ** 3 for i in range(n)]


def _ding(n: int) -> list[float]:
    return [
        (math.sin(2 * math.pi * 1320 * i / TAXA) + 0.4 * math.sin(2 * math.pi * 1980 * i / TAXA))
        * _envelope(i, n, ataque=0.01)
        / 1.4
        for i in range(n)
    ]


def _swell(n: int) -> list[float]:
    return [
        math.sin(2 * math.pi * (200 + 500 * (i / n) ** 2) * i / TAXA) * (i / n) ** 1.5 * (1 - 0.3 * i / n)
        for i in range(n)
    ]


_GERADORES = {
    SomDeCena.WHOOSH: _whoosh,
    SomDeCena.POP: _pop,
    SomDeCena.CLIQUE: _clique,
    SomDeCena.DING: _ding,
    SomDeCena.SWELL: _swell,
}


def amostras_do_som(som: SomDeCena) -> list[float]:
    """As amostras do som, de -1 a 1, já no volume do catálogo."""
    descricao = SONS[som]
    n = round(descricao.duracao_s * TAXA)
    return [valor * descricao.volume for valor in _GERADORES[som](n)]


def marcas_dos_blocos(blocos: list[BlocoFala]) -> list[tuple[float, SomDeCena]]:
    """Os instantes de cada som: o de entrada no começo da cena, o de efeito quando o texto
    aparece. Ordenados por tempo."""
    marcas: list[tuple[float, SomDeCena]] = []
    for bloco in blocos:
        if bloco.som_de_entrada is not None:
            marcas.append((bloco.inicio_s, bloco.som_de_entrada))
        if bloco.som_de_efeito is not None:
            marcas.append((bloco.inicio_s + bloco.texto_entra_em_s, bloco.som_de_efeito))
    return sorted(marcas, key=lambda marca: marca[0])


def trilha_de_efeitos(marcas: list[tuple[float, SomDeCena]], duracao_s: float, destino: Path) -> Path | None:
    """Um WAV mono com os sons nos instantes dados. ``None`` se não há som nenhum."""
    if not marcas:
        return None
    total = round(duracao_s * TAXA)
    faixa = [0.0] * total
    for instante, som in marcas:
        inicio = round(instante * TAXA)
        for deslocamento, valor in enumerate(amostras_do_som(som)):
            posicao = inicio + deslocamento
            if posicao >= total:
                break
            faixa[posicao] += valor
    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA)
        arquivo.writeframes(
            b"".join(struct.pack("<h", round(max(-1.0, min(1.0, v)) * 32767)) for v in faixa)
        )
    return destino
