"""Limitador de requisições por minuto, único para o processo inteiro.

O tier gratuito do Gemini e do Groq estoura se as nove Células, o checador e as recriações
disparam juntos. Aqui toda chamada a um provedor de LLM passa por uma janela deslizante de 60 s:
a (N+1)-ésima requisição dentro da janela espera até a mais antiga sair dela. O Jev não passa
por aqui (vai pela Netlify, com créditos próprios).

O teto (padrão 8; ``0`` desliga) vem da aba de configurações ou de ``SUNO_RPM`` no ``.env``.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

from suno.configuracoes import carregar

JANELA_S = 60.0


class LimitadorPorMinuto:
    def __init__(
        self,
        maximo: int,
        *,
        relogio: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self.maximo = maximo
        self._relogio = relogio
        self._dormir = dormir
        self._saidas: deque[float] = deque()
        self._trava = threading.Lock()

    def aguardar(self) -> float:
        """Bloqueia até haver vaga na janela, reserva a vaga e devolve quanto esperou."""
        if self.maximo <= 0:
            return 0.0
        esperou = 0.0
        while True:
            with self._trava:
                agora = self._relogio()
                while self._saidas and agora - self._saidas[0] >= JANELA_S:
                    self._saidas.popleft()
                if len(self._saidas) < self.maximo:
                    self._saidas.append(agora)
                    return esperou
                falta = JANELA_S - (agora - self._saidas[0])
            self._dormir(falta)
            esperou += falta


_global: LimitadorPorMinuto | None = None
_trava_global = threading.Lock()


def _maximo_do_ambiente() -> int:
    return carregar().requisicoes_por_minuto


def esperar_vaga() -> float:
    """Chamado antes de cada requisição HTTP a um provedor de LLM (inclusive reenvios)."""
    global _global
    maximo = _maximo_do_ambiente()
    with _trava_global:
        if _global is None or _global.maximo != maximo:
            _global = LimitadorPorMinuto(maximo)
        limitador = _global
    return limitador.aguardar()
