"""Gemini Flash via REST (httpx). Gera. O nome do modelo vem de GEMINI_MODELO.

ADR 0007.
"""

from __future__ import annotations

from suno.dominio import PedidoLLM, RespostaLLM
from suno.provedores.base import ProvedorBase


class ProvedorGemini(ProvedorBase):
    nome = "gemini"

    def __init__(self, chave: str, modelo: str) -> None:
        raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")
