"""Montar o Pacote de publicação em segundo plano: o botão "Montar Pacote" da interface.

Antes o Pacote só saía pelo terminal (``python -m suno.cli pacote``). A montagem renderiza imagens
(Pillow), então roda numa thread e a tela consulta o estado. Uma montagem por Saída por vez: a
segunda chamada, enquanto a primeira roda, só devolve o estado.

Cada Célula é liberada individualmente pelo Laudo ou por um revisor. O estado transversal da
Matriz não impede que uma Célula já aprovada gere seu próprio Pacote.

ADR 0017.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from suno.dominio import Audiencia, Execucao, Formato, PacotePublicacao
from suno.gerador.ciclo import sem_credencial
from suno.pacote import montar_pacote

_registro = logging.getLogger(__name__)

MENSAGEM_MAXIMA = 300


class EstadoDaMontagem(BaseModel):
    identificador: str
    estado: Literal["ocioso", "rodando", "ok", "erro"] = "ocioso"
    mensagem: str = ""
    total: int = 0
    concluida_em: datetime | None = None


def motivo_de_recusa(
    execucao: Execucao,
    audiencia: Audiencia | None = None,
    formato: Formato | None = None,
) -> str | None:
    """Por que esta Saída não pode montar Pacote agora, ou ``None`` se pode.

    O Pacote sai de cada Célula aprovada pelo Laudo ou por um revisor humano, independentemente das
    demais Células da Matriz.
    """
    if audiencia is not None and formato is not None:
        if not execucao.celula_liberada(audiencia, formato):
            return "esta Célula não foi aprovada pelo Laudo nem por um revisor"
        return None
    if not any(execucao.celula_liberada(h.audiencia, h.formato) for h in execucao.celulas):
        return "nenhuma Célula desta Saída foi aprovada (pelo Laudo ou por um revisor): não há Pacote para montar"
    return None


class Montador:
    def __init__(
        self,
        pasta_execucoes: Path,
        *,
        montar_fn: Callable[[str, Path], list[PacotePublicacao]] = montar_pacote,
        montar_celula_fn: Callable[
            [str, Path, Audiencia, Formato], list[PacotePublicacao]
        ]
        | None = None,
    ) -> None:
        self._pasta = Path(pasta_execucoes)
        self._montar = montar_fn
        self._montar_celula = montar_celula_fn
        self._trava = threading.Lock()
        self._estados: dict[str, EstadoDaMontagem] = {}
        self._ocupados: dict[str, threading.Event] = {}

    def estado(self, identificador: str) -> EstadoDaMontagem:
        with self._trava:
            atual = self._estados.get(identificador)
            return (atual or EstadoDaMontagem(identificador=identificador)).model_copy()

    def iniciar(
        self,
        identificador: str,
        audiencia: Audiencia | None = None,
        formato: Formato | None = None,
    ) -> EstadoDaMontagem:
        """Começa a montar, a não ser que esta Saída já esteja montando."""
        with self._trava:
            atual = self._estados.get(identificador)
            if atual is not None and atual.estado == "rodando":
                return atual.model_copy()
            self._estados[identificador] = EstadoDaMontagem(
                identificador=identificador, estado="rodando"
            )
            livre = threading.Event()
            self._ocupados[identificador] = livre
            threading.Thread(
                target=self._rodar,
                args=(identificador, livre, audiencia, formato),
                name="montar-pacote",
                daemon=True,
            ).start()
            return self._estados[identificador].model_copy()

    def aguardar(self, identificador: str, timeout: float = 30.0) -> bool:
        """Só para os testes."""
        with self._trava:
            livre = self._ocupados.get(identificador)
        return True if livre is None else livre.wait(timeout)

    def _rodar(
        self,
        identificador: str,
        livre: threading.Event,
        audiencia: Audiencia | None,
        formato: Formato | None,
    ) -> None:
        try:
            if audiencia is not None and formato is not None and self._montar_celula is not None:
                pacotes = self._montar_celula(identificador, self._pasta, audiencia, formato)
            else:
                pacotes = self._montar(identificador, self._pasta)
        except Exception as erro:  # noqa: BLE001 - a montagem falhou; a API e a fila seguem
            _registro.exception("montar Pacote de %s falhou", identificador)
            final = EstadoDaMontagem(
                identificador=identificador,
                estado="erro",
                mensagem=(sem_credencial(str(erro)) or type(erro).__name__)[:MENSAGEM_MAXIMA],
                concluida_em=datetime.now(timezone.utc),
            )
        else:
            final = EstadoDaMontagem(
                identificador=identificador,
                estado="ok",
                mensagem=f"{len(pacotes)} Pacote(s) montado(s)",
                total=len(pacotes),
                concluida_em=datetime.now(timezone.utc),
            )
        with self._trava:
            self._estados[identificador] = final
        livre.set()
