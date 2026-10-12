"""Persistência SQLite do histórico de composições do Carrossel.

O banco fica junto das execuções. Cada montagem substitui os usos da própria
execução numa transação; consultas de histórico excluem a execução atual para
que remontar o mesmo Pacote continue produzindo o mesmo plano.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from suno.dominio import ComposicaoCarrossel, DirecaoDeArteCarrossel

NOME_DO_BANCO = "suno.sqlite3"


@dataclass(frozen=True)
class UsoDeLayout:
    audiencia: str
    indice: int
    composicao: ComposicaoCarrossel
    pontuacao: int
    motivos: tuple[str, ...]


def usos_do_plano(audiencia: str, plano: DirecaoDeArteCarrossel) -> list[UsoDeLayout]:
    return [
        UsoDeLayout(
            audiencia=audiencia,
            indice=escolha.indice,
            composicao=escolha.composicao,
            pontuacao=escolha.pontuacao,
            motivos=escolha.motivos,
        )
        for escolha in plano.escolhas
    ]


class RepositorioHistoricoLayouts:
    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = sqlite3.connect(self.caminho, timeout=10)
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA foreign_keys=ON")
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS usos_de_layout (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execucao TEXT NOT NULL,
                audiencia TEXT NOT NULL,
                indice INTEGER NOT NULL CHECK (indice >= 0),
                composicao TEXT NOT NULL,
                pontuacao INTEGER NOT NULL,
                motivos_json TEXT NOT NULL,
                registrado_em TEXT NOT NULL,
                UNIQUE (execucao, audiencia, indice)
            )
            """
        )
        conexao.execute(
            "CREATE INDEX IF NOT EXISTS idx_usos_layout_recentes "
            "ON usos_de_layout (registrado_em DESC, id DESC)"
        )
        return conexao

    def recentes(
        self, *, excluir_execucao: str, limite: int = 12
    ) -> tuple[ComposicaoCarrossel, ...]:
        if limite <= 0:
            return ()
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT composicao
                FROM usos_de_layout
                WHERE execucao <> ?
                ORDER BY registrado_em DESC, id DESC
                LIMIT ?
                """,
                (excluir_execucao, limite),
            ).fetchall()
        # A consulta vem do mais novo para o mais antigo; o seletor espera o mais novo por último.
        return tuple(ComposicaoCarrossel(linha[0]) for linha in reversed(linhas))

    def substituir_execucao(self, execucao: str, usos: Iterable[UsoDeLayout]) -> None:
        itens = list(usos)
        instante = datetime.now(timezone.utc).isoformat()
        with self._conectar() as conexao:
            conexao.execute("DELETE FROM usos_de_layout WHERE execucao = ?", (execucao,))
            conexao.executemany(
                """
                INSERT INTO usos_de_layout
                    (execucao, audiencia, indice, composicao, pontuacao, motivos_json, registrado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        execucao,
                        uso.audiencia,
                        uso.indice,
                        uso.composicao.value,
                        uso.pontuacao,
                        json.dumps(uso.motivos, ensure_ascii=False),
                        instante,
                    )
                    for uso in itens
                ],
            )

    def substituir_audiencia(
        self, execucao: str, audiencia: str, usos: Iterable[UsoDeLayout]
    ) -> None:
        """Atualiza somente o Carrossel montado, preservando as outras Células da Saída."""
        itens = list(usos)
        instante = datetime.now(timezone.utc).isoformat()
        with self._conectar() as conexao:
            conexao.execute(
                "DELETE FROM usos_de_layout WHERE execucao = ? AND audiencia = ?",
                (execucao, audiencia),
            )
            conexao.executemany(
                """
                INSERT INTO usos_de_layout
                    (execucao, audiencia, indice, composicao, pontuacao, motivos_json, registrado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        execucao,
                        uso.audiencia,
                        uso.indice,
                        uso.composicao.value,
                        uso.pontuacao,
                        json.dumps(uso.motivos, ensure_ascii=False),
                        instante,
                    )
                    for uso in itens
                ],
            )

    def remover_execucao(self, execucao: str) -> None:
        with self._conectar() as conexao:
            conexao.execute("DELETE FROM usos_de_layout WHERE execucao = ?", (execucao,))

    def distribuicao(self, *, execucao: str | None = None) -> dict[str, int]:
        consulta = "SELECT composicao, COUNT(*) FROM usos_de_layout"
        parametros: tuple[str, ...] = ()
        if execucao is not None:
            consulta += " WHERE execucao = ?"
            parametros = (execucao,)
        consulta += " GROUP BY composicao ORDER BY composicao"
        with self._conectar() as conexao:
            linhas = conexao.execute(consulta, parametros).fetchall()
        return {str(composicao): int(total) for composicao, total in linhas}


__all__ = [
    "NOME_DO_BANCO",
    "RepositorioHistoricoLayouts",
    "UsoDeLayout",
    "usos_do_plano",
]
