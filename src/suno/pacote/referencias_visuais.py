"""Biblioteca local de referências estruturais para a direção de arte.

As seis sementes são exemplos originais da própria Suno e não reproduzem posts de
terceiros. Elas ficam no mesmo SQLite do histórico de layouts. ``INSERT OR IGNORE``
preserva futuras correções humanas feitas sobre os registros já existentes.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from suno.dominio import (
    AnaliseVisualReferencia,
    ComposicaoCarrossel,
    EstadoAnaliseVisual,
    ReferenciaVisual,
)
from suno.pacote import familias


_REFERENCIAS_LEGADAS: tuple[ReferenciaVisual, ...] = (
    ReferenciaVisual(
        identificador="suno-editorial-cenario-de-juros",
        titulo="Cenário de juros em perspectiva",
        tema="macroeconomia e investimentos",
        composicao=ComposicaoCarrossel.EDITORIAL,
        descricao="Abertura de relatório com manchete forte e uma leitura visual do mercado.",
        instrucao_de_design=(
            "Use título dominante no alto à esquerda, apoio curto e um elemento de mercado "
            "assimétrico; preserve área de respiro e contraste editorial."
        ),
        analise=AnaliseVisualReferencia(
            posicao_do_titulo="superior_esquerda",
            proeminencia_do_titulo="alta",
            densidade_textual="media",
            uso_de_imagem="ilustracao_financeira_lateral",
            tipo_de_fundo="escuro_solido",
            elementos_visuais=["linha_de_mercado", "formas_geometricas"],
            estrutura_do_conteudo=["manchete", "texto_de_apoio", "visual_de_mercado"],
        ),
    ),
    ReferenciaVisual(
        identificador="suno-minimalista-reserva-de-emergencia",
        titulo="Reserva primeiro, risco depois",
        tema="finanças pessoais",
        composicao=ComposicaoCarrossel.MINIMALISTA,
        descricao="Uma única ideia financeira com muita área vazia e leitura imediata.",
        instrucao_de_design=(
            "Reduza a cena ao título, uma frase e um único acento gráfico; use grande área "
            "vazia para comunicar segurança e foco."
        ),
        analise=AnaliseVisualReferencia(
            posicao_do_titulo="centro_esquerda",
            proeminencia_do_titulo="alta",
            densidade_textual="baixa",
            uso_de_imagem="sem_imagem",
            tipo_de_fundo="escuro_solido",
            elementos_visuais=["circulo_de_destaque"],
            estrutura_do_conteudo=["titulo", "frase_curta"],
        ),
    ),
    ReferenciaVisual(
        identificador="suno-infografico-caminho-da-selic",
        titulo="Da Selic ao rendimento",
        tema="renda fixa",
        composicao=ComposicaoCarrossel.INFOGRAFICO,
        descricao="Fluxo que conecta uma decisão de juros aos efeitos nos investimentos.",
        instrucao_de_design=(
            "Transforme a relação financeira em fluxo visual curto, com etapas conectadas e "
            "o indicador numérico sempre associado à sua explicação."
        ),
        analise=AnaliseVisualReferencia(
            posicao_do_titulo="superior_esquerda",
            proeminencia_do_titulo="media",
            densidade_textual="media",
            uso_de_imagem="diagrama",
            tipo_de_fundo="escuro_com_paineis",
            elementos_visuais=["fluxo", "conectores", "indicador"],
            estrutura_do_conteudo=["titulo", "etapas", "dado", "conclusao"],
        ),
    ),
    ReferenciaVisual(
        identificador="suno-comparativo-tesouro-selic-cdb",
        titulo="Tesouro Selic ou CDB?",
        tema="comparação de investimentos",
        composicao=ComposicaoCarrossel.COMPARATIVO,
        descricao="Dois investimentos lado a lado, com critérios equivalentes e sem ranking inventado.",
        instrucao_de_design=(
            "Divida a área em duas colunas equivalentes, repita os mesmos critérios em ambos "
            "os lados e use contraste apenas para orientar a comparação."
        ),
        analise=AnaliseVisualReferencia(
            posicao_do_titulo="superior_centro",
            proeminencia_do_titulo="media",
            densidade_textual="media",
            uso_de_imagem="paineis_lado_a_lado",
            tipo_de_fundo="duas_areas_contrastantes",
            elementos_visuais=["divisor", "dois_paineis", "criterios_espelhados"],
            estrutura_do_conteudo=["pergunta", "opcao_a", "opcao_b", "criterios"],
        ),
    ),
    ReferenciaVisual(
        identificador="suno-estatistico-taxa-selic",
        titulo="A taxa que move a renda fixa",
        tema="indicadores econômicos",
        composicao=ComposicaoCarrossel.ESTATISTICO,
        descricao="Um indicador central ocupa a maior hierarquia e recebe contexto mínimo.",
        instrucao_de_design=(
            "Dê ao número validado a maior hierarquia da página, mantenha unidade e rótulo "
            "juntos e limite o texto a uma explicação curta."
        ),
        analise=AnaliseVisualReferencia(
            posicao_do_titulo="superior_esquerda",
            proeminencia_do_titulo="media",
            densidade_textual="baixa",
            uso_de_imagem="numero_monumental",
            tipo_de_fundo="escuro_solido",
            elementos_visuais=["numero_principal", "rotulo", "linha_de_base"],
            estrutura_do_conteudo=["titulo", "numero", "unidade", "contexto"],
        ),
    ),
    ReferenciaVisual(
        identificador="suno-narrativo-diversificacao-em-etapas",
        titulo="Diversificação em três decisões",
        tema="construção de carteira",
        composicao=ComposicaoCarrossel.NARRATIVO,
        descricao="Sequência de decisões que conduz do objetivo à distribuição da carteira.",
        instrucao_de_design=(
            "Organize a explicação em uma sequência numerada, destaque a etapa atual e deixe "
            "clara a progressão entre objetivo, prazo e classes de ativos."
        ),
        analise=AnaliseVisualReferencia(
            posicao_do_titulo="superior_esquerda",
            proeminencia_do_titulo="media",
            densidade_textual="media",
            uso_de_imagem="sequencia_numerada",
            tipo_de_fundo="escuro_com_trilha",
            elementos_visuais=["numeracao", "trilha", "marcador_de_etapa"],
            estrutura_do_conteudo=["titulo", "etapa", "explicacao", "proxima_etapa"],
        ),
    ),
)


def _referencias_das_familias() -> tuple[ReferenciaVisual, ...]:
    """Uma referência por layout das famílias, vinda do ``familia.json`` (carrosséis reais da Suno)."""
    sementes = []
    for layout in familias.carregar_layouts().values():
        dados = layout.referencia
        if dados is None:
            raise ValueError(f"{layout.composicao.value}: o manifesto não traz a referência visual")
        sementes.append(
            ReferenciaVisual(
                identificador="suno-" + layout.composicao.value.replace("_", "-"),
                titulo=dados["titulo"],
                tema=dados["tema"],
                composicao=layout.composicao,
                descricao=dados["descricao"],
                instrucao_de_design=dados["instrucao_de_design"],
                analise=AnaliseVisualReferencia(**dados["analise"]),
                origem=dados.get("origem", "Suno — carrossel real"),
            )
        )
    return tuple(sementes)


REFERENCIAS_INICIAIS: tuple[ReferenciaVisual, ...] = (
    *_REFERENCIAS_LEGADAS,
    *_referencias_das_familias(),
)


class ReferenciaVisualDuplicada(ValueError):
    pass


class ReferenciaVisualNaoEncontrada(LookupError):
    pass


def _identificador_manual(titulo: str) -> str:
    normalizado = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalizado.casefold()).strip("-")
    return f"manual-{slug[:72] or 'referencia'}"


class RepositorioReferenciasVisuais:
    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = sqlite3.connect(self.caminho, timeout=10)
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA busy_timeout=10000")
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS referencias_visuais (
                identificador TEXT PRIMARY KEY,
                titulo TEXT NOT NULL,
                tema TEXT NOT NULL,
                composicao TEXT NOT NULL,
                descricao TEXT NOT NULL,
                instrucao_de_design TEXT NOT NULL,
                analise_json TEXT NOT NULL,
                aprovada INTEGER NOT NULL CHECK (aprovada IN (0, 1)),
                origem TEXT NOT NULL,
                criada_em TEXT NOT NULL
            )
            """
        )
        self._expandir_schema(conexao)
        return conexao

    @staticmethod
    def _expandir_schema(conexao: sqlite3.Connection) -> None:
        """Migração expansiva e idempotente; leitores antigos ignoram as novas colunas."""
        existentes = {
            str(linha[1])
            for linha in conexao.execute("PRAGMA table_info(referencias_visuais)").fetchall()
        }
        novas = {
            "imagem_arquivo": "TEXT",
            "estado_analise": "TEXT NOT NULL DEFAULT 'nao_solicitada'",
            "provedor_analise": "TEXT",
            "mensagem_analise": "TEXT",
            "analisada_em": "TEXT",
        }
        for nome, definicao in novas.items():
            if nome not in existentes:
                conexao.execute(
                    f"ALTER TABLE referencias_visuais ADD COLUMN {nome} {definicao}"
                )

    def garantir_sementes(self) -> None:
        with self._conectar() as conexao:
            conexao.executemany(
                """
                INSERT OR IGNORE INTO referencias_visuais
                    (identificador, titulo, tema, composicao, descricao,
                     instrucao_de_design, analise_json, aprovada, origem, criada_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        referencia.identificador,
                        referencia.titulo,
                        referencia.tema,
                        referencia.composicao.value,
                        referencia.descricao,
                        referencia.instrucao_de_design,
                        referencia.analise.model_dump_json(),
                        int(referencia.aprovada),
                        referencia.origem,
                        "2026-10-10T00:00:00+00:00",
                    )
                    for referencia in REFERENCIAS_INICIAIS
                ],
            )

    def listar(self, *, apenas_aprovadas: bool = False) -> list[ReferenciaVisual]:
        self.garantir_sementes()
        consulta = (
            "SELECT identificador, titulo, tema, composicao, descricao, "
            "instrucao_de_design, analise_json, aprovada, origem, imagem_arquivo, "
            "estado_analise, provedor_analise, mensagem_analise "
            "FROM referencias_visuais"
        )
        if apenas_aprovadas:
            consulta += " WHERE aprovada = 1"
        consulta += " ORDER BY composicao, identificador"
        with self._conectar() as conexao:
            linhas = conexao.execute(consulta).fetchall()
        return [
            ReferenciaVisual(
                identificador=linha[0],
                titulo=linha[1],
                tema=linha[2],
                composicao=ComposicaoCarrossel(linha[3]),
                descricao=linha[4],
                instrucao_de_design=linha[5],
                analise=AnaliseVisualReferencia.model_validate(json.loads(linha[6])),
                aprovada=bool(linha[7]),
                origem=linha[8],
                imagem_disponivel=bool(linha[9])
                or familias.miniatura_do_layout(ComposicaoCarrossel(linha[3])) is not None,
                estado_analise=EstadoAnaliseVisual(linha[10]),
                provedor_analise=linha[11],
                mensagem_analise=linha[12],
            )
            for linha in linhas
        ]

    def obter(self, identificador: str) -> ReferenciaVisual:
        try:
            return next(
                referencia
                for referencia in self.listar()
                if referencia.identificador == identificador
            )
        except StopIteration:
            raise ReferenciaVisualNaoEncontrada(identificador) from None

    def adicionar(
        self,
        *,
        titulo: str,
        tema: str,
        composicao: ComposicaoCarrossel,
        descricao: str,
        instrucao_de_design: str,
        origem: str,
    ) -> ReferenciaVisual:
        self.garantir_sementes()
        base = next(
            referencia
            for referencia in REFERENCIAS_INICIAIS
            if referencia.composicao is composicao
        )
        referencia = ReferenciaVisual(
            identificador=_identificador_manual(titulo),
            titulo=titulo.strip(),
            tema=tema.strip(),
            composicao=composicao,
            descricao=descricao.strip(),
            instrucao_de_design=instrucao_de_design.strip(),
            analise=base.analise.model_copy(deep=True),
            aprovada=False,
            origem=origem.strip() or "Importação manual",
        )
        try:
            with self._conectar() as conexao:
                conexao.execute(
                    """
                    INSERT INTO referencias_visuais
                        (identificador, titulo, tema, composicao, descricao,
                         instrucao_de_design, analise_json, aprovada, origem, criada_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        referencia.identificador,
                        referencia.titulo,
                        referencia.tema,
                        referencia.composicao.value,
                        referencia.descricao,
                        referencia.instrucao_de_design,
                        referencia.analise.model_dump_json(),
                        0,
                        referencia.origem,
                    ),
                )
        except sqlite3.IntegrityError:
            raise ReferenciaVisualDuplicada(
                f"já existe uma referência chamada {referencia.titulo!r}"
            ) from None
        return referencia

    def definir_aprovacao(self, identificador: str, aprovada: bool) -> ReferenciaVisual:
        self.garantir_sementes()
        with self._conectar() as conexao:
            alteradas = conexao.execute(
                "UPDATE referencias_visuais SET aprovada = ? WHERE identificador = ?",
                (int(aprovada), identificador),
            ).rowcount
        if not alteradas:
            raise ReferenciaVisualNaoEncontrada(identificador)
        return self.obter(identificador)

    def registrar_imagem(self, identificador: str, arquivo: Path) -> ReferenciaVisual:
        self.garantir_sementes()
        with self._conectar() as conexao:
            alteradas = conexao.execute(
                """
                UPDATE referencias_visuais
                SET imagem_arquivo = ?, estado_analise = ?, provedor_analise = NULL,
                    mensagem_analise = NULL, analisada_em = NULL, aprovada = 0
                WHERE identificador = ?
                """,
                (str(arquivo), EstadoAnaliseVisual.PENDENTE.value, identificador),
            ).rowcount
        if not alteradas:
            raise ReferenciaVisualNaoEncontrada(identificador)
        return self.obter(identificador)

    def caminho_da_imagem(self, identificador: str) -> Path:
        self.garantir_sementes()
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT imagem_arquivo FROM referencias_visuais WHERE identificador = ?",
                (identificador,),
            ).fetchone()
        if linha is None:
            raise ReferenciaVisualNaoEncontrada(identificador)
        if not linha[0]:
            # Referência de família visual: sem imagem enviada, vale a miniatura do layout.
            miniatura = familias.miniatura_do_layout(self.obter(identificador).composicao)
            if miniatura is None:
                raise FileNotFoundError(identificador)
            return miniatura
        return Path(str(linha[0]))

    def registrar_analise(
        self,
        identificador: str,
        analise: AnaliseVisualReferencia,
        *,
        provedor: str,
    ) -> ReferenciaVisual:
        with self._conectar() as conexao:
            alteradas = conexao.execute(
                """
                UPDATE referencias_visuais
                SET analise_json = ?, estado_analise = ?, provedor_analise = ?,
                    mensagem_analise = NULL, analisada_em = datetime('now')
                WHERE identificador = ?
                """,
                (
                    analise.model_dump_json(),
                    EstadoAnaliseVisual.CONCLUIDA.value,
                    provedor,
                    identificador,
                ),
            ).rowcount
        if not alteradas:
            raise ReferenciaVisualNaoEncontrada(identificador)
        return self.obter(identificador)

    def registrar_erro(self, identificador: str, mensagem: str) -> ReferenciaVisual:
        with self._conectar() as conexao:
            alteradas = conexao.execute(
                """
                UPDATE referencias_visuais
                SET estado_analise = ?, provedor_analise = NULL, mensagem_analise = ?,
                    analisada_em = datetime('now')
                WHERE identificador = ?
                """,
                (EstadoAnaliseVisual.ERRO.value, mensagem[:300], identificador),
            ).rowcount
        if not alteradas:
            raise ReferenciaVisualNaoEncontrada(identificador)
        return self.obter(identificador)


__all__ = [
    "REFERENCIAS_INICIAIS",
    "RepositorioReferenciasVisuais",
    "ReferenciaVisualDuplicada",
    "ReferenciaVisualNaoEncontrada",
]
