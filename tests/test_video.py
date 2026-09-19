"""O vídeo fora do grafo: composição determinística em CPU a partir de um Roteiro aprovado.

Só o quadro (``compor_quadro``) roda sem o extra ``video``: é Pillow puro, sem ffmpeg. Os
testes que codificam de verdade usam ``pytest.importorskip("imageio_ffmpeg")`` e pulam limpo
quando o extra não está instalado — a suíte principal nunca depende dele (ADR 0004).

O que estes testes protegem:

- 1080x1920 (9:16) em todo quadro, e a fala quebrando em poucas linhas legíveis;
- o mp4 saindo em ``<pasta>/<id>/pacote/<audiencia>-roteiro/video.mp4``, o caminho que
  ``suno.pacote`` já sabe procurar;
- ``medir_video`` acusando ``SEM_AUDIO`` sem narração (honesto, não silêncio fingido) e
  ``DURACAO_FORA_DA_FAIXA`` num vídeo de teste de 4s (abaixo dos 5s mínimos — o esperado);
- Roteiro que não foi aprovado nunca vira vídeo (ADR 0004);
- ``sintetizar`` nunca levanta: rede bloqueada devolve ``None``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from suno.dominio import (
    Ancoras,
    Audiencia,
    BlocoFala,
    Celula,
    Conteudo,
    Destino,
    Execucao,
    Formato,
    HistoricoCelula,
    Laudo,
    Medida,
    Metrica,
    MotivoReprovacao,
    Tentativa,
)
from suno.video.render import (
    DURACAO_MINIMA_S,
    LARGURA_UTIL,
    LARGURA_VIDEO,
    ALTURA_VIDEO,
    LINHAS_DA_LEGENDA,
    TAMANHO_LEGENDA,
    LETRA_COMUM,
    compor_quadro,
    medir_video,
    quebrar_linhas,
    tipografia,
)
from suno.dominio import DefeitoRender

IDENTIFICADOR = "copom-280-2026-08-05-video-0001"


# ---------------------------------------------------------------------------
# A Execução mínima, montada à mão (mesmo padrão de tests/test_pacote.py)
# ---------------------------------------------------------------------------


def _bloco_de_roteiro() -> list[BlocoFala]:
    return [
        BlocoFala(
            inicio_s=0,
            fim_s=2,
            fala="Os juros caíram e isso mexe com o seu bolso agora mesmo, hoje.",
            tela="O JURO CAIU",
        ),
        BlocoFala(
            inicio_s=2,
            fim_s=4,
            fala="O comitê reduziu a taxa básica da economia por decisão unânime.",
            tela="Gráfico da Selic",
        ),
    ]


def _celula_roteiro(audiencia: Audiencia) -> Celula:
    corpo = Conteudo(formato=Formato.ROTEIRO, blocos=_bloco_de_roteiro())
    return Celula(audiencia=audiencia, formato=Formato.ROTEIRO, conteudo=corpo)


def _laudo(celula: Celula, destino: Destino) -> Laudo:
    medidas = [Medida(metrica=Metrica.ADERENCIA, valor=1.0, atingiu=destino is Destino.APROVADO)]
    if destino is Destino.APROVADO:
        return Laudo(audiencia=celula.audiencia, formato=celula.formato, medidas=medidas, destino=destino)
    return Laudo(
        audiencia=celula.audiencia,
        formato=celula.formato,
        medidas=medidas,
        destino=destino,
        motivos=[MotivoReprovacao.FLESCH_BR],
    )


def _historico(celula: Celula, destino: Destino) -> HistoricoCelula:
    return HistoricoCelula(
        audiencia=celula.audiencia,
        formato=celula.formato,
        tentativas=[Tentativa(rodada=0, celula=celula, laudo=_laudo(celula, destino))],
        destino_final=destino,
        provedores_usados=["falso"],
    )


def _gravar_execucao(pasta_execucoes: Path, celulas: list[HistoricoCelula]) -> Path:
    execucao = Execucao(
        identificador=IDENTIFICADOR,
        ata="copom-280-2026-08-05",
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        ancoras=Ancoras(ata="copom-280-2026-08-05"),
        celulas=celulas,
    )
    pasta = pasta_execucoes / IDENTIFICADOR
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "execucao.json").write_text(execucao.model_dump_json(indent=2), encoding="utf-8")
    return pasta_execucoes


# ---------------------------------------------------------------------------
# 1 — compor_quadro é puro: sem ffmpeg, sem disco
# ---------------------------------------------------------------------------


def test_compor_quadro_sai_em_9_16_e_a_fala_quebra_em_poucas_linhas() -> None:
    bloco = _bloco_de_roteiro()[0]

    quadro = compor_quadro(bloco, Audiencia.INICIANTE, progresso=0.5)

    assert quadro.size == (LARGURA_VIDEO, ALTURA_VIDEO)
    assert (LARGURA_VIDEO, ALTURA_VIDEO) == (1080, 1920)

    # A mesma função de quebra que compor_quadro usa por dentro: a fala de um bloco cabe em
    # poucas linhas, bem abaixo do que a legenda reserva.
    letra = tipografia(LETRA_COMUM, TAMANHO_LEGENDA)
    linhas = quebrar_linhas(bloco.fala, letra, LARGURA_UTIL)
    assert len(linhas) <= LINHAS_DA_LEGENDA


def test_compor_quadro_sem_rubrica_de_cena_nao_quebra() -> None:
    """``tela`` é opcional (default ``""``); o quadro tem de sair mesmo assim."""
    bloco = BlocoFala(inicio_s=0, fim_s=2, fala="Só a fala, sem rubrica de cena nenhuma.")

    quadro = compor_quadro(bloco, Audiencia.AVANCADO, progresso=0.0)

    assert quadro.size == (LARGURA_VIDEO, ALTURA_VIDEO)


# ---------------------------------------------------------------------------
# 2 — renderizar_video + medir_video: precisam do extra `video`
# ---------------------------------------------------------------------------


def test_renderiza_um_roteiro_aprovado_e_mede_dimensao_duracao_e_audio(
    pasta_execucoes: Path,
) -> None:
    pytest.importorskip("imageio_ffmpeg")
    from suno.video.render import renderizar_video

    celula = _celula_roteiro(Audiencia.INICIANTE)
    _gravar_execucao(pasta_execucoes, [_historico(celula, Destino.APROVADO)])

    caminho = renderizar_video(IDENTIFICADOR, Audiencia.INICIANTE, pasta_execucoes)

    assert caminho == pasta_execucoes / IDENTIFICADOR / "pacote" / "iniciante-roteiro" / "video.mp4"
    assert caminho.exists()

    medicoes = medir_video(caminho)
    por_defeito = {m.defeito: m for m in medicoes}

    assert None in por_defeito, "a medição de dimensão precisa passar"
    dimensao_ok = next(m for m in medicoes if m.detalhe.startswith("1080x1920"))
    assert dimensao_ok.defeito is None

    duracao = next(m for m in medicoes if "duração" in m.detalhe)
    assert duracao.valor is not None
    assert 3.5 <= duracao.valor <= 4.5, "dois blocos de 2s a 12 fps rendem ~4s"
    assert duracao.valor < DURACAO_MINIMA_S
    assert DefeitoRender.DURACAO_FORA_DA_FAIXA in por_defeito

    audio = next(m for m in medicoes if "áudio" in m.detalhe)
    assert audio.defeito is DefeitoRender.SEM_AUDIO, "sem narração, o mp4 não tem trilha — honesto, não fingido"


# ---------------------------------------------------------------------------
# 3 — Roteiro reprovado nunca vira vídeo
# ---------------------------------------------------------------------------


def test_roteiro_reprovado_recusa_virar_video(pasta_execucoes: Path) -> None:
    pytest.importorskip("imageio_ffmpeg")
    from suno.video.render import renderizar_video

    celula = _celula_roteiro(Audiencia.AVANCADO)
    _gravar_execucao(pasta_execucoes, [_historico(celula, Destino.REPROVADO_REVISAO_HUMANA)])

    with pytest.raises(ValueError, match="Roteiro aprovado"):
        renderizar_video(IDENTIFICADOR, Audiencia.AVANCADO, pasta_execucoes)


def test_audiencia_sem_celula_nenhuma_tambem_recusa(pasta_execucoes: Path) -> None:
    pytest.importorskip("imageio_ffmpeg")
    from suno.video.render import renderizar_video

    celula = _celula_roteiro(Audiencia.INICIANTE)
    _gravar_execucao(pasta_execucoes, [_historico(celula, Destino.APROVADO)])

    with pytest.raises(ValueError, match="Roteiro aprovado"):
        renderizar_video(IDENTIFICADOR, Audiencia.AVANCADO, pasta_execucoes)


# ---------------------------------------------------------------------------
# 4 — narração: rede bloqueada devolve None, nunca levanta
# ---------------------------------------------------------------------------


def test_sintetizar_com_rede_bloqueada_devolve_none_sem_levantar(tmp_path: Path) -> None:
    pytest.importorskip("edge_tts")
    from suno.video.narracao import sintetizar

    resultado = sintetizar("Isto não pode ir para a rede no teste.", tmp_path / "narracao.mp3")

    assert resultado is None
