"""Memória SQLite do Eval visual e da decisão humana H5.

A tabela é expansiva e independente das tabelas anteriores. Código antigo a ignora; rollback
é voltar ao leitor anterior, sem apagar os sinais já registrados.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

from suno.dominio import FeedbackVisualHumano, PacotePublicacao


class RepositorioFeedbackVisual:
    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)

    def _conectar(self) -> sqlite3.Connection:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = sqlite3.connect(self.caminho, timeout=10)
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA busy_timeout=10000")
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_visual_pacotes (
                execucao TEXT NOT NULL,
                audiencia TEXT NOT NULL,
                formato TEXT NOT NULL,
                aprovado INTEGER NOT NULL CHECK (aprovado IN (0, 1)),
                revisor TEXT,
                observacao TEXT,
                decidido_em TEXT NOT NULL,
                provedor_eval TEXT,
                parece_quebrado INTEGER,
                legibilidade TEXT,
                coerencia_visual TEXT,
                aderencia_marca TEXT,
                composicoes_json TEXT NOT NULL,
                referencias_json TEXT NOT NULL,
                PRIMARY KEY (execucao, audiencia, formato)
            )
            """
        )
        return conexao

    def registrar(
        self, pacote: PacotePublicacao, feedback: FeedbackVisualHumano
    ) -> None:
        escolhas = pacote.direcao_de_arte.escolhas if pacote.direcao_de_arte else []
        parecer = pacote.conferencia.juiz_visao
        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO feedback_visual_pacotes
                    (execucao, audiencia, formato, aprovado, revisor, observacao,
                     decidido_em, provedor_eval, parece_quebrado, legibilidade,
                     coerencia_visual, aderencia_marca, composicoes_json, referencias_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(execucao, audiencia, formato) DO UPDATE SET
                    aprovado = excluded.aprovado,
                    revisor = excluded.revisor,
                    observacao = excluded.observacao,
                    decidido_em = excluded.decidido_em,
                    provedor_eval = excluded.provedor_eval,
                    parece_quebrado = excluded.parece_quebrado,
                    legibilidade = excluded.legibilidade,
                    coerencia_visual = excluded.coerencia_visual,
                    aderencia_marca = excluded.aderencia_marca,
                    composicoes_json = excluded.composicoes_json,
                    referencias_json = excluded.referencias_json
                """,
                (
                    pacote.execucao,
                    pacote.audiencia.value,
                    pacote.formato.value,
                    int(feedback.aprovado),
                    feedback.revisor,
                    feedback.observacao,
                    feedback.em.isoformat(),
                    parecer.provedor if parecer else None,
                    int(parecer.parece_quebrado) if parecer else None,
                    parecer.legibilidade if parecer else None,
                    parecer.coerencia_visual if parecer else None,
                    parecer.aderencia_marca if parecer else None,
                    json.dumps([item.composicao.value for item in escolhas]),
                    json.dumps(
                        [
                            item.referencia_visual
                            for item in escolhas
                            if item.referencia_visual is not None
                        ]
                    ),
                ),
            )

    def resumo_para_diretor(
        self, *, excluir_execucao: str | None = None
    ) -> dict[str, list[dict[str, int | str]]]:
        """Sinais positivos agregados; não expõe comentário humano ao provedor."""
        composicoes: Counter[str] = Counter()
        referencias: Counter[str] = Counter()
        with self._conectar() as conexao:
            consulta = (
                "SELECT composicoes_json, referencias_json "
                "FROM feedback_visual_pacotes WHERE aprovado = 1"
            )
            parametros: tuple[str, ...] = ()
            if excluir_execucao is not None:
                consulta += " AND execucao <> ?"
                parametros = (excluir_execucao,)
            linhas = conexao.execute(consulta, parametros).fetchall()
        for composicoes_json, referencias_json in linhas:
            composicoes.update(json.loads(composicoes_json))
            referencias.update(json.loads(referencias_json))
        return {
            "composicoes_aprovadas": [
                {"composicao": nome, "aprovacoes": total}
                for nome, total in composicoes.most_common()
            ],
            "referencias_aprovadas": [
                {"referencia": nome, "aprovacoes": total}
                for nome, total in referencias.most_common()
            ],
        }


__all__ = ["RepositorioFeedbackVisual"]
