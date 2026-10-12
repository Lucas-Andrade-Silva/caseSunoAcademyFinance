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

import math
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from suno.dominio import (
    AnimacaoDoTexto,
    Audiencia,
    BlocoFala,
    Destino,
    EfeitoDeCena,
    Formato,
    MedicaoVisual,
    DefeitoRender,
    TipoDeCena,
    TransicaoDeEntrada,
)
from suno.gerador.execucao import carregar_execucao
from suno.pacote.carrossel import (
    COR_APOIO,
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
from suno.video.design import TEMPOS, orcamento_de, duracoes_aceitas, TOLERANCIA_DA_DURACAO
from suno.video.icones import desenhar_icone
from suno.video.sons import marcas_dos_blocos, trilha_de_efeitos

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
DURACAO_MAXIMA_S = max(duracoes_aceitas()) * (1 + TOLERANCIA_DA_DURACAO)
"""A faixa de um vídeo sem duração escolhida: abaixo de 5s não é conteúdo, e acima do maior
alvo (3 min, mais a tolerância) sai do vídeo curto (ADR 0014). Com duração escolhida, a faixa
é a do alvo: de 75% a 125% dele (``suno.video.design.Orcamento``)."""

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
ENTRELINHA_TITULO = 16
"""``tela``: a rubrica de cena, em destaque — grande o bastante para ler em tela de celular."""

TAMANHO_LEGENDA = 42
LINHAS_DA_LEGENDA = 6
ENTRELINHA_LEGENDA = 12
Y_LEGENDA = 1360
"""``fala``: a legenda na parte inferior, como o brief pede."""

COR_TRILHO_DA_BARRA = "#1B2536"
ALTURA_DA_BARRA = 10
Y_BARRA = 1840

TAMANHO_DO_ICONE = 260
Y_DO_ICONE = 430
"""O ícone da cena, centrado, acima do texto da rubrica."""

Y_TEXTO_COM_ICONE = 640
Y_TEXTO_SEM_ICONE = 520
TAMANHO_DA_CHAMADA = 74
TAMANHO_DO_DADO = 190
TAMANHO_DO_ITEM = 54
TAMANHO_DA_CITACAO = 50

ATRASO_ENTRE_ITENS_S = 0.5
CONTAGEM_S = 1.0
DIGITACAO_CARACTERES_POR_S = 30.0

_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _rgba(cor: str, alfa: float = 1.0) -> tuple[int, int, int, int]:
    return (
        int(cor[1:3], 16),
        int(cor[3:5], 16),
        int(cor[5:7], 16),
        round(255 * min(max(alfa, 0.0), 1.0)),
    )


def _suave(x: float) -> float:
    """Aceleração de entrada (ease-out cúbico) de 0 a 1."""
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def _desenhar_texto_centralizado(
    desenho: ImageDraw.ImageDraw,
    *,
    texto: str,
    letra_nome: str,
    tamanho: int,
    cor: str | tuple[int, int, int, int],
    y: int,
    entrelinha: int,
) -> int:
    """Quebra por largura medida (a mesma função do Carrossel) e centraliza cada linha.
    Devolve a altura ocupada, para quem vem depois empilhar abaixo."""
    letra = tipografia(letra_nome, tamanho)
    linhas = quebrar_linhas(texto, letra, LARGURA_UTIL)
    passo = altura_da_linha(letra) + entrelinha
    for ordem, linha in enumerate(linhas):
        x = MARGEM + (LARGURA_UTIL - medir_largura(linha, letra)) // 2
        desenho.text((x, y + ordem * passo), linha, font=letra, fill=cor)
    return len(linhas) * passo


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


def _partes_da_tela(bloco: BlocoFala) -> list[str]:
    return [parte.strip() for parte in bloco.tela.split("|") if parte.strip()]


def _contar_numero(texto: str, progresso: float) -> str:
    """Troca o primeiro número de ``texto`` por ele mesmo a ``progresso`` do caminho desde zero,
    com as mesmas casas decimais e a vírgula brasileira. Sem número, devolve o texto."""
    achado = _NUMERO.search(texto)
    if achado is None or progresso >= 1.0:
        return texto
    bruto = achado.group(0)
    separador = "," if "," in bruto else "."
    casas = len(bruto.split(separador)[1]) if separador in bruto else 0
    valor = float(bruto.replace(",", ".")) * _suave(progresso)
    mostrado = f"{valor:.{casas}f}".replace(".", ",")
    return texto[: achado.start()] + mostrado + texto[achado.end():]


def _tamanho_que_cabe(texto: str, letra_nome: str, tamanho: int) -> int:
    """O maior tamanho, até ``tamanho``, em que ``texto`` cabe numa linha só."""
    while tamanho > 40:
        if medir_largura(texto, tipografia(letra_nome, tamanho)) <= LARGURA_UTIL:
            break
        tamanho -= 6
    return tamanho


def _itens_da_cena(bloco: BlocoFala, tempo: float | None) -> list[tuple[str, str, int, str, float]]:
    """Os textos da rubrica no layout da cena: (texto, letra, tamanho, cor, atraso em s)."""
    partes = _partes_da_tela(bloco)
    cena = bloco.cena
    junto = " ".join(partes)
    if cena is TipoDeCena.DADO_GRANDE:
        texto = junto
        if bloco.efeito is EfeitoDeCena.CONTAGEM and tempo is not None:
            texto = _contar_numero(junto, (tempo - bloco.texto_entra_em_s) / CONTAGEM_S)
        return [(texto, LETRA_FORTE, _tamanho_que_cabe(junto, LETRA_FORTE, TAMANHO_DO_DADO), COR_TEXTO, 0.0)]
    if cena is TipoDeCena.LISTA:
        return [
            (f"•  {parte}", LETRA_FORTE, TAMANHO_DO_ITEM, COR_TEXTO, ordem * ATRASO_ENTRE_ITENS_S)
            for ordem, parte in enumerate(partes)
        ]
    if cena is TipoDeCena.COMPARACAO and len(partes) >= 2:
        return [
            (partes[0], LETRA_FORTE, TAMANHO_TITULO, COR_TEXTO, 0.0),
            ("↓", LETRA_FORTE, 70, COR_DESTAQUE, ATRASO_ENTRE_ITENS_S / 2),
            (" ".join(partes[1:]), LETRA_FORTE, TAMANHO_TITULO, COR_TEXTO, ATRASO_ENTRE_ITENS_S),
        ]
    if cena is TipoDeCena.CITACAO:
        return [
            ("“", LETRA_FORTE, 150, COR_DESTAQUE, 0.0),
            (junto, LETRA_COMUM, TAMANHO_DA_CITACAO, COR_APOIO, 0.1),
        ]
    if cena in (TipoDeCena.GANCHO, TipoDeCena.ENCERRAMENTO):
        return [(junto, LETRA_FORTE, TAMANHO_DA_CHAMADA, COR_TEXTO, 0.0)]
    return [(junto, LETRA_FORTE, TAMANHO_TITULO, COR_TEXTO, 0.0)]


def _camada_do_texto(
    bloco: BlocoFala, tempo: float | None, tem_icone: bool
) -> tuple[Image.Image, int]:
    """A camada RGBA da rubrica, animada em ``tempo`` (``None`` = estado final), e o ``y`` logo
    abaixo do bloco, onde o efeito de sublinhado se apoia."""
    camada = Image.new("RGBA", (LARGURA_VIDEO, ALTURA_VIDEO), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(camada)
    y = Y_TEXTO_COM_ICONE if tem_icone else Y_TEXTO_SEM_ICONE
    if not _partes_da_tela(bloco):
        return camada, y

    itens = _itens_da_cena(bloco, tempo)
    animacao = bloco.texto_anima

    pulso = 1.0
    if bloco.efeito is EfeitoDeCena.PULSO and tempo is not None:
        fase = (tempo - bloco.texto_entra_em_s - 0.25) / 0.5
        if 0.0 < fase < 1.0:
            pulso = 1.0 + 0.08 * math.sin(math.pi * fase)

    for texto, letra, tamanho, cor, atraso in itens:
        p = 1.0
        if tempo is not None:
            p = (tempo - bloco.texto_entra_em_s - atraso) / TEMPOS["entrada_do_texto_s"]
            if p <= 0.0:
                y += 90
                continue
            p = min(p, 1.0)
        alfa, deslocamento, escala, visivel = 1.0, 0, 1.0, texto
        if tempo is not None:
            if animacao is AnimacaoDoTexto.FADE:
                alfa = _suave(p)
            elif animacao is AnimacaoDoTexto.DESLIZAR_BAIXO:
                alfa, deslocamento = _suave(p), round(-(1 - _suave(p)) * 80)
            elif animacao is AnimacaoDoTexto.POP:
                alfa = min(1.0, p * 2)
                escala = 0.6 + 0.4 * _suave(p) + (0.08 * math.sin(math.pi * p) if p < 1 else 0.0)
            elif animacao is AnimacaoDoTexto.DIGITAR:
                decorrido = tempo - bloco.texto_entra_em_s - atraso
                visivel = texto[: max(1, int(decorrido * DIGITACAO_CARACTERES_POR_S))]
        altura = _desenhar_texto_centralizado(
            desenho,
            texto=visivel,
            letra_nome=letra,
            tamanho=max(20, round(tamanho * escala * pulso)),
            cor=_rgba(cor, alfa),
            y=y + deslocamento,
            entrelinha=ENTRELINHA_TITULO,
        )
        y += altura + (8 if len(itens) > 1 else 0)
    return camada, y


def _aplicar_zoom(imagem: Image.Image, fator: float) -> Image.Image:
    if fator <= 1.0005:
        return imagem
    largura = round(LARGURA_VIDEO * fator)
    altura = round(ALTURA_VIDEO * fator)
    ampliada = imagem.resize((largura, altura), Image.BILINEAR)
    x, y = (largura - LARGURA_VIDEO) // 2, (altura - ALTURA_VIDEO) // 2
    return ampliada.crop((x, y, x + LARGURA_VIDEO, y + ALTURA_VIDEO))


def compor_quadro(
    bloco: BlocoFala,
    audiencia: Audiencia,
    progresso: float,
    tempo_na_cena: float | None = None,
) -> Image.Image:
    """Um quadro 1080x1920, puro: sem ffmpeg e sem disco, por isso testável sem o extra
    ``video`` instalado. Fundo escuro, ícone, a rubrica ``tela`` no layout da ``cena``, ``fala``
    como legenda na parte inferior, selo da Audiência e barra de progresso do tempo.

    ``tempo_na_cena`` é o instante, em segundos desde o início do bloco, que as animações e os
    efeitos usam; ``None`` desenha o estado final (tudo já apareceu, sem efeito) — o quadro
    de uma cena estática e o que os testes de layout medem.
    """
    imagem = Image.new("RGB", (LARGURA_VIDEO, ALTURA_VIDEO), COR_FUNDO)
    desenho = ImageDraw.Draw(imagem)
    _desenhar_selo(desenho, audiencia)

    if bloco.icone is not None:
        aparece = 1.0 if tempo_na_cena is None else _suave(tempo_na_cena / TEMPOS["entrada_do_texto_s"])
        if aparece > 0.0:
            camada_do_icone = Image.new("RGBA", (LARGURA_VIDEO, ALTURA_VIDEO), (0, 0, 0, 0))
            desenhar_icone(
                ImageDraw.Draw(camada_do_icone),
                bloco.icone,
                LARGURA_VIDEO / 2,
                Y_DO_ICONE,
                TAMANHO_DO_ICONE * (0.8 + 0.2 * aparece),
                _rgba(COR_DESTAQUE, aparece),
            )
            imagem.paste(camada_do_icone, (0, 0), camada_do_icone)

    if bloco.tela:
        camada, base_do_texto = _camada_do_texto(bloco, tempo_na_cena, bloco.icone is not None)
        imagem.paste(camada, (0, 0), camada)
        if bloco.efeito is EfeitoDeCena.SUBLINHADO:
            p = 1.0 if tempo_na_cena is None else _suave((tempo_na_cena - bloco.texto_entra_em_s) / 0.5)
            largura = round(LARGURA_UTIL * 0.5 * p)
            if largura > 0:
                centro = LARGURA_VIDEO // 2
                desenho.rectangle(
                    [centro - largura // 2, base_do_texto + 12, centro + largura // 2, base_do_texto + 22],
                    fill=COR_DESTAQUE,
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

    if bloco.efeito is EfeitoDeCena.ZOOM_LENTO and tempo_na_cena is not None:
        duracao = max(bloco.fim_s - bloco.inicio_s, 0.1)
        imagem = _aplicar_zoom(imagem, 1.0 + 0.06 * min(tempo_na_cena / duracao, 1.0))
    return imagem


def compor_transicao(
    anterior: Image.Image, atual: Image.Image, transicao: TransicaoDeEntrada, p: float
) -> Image.Image:
    """O quadro da transição em ``p`` (0 = ainda a cena anterior, 1 = a cena nova inteira)."""
    p = min(max(p, 0.0), 1.0)
    if transicao is TransicaoDeEntrada.CORTE or p >= 1.0:
        return atual
    q = _suave(p)
    if transicao is TransicaoDeEntrada.FADE:
        return Image.blend(anterior, atual, q)
    saida = anterior.copy()
    if transicao is TransicaoDeEntrada.DESLIZAR_ESQUERDA:
        deslocamento = round(LARGURA_VIDEO * (1 - q))
        saida.paste(anterior.crop((round(LARGURA_VIDEO * q), 0, LARGURA_VIDEO, ALTURA_VIDEO)), (0, 0))
        saida.paste(atual.crop((0, 0, LARGURA_VIDEO - deslocamento, ALTURA_VIDEO)), (deslocamento, 0))
        return saida
    if transicao is TransicaoDeEntrada.DESLIZAR_CIMA:
        deslocamento = round(ALTURA_VIDEO * (1 - q))
        saida.paste(anterior.crop((0, round(ALTURA_VIDEO * q), LARGURA_VIDEO, ALTURA_VIDEO)), (0, 0))
        saida.paste(atual.crop((0, 0, LARGURA_VIDEO, ALTURA_VIDEO - deslocamento)), (0, deslocamento))
        return saida
    # ZOOM: a cena nova cresce de 85% a 100% enquanto surge.
    fator = 0.85 + 0.15 * q
    menor = atual.resize((round(LARGURA_VIDEO * fator), round(ALTURA_VIDEO * fator)), Image.BILINEAR)
    base = anterior.copy()
    base.paste(menor, ((LARGURA_VIDEO - menor.width) // 2, (ALTURA_VIDEO - menor.height) // 2))
    return Image.blend(anterior, base, q)


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


def _marcas_no_tempo_real(blocos: list[BlocoFala], inicios: list[float]) -> list:
    """Os sons nos instantes do vídeo renderizado: a narração pode alongar uma cena, então o
    início de cada uma vem da soma das durações reais, não do ``inicio_s`` do Roteiro."""
    deslocados = [bloco.model_copy(update={"inicio_s": inicio}) for bloco, inicio in zip(blocos, inicios)]
    return marcas_dos_blocos(deslocados)


def _misturar(ffmpeg: str, narracao: Path, efeitos: Path, destino: Path) -> None:
    comando = [
        ffmpeg, "-y", "-i", str(narracao), "-i", str(efeitos),
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "[a]", "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(destino),
    ]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ao misturar os efeitos: {resultado.stderr[-2000:]}")


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

    O render segue a direção de cena de cada bloco (layout, ícone, animação do texto, efeito e
    transição); os sons do catálogo se misturam à narração e só existem quando há narração.
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
        inicios: list[float] = []
        quadro_anterior: Image.Image | None = None
        for bloco, duracao_bloco in zip(blocos, duracoes_dos_blocos):
            inicios.append(tempo_decorrido)
            n_quadros = max(1, round(duracao_bloco * FPS))
            n_transicao = (
                round(TEMPOS["transicao_s"] * FPS)
                if quadro_anterior is not None and bloco.entrada is not TransicaoDeEntrada.CORTE
                else 0
            )
            for indice_quadro in range(n_quadros):
                progresso = (tempo_decorrido + indice_quadro / FPS) / duracao_total if duracao_total > 0 else 0.0
                quadro = compor_quadro(bloco, audiencia, progresso, indice_quadro / FPS)
                if indice_quadro < n_transicao and quadro_anterior is not None:
                    quadro = compor_transicao(
                        quadro_anterior, quadro, bloco.entrada, (indice_quadro + 1) / (n_transicao + 1)
                    )
                contador += 1
                quadro.save(pasta_quadros / f"quadro-{contador:06d}.png")
            quadro_anterior = quadro
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
            # Os sons de transição e de efeito entram só com narração: um mp4 sem voz continua
            # sem trilha de áudio, para ``medir_video`` não ser enganado por um som solto (ADR 0014).
            efeitos = trilha_de_efeitos(
                _marcas_no_tempo_real(blocos, inicios), duracao_total, pasta_trilhas / "efeitos.wav"
            )
            if efeitos is not None:
                misturada = pasta_trilhas / "trilha-com-efeitos.wav"
                _misturar(ffmpeg, trilha_final, efeitos, misturada)
                trilha_final = misturada

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


def medir_video(caminho: Path, duracao_alvo_s: int | None = None) -> list[MedicaoVisual]:
    """Duração, proporção e presença de áudio — a camada determinística que cobre o vídeo
    desde o início (ADR 0014). Lido de ``ffmpeg -i`` (sem saída): a informação vem no
    ``stderr``, porque ``imageio_ffmpeg`` não embute ``ffprobe``.

    ``duracao_alvo_s`` é a duração que a pessoa escolheu para o Roteiro; com ela a faixa aceita
    é a do alvo (75% a 125%), sem ela é a faixa geral de 5s ao maior alvo.
    """
    ffmpeg = _ffmpeg_exe()
    info = subprocess.run([ffmpeg, "-i", str(caminho)], capture_output=True, text=True).stderr
    nome = Path(caminho).name

    duracao = _extrair_duracao(info)
    minimo, maximo = (
        orcamento_de(duracao_alvo_s).faixa_de_duracao_s
        if duracao_alvo_s is not None
        else (DURACAO_MINIMA_S, DURACAO_MAXIMA_S)
    )
    defeito_duracao = None
    if duracao is None or duracao < minimo or duracao > maximo:
        defeito_duracao = DefeitoRender.DURACAO_FORA_DA_FAIXA
    medicoes = [
        MedicaoVisual(
            artefato=nome,
            defeito=defeito_duracao,
            valor=duracao,
            detalhe=(
                f"duração {duracao:.1f}s; a faixa aceita é {minimo:.0f}–{maximo:.0f}s"
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
