"""Composição determinística em CPU a partir do Roteiro aprovado. Medições: duração,
proporção, presença de áudio.

ADR 0004, 0014.

## O caminho

Cada ``BlocoFala`` vira uma sequência de quadros 1080x1920 (Pillow), colados em disco e
codificados num único ``video.mp4`` pelo ffmpeg que ``imageio_ffmpeg`` embute (chamado por
``subprocess``, nunca linkado — o binário do gyan.dev usado aqui é GPLv3; ver o relatório do
Agente 13 para a licença completa). Sem narração, o mp4 sai deliberadamente **sem trilha de
áudio**: gerar silêncio para enganar ``medir_video`` esconderia do H5 exatamente o que ele
precisa ver (ADR 0014).

``compor_quadro`` é pura — nem ffmpeg nem disco — e é o que ``tests/test_video.py`` exercita
sem precisar do extra ``video`` instalado.

## Determinismo

Os quadros são determinísticos byte a byte (mesma Célula, mesmos pixels). A codificação H.264
não é: duas rodadas do mesmo Roteiro produzem arquivos com bytes diferentes, mesmo quando o
conteúdo visual é idêntico. Por isso ``tests/test_video.py`` compara **medidas** (dimensão,
duração, presença de áudio), nunca o mp4 byte a byte — ao contrário do Carrossel, que é
comparável por pixel porque não passa por um codec com estado interno.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from suno.dominio import (
    Audiencia,
    BlocoFala,
    Destino,
    Formato,
    MedicaoVisual,
    DefeitoRender,
)
from suno.gerador.execucao import carregar_execucao
from suno.pacote.carrossel import (
    COR_DESTAQUE,
    COR_FUNDO,
    COR_TEXTO,
    LETRA_COMUM,
    LETRA_FORTE,
    SELO_DA_AUDIENCIA,
    altura_da_linha,
    medir_largura,
    quebrar_linhas,
    tipografia,
)

# ---------------------------------------------------------------------------
# Formato do vídeo: 9:16, o único que as redes verticais aceitam
# ---------------------------------------------------------------------------

LARGURA_VIDEO = 1080
ALTURA_VIDEO = 1920

FPS = 12
"""12 fps, não 24: os quadros mudam por bloco de fala (a cada segundo, no máximo), nunca por
movimento — metade dos quadros para o mesmo resultado visual, metade do tempo de render. É o
corte certo para composição estática em CPU (item 3 da ordem de corte do CLAUDE.md já tirou o
avatar; isto seria o próximo, se precisasse)."""

DURACAO_MINIMA_S = 5.0
DURACAO_MAXIMA_S = 60.0
"""A faixa que o enunciado e as plataformas verticais pedem (Reels/Shorts/TikTok): abaixo de
5s não é conteúdo, acima de 60s sai do formato vertical curto (ADR 0014)."""

NOME_DO_VIDEO = "video.mp4"

# ---------------------------------------------------------------------------
# Layout do quadro
# ---------------------------------------------------------------------------

MARGEM = 84
LARGURA_UTIL = LARGURA_VIDEO - 2 * MARGEM

TAMANHO_SELO = 30
RECUO_DO_SELO = 24
RECUO_VERTICAL_DO_SELO = 14
Y_SELO = 64

TAMANHO_TITULO = 58
LINHAS_DO_TITULO = 4
ENTRELINHA_TITULO = 16
Y_TITULO = 300
"""``tela``: a rubrica de cena, em destaque — grande o bastante para ler em tela de celular."""

TAMANHO_LEGENDA = 42
LINHAS_DA_LEGENDA = 6
ENTRELINHA_LEGENDA = 12
Y_LEGENDA = 1360
"""``fala``: a legenda na parte inferior, como o brief pede."""

COR_TRILHO_DA_BARRA = "#1B2536"
ALTURA_DA_BARRA = 10
Y_BARRA = 1840

_REGUA_DE_TEXTO = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _desenhar_texto_centralizado(
    desenho: ImageDraw.ImageDraw,
    *,
    texto: str,
    letra_nome: str,
    tamanho: int,
    cor: str,
    y: int,
    entrelinha: int,
) -> None:
    """Quebra por largura medida (a mesma função do Carrossel) e centraliza cada linha."""
    letra = tipografia(letra_nome, tamanho)
    linhas = quebrar_linhas(texto, letra, LARGURA_UTIL)
    passo = altura_da_linha(letra) + entrelinha
    for ordem, linha in enumerate(linhas):
        x = MARGEM + (LARGURA_UTIL - medir_largura(linha, letra)) // 2
        desenho.text((x, y + ordem * passo), linha, font=letra, fill=cor)


def _desenhar_selo(desenho: ImageDraw.ImageDraw, audiencia: Audiencia) -> None:
    """O mesmo selo de canto do Carrossel: a identidade visual é uma só nas nove Células."""
    rotulo = SELO_DA_AUDIENCIA[audiencia]
    letra = tipografia(LETRA_FORTE, TAMANHO_SELO)
    largura = medir_largura(rotulo, letra) + 2 * RECUO_DO_SELO
    altura = altura_da_linha(letra) + 2 * RECUO_VERTICAL_DO_SELO
    desenho.rounded_rectangle(
        [MARGEM, Y_SELO, MARGEM + largura, Y_SELO + altura], radius=12, fill=COR_DESTAQUE
    )
    desenho.text(
        (MARGEM + RECUO_DO_SELO, Y_SELO + RECUO_VERTICAL_DO_SELO),
        rotulo,
        font=letra,
        fill=COR_FUNDO,
    )


def _desenhar_barra_de_progresso(desenho: ImageDraw.ImageDraw, progresso: float) -> None:
    """Barra do tempo decorrido no vídeo inteiro (não só no bloco atual)."""
    progresso = min(max(progresso, 0.0), 1.0)
    desenho.rectangle(
        [MARGEM, Y_BARRA, LARGURA_VIDEO - MARGEM, Y_BARRA + ALTURA_DA_BARRA],
        fill=COR_TRILHO_DA_BARRA,
    )
    largura_preenchida = round(LARGURA_UTIL * progresso)
    if largura_preenchida > 0:
        desenho.rectangle(
            [MARGEM, Y_BARRA, MARGEM + largura_preenchida, Y_BARRA + ALTURA_DA_BARRA],
            fill=COR_DESTAQUE,
        )


def compor_quadro(bloco: BlocoFala, audiencia: Audiencia, progresso: float) -> Image.Image:
    """Um quadro 1080x1920, puro: sem ffmpeg e sem disco, por isso testável sem o extra
    ``video`` instalado. Fundo escuro, ``tela`` como título grande, ``fala`` como legenda na
    parte inferior, selo da Audiência e barra de progresso do tempo — o que o brief pede.
    """
    imagem = Image.new("RGB", (LARGURA_VIDEO, ALTURA_VIDEO), COR_FUNDO)
    desenho = ImageDraw.Draw(imagem)
    _desenhar_selo(desenho, audiencia)
    if bloco.tela:
        _desenhar_texto_centralizado(
            desenho,
            texto=bloco.tela,
            letra_nome=LETRA_FORTE,
            tamanho=TAMANHO_TITULO,
            cor=COR_DESTAQUE,
            y=Y_TITULO,
            entrelinha=ENTRELINHA_TITULO,
        )
    _desenhar_texto_centralizado(
        desenho,
        texto=bloco.fala,
        letra_nome=LETRA_COMUM,
        tamanho=TAMANHO_LEGENDA,
        cor=COR_TEXTO,
        y=Y_LEGENDA,
        entrelinha=ENTRELINHA_LEGENDA,
    )
    _desenhar_barra_de_progresso(desenho, progresso)
    return imagem


# ---------------------------------------------------------------------------
# A codificação: subprocesso ffmpeg, nunca linkado
# ---------------------------------------------------------------------------


def _ffmpeg_exe() -> str:
    """Import tardio: só quem chega até aqui precisa do extra ``video`` instalado."""
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _preparar_trilha_do_bloco(
    ffmpeg: str, audio: Path | None, duracao_bloco: float, destino: Path
) -> None:
    """Um WAV mono de exatamente ``duracao_bloco``: silêncio se não há narração deste bloco,
    ou o áudio sintetizado completado com silêncio até preencher o bloco (nunca cortado —
    ``renderizar_video`` já garante ``duracao_bloco >= duração do áudio``)."""
    if audio is None:
        comando = [
            ffmpeg, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-t", f"{duracao_bloco:.3f}", "-c:a", "pcm_s16le", str(destino),
        ]
    else:
        comando = [
            ffmpeg, "-y", "-i", str(audio), "-af", "apad",
            "-t", f"{duracao_bloco:.3f}", "-ar", "24000", "-ac", "1",
            "-c:a", "pcm_s16le", str(destino),
        ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao preparar a trilha de um bloco: {resultado.stderr[-2000:]}")


def _concatenar_trilhas(ffmpeg: str, trilhas: list[Path], destino: Path) -> None:
    lista = destino.with_suffix(".txt")
    conteudo = "\n".join(f"file '{trilha.as_posix()}'" for trilha in trilhas)
    lista.write_text(conteudo, encoding="utf-8")
    comando = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(destino)]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao concatenar a trilha: {resultado.stderr[-2000:]}")


def _duracao_do_audio(ffmpeg: str, caminho: Path) -> float:
    info = subprocess.run([ffmpeg, "-i", str(caminho)], capture_output=True, text=True).stderr
    duracao = _extrair_duracao(info)
    return duracao if duracao is not None else 0.0


def _codificar(ffmpeg: str, pasta_quadros: Path, trilha: Path | None, destino: Path) -> None:
    comando = [ffmpeg, "-y", "-framerate", str(FPS), "-i", str(pasta_quadros / "quadro-%06d.png")]
    if trilha is not None:
        comando += ["-i", str(trilha)]
    comando += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if trilha is not None:
        comando += ["-c:a", "aac", "-shortest"]
    comando += ["-movflags", "+faststart", "-map_metadata", "-1", str(destino)]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao codificar {destino}: {resultado.stderr[-2000:]}")


def renderizar_video(
    identificador_execucao: str,
    audiencia: Audiencia,
    pasta_execucoes: Path,
    *,
    narracao: bool = False,
) -> Path:
    """Um único mp4 9:16 a partir do Roteiro aprovado de ``audiencia`` (ADR 0004).

    Levanta ``ValueError`` se a Célula não existe ou não foi aprovada — vídeo nunca nasce de
    Roteiro reprovado. Grava em
    ``<pasta_execucoes>/<identificador_execucao>/pacote/<audiencia>-roteiro/video.mp4``, o
    caminho que ``suno.pacote`` já sabe procurar. ``narracao=True`` liga o ``edge-tts``
    (nunca em teste, nunca no caminho crítico da demo); ``False`` (padrão) produz um mp4 sem
    trilha de áudio — honesto, não silêncio fingido (ADR 0014).
    """
    execucao = carregar_execucao(identificador_execucao, pasta_execucoes)
    historico = execucao.historico(audiencia, Formato.ROTEIRO)
    if historico is None or historico.destino_final is not Destino.APROVADO:
        raise ValueError("só Roteiro aprovado vira vídeo (ADR 0004)")
    celula = historico.celula_final
    if celula is None:
        raise ValueError("só Roteiro aprovado vira vídeo (ADR 0004)")
    blocos = celula.conteudo.blocos or []
    if not blocos:
        raise ValueError("Roteiro aprovado sem blocos de fala não tem o que renderizar")

    pasta_do_pacote = Path(pasta_execucoes) / identificador_execucao / "pacote" / f"{audiencia.value}-roteiro"
    pasta_do_pacote.mkdir(parents=True, exist_ok=True)
    caminho_video = pasta_do_pacote / NOME_DO_VIDEO

    ffmpeg = _ffmpeg_exe()

    audios: list[Path | None] = [None] * len(blocos)
    if narracao:
        from suno.video.narracao import sintetizar

        pasta_narracao = pasta_do_pacote / "narracao"
        for indice, bloco in enumerate(blocos):
            audios[indice] = sintetizar(bloco.fala, pasta_narracao / f"bloco-{indice:02d}.mp3")
    tem_narracao = any(audio is not None for audio in audios)

    duracoes_dos_blocos: list[float] = []
    for bloco, audio in zip(blocos, audios):
        duracao = bloco.fim_s - bloco.inicio_s
        if audio is not None:
            duracao = max(duracao, _duracao_do_audio(ffmpeg, audio))
        duracoes_dos_blocos.append(duracao)
    duracao_total = sum(duracoes_dos_blocos)

    with tempfile.TemporaryDirectory(prefix="suno-video-") as bruto:
        pasta_temp = Path(bruto)
        pasta_quadros = pasta_temp / "quadros"
        pasta_quadros.mkdir()

        contador = 0
        tempo_decorrido = 0.0
        for bloco, duracao_bloco in zip(blocos, duracoes_dos_blocos):
            n_quadros = max(1, round(duracao_bloco * FPS))
            for indice_quadro in range(n_quadros):
                progresso = (tempo_decorrido + indice_quadro / FPS) / duracao_total if duracao_total > 0 else 0.0
                quadro = compor_quadro(bloco, audiencia, progresso)
                contador += 1
                quadro.save(pasta_quadros / f"quadro-{contador:06d}.png")
            tempo_decorrido += duracao_bloco

        trilha_final: Path | None = None
        if tem_narracao:
            pasta_trilhas = pasta_temp / "trilhas"
            pasta_trilhas.mkdir()
            trilhas: list[Path] = []
            for indice, (audio, duracao_bloco) in enumerate(zip(audios, duracoes_dos_blocos)):
                trilha = pasta_trilhas / f"bloco-{indice:02d}.wav"
                _preparar_trilha_do_bloco(ffmpeg, audio, duracao_bloco, trilha)
                trilhas.append(trilha)
            trilha_final = pasta_trilhas / "trilha.wav"
            _concatenar_trilhas(ffmpeg, trilhas, trilha_final)

        _codificar(ffmpeg, pasta_quadros, trilha_final, caminho_video)

    return caminho_video


# ---------------------------------------------------------------------------
# A medição: ffmpeg -i, lido do stderr (o pacote não embute ffprobe)
# ---------------------------------------------------------------------------

_PADRAO_DURACAO = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_PADRAO_VIDEO = re.compile(r"Video:.*?(\d{2,5})x(\d{2,5})")
_PADRAO_AUDIO = re.compile(r"Stream #\d+:\d+.*Audio:")


def _extrair_duracao(info: str) -> float | None:
    encontrado = _PADRAO_DURACAO.search(info)
    if encontrado is None:
        return None
    horas, minutos, segundos = encontrado.groups()
    return int(horas) * 3600 + int(minutos) * 60 + float(segundos)


def _extrair_dimensao(info: str) -> tuple[int, int] | None:
    encontrado = _PADRAO_VIDEO.search(info)
    if encontrado is None:
        return None
    largura, altura = encontrado.groups()
    return int(largura), int(altura)


def medir_video(caminho: Path) -> list[MedicaoVisual]:
    """Duração, proporção e presença de áudio — a camada determinística que cobre o vídeo
    desde o início (ADR 0014). Lido de ``ffmpeg -i`` (sem saída): a informação vem no
    ``stderr``, porque ``imageio_ffmpeg`` não embute ``ffprobe``.
    """
    ffmpeg = _ffmpeg_exe()
    info = subprocess.run([ffmpeg, "-i", str(caminho)], capture_output=True, text=True).stderr
    nome = Path(caminho).name

    duracao = _extrair_duracao(info)
    defeito_duracao = None
    if duracao is None or duracao < DURACAO_MINIMA_S or duracao > DURACAO_MAXIMA_S:
        defeito_duracao = DefeitoRender.DURACAO_FORA_DA_FAIXA
    medicoes = [
        MedicaoVisual(
            artefato=nome,
            defeito=defeito_duracao,
            valor=duracao,
            detalhe=(
                f"duração {duracao:.1f}s; a faixa aceita é {DURACAO_MINIMA_S:.0f}–{DURACAO_MAXIMA_S:.0f}s"
                if duracao is not None
                else "duração não lida do ffmpeg"
            ),
        )
    ]

    dimensao = _extrair_dimensao(info)
    defeito_dimensao = None if dimensao == (LARGURA_VIDEO, ALTURA_VIDEO) else DefeitoRender.DIMENSAO_ERRADA
    medicoes.append(
        MedicaoVisual(
            artefato=nome,
            defeito=defeito_dimensao,
            valor=float(dimensao[0]) if dimensao else None,
            detalhe=(
                f"{dimensao[0]}x{dimensao[1]}; o vídeo precisa de {LARGURA_VIDEO}x{ALTURA_VIDEO} (9:16)"
                if dimensao is not None
                else "dimensão não lida do ffmpeg"
            ),
        )
    )

    tem_audio = _PADRAO_AUDIO.search(info) is not None
    medicoes.append(
        MedicaoVisual(
            artefato=nome,
            defeito=None if tem_audio else DefeitoRender.SEM_AUDIO,
            valor=1.0 if tem_audio else 0.0,
            detalhe="trilha de áudio presente" if tem_audio else "sem trilha de áudio (sem narração)",
        )
    )
    return medicoes
