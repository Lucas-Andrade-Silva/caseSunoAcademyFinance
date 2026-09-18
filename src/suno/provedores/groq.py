"""Groq via REST compatível com OpenAI (httpx). Julga. Distingue 'per minute' de 'per day' no 429.

ADR 0007.
"""

from __future__ import annotations

from suno.dominio import PedidoLLM, RespostaLLM
from suno.provedores.base import ProvedorBase


class ProvedorGroq(ProvedorBase):
    nome = "groq"

    def __init__(self, chave: str, modelo: str) -> None:
        raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")
