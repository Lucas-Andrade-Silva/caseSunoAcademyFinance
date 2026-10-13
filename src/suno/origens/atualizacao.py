"""O job "Atualizar fontes", em duas etapas, uma thread por vez.

1. **Consulta**: cada Origem ligada lista o que publicou nos últimos 30 dias e ainda não está em
   disco (só metadados, barato). Com até ``LIMITE_SEM_FILTRO`` documentos o job já baixa tudo. Com
   mais, o estado vira ``aguardando_filtro`` e a pessoa vê a quantidade e escolhe um período.
2. **Download**: ``baixar(de, ate)`` baixa só o que cai no período escolhido.

Precisa de rede e falha sem travar a tela: cada Origem que falha entra na mensagem e as outras
seguem. O que já está em disco nunca é apagado. O estado fica em memória (um processo só).
ADR 0029.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from suno.ingestao.bcb import ErroDeIngestao
from suno.origens.catalogo import carregar_catalogo
from suno.origens.coleta import (
    JANELA_DA_BUSCA_EM_DIAS,
    Candidato,
    Coletor,
    cliente_padrao,
    coletores_padrao,
)

_registro = logging.getLogger(__name__)

LIMITE_SEM_FILTRO = 2
"""Até este número de documentos novos o job baixa sem perguntar."""

MAXIMO_POR_DOWNLOAD = 40
"""Teto de documentos por pedido: a CVM pede 10 s entre downloads, 40 já são uns 7 minutos."""

ORIGEM_DAS_ATAS_DO_COPOM = "copom"


class PedidoDeDownloadRecusado(ValueError):
    """O período está fora da janela, não há consulta esperando, ou são documentos demais."""


class Disponivel(BaseModel):
    origem: str
    identificador: str
    titulo: str
    data: date


class EstadoDaAtualizacao(BaseModel):
    estado: Literal["ocioso", "consultando", "aguardando_filtro", "baixando", "ok", "erro"] = "ocioso"
    mensagem: str = ""
    novos: int = 0
    iniciada_em: datetime | None = None
    concluida_em: datetime | None = None
    janela_dias: int = JANELA_DA_BUSCA_EM_DIAS
    desde: date | None = None
    ate: date | None = None
    disponiveis: list[Disponivel] = Field(default_factory=list)
    """O que há para baixar na janela; só vem preenchido em ``aguardando_filtro``."""
    a_baixar: int = 0
    baixados: int = 0


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Atualizador:
    def __init__(
        self,
        pasta_atas: Path,
        pasta_fontes: Path,
        *,
        coletores: dict[str, Coletor] | None = None,
        fabrica_de_cliente: Callable[[], httpx.Client] = cliente_padrao,
        dormir: Callable[[float], None] = time.sleep,
        hoje: Callable[[], date] = lambda: _agora().date(),
    ) -> None:
        self._pasta_atas = Path(pasta_atas)
        self._pasta_fontes = Path(pasta_fontes)
        self._coletores = coletores if coletores is not None else coletores_padrao()
        self._fabrica = fabrica_de_cliente
        self._dormir = dormir
        self._hoje = hoje
        self._trava = threading.Lock()
        self._estado = EstadoDaAtualizacao()
        self._pendentes: list[Candidato] = []
        self._falhas_da_consulta: list[str] = []
        self._ocioso = threading.Event()
        self._ocioso.set()

    # -- estado -------------------------------------------------------------

    def estado(self) -> EstadoDaAtualizacao:
        with self._trava:
            return self._estado.model_copy(deep=True)

    def aguardar(self, timeout: float = 30.0) -> bool:
        """Só para os testes: espera o job parar (ocioso, aguardando o filtro, ok ou erro)."""
        return self._ocioso.wait(timeout)

    def _ocupado(self) -> bool:
        return self._estado.estado in ("consultando", "baixando")

    def _destino(self, origem: str) -> Path:
        return self._pasta_atas if origem == ORIGEM_DAS_ATAS_DO_COPOM else self._pasta_fontes / origem

    def _em_disco(self, candidato: Candidato) -> bool:
        pasta = self._destino(candidato.origem)
        return any((pasta / f"{candidato.identificador}{sufixo}").exists() for sufixo in (".pdf", ".txt"))

    # -- etapa 1: consultar -------------------------------------------------

    def iniciar(self) -> EstadoDaAtualizacao:
        """Começa a consultar, a não ser que já haja uma consulta ou um download rodando."""
        with self._trava:
            if not self._ocupado():
                hoje = self._hoje()
                self._estado = EstadoDaAtualizacao(
                    estado="consultando",
                    iniciada_em=_agora(),
                    desde=hoje - timedelta(days=JANELA_DA_BUSCA_EM_DIAS),
                    ate=hoje,
                )
                self._pendentes = []
                self._falhas_da_consulta = []
                self._ocioso.clear()
                threading.Thread(target=self._consultar, name="consultar-fontes", daemon=True).start()
            return self._estado.model_copy(deep=True)

    def _consultar(self) -> None:
        falhas: list[str] = []
        pendentes: list[Candidato] = []
        try:
            hoje = self._hoje()
            desde = hoje - timedelta(days=JANELA_DA_BUSCA_EM_DIAS)
            cliente = self._fabrica()
            try:
                for origem in carregar_catalogo(self._pasta_fontes):
                    coletor = self._coletores.get(origem.id)
                    if coletor is None or not (origem.ativa and origem.disponivel):
                        continue
                    try:
                        achados = coletor.listar(cliente, desde, hoje)
                    except Exception as erro:  # noqa: BLE001 - uma Origem que falha não derruba as outras
                        _registro.warning("consultar %s falhou: %s", origem.id, erro)
                        falhas.append(f"{origem.nome}: {erro}")
                        continue
                    pendentes += [c for c in achados if not self._em_disco(c)]
            finally:
                cliente.close()
        except Exception as erro:  # noqa: BLE001 - nunca deixa o estado preso em "consultando"
            _registro.exception("consulta das fontes quebrou")
            falhas.append(str(erro))
        pendentes.sort(key=lambda c: (c.data, c.identificador), reverse=True)

        with self._trava:
            self._pendentes = pendentes
            self._falhas_da_consulta = falhas
            if len(pendentes) > LIMITE_SEM_FILTRO:
                self._estado = self._estado.model_copy(
                    update={
                        "estado": "aguardando_filtro",
                        "disponiveis": [
                            Disponivel(origem=c.origem, identificador=c.identificador, titulo=c.titulo, data=c.data)
                            for c in pendentes
                        ],
                        "mensagem": "; ".join(falhas),
                    }
                )
                self._ocioso.set()
                return
            if pendentes:
                self._estado = self._estado.model_copy(update={"estado": "baixando", "a_baixar": len(pendentes)})
                a_baixar = list(pendentes)
            else:
                self._estado = self._fechar("Nada novo nos últimos 30 dias", [], falhas)
                self._ocioso.set()
                return
        self._baixar_lista(a_baixar, falhas)

    # -- etapa 2: baixar ----------------------------------------------------

    def baixar(self, de: date, ate: date) -> EstadoDaAtualizacao:
        """Baixa o que a consulta achou entre ``de`` e ``ate`` (datas incluídas)."""
        with self._trava:
            if self._estado.estado != "aguardando_filtro":
                raise PedidoDeDownloadRecusado("não há consulta esperando o período")
            if de > ate:
                raise PedidoDeDownloadRecusado("a data inicial vem depois da final")
            escolhidos = [c for c in self._pendentes if de <= c.data <= ate]
            if not escolhidos:
                raise PedidoDeDownloadRecusado("nenhum documento nesse período")
            if len(escolhidos) > MAXIMO_POR_DOWNLOAD:
                raise PedidoDeDownloadRecusado(
                    f"são {len(escolhidos)} documentos; escolha um período com no máximo {MAXIMO_POR_DOWNLOAD}"
                )
            self._estado = self._estado.model_copy(
                update={"estado": "baixando", "a_baixar": len(escolhidos), "baixados": 0, "disponiveis": []}
            )
            self._ocioso.clear()
            falhas = list(self._falhas_da_consulta)
            threading.Thread(
                target=self._baixar_lista, args=(escolhidos, falhas), name="baixar-fontes", daemon=True
            ).start()
            return self._estado.model_copy(deep=True)

    def cancelar(self) -> EstadoDaAtualizacao:
        """Descarta a consulta que espera o período (o que já está em disco fica)."""
        with self._trava:
            if self._estado.estado == "aguardando_filtro":
                self._pendentes = []
                self._estado = EstadoDaAtualizacao(estado="ocioso")
            return self._estado.model_copy(deep=True)

    def _baixar_lista(self, candidatos: list[Candidato], falhas: list[str]) -> None:
        feitos: list[Candidato] = []
        falhas = list(falhas)
        try:
            cliente = self._fabrica()
            try:
                ultimo_por_origem: set[str] = set()
                for candidato in candidatos:
                    coletor = self._coletores[candidato.origem]
                    if candidato.origem in ultimo_por_origem:
                        self._dormir(coletor.espera_s)
                    ultimo_por_origem.add(candidato.origem)
                    try:
                        coletor.baixar(cliente, candidato, self._destino(candidato.origem))
                        feitos.append(candidato)
                    except ErroDeIngestao as erro:
                        _registro.warning("baixar %s falhou: %s", candidato.identificador, erro)
                        falhas.append(str(erro))
                    except Exception as erro:  # noqa: BLE001 - um documento ruim não para a fila
                        _registro.warning("baixar %s quebrou: %s", candidato.identificador, erro)
                        falhas.append(f"{candidato.identificador}: {erro}")
                    with self._trava:
                        self._estado = self._estado.model_copy(update={"baixados": len(feitos)})
            finally:
                cliente.close()
        except Exception as erro:  # noqa: BLE001 - nunca deixa o estado preso em "baixando"
            _registro.exception("download das fontes quebrou")
            falhas.append(str(erro))
        finally:
            with self._trava:
                self._pendentes = [c for c in self._pendentes if c not in feitos]
                self._estado = self._fechar("", feitos, falhas)
                self._ocioso.set()

    def _fechar(self, vazio: str, feitos: list[Candidato], falhas: list[str]) -> EstadoDaAtualizacao:
        por_origem: dict[str, int] = {}
        for candidato in feitos:
            por_origem[candidato.origem] = por_origem.get(candidato.origem, 0) + 1
        nomes = {o.id: o.nome for o in carregar_catalogo(self._pasta_fontes)}
        partes = [f"{nomes.get(origem, origem)}: {quantidade} {'novo' if quantidade == 1 else 'novos'}"
                  for origem, quantidade in por_origem.items()]
        mensagem = "; ".join([*([vazio] if vazio else []), *partes, *falhas])
        return self._estado.model_copy(
            update={
                "estado": "erro" if falhas else "ok",
                "mensagem": mensagem,
                "novos": len(feitos),
                "concluida_em": _agora(),
                "disponiveis": [],
                "a_baixar": 0,
                "baixados": len(feitos),
            }
        )
