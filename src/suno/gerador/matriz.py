"""As nove Células geram em paralelo. Em sequência, uma Ata leva minutos e a demo morre esperando.

ADR 0010.

Paralelismo aqui é um ``ThreadPoolExecutor`` e nada mais: as nove posições da Matriz são
independentes — nenhuma lê o resultado da outra — então não há sequência a decidir, e sim
nove transformações que rodam ao mesmo tempo. A espera é de rede, não de CPU, e por isso
thread basta.

O retorno é o **histórico** de cada posição, não só a Célula: o Ciclo de correção pode ter
gerado até três, e a reprovação consertada é entregável do case tanto quanto a aprovação.
A ordem do resultado é a de ``MATRIZ``, sempre, qualquer que tenha sido a ordem de término.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from suno.dominio import MATRIZ, Ancoras, Ata, Audiencia, Formato, HistoricoCelula
from suno.gerador.ciclo import rodar_ciclo
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.comite import Comite

TRABALHADORES = len(MATRIZ)
"""Uma thread por posição da Matriz: nove."""


def gerar_matriz(
    ata: Ata,
    ancoras: Ancoras,
    provedor: Provedor,
    *,
    comite: "Comite | None" = None,
) -> list[HistoricoCelula]:
    """As nove posições da Matriz, cada uma com o seu Ciclo, na ordem de ``MATRIZ``."""
    prontos: dict[tuple[Audiencia, Formato], HistoricoCelula] = {}
    with ThreadPoolExecutor(max_workers=TRABALHADORES) as executor:
        futuros = {
            executor.submit(
                rodar_ciclo, ata, ancoras, audiencia, formato, provedor, comite=comite
            ): (audiencia, formato)
            for audiencia, formato in MATRIZ
        }
        for futuro, posicao in futuros.items():
            prontos[posicao] = futuro.result()
    return [prontos[posicao] for posicao in MATRIZ]
