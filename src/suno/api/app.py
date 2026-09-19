"""A aplicação FastAPI. O cliente TypeScript é gerado do OpenAPI daqui.

Lê do disco o mesmo ``execucao.json`` e ``pacote.json`` que ``gravar_execucao`` e
``montar_pacote`` gravam — é a prova de que a tela mostra o que o pytest confere. A API
não executa o pipeline: ``executar`` e ``montar_pacote`` são comando de terminal
(``suno.cli``), nunca chamados por uma rota.

ADR 0005.
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

_REGISTRO = logging.getLogger(__name__)

from suno import __version__
from suno.dominio import (
    Ancoras,
    AncoraNumerica,
    Ata,
    Audiencia,
    Destino,
    EstadoMedida,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    PacotePublicacao,
    Pendencia,
)
from suno.gerador.execucao import carregar_execucao, gravar_execucao, listar_execucoes
from suno.ingestao.pdf import carregar_ata

PASTA_ATAS = Path("data/atas")
"""Mesma pasta fixa de ``suno.cli.PASTA_ATAS``: a API só lê Ata versionada em disco."""

SUFIXOS_DE_ATA = (".pdf", ".txt")

NOME_DA_PASTA_DO_PACOTE = "pacote"
NOME_DO_REGISTRO_DO_PACOTE = "pacote.json"

PASTA_DA_SPA = Path("web/dist")
"""Se ``index.html`` existir aqui (build do Agente 12), a API serve a SPA em ``/``."""


# ---------------------------------------------------------------------------
# Modelos de resposta próprios da API (não pertencem ao contrato de dominio.py)
# ---------------------------------------------------------------------------


class AtaResumo(BaseModel):
    """A Ata sem ``texto``: a listagem não carrega o comunicado inteiro por item."""

    identificador: str
    titulo: str
    reuniao: int | None
    data_referencia: date


class ExecucaoResumo(BaseModel):
    """O que a lista de execuções mostra sem abrir o Laudo de cada Célula."""

    identificador: str
    ata: str
    provedor: str
    iniciada_em: datetime
    aprovadas: int
    total_celulas: int
    pendencias: int


class Saude(BaseModel):
    ok: bool
    execucoes: int


class Filas(BaseModel):
    """As três filas humanas H3, H4 e H5, sempre listas de ``Pendencia``."""

    h3_desempate: list[Pendencia] = []
    h4_revisao: list[Pendencia] = []
    h5_aprovacao_pacote: list[Pendencia] = []


class DecisaoFila(BaseModel):
    """O corpo do ``POST .../resolver``: a decisão que um humano registrou em H4."""

    decisao: str


# ---------------------------------------------------------------------------
# Leitura de disco (a Ata e o Pacote não têm ``carregar_*`` de fila pronta)
# ---------------------------------------------------------------------------


def _arquivo_da_ata(identificador: str) -> Path | None:
    for sufixo in SUFIXOS_DE_ATA:
        caminho = PASTA_ATAS / f"{identificador}{sufixo}"
        if caminho.exists():
            return caminho
    return None


def _identificadores_de_ata() -> list[str]:
    """Um identificador por Ata em ``data/atas/``, mesmo quando ``.pdf`` e ``.txt`` coexistem."""
    if not PASTA_ATAS.exists():
        return []
    encontrados = {
        caminho.stem for caminho in PASTA_ATAS.iterdir() if caminho.suffix in SUFIXOS_DE_ATA
    }
    return sorted(encontrados)


def _pasta_do_pacote(pasta_execucoes: Path, identificador: str, audiencia: Audiencia, formato: Formato) -> Path:
    nome = f"{audiencia.value}-{formato.value}"
    return Path(pasta_execucoes) / identificador / NOME_DA_PASTA_DO_PACOTE / nome


def _pacotes_da_execucao(pasta_execucoes: Path, identificador: str) -> list[PacotePublicacao]:
    """Lê ``pacote/*/pacote.json``, na mesma ordem estável do sistema de arquivos."""
    raiz = Path(pasta_execucoes) / identificador / NOME_DA_PASTA_DO_PACOTE
    if not raiz.exists():
        return []
    pacotes = []
    for pasta in sorted(raiz.iterdir()):
        arquivo = pasta / NOME_DO_REGISTRO_DO_PACOTE
        if arquivo.exists():
            pacotes.append(PacotePublicacao.model_validate_json(arquivo.read_text(encoding="utf-8")))
    return pacotes


def _fila_h3(execucao: Execucao) -> list[Pendencia]:
    """Uma Pendência por dimensão subjetiva em ``REVISAO_HUMANA`` no Laudo final de cada Célula.

    O desempate (H3) é decidido durante a avaliação, então olhar só o Laudo final —
    não cada rodada do Ciclo de correção — basta: é o que decide o destino que já saiu.
    """
    pendencias: list[Pendencia] = []
    for historico in execucao.celulas:
        laudo = historico.laudo_final
        if laudo is None or laudo.comite is None:
            continue
        for dimensao in laudo.comite.dimensoes:
            if dimensao.estado is EstadoMedida.REVISAO_HUMANA:
                pendencias.append(
                    Pendencia(
                        fila=FilaHumana.H3_DESEMPATE,
                        audiencia=historico.audiencia,
                        formato=historico.formato,
                        motivo=f"juízes discordam em {dimensao.dimensao.value}",
                    )
                )
    return pendencias


def _fila_h5(pacotes: list[PacotePublicacao]) -> list[Pendencia]:
    """Uma Pendência por Pacote ainda sem ``aprovado_por_humano`` (ADR 0014: nunca reprova)."""
    pendencias: list[Pendencia] = []
    for pacote in pacotes:
        if pacote.aprovado_por_humano:
            continue
        defeitos = pacote.conferencia.defeitos
        motivo = (
            f"{len(defeitos)} defeito(s) de render achado(s) pela conferência visual"
            if defeitos
            else "sem defeito de render, aguardando aprovação"
        )
        pendencias.append(
            Pendencia(
                fila=FilaHumana.H5_APROVACAO_PACOTE,
                audiencia=pacote.audiencia,
                formato=pacote.formato,
                motivo=motivo,
            )
        )
    return pendencias


def criar_app(pasta_execucoes: Path) -> FastAPI:
    """Monta a API com a pasta de execuções injetada — nada global (ADR 0005).

    CORS liberado para ``localhost``/``127.0.0.1`` em qualquer porta, para o Vite em dev.
    Quando ``web/dist/index.html`` existe (build do Agente 12), a SPA é servida em ``/``
    com fallback para ``index.html``.
    """
    pasta_execucoes = Path(pasta_execucoes)
    app = FastAPI(title="Suno Content", version=__version__)
    # H4 e H5 fazem leitura-altera-escrita em execucao.json/pacote.json. Rota `def` (não
    # `async def`) roda no threadpool do Starlette — duas resoluções humanas chegando juntas
    # perdiam uma sem erro nenhum (achado do revisor de erros, 2026-09-19). Uma trava por app
    # é suficiente: o volume de escrita de H4/H5 é de poucas por execução, nunca um caminho quente.
    trava_de_escrita = threading.Lock()

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def _execucao_ou_404(identificador: str) -> Execucao:
        try:
            return carregar_execucao(identificador, pasta_execucoes)
        except FileNotFoundError:
            raise HTTPException(404, f"execução {identificador!r} não encontrada") from None
        except OSError:
            # Windows recusa `"`, `*`, `?`, `<`, `>`, `|` num caminho — um identificador com
            # esses caracteres nunca existiu, então é o mesmo 404, não um 500 (achado do
            # revisor de erros, 2026-09-19).
            raise HTTPException(404, f"execução {identificador!r} não encontrada") from None
        except ValidationError:
            # execucao.json em disco não bate mais com o domínio (escrita interrompida,
            # versão antiga): a execução existe, mas está ilegível — 404 é enganoso, e 500
            # some com a tela inteira; 409 diz "está lá, mas quebrado".
            raise HTTPException(409, f"execução {identificador!r} está gravada, mas ilegível") from None

    @app.get("/api/atas")
    def listar_atas() -> list[AtaResumo]:
        resumos: list[AtaResumo] = []
        for identificador in _identificadores_de_ata():
            caminho = _arquivo_da_ata(identificador)
            if caminho is None:
                continue
            ata = carregar_ata(caminho)
            resumos.append(
                AtaResumo(
                    identificador=ata.identificador,
                    titulo=ata.titulo,
                    reuniao=ata.reuniao,
                    data_referencia=ata.data_referencia,
                )
            )
        return resumos

    @app.get("/api/atas/{identificador}")
    def obter_ata(identificador: str) -> Ata:
        caminho = _arquivo_da_ata(identificador)
        if caminho is None:
            raise HTTPException(404, f"Ata {identificador!r} não encontrada")
        return carregar_ata(caminho)

    @app.get("/api/execucoes")
    def listar_execucoes_rota() -> list[ExecucaoResumo]:
        resumos: list[ExecucaoResumo] = []
        for identificador in listar_execucoes(pasta_execucoes):
            try:
                execucao = carregar_execucao(identificador, pasta_execucoes)
            except (OSError, ValidationError) as erro:
                # Uma execução ilegível não pode derrubar a listagem inteira — a tela inicial
                # some para todo mundo por causa de uma pasta só (achado do revisor de erros,
                # 2026-09-19). Ela some da lista; `/api/execucoes/{id}` ainda devolve 409 para
                # quem perguntar por ela direto.
                _REGISTRO.warning("execução %r ilegível, fora da listagem: %s", identificador, erro)
                continue
            aprovadas = sum(1 for h in execucao.celulas if h.destino_final is Destino.APROVADO)
            resumos.append(
                ExecucaoResumo(
                    identificador=execucao.identificador,
                    ata=execucao.ata,
                    provedor=execucao.provedor_gerador,
                    iniciada_em=execucao.iniciada_em,
                    aprovadas=aprovadas,
                    total_celulas=len(execucao.celulas),
                    pendencias=len(execucao.pendencias),
                )
            )
        return resumos

    @app.get("/api/execucoes/{identificador}")
    def obter_execucao(identificador: str) -> Execucao:
        return _execucao_ou_404(identificador)

    @app.get("/api/execucoes/{identificador}/ancoras")
    def obter_ancoras(identificador: str) -> Ancoras:
        return _execucao_ou_404(identificador).ancoras

    @app.get("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}")
    def obter_celula(identificador: str, audiencia: Audiencia, formato: Formato) -> HistoricoCelula:
        execucao = _execucao_ou_404(identificador)
        historico = execucao.historico(audiencia, formato)
        if historico is None:
            raise HTTPException(404, "Célula não encontrada nesta execução")
        return historico

    @app.get("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/ancoras")
    def obter_ancoras_da_celula(
        identificador: str, audiencia: Audiencia, formato: Formato
    ) -> list[AncoraNumerica]:
        """As Âncoras numéricas citadas pela Célula final — "Âncoras ao lado da Célula"."""
        execucao = _execucao_ou_404(identificador)
        historico = execucao.historico(audiencia, formato)
        if historico is None:
            raise HTTPException(404, "Célula não encontrada nesta execução")
        celula = historico.celula_final
        if celula is None:
            return []
        citadas: list[AncoraNumerica] = []
        for chave in celula.conteudo.ancoras_citadas:
            ancora = execucao.ancoras.numerica(chave)
            if ancora is not None:
                citadas.append(ancora)
        return citadas

    @app.get("/api/execucoes/{identificador}/pacotes")
    def listar_pacotes(identificador: str) -> list[PacotePublicacao]:
        _execucao_ou_404(identificador)  # 404 cedo se a execução nem existe
        return _pacotes_da_execucao(pasta_execucoes, identificador)

    @app.get("/api/execucoes/{identificador}/arquivos/{caminho:path}")
    def obter_arquivo(identificador: str, caminho: str) -> FileResponse:
        if ".." in Path(caminho).parts:
            raise HTTPException(400, "caminho não pode conter '..'")
        raiz = (pasta_execucoes / identificador).resolve()
        alvo = (raiz / caminho).resolve()
        if not alvo.is_relative_to(raiz):
            raise HTTPException(400, "caminho sai da pasta da execução")
        if not alvo.is_file():
            raise HTTPException(404, f"arquivo {caminho!r} não encontrado")
        return FileResponse(alvo)

    @app.get("/api/execucoes/{identificador}/filas")
    def obter_filas(identificador: str) -> Filas:
        execucao = _execucao_ou_404(identificador)
        pacotes = _pacotes_da_execucao(pasta_execucoes, identificador)
        return Filas(
            h3_desempate=_fila_h3(execucao),
            h4_revisao=list(execucao.pendencias),
            h5_aprovacao_pacote=_fila_h5(pacotes),
        )

    @app.post("/api/execucoes/{identificador}/filas/h4/{indice}/resolver")
    def resolver_pendencia(identificador: str, indice: int, corpo: DecisaoFila) -> Pendencia:
        with trava_de_escrita:
            execucao = _execucao_ou_404(identificador)
            if indice < 0 or indice >= len(execucao.pendencias):
                raise HTTPException(404, f"índice {indice} fora da fila H4")
            pendencia = execucao.pendencias[indice]
            pendencia.resolvida = True
            pendencia.decisao = corpo.decisao
            gravar_execucao(execucao, pasta_execucoes)
            return pendencia

    @app.post("/api/execucoes/{identificador}/pacotes/{audiencia}/{formato}/aprovar")
    def aprovar_pacote(identificador: str, audiencia: Audiencia, formato: Formato) -> PacotePublicacao:
        with trava_de_escrita:
            _execucao_ou_404(identificador)
            arquivo = _pasta_do_pacote(pasta_execucoes, identificador, audiencia, formato) / NOME_DO_REGISTRO_DO_PACOTE
            if not arquivo.exists():
                raise HTTPException(404, "Pacote não encontrado")
            pacote = PacotePublicacao.model_validate_json(arquivo.read_text(encoding="utf-8"))
            pacote = pacote.model_copy(update={"aprovado_por_humano": True})
            arquivo.write_text(pacote.model_dump_json(indent=2), encoding="utf-8")
            return pacote

    @app.get("/api/saude")
    def saude() -> Saude:
        return Saude(ok=True, execucoes=len(listar_execucoes(pasta_execucoes)))

    if (PASTA_DA_SPA / "index.html").exists():
        app.mount("/", StaticFiles(directory=PASTA_DA_SPA, html=True), name="spa")

    return app
