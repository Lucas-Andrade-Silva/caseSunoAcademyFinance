"""A porta de entrada única para qualquer LLM (ADR 0007).

Nenhum outro pacote importa SDK de provedor nem fala com a rede. Quem precisa de um LLM
recebe um ``Provedor`` por injeção e chama ``completar`` ou ``completar_estruturado``.
"""

from suno.provedores.base import Provedor, ProvedorBase
from suno.provedores.falso import ProvedorFalso

__all__ = ["Provedor", "ProvedorBase", "ProvedorFalso"]
