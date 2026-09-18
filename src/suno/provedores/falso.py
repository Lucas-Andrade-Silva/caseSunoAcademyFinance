"""Um LLM de mentira: devolve respostas prontas de uma fila, sem tocar na rede (ADR 0007).

É ele que deixa o Gerador, o Ciclo de correção e o roteador testáveis em CI. As respostas
ficam em filas por ``rotulo`` do pedido, o que mantém a demo determinística mesmo com as
nove Células gerando em paralelo. Uma entrada da fila pode ser uma exceção: ela é levantada
em vez de devolvida, e é assim que se simula um 429.

Uso::

    provedor = ProvedorFalso({"extracao": ['{"numericas": []}'], "*": ["texto qualquer"]})
    provedor = ProvedorFalso.de_arquivo("data/respostas_prontas/copom-280.json")
"""

from __future__ import annotations

import json
import threading
from collections import deque
from pathlib import Path
from typing import Any, Mapping, Sequence

from suno.dominio import ErroProvedor, PedidoLLM, RespostaLLM
from suno.provedores.base import ProvedorBase

FILA_PADRAO = "*"

Entrada = str | dict[str, Any] | list[Any] | BaseException


class FilaVazia(ErroProvedor):
    """O LLM falso não tinha resposta pronta para este rótulo."""


class ProvedorFalso(ProvedorBase):
    nome = "falso"

    def __init__(
        self,
        respostas: Mapping[str, Sequence[Entrada]] | Sequence[Entrada] | None = None,
        *,
        modelo: str = "falso-1",
        latencia_s: float = 0.0,
    ) -> None:
        self.modelo = modelo
        self.latencia_s = latencia_s
        self.pedidos: list[PedidoLLM] = []
        self._filas: dict[str, deque[Entrada]] = {}
        self._trava = threading.Lock()
        if respostas is None:
            respostas = {}
        if not isinstance(respostas, Mapping):
            respostas = {FILA_PADRAO: list(respostas)}
        for rotulo, fila in respostas.items():
            self._filas[rotulo] = deque(fila)

    # -- configuração -------------------------------------------------------

    @classmethod
    def de_arquivo(cls, caminho: str | Path, **kwargs: Any) -> ProvedorFalso:
        """Carrega ``{rotulo: [resposta, ...]}`` de um JSON. Respostas que são objetos viram texto JSON."""
        bruto = json.loads(Path(caminho).read_text(encoding="utf-8"))
        if not isinstance(bruto, dict):
            raise ValueError("o arquivo de respostas prontas precisa ser um objeto {rotulo: [..]}")
        return cls(bruto, **kwargs)

    def enfileirar(self, rotulo: str, *entradas: Entrada) -> None:
        with self._trava:
            self._filas.setdefault(rotulo, deque()).extend(entradas)

    def restantes(self, rotulo: str = FILA_PADRAO) -> int:
        with self._trava:
            return len(self._filas.get(rotulo, ()))

    # -- contrato -----------------------------------------------------------

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        with self._trava:
            self.pedidos.append(pedido)
            entrada = self._proxima(pedido.rotulo)
        if isinstance(entrada, BaseException):
            raise entrada
        texto = entrada if isinstance(entrada, str) else json.dumps(entrada, ensure_ascii=False)
        return RespostaLLM(
            texto=texto,
            provedor=self.nome,
            modelo=self.modelo,
            tokens_entrada=sum(len(m.texto) // 4 for m in pedido.mensagens),
            tokens_saida=len(texto) // 4,
            latencia_s=self.latencia_s,
        )

    def _proxima(self, rotulo: str) -> Entrada:
        fila = self._filas.get(rotulo)
        if fila:
            return fila.popleft()
        padrao = self._filas.get(FILA_PADRAO)
        if padrao:
            return padrao.popleft()
        raise FilaVazia(self.nome, f"sem resposta pronta para o rótulo {rotulo!r}")

    def rotulos_pedidos(self) -> list[str]:
        with self._trava:
            return [p.rotulo for p in self.pedidos]
