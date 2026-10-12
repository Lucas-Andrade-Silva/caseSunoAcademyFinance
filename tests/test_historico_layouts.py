"""O histórico de layouts usa SQLite local e mantém remontagens idempotentes."""

from __future__ import annotations

from pathlib import Path

from suno.dominio import ComposicaoCarrossel
from suno.pacote.historico_layouts import RepositorioHistoricoLayouts, UsoDeLayout


def _uso(indice: int, composicao: ComposicaoCarrossel) -> UsoDeLayout:
    return UsoDeLayout(
        audiencia="iniciante",
        indice=indice,
        composicao=composicao,
        pontuacao=7,
        motivos=("compatível com o conteúdo",),
    )


def test_sqlite_substitui_a_execucao_sem_duplicar_e_mede_distribuicao(tmp_path: Path) -> None:
    repositorio = RepositorioHistoricoLayouts(tmp_path / "suno.sqlite3")
    repositorio.substituir_execucao(
        "exec-1",
        [
            _uso(0, ComposicaoCarrossel.EDITORIAL),
            _uso(1, ComposicaoCarrossel.MINIMALISTA),
        ],
    )

    assert repositorio.distribuicao(execucao="exec-1") == {
        "editorial": 1,
        "minimalista": 1,
    }

    repositorio.substituir_execucao(
        "exec-1", [_uso(0, ComposicaoCarrossel.NARRATIVO)]
    )

    assert repositorio.distribuicao(execucao="exec-1") == {"narrativo": 1}
    assert repositorio.recentes(excluir_execucao="exec-1") == ()


def test_consulta_recente_exclui_a_execucao_atual(tmp_path: Path) -> None:
    repositorio = RepositorioHistoricoLayouts(tmp_path / "suno.sqlite3")
    repositorio.substituir_execucao(
        "anterior",
        [
            _uso(0, ComposicaoCarrossel.EDITORIAL),
            _uso(1, ComposicaoCarrossel.ESTATISTICO),
        ],
    )
    repositorio.substituir_execucao(
        "atual", [_uso(0, ComposicaoCarrossel.COMPARATIVO)]
    )

    assert repositorio.recentes(excluir_execucao="atual") == (
        ComposicaoCarrossel.EDITORIAL,
        ComposicaoCarrossel.ESTATISTICO,
    )


def test_substituir_audiencia_preserva_as_demais_celulas(tmp_path: Path) -> None:
    repositorio = RepositorioHistoricoLayouts(tmp_path / "suno.sqlite3")
    iniciante = _uso(0, ComposicaoCarrossel.EDITORIAL)
    avancado = UsoDeLayout(
        audiencia="avancado",
        indice=0,
        composicao=ComposicaoCarrossel.ESTATISTICO,
        pontuacao=8,
        motivos=("dado central",),
    )
    repositorio.substituir_execucao("exec-1", [iniciante, avancado])

    repositorio.substituir_audiencia(
        "exec-1", "iniciante", [_uso(0, ComposicaoCarrossel.NARRATIVO)]
    )

    assert repositorio.distribuicao(execucao="exec-1") == {
        "estatistico": 1,
        "narrativo": 1,
    }
