"""A aprovação H5 vira sinal positivo sem substituir compatibilidade ou revisão humana."""

from pathlib import Path

from suno.dominio import (
    Audiencia,
    ComposicaoCarrossel,
    DirecaoDeArteCarrossel,
    EscolhaDeLayout,
    FeedbackVisualHumano,
    Formato,
    PacotePublicacao,
)
from suno.pacote.feedback_visual import RepositorioFeedbackVisual


def _pacote(execucao: str = "exec-1") -> PacotePublicacao:
    return PacotePublicacao(
        execucao=execucao,
        audiencia=Audiencia.INICIANTE,
        formato=Formato.CARROSSEL,
        legenda="Legenda",
        direcao_de_arte=DirecaoDeArteCarrossel(
            escolhas=[
                EscolhaDeLayout(
                    indice=0,
                    composicao=ComposicaoCarrossel.EDITORIAL,
                    pontuacao=100,
                    referencia_visual="suno-editorial-cenario-de-juros",
                )
            ]
        ),
    )


def test_feedback_humano_e_idempotente_e_vira_resumo_para_o_diretor(
    tmp_path: Path,
) -> None:
    repositorio = RepositorioFeedbackVisual(tmp_path / "suno.sqlite3")
    pacote = _pacote()
    feedback = FeedbackVisualHumano(revisor="Ana", observacao="Pronto para uso")

    repositorio.registrar(pacote, feedback)
    repositorio.registrar(pacote, feedback)

    assert repositorio.resumo_para_diretor() == {
        "composicoes_aprovadas": [{"composicao": "editorial", "aprovacoes": 1}],
        "referencias_aprovadas": [
            {
                "referencia": "suno-editorial-cenario-de-juros",
                "aprovacoes": 1,
            }
        ],
    }
    assert repositorio.resumo_para_diretor(excluir_execucao="exec-1") == {
        "composicoes_aprovadas": [],
        "referencias_aprovadas": [],
    }
