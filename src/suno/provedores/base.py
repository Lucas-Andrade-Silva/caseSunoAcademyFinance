"""O contrato de provedor de LLM. É a única porta de entrada (ADR 0007).

Regras que este arquivo fixa e que os provedores concretos (``gemini.py``, ``groq.py``,
``sambanova.py``) e o ``roteador.py`` herdam:

- O schema de saída viaja dentro do ``PedidoLLM``. Nenhum cliente guarda binding de schema;
  por isso trocar de provedor no meio de uma execução não perde a saída estruturada.
- Um 429 nunca sobe cru: o provedor concreto lê a mensagem e levanta ``CotaEsgotada`` com
  ``esgotamento`` POR_MINUTO ou POR_DIA. Quem decide entre esperar e trocar é o roteador.
- Nomes de modelo vêm de configuração (``.env``), nunca de constante em código.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ValidationError

from suno.dominio import PedidoLLM, RespostaLLM, RespostaMalformada

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class Provedor(Protocol):
    """O que o resto do sistema enxerga de um LLM."""

    nome: str

    def completar(self, pedido: PedidoLLM) -> RespostaLLM: ...

    def completar_estruturado(self, pedido: PedidoLLM, modelo: type[T]) -> T: ...


class ProvedorBase(ABC):
    """Implementação comum: ``completar_estruturado`` anexa o schema ao pedido e valida."""

    nome: str = "base"

    @abstractmethod
    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        """Uma chamada. Levanta ``CotaEsgotada`` em 429 e ``ErroProvedor`` no resto."""

    def completar_estruturado(self, pedido: PedidoLLM, modelo: type[T]) -> T:
        pedido_com_schema = pedido.model_copy(
            update={"schema_saida": pedido.schema_saida or modelo.model_json_schema()}
        )
        resposta = self.completar(pedido_com_schema)
        return validar_resposta(self.nome, resposta.texto, modelo)


def validar_resposta(provedor: str, texto: str, modelo: type[T]) -> T:
    """Converte o texto da resposta no modelo pedido, tolerando cerca de ```json."""
    bruto = extrair_json(texto)
    try:
        return modelo.model_validate_json(bruto)
    except ValidationError as erro:
        raise RespostaMalformada(provedor, f"resposta fora do schema {modelo.__name__}: {erro}") from erro


def extrair_json(texto: str) -> str:
    """Tira a cerca de código, se houver, e devolve o trecho JSON."""
    limpo = texto.strip()
    if limpo.startswith("```"):
        primeira_quebra = limpo.find("\n")
        limpo = limpo[primeira_quebra + 1 :] if primeira_quebra != -1 else limpo[3:]
        if limpo.endswith("```"):
            limpo = limpo[:-3]
    limpo = limpo.strip()
    try:
        json.loads(limpo)
        return limpo
    except json.JSONDecodeError:
        inicio = limpo.find("{")
        fim = limpo.rfind("}")
        if inicio != -1 and fim > inicio:
            return limpo[inicio : fim + 1]
        return limpo
