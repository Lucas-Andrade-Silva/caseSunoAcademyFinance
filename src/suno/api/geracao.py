"""Geração em segundo plano: a API inicia o pipeline, acompanha e registra o andamento.

Um job por vez. O tier gratuito dos provedores tem cota (ADR 0007) e dois jobs juntos só
multiplicam os 429; as Células de um job já geram em paralelo dentro dele. Os demais pedidos
ficam em fila. O estado de cada job vai para ``<pasta>/<id>/andamento.json``, ao lado do
``execucao.json`` que o pipeline só grava ao fim. No boot, o que ficou ``na_fila`` ou ``gerando``
vira ``interrompida``: o processo que o rodava morreu.

ADR 0017.
"""

from __future__ import annotations

import logging
import os
import queue
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path

from pydantic import ValidationError

from suno.dominio import (
    Andamento,
    AndamentoDaCelula,
    Audiencia,
    ComposicaoCarrossel,
    DuracaoDoVideo,
    ErroProvedor,
    CategoriaDaAta,
    EstadoDoAndamento,
    EtapaDaCelula,
    Execucao,
    FaseDaExecucao,
    Formato,
    PosicaoDaMatriz,
)
from suno.gerador.ciclo import sem_credencial
from suno.gerador.curador import MAXIMO_DE_PARTES, MINIMO_DE_PARTES, compor_uniao
from suno.gerador.execucao import PASTA_RESPOSTAS_PRONTAS, executar
from suno.origens.catalogo import PASTA_FONTES
from suno.origens.repositorio import RepositorioDeAtas
from suno.provedores.roteador import provedor_por_nome

_registro = logging.getLogger(__name__)

NOME_DO_ANDAMENTO = "andamento.json"
NOME_MAXIMO = 120
ERRO_MAXIMO = 500

ESTADOS_EM_ANDAMENTO = (EstadoDoAndamento.NA_FILA, EstadoDoAndamento.GERANDO)


class ModoDeGeracao(StrEnum):
    """Demo roda sem rede, com respostas prontas; Real usa o roteador e gasta cota gratuita."""

    DEMO = "demo"
    REAL = "real"


PROVEDOR_DO_MODO = {ModoDeGeracao.DEMO: "falso", ModoDeGeracao.REAL: "roteador"}


class PedidoRecusado(ValueError):
    """O pedido de geração não pode ser atendido; a mensagem é a frase que a tela mostra."""


class AtaNaoEncontrada(LookupError):
    """Não há Ata com esse identificador em ``data/atas/``."""


def caminho_do_andamento(pasta_execucoes: Path, identificador: str) -> Path:
    return Path(pasta_execucoes) / identificador / NOME_DO_ANDAMENTO


def ler_andamento(pasta_execucoes: Path, identificador: str) -> Andamento | None:
    """Lê ``andamento.json``. Ausente ou ilegível devolve ``None``: a listagem não pode quebrar."""
    try:
        return Andamento.model_validate_json(
            caminho_do_andamento(pasta_execucoes, identificador).read_text(encoding="utf-8")
        )
    except (OSError, ValidationError):
        return None


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _gravar(pasta_execucoes: Path, andamento: Andamento) -> None:
    """Grava por arquivo temporário e troca: quem lê nunca vê metade de um JSON.

    No Windows o ``os.replace`` falha enquanto outro processo mantém o destino aberto, então
    tenta algumas vezes antes de desistir. Falhar em gravar o andamento nunca derruba o job.
    """
    destino = caminho_do_andamento(pasta_execucoes, andamento.identificador)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".json.tmp")
    temporario.write_text(andamento.model_dump_json(indent=2), encoding="utf-8")
    for tentativa in range(5):
        try:
            os.replace(temporario, destino)
            return
        except PermissionError:
            time.sleep(0.02 * (tentativa + 1))
    _registro.warning("não consegui trocar %s; o andamento fica no temporário", destino)


@dataclass(frozen=True)
class _Trabalho:
    identificador: str
    caminho_ata: Path | list[Path]
    provedor: str
    pedido: list[tuple[Audiencia, Formato]]
    nome: str
    duracao: DuracaoDoVideo
    composicao_visual: ComposicaoCarrossel | None
    referencia_visual: str | None


class Gerenciador:
    """A fila de gerações e a thread que as roda, uma de cada vez."""

    def __init__(
        self,
        pasta_execucoes: Path,
        *,
        pasta_atas: Path,
        executar_fn: Callable[..., Execucao] = executar,
        repositorio: RepositorioDeAtas | None = None,
    ) -> None:
        self._pasta = Path(pasta_execucoes)
        self._repositorio = repositorio or RepositorioDeAtas(Path(pasta_atas), PASTA_FONTES)
        self._executar = executar_fn
        self._trava = threading.Lock()
        self._fila: queue.Queue[_Trabalho] = queue.Queue()
        self._em_memoria: dict[str, Andamento] = {}
        self._rodando = False
        self._ocioso = threading.Event()
        self._ocioso.set()

    # -- pedido ---------------------------------------------------------------

    def pedir(
        self,
        *,
        modo: ModoDeGeracao,
        pedido: list[PosicaoDaMatriz],
        nome: str | None,
        ata: str | None = None,
        itens: list[str] | None = None,
        duracao: DuracaoDoVideo = DuracaoDoVideo.S60,
        composicao_visual: ComposicaoCarrossel | None = None,
        referencia_visual: str | None = None,
    ) -> Andamento:
        """Valida, grava ``na_fila`` e enfileira. Recusa antes de gastar qualquer chamada.

        ``ata`` é o Destaque único; ``itens`` (de 2 a 5 identificadores) é a Visão unida. Exatamente
        um dos dois.
        """
        if (ata is None) == (not itens):
            raise PedidoRecusado(
                "informe a Ata (ata) ou a lista da Visão unida (itens), nunca os dois nem nenhum"
            )
        posicoes = [p.como_tupla() for p in pedido]
        if not posicoes:
            raise PedidoRecusado("o pedido está vazio: escolha ao menos uma Célula")
        if len(set(posicoes)) != len(posicoes):
            raise PedidoRecusado("o pedido tem posição repetida")
        if (composicao_visual is None) != (referencia_visual is None):
            raise PedidoRecusado(
                "composição visual e referência visual devem ser informadas juntas"
            )
        rotulo = (nome or "").strip()
        if len(rotulo) > NOME_MAXIMO:
            raise PedidoRecusado(f"o nome passa de {NOME_MAXIMO} caracteres")

        provedor = PROVEDOR_DO_MODO[modo]
        if itens:
            caminhos, categoria, ata_do_dossie, identificadores = self._visao_unida(itens, modo)
        else:
            assert ata is not None
            caminhos, categoria, ata_do_dossie = self._destaque_unico(ata, modo)
            identificadores = [ata]

        agora = _agora()
        with self._trava:
            identificador = self._identificador_novo(ata_do_dossie, provedor, agora)
            andamento = Andamento(
                identificador=identificador,
                nome=rotulo or identificador,
                ata=ata_do_dossie,
                atas=identificadores,
                provedor=provedor,
                categoria=categoria,
                estado=EstadoDoAndamento.NA_FILA,
                celulas=[
                    AndamentoDaCelula(audiencia=a, formato=f)
                    for a, f in sorted(posicoes, key=_ordem_da_matriz)
                ],
                criado_em=agora,
                atualizado_em=agora,
                composicao_visual=composicao_visual,
                referencia_visual=referencia_visual,
            )
            self._em_memoria[identificador] = andamento
            _gravar(self._pasta, andamento)
            self._fila.put(
                _Trabalho(
                    identificador=identificador,
                    caminho_ata=caminhos,
                    provedor=provedor,
                    pedido=sorted(posicoes, key=_ordem_da_matriz),
                    nome=rotulo,
                    duracao=duracao,
                    composicao_visual=composicao_visual,
                    referencia_visual=referencia_visual,
                )
            )
            self._acordar_o_trabalhador()
            return andamento.model_copy(deep=True)

    def _ata_geravel(self, identificador: str) -> tuple[Path, CategoriaDaAta, str]:
        """O arquivo, a categoria e o identificador de uma Ata, ou a recusa com o motivo."""
        caminho = self._repositorio.arquivo(identificador)
        if caminho is None:
            raise AtaNaoEncontrada(f"Ata {identificador!r} não encontrada")
        carregada = self._repositorio.carregar(identificador)
        if carregada is None:
            raise PedidoRecusado(f"a Ata {identificador!r} está ilegível")
        resumo = self._repositorio.resumir(identificador)
        if resumo is not None and not resumo.extracao_completa:
            raise PedidoRecusado(
                f"a Ata {identificador!r} tem texto curto demais, sem número: não há uma afirmação "
                "central para conferir, toda Célula reprovaria por falha de extração e a geração "
                "só gastaria cota. Importe o documento completo."
            )
        return caminho, carregada.categoria, carregada.identificador

    def _destaque_unico(
        self, ata: str, modo: ModoDeGeracao
    ) -> tuple[Path, CategoriaDaAta, str]:
        caminho, categoria, identificador = self._ata_geravel(ata)
        self._conferir_o_modo(modo, identificador)
        return caminho, categoria, identificador

    def _visao_unida(
        self, itens: list[str], modo: ModoDeGeracao
    ) -> tuple[list[Path], CategoriaDaAta, str, list[str]]:
        """Valida as Atas da união e devolve os caminhos, a categoria, o id do dossiê e os itens."""
        if not MINIMO_DE_PARTES <= len(itens) <= MAXIMO_DE_PARTES:
            raise PedidoRecusado(
                f"a Visão unida junta de {MINIMO_DE_PARTES} a {MAXIMO_DE_PARTES} Atas: para uma só, "
                "use o Destaque único"
            )
        if len(set(itens)) != len(itens):
            raise PedidoRecusado("a Visão unida não aceita Ata repetida")
        if modo is ModoDeGeracao.DEMO:
            raise PedidoRecusado(
                "a Demo não existe para a Visão unida: não há respostas prontas para uma "
                "combinação de Atas. Use o modo Real."
            )
        caminhos = [self._ata_geravel(identificador)[0] for identificador in itens]
        atas = [self._repositorio.carregar(identificador) for identificador in itens]
        self._conferir_o_modo(modo, "uniao")
        uniao = compor_uniao([a for a in atas if a is not None])
        return caminhos, CategoriaDaAta.UNIDA, uniao.identificador, list(itens)

    def _conferir_o_modo(self, modo: ModoDeGeracao, identificador_da_ata: str) -> None:
        if modo is ModoDeGeracao.DEMO:
            if not (PASTA_RESPOSTAS_PRONTAS / f"{identificador_da_ata}.json").exists():
                raise PedidoRecusado(
                    "a Demo só existe para Atas com respostas prontas "
                    f"(data/respostas_prontas/{identificador_da_ata}.json); use o modo Real"
                )
            return
        try:
            provedor_por_nome(PROVEDOR_DO_MODO[modo])
        except ErroProvedor as erro:
            motivo = erro.mensagem.replace(" — ou rode com --provedor falso", "")
            raise PedidoRecusado(
                f"o modo Real não está configurado: {motivo}. Use a Demo para gerar sem chave."
            ) from None

    def _identificador_novo(self, ata: str, provedor: str, agora: datetime) -> str:
        base = f"{ata}-{provedor}-{agora.strftime('%Y%m%d-%H%M%S')}"
        candidato, numero = base, 1
        while candidato in self._em_memoria or (self._pasta / candidato).exists():
            numero += 1
            candidato = f"{base}-{numero}"
        return candidato

    # -- leitura --------------------------------------------------------------

    def andamento(self, identificador: str) -> Andamento | None:
        """Em memória quando o job é desta vida do servidor; senão, o que está no disco."""
        with self._trava:
            vivo = self._em_memoria.get(identificador)
            if vivo is not None:
                return vivo.model_copy(deep=True)
        return ler_andamento(self._pasta, identificador)

    def listar(self) -> list[Andamento]:
        """Todo job conhecido: o desta vida do servidor e os que só existem no disco."""
        with self._trava:
            todos = {i: a.model_copy(deep=True) for i, a in self._em_memoria.items()}
        if self._pasta.exists():
            for pasta in self._pasta.iterdir():
                if pasta.name in todos or not (pasta / NOME_DO_ANDAMENTO).exists():
                    continue
                do_disco = ler_andamento(self._pasta, pasta.name)
                if do_disco is not None:
                    todos[pasta.name] = do_disco
        return list(todos.values())

    def excluir(self, identificador: str) -> bool:
        """Apaga a Saída e tudo o que ela gravou. ``False`` se não existe.

        Levanta ``PedidoRecusado`` se a geração está na fila ou rodando: a thread ainda grava ali.
        """
        raiz = self._pasta.resolve()
        alvo = (raiz / identificador).resolve()
        if alvo.parent != raiz:
            return False
        with self._trava:
            vivo = self._em_memoria.get(identificador)
            if vivo is not None and vivo.estado in ESTADOS_EM_ANDAMENTO:
                raise PedidoRecusado("a Saída ainda está sendo gerada: espere terminar para excluir")
            if not alvo.is_dir() and vivo is None:
                return False
            self._em_memoria.pop(identificador, None)
            shutil.rmtree(alvo, ignore_errors=True)
        return True

    def recuperar_interrompidos(self) -> list[str]:
        """No boot: o que estava ``na_fila`` ou ``gerando`` perdeu o processo e vira ``interrompida``."""
        recuperados: list[str] = []
        if not self._pasta.exists():
            return recuperados
        for pasta in sorted(self._pasta.iterdir()):
            andamento = ler_andamento(self._pasta, pasta.name)
            if andamento is None or andamento.estado not in ESTADOS_EM_ANDAMENTO:
                continue
            with self._trava:
                if pasta.name in self._em_memoria:
                    continue  # é job desta vida do servidor, não um órfão
                andamento.estado = EstadoDoAndamento.INTERROMPIDA
                andamento.erro = "o servidor reiniciou antes de a geração terminar"
                andamento.atualizado_em = _agora()
                _gravar(self._pasta, andamento)
            recuperados.append(andamento.identificador)
        return recuperados

    def aguardar_ocioso(self, timeout: float = 30.0) -> bool:
        """Só para os testes: espera a fila esvaziar e o último job terminar."""
        return self._ocioso.wait(timeout)

    # -- a thread --------------------------------------------------------------

    def _acordar_o_trabalhador(self) -> None:
        """Chamado com a trava. Sobe a thread se ela não estiver rodando."""
        if self._rodando:
            return
        self._rodando = True
        self._ocioso.clear()
        threading.Thread(target=self._trabalhar, name="geracao-suno", daemon=True).start()

    def _trabalhar(self) -> None:
        while True:
            with self._trava:
                try:
                    trabalho = self._fila.get_nowait()
                except queue.Empty:
                    self._rodando = False
                    self._ocioso.set()
                    return
            self._processar(trabalho)

    def _processar(self, trabalho: _Trabalho) -> None:
        self._mudar(trabalho.identificador, estado=EstadoDoAndamento.GERANDO)
        try:
            self._executar(
                trabalho.caminho_ata,
                trabalho.provedor,
                self._pasta,
                duracao=trabalho.duracao,
                identificador=trabalho.identificador,
                pedido=trabalho.pedido,
                nome=trabalho.nome or None,
                composicao_visual=trabalho.composicao_visual,
                referencia_visual=trabalho.referencia_visual,
                ao_mudar_fase=lambda fase: self._mudar(trabalho.identificador, fase=fase),
                ao_andar=lambda aud, fmt, etapa, rodada: self._andar(
                    trabalho.identificador, aud, fmt, etapa, rodada
                ),
            )
        except Exception as erro:  # noqa: BLE001 - o job falhou; o servidor e a fila seguem
            _registro.exception("geração %s falhou", trabalho.identificador)
            self._mudar(
                trabalho.identificador,
                estado=EstadoDoAndamento.FALHOU,
                erro=sem_credencial(str(erro))[:ERRO_MAXIMO] or type(erro).__name__,
            )
            return
        self._mudar(
            trabalho.identificador,
            estado=EstadoDoAndamento.CONCLUIDA,
            fase=None,
            concluido_em=_agora(),
        )

    def _mudar(self, identificador: str, **campos: object) -> None:
        with self._trava:
            andamento = self._em_memoria[identificador]
            for campo, valor in campos.items():
                setattr(andamento, campo, valor)
            andamento.atualizado_em = _agora()
            _gravar(self._pasta, andamento)

    def _andar(
        self,
        identificador: str,
        audiencia: Audiencia,
        formato: Formato,
        etapa: EtapaDaCelula,
        rodada: int,
    ) -> None:
        with self._trava:
            andamento = self._em_memoria[identificador]
            for celula in andamento.celulas:
                if celula.audiencia is audiencia and celula.formato is formato:
                    celula.etapa = etapa
                    celula.rodada = rodada
                    break
            andamento.atualizado_em = _agora()
            _gravar(self._pasta, andamento)


def _ordem_da_matriz(posicao: tuple[Audiencia, Formato]) -> tuple[int, int]:
    return (list(Audiencia).index(posicao[0]), list(Formato).index(posicao[1]))


__all__ = [
    "AtaNaoEncontrada",
    "FaseDaExecucao",
    "Gerenciador",
    "ModoDeGeracao",
    "NOME_DO_ANDAMENTO",
    "NOME_MAXIMO",
    "PROVEDOR_DO_MODO",
    "PedidoRecusado",
    "caminho_do_andamento",
    "ler_andamento",
]
