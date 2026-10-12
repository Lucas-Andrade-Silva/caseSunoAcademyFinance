"""A aplicação FastAPI. O cliente TypeScript é gerado do OpenAPI daqui.

Lê do disco o mesmo ``execucao.json`` e ``pacote.json`` que ``gravar_execucao`` e
``montar_pacote`` gravam — é a prova de que a tela mostra o que o pytest confere.

A API também inicia a geração: ``POST /api/execucoes`` enfileira um job no ``Gerenciador``
(um por vez, em segundo plano) e o andamento fica em ``andamento.json`` ao lado do
``execucao.json``. ``montar_pacote`` continua sendo comando de terminal (``suno.cli``).

ADR 0005, 0017.
"""

from __future__ import annotations

import io
import logging
import threading
import zipfile
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi import status as http
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as ErroHttpDoStarlette
from starlette.types import Scope

_REGISTRO = logging.getLogger(__name__)

from suno import __version__
from suno.api.geracao import (
    NOME_MAXIMO,
    AtaNaoEncontrada,
    Gerenciador,
    ModoDeGeracao,
    PedidoRecusado,
)
from suno.api.pacotes import EstadoDaMontagem, Montador, motivo_de_recusa
from suno.api.resumo import (
    PosicaoResumo,
    StatusSaida,
    montar_posicoes,
    montar_posicoes_do_andamento,
    status_da_saida,
    status_do_andamento,
)
from suno.dominio import (
    Ancoras,
    AncoraNumerica,
    Andamento,
    Ata,
    DuracaoDoVideo,
    Audiencia,
    CategoriaDaAta,
    ComposicaoCarrossel,
    DecisaoHumana,
    Destino,
    ErroProvedor,
    EstadoDecisao,
    EstadoMedida,
    Execucao,
    FeedbackVisualHumano,
    FilaHumana,
    Formato,
    HistoricoCelula,
    ModoSelecao,
    PacotePublicacao,
    Pendencia,
    PosicaoDaMatriz,
    ReferenciaVisual,
)
from suno.exportacao import FormatoExportacao, exportar
from suno.gerador.execucao import (
    PASTA_RESPOSTAS_PRONTAS,
    carregar_execucao,
    gravar_execucao,
    listar_execucoes,
)
from suno.origens.atualizacao import Atualizador, EstadoDaAtualizacao
from suno.origens.catalogo import (
    PASTA_FONTES,
    Origem,
    OrigemDesconhecida,
    OrigemIndisponivel,
    alternar,
    carregar_catalogo,
)
from suno.origens.curadoria import Sugestao, sugerir, sugerir_visao_unida
from suno.origens.importacao import (
    LIMITE_DO_ARQUIVO,
    ArquivoGrandeDemais,
    ArquivoRecusado,
    importar,
)
from suno.origens.repositorio import RepositorioDeAtas
from suno.origens.resumo import ResumoDaAta
from suno.pacote.historico_layouts import NOME_DO_BANCO
from suno.pacote import montar_pacote
from suno.pacote.coleta_referencias import (
    CandidatoDeReferencia,
    ColetorDeReferencias,
    ColetorInstaloader,
    DescobertaDeReferencias,
    PerfilDeReferencia,
    RepositorioDaColeta,
    ResultadoDaColeta,
    SetorDaReferencia,
)
from suno.pacote.analise_visual import (
    ImagemReferenciaInvalida,
    LIMITE_DA_IMAGEM,
    analisar_referencia_visual,
    normalizar_imagem,
)
from suno.pacote.referencias_visuais import (
    ReferenciaVisualDuplicada,
    ReferenciaVisualNaoEncontrada,
    RepositorioReferenciasVisuais,
)
from suno.pacote.feedback_visual import RepositorioFeedbackVisual
from suno.provedores.roteador import provedor_por_nome
from suno.provedores.base import Provedor
from suno.revisao import CelulaNaoEncontrada, DecisaoBloqueada, DecisaoInvalida, decidir
from suno.video.plano import montar_plano, plano_em_markdown

PASTA_ATAS = Path("data/atas")
"""Mesma pasta fixa de ``suno.cli.PASTA_ATAS``: a API só lê Ata versionada em disco."""

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
    categoria: CategoriaDaAta
    origem: str
    demo_disponivel: bool
    """Há ``data/respostas_prontas/<id>.json``: só então a Demo roda sem rede para esta Ata."""


class ExecucaoResumo(BaseModel):
    """O que a lista de Saídas mostra sem abrir o Laudo de cada Célula."""

    identificador: str
    nome: str
    ata: str
    provedor: str
    modo: ModoSelecao | None
    iniciada_em: datetime
    aprovadas: int
    aprovadas_humano: int
    total_celulas: int
    pendencias: int
    status: StatusSaida
    posicoes: list[PosicaoResumo]
    erro: str | None = None
    categoria: CategoriaDaAta = CategoriaDaAta.COPOM
    """Fora do Copom a Saída é não calibrada: Limiares e Léxico foram medidos só com o Copom."""
    atas: list[str] = []
    """As Atas usadas: uma, ou de 2 a 5 na Visão unida."""


class Saude(BaseModel):
    ok: bool
    execucoes: int
    real_disponivel: bool
    """O ambiente tem chave e modelo de ao menos um provedor: só então o modo Real pode gerar."""


class Filas(BaseModel):
    """As três filas humanas H3, H4 e H5, sempre listas de ``Pendencia``."""

    h3_desempate: list[Pendencia] = []
    h4_revisao: list[Pendencia] = []
    h5_aprovacao_pacote: list[Pendencia] = []


class DecisaoFila(BaseModel):
    """O corpo do ``POST .../resolver``: a decisão que um humano registrou em H4."""

    decisao: str


class NovaReferenciaVisual(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    tema: str = Field(min_length=3, max_length=100)
    composicao: ComposicaoCarrossel
    descricao: str = Field(min_length=10, max_length=400)
    instrucao_de_design: str = Field(min_length=10, max_length=500)
    origem: str = Field(default="Importação manual", max_length=500)


class AlteracaoDaReferenciaVisual(BaseModel):
    aprovada: bool


class NovoPerfilDeReferencia(BaseModel):
    usuario: str = Field(min_length=1, max_length=31)


class PedidoDeColeta(BaseModel):
    janela_dias: int = Field(default=30)


class ImportacaoDeCandidato(BaseModel):
    composicao: ComposicaoCarrossel


class AprovacaoDoPacote(BaseModel):
    revisor: str | None = Field(default=None, max_length=100)
    observacao: str | None = Field(default=None, max_length=500)


class Renomeacao(BaseModel):
    """O corpo do ``PATCH /api/execucoes/{id}``."""

    nome: str


class OrigemComAtas(Origem):
    """Uma Origem do catálogo com as Atas que ela tem em disco (a Fonte e seus itens, na tela)."""

    atas: list[ResumoDaAta]


class ListaDeOrigens(BaseModel):
    origens: list[OrigemComAtas]
    atualizacao: EstadoDaAtualizacao


class AlteracaoDaOrigem(BaseModel):
    """O corpo do ``PATCH /api/fontes/{id}``: ligar ou desligar."""

    ativa: bool


class Sugestoes(BaseModel):
    """As duas sugestões da curadoria. ``visao_unida`` é ``None`` com menos de 2 Atas que geram."""

    destaque_unico: Sugestao | None
    visao_unida: Sugestao | None


class NovaSaida(BaseModel):
    """O corpo do ``POST /api/execucoes``: o que gerar, de onde e em que modo."""

    nome: str | None = None
    ata: str | None = None
    """O Destaque único: uma Ata. Exatamente um entre ``ata`` e ``itens``."""
    itens: list[str] | None = None
    """A Visão unida: de 2 a 5 Atas."""
    modo: ModoDeGeracao
    pedido: list[PosicaoDaMatriz]
    comite: bool = False
    duracao: DuracaoDoVideo = DuracaoDoVideo.S60
    """A duração do Roteiro: 40, 60, 90, 120 ou 180 segundos."""
    composicao_visual: ComposicaoCarrossel | None = None
    """Família visual escolhida na curadoria, quando o pedido inclui Carrossel."""
    referencia_visual: str | None = Field(default=None, max_length=160)
    """Exemplo aprovado escolhido dentro da família visual."""


class PlanoDeEdicao(BaseModel):
    """O plano de edição de um Roteiro: o JSON para o gerador de avatar e a tabela legível."""

    plano: dict[str, Any]
    markdown: str


class PedidoDeDecisao(BaseModel):
    """O corpo do ``POST .../decisao``: aprovar ou reprovar uma Célula."""

    estado: EstadoDecisao
    motivo: str | None = None
    revisor: str | None = None



# ---------------------------------------------------------------------------
# Leitura de disco (a Ata e o Pacote não têm ``carregar_*`` de fila pronta)
# ---------------------------------------------------------------------------


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


def _real_disponivel() -> bool:
    """O modo Real precisa de chave e modelo de algum provedor no ambiente."""
    try:
        provedor_por_nome("roteador")
    except ErroProvedor:
        return False
    return True


def _resumo_do_andamento(andamento: Andamento) -> ExecucaoResumo:
    """A Saída que ainda não tem ``execucao.json``: em geração, na fila, interrompida ou que falhou."""
    return ExecucaoResumo(
        identificador=andamento.identificador,
        nome=andamento.nome,
        ata=andamento.ata,
        provedor=andamento.provedor,
        modo=ModoSelecao.SEPARADA,
        iniciada_em=andamento.criado_em,
        aprovadas=0,
        aprovadas_humano=0,
        total_celulas=len(andamento.celulas),
        pendencias=0,
        status=status_do_andamento(andamento),
        posicoes=montar_posicoes_do_andamento(andamento),
        erro=andamento.erro,
        categoria=andamento.categoria,
        atas=andamento.atas or [andamento.ata],
    )


def _resumo_da_execucao(execucao: Execucao) -> ExecucaoResumo:
    posicoes = montar_posicoes(execucao)
    return ExecucaoResumo(
        identificador=execucao.identificador,
        nome=execucao.nome,
        ata=execucao.ata,
        provedor=execucao.provedor_gerador,
        modo=execucao.selecao.modo if execucao.selecao is not None else None,
        iniciada_em=execucao.iniciada_em,
        aprovadas=sum(1 for h in execucao.celulas if h.destino_final is Destino.APROVADO),
        aprovadas_humano=sum(1 for d in execucao.decisoes if d.estado is EstadoDecisao.APROVADA),
        total_celulas=len(execucao.celulas),
        pendencias=len(execucao.pendencias),
        status=status_da_saida(posicoes),
        posicoes=posicoes,
        categoria=execucao.categoria,
        atas=execucao.selecao.itens if execucao.selecao is not None else [execucao.ata],
    )


class _SpaEstatica(StaticFiles):
    """Serve ``web/dist`` e cai em ``index.html`` para rota do React Router (ex. ``/saidas/abc``).

    ``StaticFiles(html=True)`` só devolve ``index.html`` para o diretório raiz: atualizar a
    página numa rota interna dava 404. Rota de API que não existe continua sendo 404 de verdade.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except ErroHttpDoStarlette as erro:
            # No Windows o Starlette entrega o caminho com barra invertida ("api\nao-existe").
            e_da_api = path.replace("\\", "/").startswith("api/")
            if erro.status_code == 404 and not e_da_api:
                return await super().get_response("index.html", scope)
            raise


def criar_app(
    pasta_execucoes: Path,
    *,
    pasta_atas: Path = PASTA_ATAS,
    pasta_fontes: Path = PASTA_FONTES,
    executar_fn: Callable[..., Execucao] | None = None,
    atualizador: Atualizador | None = None,
    montar_fn: Callable[[str, Path], list[PacotePublicacao]] | None = None,
    provedor_visao: Provedor | None = None,
    coletor_referencias: ColetorDeReferencias | None = None,
    recuperar_ao_iniciar: bool = True,
) -> FastAPI:
    """Monta a API com a pasta de execuções injetada — nada global (ADR 0005).

    CORS liberado para ``localhost``/``127.0.0.1`` em qualquer porta, para o Vite em dev.
    Quando ``web/dist/index.html`` existe (build do Agente 12), a SPA é servida em ``/``
    com fallback para ``index.html``.

    ``pasta_atas`` e ``executar_fn`` existem para os testes: a primeira aponta para outra
    pasta de Atas e a segunda troca o pipeline por um executor falso. No boot, o job que
    ficou ``na_fila`` ou ``gerando`` de uma vida anterior do servidor vira ``interrompida``;
    ``recuperar_ao_iniciar=False`` pula isso (gerar o schema não mexe em disco).
    """
    pasta_execucoes = Path(pasta_execucoes)
    pasta_atas = Path(pasta_atas)
    pasta_fontes = Path(pasta_fontes)
    app = FastAPI(title="Suno Content", version=__version__)
    repositorio = RepositorioDeAtas(pasta_atas, pasta_fontes)
    referencias_visuais = RepositorioReferenciasVisuais(pasta_execucoes / NOME_DO_BANCO)
    coleta_referencias = RepositorioDaColeta(pasta_execucoes / NOME_DO_BANCO)
    feedback_visual = RepositorioFeedbackVisual(pasta_execucoes / NOME_DO_BANCO)
    gerenciador = (
        Gerenciador(
            pasta_execucoes, pasta_atas=pasta_atas, executar_fn=executar_fn, repositorio=repositorio
        )
        if executar_fn is not None
        else Gerenciador(pasta_execucoes, pasta_atas=pasta_atas, repositorio=repositorio)
    )
    if recuperar_ao_iniciar:
        gerenciador.recuperar_interrompidos()
    app.state.gerenciador = gerenciador
    atualizador = atualizador or Atualizador(pasta_atas, pasta_fontes)
    app.state.atualizador = atualizador
    if montar_fn is not None:
        montador = Montador(pasta_execucoes, montar_fn=montar_fn)
    else:
        montador = Montador(
            pasta_execucoes,
            montar_fn=lambda identificador, pasta: montar_pacote(
                identificador, pasta, provedor_visao=provedor_visao
            ),
            montar_celula_fn=lambda identificador, pasta, audiencia, formato: montar_pacote(
                identificador,
                pasta,
                alvo=(audiencia, formato),
                provedor_visao=provedor_visao,
            ),
        )
    app.state.montador = montador
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

    def _resumo_ou_404(identificador: str) -> ExecucaoResumo:
        """O resumo da execução gravada ou, sem ela, o do job que ainda a está gerando."""
        try:
            return _resumo_da_execucao(carregar_execucao(identificador, pasta_execucoes))
        except (FileNotFoundError, OSError):
            andamento = gerenciador.andamento(identificador)
            if andamento is None:
                raise HTTPException(404, f"execução {identificador!r} não encontrada") from None
            return _resumo_do_andamento(andamento)
        except ValidationError:
            raise HTTPException(409, f"execução {identificador!r} está gravada, mas ilegível") from None

    @app.get("/api/atas")
    def listar_atas() -> list[AtaResumo]:
        resumos: list[AtaResumo] = []
        for identificador in repositorio.identificadores():
            ata = repositorio.carregar(identificador)
            if ata is None:
                continue
            resumos.append(
                AtaResumo(
                    identificador=ata.identificador,
                    titulo=ata.titulo,
                    reuniao=ata.reuniao,
                    data_referencia=ata.data_referencia,
                    categoria=ata.categoria,
                    origem=ata.origem,
                    demo_disponivel=(PASTA_RESPOSTAS_PRONTAS / f"{ata.identificador}.json").exists(),
                )
            )
        return resumos

    @app.get("/api/atas/{identificador}")
    def obter_ata(identificador: str) -> Ata:
        ata = repositorio.carregar(identificador)
        if ata is None:
            raise HTTPException(404, f"Ata {identificador!r} não encontrada")
        return ata

    @app.get("/api/fontes")
    def listar_fontes() -> ListaDeOrigens:
        return ListaDeOrigens(
            origens=[
                OrigemComAtas(**origem.model_dump(), atas=repositorio.itens_da_origem(origem))
                for origem in carregar_catalogo(pasta_fontes)
            ],
            atualizacao=atualizador.estado(),
        )

    @app.patch("/api/fontes/{identificador}")
    def alterar_origem(identificador: str, corpo: AlteracaoDaOrigem) -> Origem:
        try:
            return alternar(pasta_fontes, identificador, corpo.ativa)
        except OrigemDesconhecida as erro:
            raise HTTPException(404, str(erro)) from None
        except OrigemIndisponivel as erro:
            raise HTTPException(409, str(erro)) from None

    @app.post("/api/fontes/atualizar", status_code=http.HTTP_202_ACCEPTED)
    def atualizar_fontes() -> EstadoDaAtualizacao:
        """Busca nas Origens ligadas, em segundo plano. Precisa de rede e falha sem travar a tela."""
        return atualizador.iniciar()

    @app.get("/api/fontes/atualizacao")
    def obter_atualizacao() -> EstadoDaAtualizacao:
        return atualizador.estado()

    @app.post("/api/fontes/importar", status_code=http.HTTP_201_CREATED)
    async def importar_comunicado(
        request: Request, titulo: str, data_referencia: date | None = None
    ) -> ResumoDaAta:
        """O corpo é o arquivo cru (PDF ou texto UTF-8); título e data vão na query."""
        declarado = request.headers.get("content-length", "")
        if declarado.isdigit() and int(declarado) > LIMITE_DO_ARQUIVO:
            raise HTTPException(413, "o arquivo passa de 15 MB")
        corpo = bytearray()
        async for pedaco in request.stream():
            corpo.extend(pedaco)
            if len(corpo) > LIMITE_DO_ARQUIVO:
                raise HTTPException(413, "o arquivo passa de 15 MB")
        try:
            ata = await run_in_threadpool(
                importar,
                pasta_fontes,
                conteudo=bytes(corpo),
                titulo=titulo,
                data_referencia=data_referencia,
            )
        except ArquivoGrandeDemais as erro:
            raise HTTPException(413, str(erro)) from None
        except ArquivoRecusado as erro:
            raise HTTPException(422, str(erro)) from None
        resumo = repositorio.resumir(ata.identificador)
        if resumo is None:  # gravou e não leu de volta: nunca devia acontecer
            raise HTTPException(500, "a Ata foi gravada mas não pôde ser lida de volta")
        return resumo

    @app.get("/api/curadoria/sugestoes")
    def obter_sugestoes() -> Sugestoes:
        origens = carregar_catalogo(pasta_fontes)
        atas = {origem.id: repositorio.itens_da_origem(origem) for origem in origens}
        return Sugestoes(
            destaque_unico=sugerir(origens, atas),
            visao_unida=sugerir_visao_unida(origens, atas),
        )

    @app.get("/api/referencias-visuais")
    def listar_referencias_visuais() -> list[ReferenciaVisual]:
        """A biblioteca local de padrões aprovados que orienta a direção de arte."""
        return referencias_visuais.listar()

    @app.post("/api/referencias-visuais", status_code=http.HTTP_201_CREATED)
    def importar_referencia_visual(corpo: NovaReferenciaVisual) -> ReferenciaVisual:
        """Cadastra metadados autorizados; a nova referência nasce não aprovada."""
        try:
            return referencias_visuais.adicionar(**corpo.model_dump())
        except ReferenciaVisualDuplicada as erro:
            raise HTTPException(409, str(erro)) from None

    @app.get("/api/referencias-visuais/coleta/perfis")
    def listar_perfis_de_referencia() -> list[PerfilDeReferencia]:
        return coleta_referencias.listar_perfis()

    @app.post(
        "/api/referencias-visuais/coleta/perfis",
        status_code=http.HTTP_201_CREATED,
    )
    def adicionar_perfil_de_referencia(corpo: NovoPerfilDeReferencia) -> PerfilDeReferencia:
        try:
            return coleta_referencias.adicionar_perfil(corpo.usuario)
        except ValueError as erro:
            raise HTTPException(422, str(erro)) from None

    @app.get("/api/referencias-visuais/coleta/candidatos")
    def listar_candidatos_de_referencia() -> list[CandidatoDeReferencia]:
        return coleta_referencias.listar_candidatos()

    @app.get("/api/referencias-visuais/descoberta")
    def descobrir_referencias(
        janela_dias: int = 30,
        setor: SetorDaReferencia | None = None,
    ) -> DescobertaDeReferencias:
        """Filtra carrosséis e ranqueia os perfis monitorados por movimentação."""
        try:
            return coleta_referencias.descobrir(
                janela_dias=janela_dias,
                setor=setor,
            )
        except ValueError as erro:
            raise HTTPException(422, str(erro)) from None

    @app.post("/api/referencias-visuais/coleta/executar")
    def executar_coleta_de_referencias(corpo: PedidoDeColeta) -> ResultadoDaColeta:
        try:
            return coleta_referencias.coletar(
                coletor_referencias or ColetorInstaloader(),
                janela_dias=corpo.janela_dias,
            )
        except ValueError as erro:
            raise HTTPException(422, str(erro)) from None

    @app.post(
        "/api/referencias-visuais/coleta/candidatos/{identificador}/importar",
        status_code=http.HTTP_201_CREATED,
    )
    def importar_candidato_de_referencia(
        identificador: str, corpo: ImportacaoDeCandidato
    ) -> ReferenciaVisual:
        candidato = next(
            (
                item
                for item in coleta_referencias.listar_candidatos()
                if item.identificador == identificador
            ),
            None,
        )
        if candidato is None:
            raise HTTPException(404, "candidato de referencia nao encontrado")
        descricao = candidato.legenda.strip() or (
            f"Carrossel publico descoberto no perfil @{candidato.usuario}."
        )
        try:
            referencia = referencias_visuais.adicionar(
                titulo=candidato.titulo,
                tema=f"referencia publica de @{candidato.usuario}",
                composicao=corpo.composicao,
                descricao=descricao[:400],
                instrucao_de_design=(
                    "Revise a estrutura visual manualmente antes de aprovar; nao copie "
                    "texto, imagem ou identidade da publicacao original."
                ),
                origem=candidato.url,
            )
        except ReferenciaVisualDuplicada as erro:
            raise HTTPException(409, str(erro)) from None
        coleta_referencias.marcar_importado(identificador)
        return referencia

    @app.patch("/api/referencias-visuais/{identificador}")
    def alterar_referencia_visual(
        identificador: str, corpo: AlteracaoDaReferenciaVisual
    ) -> ReferenciaVisual:
        try:
            return referencias_visuais.definir_aprovacao(identificador, corpo.aprovada)
        except ReferenciaVisualNaoEncontrada:
            raise HTTPException(404, f"referência {identificador!r} não encontrada") from None

    @app.post("/api/referencias-visuais/{identificador}/imagem")
    async def enviar_imagem_da_referencia(
        identificador: str, request: Request
    ) -> ReferenciaVisual:
        """Normaliza a imagem e tenta analisá-la no Gemini; falha mantém revisão manual."""
        declarado = request.headers.get("content-length", "")
        if declarado.isdigit() and int(declarado) > LIMITE_DA_IMAGEM:
            raise HTTPException(413, "a imagem passa de 10 MB")
        try:
            referencia = referencias_visuais.obter(identificador)
        except ReferenciaVisualNaoEncontrada:
            raise HTTPException(404, f"referência {identificador!r} não encontrada") from None
        corpo = bytearray()
        async for pedaco in request.stream():
            corpo.extend(pedaco)
            if len(corpo) > LIMITE_DA_IMAGEM:
                raise HTTPException(413, "a imagem passa de 10 MB")
        caminho = pasta_execucoes / "referencias-visuais" / f"{referencia.identificador}.png"
        try:
            await run_in_threadpool(normalizar_imagem, bytes(corpo), caminho)
        except ImagemReferenciaInvalida as erro:
            raise HTTPException(422, str(erro)) from None
        referencia = referencias_visuais.registrar_imagem(identificador, caminho)
        analisador = provedor_visao
        if analisador is None:
            try:
                analisador = provedor_por_nome("gemini")
            except ErroProvedor:
                return referencias_visuais.registrar_erro(
                    identificador,
                    "Gemini indisponível; revise a análise estrutural manualmente.",
                )
        try:
            analise = await run_in_threadpool(
                analisar_referencia_visual, caminho, referencia, analisador
            )
        except ErroProvedor:
            return referencias_visuais.registrar_erro(
                identificador,
                "A análise automática falhou; revise a estrutura manualmente.",
            )
        return referencias_visuais.registrar_analise(
            identificador, analise, provedor=analisador.nome
        )

    @app.get("/api/referencias-visuais/{identificador}/imagem")
    def obter_imagem_da_referencia(identificador: str) -> FileResponse:
        try:
            caminho = referencias_visuais.caminho_da_imagem(identificador)
        except ReferenciaVisualNaoEncontrada:
            raise HTTPException(404, f"referência {identificador!r} não encontrada") from None
        except FileNotFoundError:
            raise HTTPException(404, "esta referência ainda não tem imagem") from None
        raiz = (pasta_execucoes / "referencias-visuais").resolve()
        alvo = caminho.resolve()
        if not alvo.is_relative_to(raiz) or not alvo.is_file():
            raise HTTPException(404, "imagem da referência não encontrada")
        return FileResponse(alvo, media_type="image/png")

    @app.get("/api/execucoes")
    def listar_execucoes_rota() -> list[ExecucaoResumo]:
        resumos: list[ExecucaoResumo] = []
        gravadas = set(listar_execucoes(pasta_execucoes))
        for identificador in sorted(gravadas):
            try:
                execucao = carregar_execucao(identificador, pasta_execucoes)
            except (OSError, ValidationError) as erro:
                # Uma execução ilegível não pode derrubar a listagem inteira — a tela inicial
                # some para todo mundo por causa de uma pasta só (achado do revisor de erros,
                # 2026-09-19). Ela some da lista; `/api/execucoes/{id}` ainda devolve 409 para
                # quem perguntar por ela direto.
                _REGISTRO.warning("execução %r ilegível, fora da listagem: %s", identificador, erro)
                continue
            resumos.append(_resumo_da_execucao(execucao))
        # Saída que ainda não gravou o execucao.json: em geração, na fila, interrompida ou que falhou.
        for andamento in gerenciador.listar():
            if andamento.identificador not in gravadas:
                resumos.append(_resumo_do_andamento(andamento))
        return resumos

    @app.post("/api/execucoes", status_code=http.HTTP_202_ACCEPTED)
    def criar_saida(corpo: NovaSaida) -> Andamento:
        """Enfileira a geração e responde na hora; a tela acompanha por ``.../andamento``."""
        if (corpo.composicao_visual is None) != (corpo.referencia_visual is None):
            raise HTTPException(
                422, "composição visual e referência visual devem ser informadas juntas"
            )
        if corpo.referencia_visual is not None:
            try:
                referencia = referencias_visuais.obter(corpo.referencia_visual)
            except ReferenciaVisualNaoEncontrada:
                raise HTTPException(422, "a referência visual escolhida não existe") from None
            if not referencia.aprovada:
                raise HTTPException(422, "a referência visual escolhida ainda não foi aprovada")
            if referencia.composicao is not corpo.composicao_visual:
                raise HTTPException(
                    422, "a referência visual não pertence à composição escolhida"
                )
        try:
            return gerenciador.pedir(
                ata=corpo.ata,
                itens=corpo.itens,
                modo=corpo.modo,
                pedido=corpo.pedido,
                nome=corpo.nome,
                comite=corpo.comite,
                duracao=corpo.duracao,
                composicao_visual=corpo.composicao_visual,
                referencia_visual=corpo.referencia_visual,
            )
        except AtaNaoEncontrada as erro:
            raise HTTPException(404, str(erro)) from None
        except PedidoRecusado as erro:
            raise HTTPException(422, str(erro)) from None

    @app.get("/api/execucoes/{identificador}/andamento")
    def obter_andamento(identificador: str) -> Andamento:
        andamento = gerenciador.andamento(identificador)
        if andamento is None:
            raise HTTPException(404, f"{identificador!r} não tem andamento de geração")
        return andamento

    @app.get("/api/execucoes/{identificador}")
    def obter_execucao(identificador: str) -> Execucao:
        return _execucao_ou_404(identificador)

    @app.get("/api/execucoes/{identificador}/resumo")
    def obter_resumo(identificador: str) -> ExecucaoResumo:
        return _resumo_ou_404(identificador)

    @app.patch("/api/execucoes/{identificador}")
    def renomear_execucao(identificador: str, corpo: Renomeacao) -> ExecucaoResumo:
        nome = corpo.nome.strip()
        if not nome:
            raise HTTPException(422, "o nome não pode ficar vazio")
        if len(nome) > NOME_MAXIMO:
            raise HTTPException(422, f"o nome passa de {NOME_MAXIMO} caracteres")
        with trava_de_escrita:
            execucao = _execucao_ou_404(identificador)
            execucao.nome = nome
            gravar_execucao(execucao, pasta_execucoes)
            return _resumo_da_execucao(execucao)

    @app.delete("/api/execucoes/{identificador}", status_code=http.HTTP_204_NO_CONTENT)
    def excluir_execucao(identificador: str) -> None:
        with trava_de_escrita:
            try:
                existia = gerenciador.excluir(identificador)
            except PedidoRecusado as erro:
                raise HTTPException(409, str(erro)) from None
        if not existia:
            raise HTTPException(404, f"execução {identificador!r} não encontrada")

    @app.post("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/decisao")
    def registrar_decisao(
        identificador: str, audiencia: Audiencia, formato: Formato, corpo: PedidoDeDecisao
    ) -> DecisaoHumana:
        with trava_de_escrita:
            execucao = _execucao_ou_404(identificador)
            try:
                decisao = decidir(
                    execucao,
                    audiencia,
                    formato,
                    corpo.estado,
                    motivo=corpo.motivo,
                    revisor=corpo.revisor,
                )
            except CelulaNaoEncontrada as erro:
                raise HTTPException(404, str(erro)) from None
            except DecisaoBloqueada as erro:
                raise HTTPException(409, str(erro)) from None
            except DecisaoInvalida as erro:
                raise HTTPException(422, str(erro)) from None
            gravar_execucao(execucao, pasta_execucoes)
            return decisao

    @app.get("/api/execucoes/{identificador}/exportar")
    def exportar_execucao(identificador: str, formato: FormatoExportacao) -> Response:
        execucao = _execucao_ou_404(identificador)
        conteudo, media_type, nome_do_arquivo = exportar(
            execucao, pasta_execucoes / identificador, formato
        )
        return Response(
            content=conteudo,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{nome_do_arquivo}"'},
        )

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

    @app.get("/api/execucoes/{identificador}/celulas/{audiencia}/roteiro/plano")
    def obter_plano_de_edicao(identificador: str, audiencia: Audiencia) -> PlanoDeEdicao:
        """O plano de edição do Roteiro aprovado: cenas, ícones, transições, efeitos e sons, em
        JSON para colar num gerador de avatar e em Markdown para conferir. Roteiro que não foi
        aprovado não tem plano (ADR 0004)."""
        historico = _execucao_ou_404(identificador).historico(audiencia, Formato.ROTEIRO)
        if historico is None:
            raise HTTPException(404, "Roteiro não encontrado nesta execução")
        celula = historico.celula_final
        if historico.destino_final is not Destino.APROVADO or celula is None:
            raise HTTPException(409, "só Roteiro aprovado tem plano de edição")
        plano = montar_plano(celula.conteudo, audiencia)
        return PlanoDeEdicao(plano=plano, markdown=plano_em_markdown(plano))

    @app.post("/api/execucoes/{identificador}/pacotes/montar", status_code=http.HTTP_202_ACCEPTED)
    def montar_pacotes(
        identificador: str,
        audiencia: Audiencia | None = None,
        formato: Formato | None = None,
    ) -> EstadoDaMontagem:
        """Monta os Pacotes das Células aprovadas, em segundo plano.

        Cada Célula é considerada individualmente; uma pendência em outra posição da Matriz não
        bloqueia seu Pacote. Recusa apenas quando nenhuma Célula foi aprovada.
        """
        if (audiencia is None) != (formato is None):
            raise HTTPException(422, "audiencia e formato devem ser informados juntos")
        execucao = _execucao_ou_404(identificador)
        if audiencia is not None and formato is not None:
            if execucao.historico(audiencia, formato) is None:
                raise HTTPException(404, "Célula não encontrada nesta execução")
        motivo = motivo_de_recusa(execucao, audiencia, formato)
        if motivo is not None:
            raise HTTPException(409, motivo)
        return montador.iniciar(identificador, audiencia, formato)

    @app.get("/api/execucoes/{identificador}/pacotes/montagem")
    def obter_montagem(identificador: str) -> EstadoDaMontagem:
        _execucao_ou_404(identificador)
        return montador.estado(identificador)

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

    @app.get("/api/execucoes/{identificador}/pacotes/{audiencia}/{formato}/baixar")
    def baixar_pacote(identificador: str, audiencia: Audiencia, formato: Formato) -> Response:
        """O Pacote pronto para publicar, num .zip: slides, legenda (com hashtags) e vídeo."""
        _execucao_ou_404(identificador)
        pasta = _pasta_do_pacote(pasta_execucoes, identificador, audiencia, formato)
        arquivos = sorted(
            caminho
            for caminho in pasta.glob("*")
            if caminho.is_file()
            and (
                caminho.name == "legenda.txt"
                or (caminho.name.startswith("slide-") and caminho.suffix == ".png")
                or caminho.suffix == ".mp4"
            )
        )
        if not arquivos:
            raise HTTPException(404, "Pacote não encontrado")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zip_:
            for caminho in arquivos:
                zip_.write(caminho, caminho.name)
        nome = f"suno-{audiencia.value}-{formato.value}.zip"
        return Response(
            buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{nome}"'},
        )

    @app.post("/api/execucoes/{identificador}/pacotes/{audiencia}/{formato}/aprovar")
    def aprovar_pacote(
        identificador: str,
        audiencia: Audiencia,
        formato: Formato,
        corpo: AprovacaoDoPacote | None = None,
    ) -> PacotePublicacao:
        with trava_de_escrita:
            _execucao_ou_404(identificador)
            arquivo = _pasta_do_pacote(pasta_execucoes, identificador, audiencia, formato) / NOME_DO_REGISTRO_DO_PACOTE
            if not arquivo.exists():
                raise HTTPException(404, "Pacote não encontrado")
            pacote = PacotePublicacao.model_validate_json(arquivo.read_text(encoding="utf-8"))
            feedback = FeedbackVisualHumano(
                revisor=((corpo.revisor or "").strip() or None) if corpo else None,
                observacao=((corpo.observacao or "").strip() or None) if corpo else None,
            )
            pacote = pacote.model_copy(
                update={
                    "aprovado_por_humano": True,
                    "feedback_visual_humano": feedback,
                }
            )
            arquivo.write_text(pacote.model_dump_json(indent=2), encoding="utf-8")
            feedback_visual.registrar(pacote, feedback)
            return pacote

    @app.get("/api/saude")
    def saude() -> Saude:
        return Saude(
            ok=True,
            execucoes=len(listar_execucoes(pasta_execucoes)),
            real_disponivel=_real_disponivel(),
        )

    if (PASTA_DA_SPA / "index.html").exists():
        app.mount("/", _SpaEstatica(directory=PASTA_DA_SPA, html=True), name="spa")

    return app
