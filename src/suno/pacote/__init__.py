"""O Pacote de publicação: só de Célula aprovada. Imagens geradas, nunca raspadas.
Conferência visual própria que não reprova a Célula.

ADR 0009, 0014.

``montar_pacote`` é o comando ``python -m suno.cli pacote --execucao <id>``: lê o
``execucao.json`` que o Gerador já gravou, percorre as Células aprovadas e grava, para cada uma,
uma pasta pronta para um humano publicar.

Três coisas que este módulo deliberadamente **não** faz:

- **Não publica.** Instagram, TikTok e Drive são destinos manuais; o sistema entrega a pasta.
- **Não renderiza vídeo.** O vídeo é comando separado e fora do grafo (ADR 0004); se o mp4 já
  existir em disco, o Pacote aponta para ele, senão ``video`` fica nulo.
- **Não reprova nada.** A conferência visual entra no Pacote como lista para o H5 e o
  ``execucao.json`` sai da montagem byte a byte igual ao que entrou (ADR 0014).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from suno.dominio import (
    Audiencia,
    Celula,
    ConferenciaVisual,
    Destino,
    Execucao,
    Formato,
    ImagemSlide,
    PacotePublicacao,
)
from suno.pacote.carrossel import folha_de_contato, renderizar_carrossel
from suno.pacote.legenda import montar_legenda
from suno.pacote.visual import conferir_imagens

NOME_DA_PASTA = "pacote"
NOME_DA_FOLHA = "folha-de-contato.png"
NOME_DO_TEXTO = "texto.md"
NOME_DA_LEGENDA = "legenda.txt"
NOME_DO_REGISTRO = "pacote.json"
_REGISTRO = logging.getLogger(__name__)
NOME_DO_VIDEO = "video.mp4"


def _ler_execucao(identificador: str, pasta_execucoes: Path) -> Execucao:
    """O ``execucao.json`` da execução, sempre em modo leitura.

    O import é local porque ``suno.gerador`` puxa o caminho de geração inteiro, e montar o
    Pacote não precisa dele: é leitura de disco mais Pillow.
    """
    from suno.gerador.execucao import carregar_execucao

    return carregar_execucao(identificador, pasta_execucoes)


def _video_ja_renderizado(pasta_do_pacote: Path, pasta_da_execucao: Path, audiencia: Audiencia) -> Path | None:
    """O mp4 só entra no Pacote se alguém já rodou ``suno.cli video`` (ADR 0004)."""
    candidatos = (
        pasta_do_pacote / NOME_DO_VIDEO,
        pasta_da_execucao / f"video-{audiencia.value}.mp4",
        pasta_da_execucao / NOME_DO_VIDEO,
    )
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    return None


def _medir_video_se_disponivel(video: Path) -> list:
    """Duração, proporção e áudio do mp4 já renderizado (ADR 0014) — sempre ligada, mas só entra
    no Pacote quando alguém rodou ``suno.cli video`` antes: este módulo não renderiza.

    ``suno.video.render`` importa ``imageio_ffmpeg`` só dentro de função, então
    ``from ... import medir_video`` nunca é o que falta sem o extra ``video`` — quem levanta o
    ``ImportError`` é a chamada em si, dentro de ``_ffmpeg_exe()`` (achado do revisor de erros,
    2026-09-19: o ``try`` errado guardava o import, não a chamada, e ``montar_pacote`` quebrava).
    """
    from suno.video.render import medir_video

    try:
        return medir_video(video)
    except ImportError:
        _REGISTRO.warning(
            "%s existe, mas o extra \"video\" não está instalado (uv sync --extra video); "
            "o Pacote sai sem as medições de duração/proporção/áudio.",
            video,
        )
        return []


def _montar_uma(
    execucao: Execucao, celula: Celula, pasta_do_pacote: Path, pasta_da_execucao: Path
) -> PacotePublicacao:
    pasta_do_pacote.mkdir(parents=True, exist_ok=True)
    legenda, hashtags = montar_legenda(celula, execucao.ancoras)

    imagens: list[ImagemSlide] = []
    folha: Path | None = None
    conferencia = ConferenciaVisual()
    video: Path | None = None

    if celula.formato is Formato.CARROSSEL:
        imagens = renderizar_carrossel(celula, execucao.ancoras, pasta_do_pacote)
        folha = folha_de_contato(imagens, pasta_do_pacote / NOME_DA_FOLHA)
        conferencia = conferir_imagens(imagens, execucao.ancoras)
    elif celula.formato is Formato.TEXTO_ANALITICO:
        (pasta_do_pacote / NOME_DO_TEXTO).write_text(celula.conteudo.texto or "", encoding="utf-8")
    else:
        video = _video_ja_renderizado(pasta_do_pacote, pasta_da_execucao, celula.audiencia)
        if video is not None:
            conferencia = ConferenciaVisual(medicoes=_medir_video_se_disponivel(video))

    (pasta_do_pacote / NOME_DA_LEGENDA).write_text(
        f"{legenda}\n\n{' '.join(hashtags)}\n", encoding="utf-8"
    )
    pacote = PacotePublicacao(
        execucao=execucao.identificador,
        audiencia=celula.audiencia,
        formato=celula.formato,
        legenda=legenda,
        hashtags=hashtags,
        imagens=imagens,
        folha_de_contato=folha,
        video=video,
        conferencia=conferencia,
    )
    (pasta_do_pacote / NOME_DO_REGISTRO).write_text(
        pacote.model_dump_json(indent=2), encoding="utf-8"
    )
    return pacote


def montar_pacote(identificador_execucao: str, pasta_execucoes: Path) -> list[PacotePublicacao]:
    """Um Pacote por Célula aprovada, em ``<pasta_execucoes>/<id>/pacote/<audiencia>-<formato>/``.

    Célula reprovada nunca ganha Pacote: o que o Avaliador recusou não chega ao humano como
    pronto para publicar. Defeito de render achado pela conferência **não** tira o Pacote da
    lista — quem decide com essa lista na mão é o H5 (ADR 0014).
    """
    execucao = _ler_execucao(identificador_execucao, pasta_execucoes)
    pasta_da_execucao = pasta_execucoes / identificador_execucao
    raiz = pasta_da_execucao / NOME_DA_PASTA
    pacotes: list[PacotePublicacao] = []
    aprovadas: set[str] = set()
    for historico in execucao.celulas:
        if historico.destino_final is not Destino.APROVADO:
            continue
        celula = historico.celula_final
        if celula is None:
            continue
        nome = f"{historico.audiencia.value}-{historico.formato.value}"
        aprovadas.add(nome)
        pacotes.append(_montar_uma(execucao, celula, raiz / nome, pasta_da_execucao))
    _remover_pacotes_obsoletos(raiz, aprovadas)
    return pacotes


def _remover_pacotes_obsoletos(raiz: Path, aprovadas: set[str]) -> None:
    """Uma Célula que deixou de ser aprovada (Ciclo regerou, Limiar mudou) não pode deixar o
    Pacote velho para trás: ele apareceria na API e no H5 como pronto para publicar algo que o
    Avaliador recusou — o inverso da regra deste módulo (achado do revisor de erros, 2026-09-19).
    """
    if not raiz.is_dir():
        return
    for pasta in raiz.iterdir():
        if pasta.is_dir() and pasta.name not in aprovadas:
            shutil.rmtree(pasta)


__all__ = ["montar_pacote", "renderizar_carrossel", "folha_de_contato", "montar_legenda", "conferir_imagens"]
