"""Roteador: Gemini -> Groq -> SambaNova. Lê o tipo de 429 antes de decidir entre esperar e
trocar. O schema viaja no pedido, então a troca não perde saída estruturada. O juiz nunca
resolve para o provedor do Gerador.

ADR 0007.
"""

from __future__ import annotations

from typing import Sequence

from suno.dominio import PapelLLM, PedidoLLM, RespostaLLM
from suno.provedores.base import Provedor, ProvedorBase


class Roteador(ProvedorBase):
    nome = "roteador"

    def __init__(self, provedores: Sequence[Provedor], *, excluir: Sequence[str] = ()) -> None:
        raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")


def provedor_por_nome(nome: str) -> Provedor:
    """'falso' | 'gemini' | 'groq' | 'sambanova' | 'roteador'. Lê chaves e modelos do ambiente."""
    raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")


def roteador_para(papel: PapelLLM, *, excluir: Sequence[str] = ()) -> Provedor:
    raise NotImplementedError("Etapa 1, agente 6 — ADR 0007")
