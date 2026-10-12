"""O job "Atualizar fontes": busca nas Origens que estão ligadas, uma thread por vez.

Precisa de rede e falha sem travar a tela: cada Origem que falha entra na mensagem e as outras
seguem. O que já está em disco nunca é apagado. O estado fica em memória (um processo só).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from suno.dominio import Ata
from suno.ingestao.bcb import buscar_ata
from suno.origens.catalogo import carregar_catalogo
from suno.origens.cvm import buscar_fatos_relevantes

_registro = logging.getLogger(__name__)


class EstadoDaAtualizacao(BaseModel):
    estado: Literal["ocioso", "rodando", "ok", "erro"] = "ocioso"
    mensagem: str = ""
    novos: int = 0
    iniciada_em: datetime | None = None
    concluida_em: datetime | None = None


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Atualizador:
    def __init__(
        self,
        pasta_atas: Path,
        pasta_fontes: Path,
        *,
        buscar_copom: Callable[[Path], Ata] = lambda destino: buscar_ata(destino),
        buscar_cvm: Callable[[Path], list[Ata]] = lambda destino: buscar_fatos_relevantes(destino),
    ) -> None:
        self._pasta_atas = Path(pasta_atas)
        self._pasta_fontes = Path(pasta_fontes)
        self._buscar_copom = buscar_copom
        self._buscar_cvm = buscar_cvm
        self._trava = threading.Lock()
        self._estado = EstadoDaAtualizacao()
        self._ocioso = threading.Event()
        self._ocioso.set()

    def estado(self) -> EstadoDaAtualizacao:
        with self._trava:
            return self._estado.model_copy()

    def iniciar(self) -> EstadoDaAtualizacao:
        """Começa a atualizar, a não ser que já esteja rodando."""
        with self._trava:
            if self._estado.estado != "rodando":
                self._estado = EstadoDaAtualizacao(estado="rodando", iniciada_em=_agora())
                self._ocioso.clear()
                threading.Thread(target=self._rodar, name="atualizar-fontes", daemon=True).start()
            return self._estado.model_copy()

    def aguardar(self, timeout: float = 30.0) -> bool:
        """Só para os testes."""
        return self._ocioso.wait(timeout)

    def _identificadores_do_copom(self) -> set[str]:
        if not self._pasta_atas.exists():
            return set()
        return {caminho.stem for caminho in self._pasta_atas.iterdir()}

    def _rodar(self) -> None:
        partes: list[str] = []
        falhas: list[str] = []
        novos = 0
        try:
            for origem in carregar_catalogo(self._pasta_fontes):
                if not (origem.ativa and origem.disponivel):
                    continue
                try:
                    if origem.id == "copom":
                        antes = self._identificadores_do_copom()
                        ata = self._buscar_copom(self._pasta_atas)
                        if ata.identificador in antes:
                            partes.append("Copom: sem novidade")
                        else:
                            novos += 1
                            partes.append(f"Copom: nova Ata {ata.identificador}")
                    elif origem.id == "cvm_fatos_relevantes":
                        atas = self._buscar_cvm(self._pasta_fontes)
                        novos += len(atas)
                        partes.append(f"CVM: {len(atas)} novos")
                except Exception as erro:  # noqa: BLE001 - uma Origem que falha não derruba as outras
                    _registro.warning("atualizar %s falhou: %s", origem.id, erro)
                    falhas.append(f"{origem.nome}: {erro}")
        finally:
            with self._trava:
                self._estado = EstadoDaAtualizacao(
                    estado="erro" if falhas else "ok",
                    mensagem="; ".join([*partes, *falhas]),
                    novos=novos,
                    iniciada_em=self._estado.iniciada_em,
                    concluida_em=_agora(),
                )
                self._ocioso.set()
