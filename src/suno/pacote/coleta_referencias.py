"""Descoberta opcional de carrosseis publicos para a fila de curadoria.

O adaptador nunca baixa midia, nao autentica e nao participa da geracao. O
Instaloader e opcional porque consultas publicas do Instagram sao inerentemente
faliveis; importar uma referencia manualmente continua sendo o caminho garantido.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


JANELAS_PERMITIDAS = (30, 60, 90)
LIMITE_POR_PERFIL = 20


class SetorDaReferencia(StrEnum):
    INVESTIMENTOS = "investimentos"
    FINANCAS_PESSOAIS = "financas_pessoais"
    ECONOMIA = "economia"
    MERCADO_FINANCEIRO = "mercado_financeiro"
    CRIPTOATIVOS = "criptoativos"
    OUTROS = "outros"


_TERMOS_POR_SETOR: dict[SetorDaReferencia, tuple[str, ...]] = {
    SetorDaReferencia.CRIPTOATIVOS: ("cripto", "bitcoin", "ethereum", "blockchain"),
    SetorDaReferencia.FINANCAS_PESSOAIS: (
        "financas pessoais", "orcamento", "divida", "reserva de emergencia",
    ),
    SetorDaReferencia.INVESTIMENTOS: (
        "investimento", "renda fixa", "acoes", "carteira", "tesouro", "cdb", "fundo",
    ),
    SetorDaReferencia.ECONOMIA: (
        "economia", "inflacao", "selic", "pib", "copom", "juros",
    ),
    SetorDaReferencia.MERCADO_FINANCEIRO: (
        "mercado financeiro", "bolsa", "ibovespa", "cambio", "dolar",
    ),
}


def classificar_setor(texto: str) -> SetorDaReferencia:
    normalizado = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto.casefold())
        if not unicodedata.combining(caractere)
    )
    for setor, termos in _TERMOS_POR_SETOR.items():
        if any(termo in normalizado for termo in termos):
            return setor
    return SetorDaReferencia.OUTROS


class PerfilDeReferencia(BaseModel):
    usuario: str
    ativo: bool = True
    ultima_coleta_em: datetime | None = None
    ultimo_estado: str = "nao_executada"
    ultima_mensagem: str | None = None


class CandidatoDeReferencia(BaseModel):
    identificador: str
    usuario: str
    titulo: str
    legenda: str
    url: str
    publicado_em: datetime
    curtidas: int | None = Field(default=None, ge=0)
    comentarios: int | None = Field(default=None, ge=0)
    seguidores: int | None = Field(default=None, ge=0)
    taxa_engajamento: float | None = Field(default=None, ge=0)
    setor: SetorDaReferencia = SetorDaReferencia.OUTROS
    capa_url: str | None = None
    importado: bool = False


class PerfilEmAlta(BaseModel):
    usuario: str
    publicacoes: int = Field(ge=1)
    movimentacao: int = Field(ge=0)
    taxa_engajamento_media: float | None = Field(default=None, ge=0)
    ultimo_post_em: datetime


class DescobertaDeReferencias(BaseModel):
    janela_dias: int
    setor: SetorDaReferencia | None = None
    perfis: list[PerfilEmAlta] = Field(default_factory=list)
    candidatos: list[CandidatoDeReferencia] = Field(default_factory=list)


class ResultadoDaColeta(BaseModel):
    janela_dias: int
    candidatos_novos: int = 0
    perfis_consultados: int = 0
    falhas: list[str] = Field(default_factory=list)


class ColetaIndisponivel(RuntimeError):
    pass


class ColetorDeReferencias(Protocol):
    def coletar(self, usuario: str, desde: datetime) -> list[CandidatoDeReferencia]: ...


def _usuario_normalizado(valor: str) -> str:
    usuario = valor.strip().removeprefix("@").casefold()
    if not re.fullmatch(r"[a-z0-9._]{1,30}", usuario):
        raise ValueError("informe um usuario publico valido do Instagram")
    return usuario


class ColetorInstaloader:
    """Adaptador publico, sem login e sem chamadas de download."""

    def coletar(self, usuario: str, desde: datetime) -> list[CandidatoDeReferencia]:
        try:
            import instaloader
        except ImportError as erro:
            raise ColetaIndisponivel(
                "coleta opcional nao instalada; instale o extra 'coleta'"
            ) from erro

        try:
            carregador = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                quiet=True,
            )
            perfil = instaloader.Profile.from_username(carregador.context, usuario)
            if perfil.is_private:
                raise ColetaIndisponivel("o perfil e privado")
            seguidores = int(perfil.followers) if perfil.followers is not None else None
            candidatos: list[CandidatoDeReferencia] = []
            for post in perfil.get_posts():
                publicado = post.date_utc
                if publicado.tzinfo is None:
                    publicado = publicado.replace(tzinfo=timezone.utc)
                if publicado < desde:
                    break
                if post.typename != "GraphSidecar":
                    continue
                legenda = (post.caption or "").strip()
                primeira_linha = next(
                    (linha.strip() for linha in legenda.splitlines() if linha.strip()),
                    f"Carrossel de @{usuario}",
                )
                curtidas = getattr(post, "likes", None)
                comentarios = getattr(post, "comments", None)
                taxa = None
                if seguidores and curtidas is not None and comentarios is not None:
                    taxa = round((int(curtidas) + int(comentarios)) / seguidores * 100, 4)
                candidatos.append(
                    CandidatoDeReferencia(
                        identificador=f"instagram-{post.shortcode}",
                        usuario=usuario,
                        titulo=primeira_linha[:120],
                        legenda=legenda[:1000],
                        url=f"https://www.instagram.com/p/{post.shortcode}/",
                        publicado_em=publicado,
                        curtidas=int(curtidas) if curtidas is not None else None,
                        comentarios=int(comentarios) if comentarios is not None else None,
                        seguidores=seguidores,
                        taxa_engajamento=taxa,
                        setor=classificar_setor(f"{primeira_linha} {legenda}"),
                        capa_url=str(post.url) if getattr(post, "url", None) else None,
                    )
                )
                if len(candidatos) >= LIMITE_POR_PERFIL:
                    break
            return candidatos
        except ColetaIndisponivel:
            raise
        except Exception as erro:
            raise ColetaIndisponivel(
                "o Instagram recusou ou interrompeu a consulta publica"
            ) from erro


class RepositorioDaColeta:
    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = sqlite3.connect(self.caminho, timeout=10)
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA busy_timeout=10000")
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS perfis_referencias (
                usuario TEXT PRIMARY KEY,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                ultima_coleta_em TEXT,
                ultimo_estado TEXT NOT NULL DEFAULT 'nao_executada',
                ultima_mensagem TEXT
            );
            CREATE TABLE IF NOT EXISTS candidatos_referencias (
                identificador TEXT PRIMARY KEY,
                usuario TEXT NOT NULL,
                titulo TEXT NOT NULL,
                legenda TEXT NOT NULL,
                url TEXT NOT NULL,
                publicado_em TEXT NOT NULL,
                curtidas INTEGER,
                comentarios INTEGER,
                seguidores INTEGER,
                taxa_engajamento REAL,
                capa_url TEXT,
                importado INTEGER NOT NULL DEFAULT 0 CHECK (importado IN (0, 1)),
                coletado_em TEXT NOT NULL
            );
            """
        )
        colunas = {
            linha[1]
            for linha in conexao.execute("PRAGMA table_info(candidatos_referencias)").fetchall()
        }
        if "capa_url" not in colunas:
            conexao.execute("ALTER TABLE candidatos_referencias ADD COLUMN capa_url TEXT")
        return conexao

    def adicionar_perfil(self, usuario: str) -> PerfilDeReferencia:
        usuario = _usuario_normalizado(usuario)
        with self._conectar() as conexao:
            conexao.execute(
                "INSERT OR IGNORE INTO perfis_referencias (usuario) VALUES (?)",
                (usuario,),
            )
        return next(item for item in self.listar_perfis() if item.usuario == usuario)

    def listar_perfis(self) -> list[PerfilDeReferencia]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT usuario, ativo, ultima_coleta_em, ultimo_estado, ultima_mensagem "
                "FROM perfis_referencias ORDER BY usuario"
            ).fetchall()
        return [
            PerfilDeReferencia(
                usuario=linha[0],
                ativo=bool(linha[1]),
                ultima_coleta_em=linha[2],
                ultimo_estado=linha[3],
                ultima_mensagem=linha[4],
            )
            for linha in linhas
        ]

    def listar_candidatos(
        self,
        *,
        janela_dias: int | None = None,
        setor: SetorDaReferencia | None = None,
        agora: datetime | None = None,
    ) -> list[CandidatoDeReferencia]:
        if janela_dias is not None and janela_dias not in JANELAS_PERMITIDAS:
            raise ValueError("a janela deve ser de 30, 60 ou 90 dias")
        if setor is not None:
            setor = SetorDaReferencia(setor)
        with self._conectar() as conexao:
            linhas = conexao.execute(
                "SELECT identificador, usuario, titulo, legenda, url, publicado_em, "
                "curtidas, comentarios, seguidores, taxa_engajamento, importado, capa_url "
                "FROM candidatos_referencias ORDER BY publicado_em DESC, identificador"
            ).fetchall()
        candidatos = [
            CandidatoDeReferencia(
                identificador=linha[0], usuario=linha[1], titulo=linha[2],
                legenda=linha[3], url=linha[4], publicado_em=linha[5],
                curtidas=linha[6], comentarios=linha[7], seguidores=linha[8],
                taxa_engajamento=linha[9], importado=bool(linha[10]), capa_url=linha[11],
                setor=classificar_setor(f"{linha[2]} {linha[3]}"),
            )
            for linha in linhas
        ]
        if janela_dias is not None:
            limite = (agora or datetime.now(timezone.utc)) - timedelta(days=janela_dias)
            candidatos = [item for item in candidatos if item.publicado_em >= limite]
        if setor is not None:
            candidatos = [item for item in candidatos if item.setor is setor]
        return candidatos

    def descobrir(
        self,
        *,
        janela_dias: int,
        setor: SetorDaReferencia | None = None,
        agora: datetime | None = None,
    ) -> DescobertaDeReferencias:
        candidatos = self.listar_candidatos(
            janela_dias=janela_dias, setor=setor, agora=agora
        )
        por_perfil: dict[str, list[CandidatoDeReferencia]] = defaultdict(list)
        for candidato in candidatos:
            por_perfil[candidato.usuario].append(candidato)
        perfis: list[PerfilEmAlta] = []
        for usuario, itens in por_perfil.items():
            taxas = [item.taxa_engajamento for item in itens if item.taxa_engajamento is not None]
            perfis.append(
                PerfilEmAlta(
                    usuario=usuario,
                    publicacoes=len(itens),
                    movimentacao=sum((item.curtidas or 0) + (item.comentarios or 0) for item in itens),
                    taxa_engajamento_media=(
                        round(sum(taxas) / len(taxas), 4) if taxas else None
                    ),
                    ultimo_post_em=max(item.publicado_em for item in itens),
                )
            )
        perfis.sort(
            key=lambda item: (
                item.movimentacao,
                item.taxa_engajamento_media or 0,
                item.ultimo_post_em,
            ),
            reverse=True,
        )
        return DescobertaDeReferencias(
            janela_dias=janela_dias,
            setor=setor,
            perfis=perfis,
            candidatos=candidatos,
        )

    def marcar_importado(self, identificador: str) -> None:
        with self._conectar() as conexao:
            alteradas = conexao.execute(
                "UPDATE candidatos_referencias SET importado = 1 WHERE identificador = ?",
                (identificador,),
            ).rowcount
        if not alteradas:
            raise LookupError(identificador)

    def coletar(
        self,
        coletor: ColetorDeReferencias,
        *,
        janela_dias: int,
        agora: datetime | None = None,
    ) -> ResultadoDaColeta:
        if janela_dias not in JANELAS_PERMITIDAS:
            raise ValueError("a janela deve ser de 30, 60 ou 90 dias")
        agora = agora or datetime.now(timezone.utc)
        desde = agora - timedelta(days=janela_dias)
        resultado = ResultadoDaColeta(janela_dias=janela_dias)
        for perfil in (item for item in self.listar_perfis() if item.ativo):
            resultado.perfis_consultados += 1
            try:
                candidatos = coletor.coletar(perfil.usuario, desde)
            except ColetaIndisponivel as erro:
                mensagem = str(erro)[:300]
                resultado.falhas.append(f"@{perfil.usuario}: {mensagem}")
                self._registrar_estado(perfil.usuario, agora, "erro", mensagem)
                continue
            with self._conectar() as conexao:
                antes = conexao.total_changes
                for candidato in candidatos:
                    conexao.execute(
                        """
                        INSERT OR IGNORE INTO candidatos_referencias
                            (identificador, usuario, titulo, legenda, url, publicado_em,
                            curtidas, comentarios, seguidores, taxa_engajamento, capa_url,
                            coletado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            candidato.identificador, candidato.usuario, candidato.titulo,
                            candidato.legenda, candidato.url,
                            candidato.publicado_em.isoformat(), candidato.curtidas,
                            candidato.comentarios, candidato.seguidores,
                            candidato.taxa_engajamento, candidato.capa_url,
                            agora.isoformat(),
                        ),
                    )
                resultado.candidatos_novos += conexao.total_changes - antes
            self._registrar_estado(perfil.usuario, agora, "concluida", None)
        return resultado

    def _registrar_estado(
        self, usuario: str, quando: datetime, estado: str, mensagem: str | None
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute(
                "UPDATE perfis_referencias SET ultima_coleta_em = ?, ultimo_estado = ?, "
                "ultima_mensagem = ? WHERE usuario = ?",
                (quando.isoformat(), estado, mensagem, usuario),
            )


__all__ = [
    "CandidatoDeReferencia", "ColetaIndisponivel", "ColetorDeReferencias",
    "ColetorInstaloader", "JANELAS_PERMITIDAS", "PerfilDeReferencia",
    "RepositorioDaColeta", "ResultadoDaColeta", "SetorDaReferencia",
    "PerfilEmAlta", "DescobertaDeReferencias", "classificar_setor",
]
