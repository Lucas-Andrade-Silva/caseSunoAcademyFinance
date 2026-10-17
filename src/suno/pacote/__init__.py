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

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

from suno.dominio import (
    Audiencia,
    Celula,
    ConferenciaVisual,
    Execucao,
    ErroProvedor,
    FamiliaVisual,
    Formato,
    FotoDoPacote,
    ImagemSlide,
    PacotePublicacao,
    PapelLLM,
    ReferenciaVisual,
)
from suno.imagens import BibliotecaDeImagens, bloco_de_creditos
from suno.pacote.carrossel import folha_de_contato, motor_de_render, renderizar_carrossel
from suno.pacote.direcao_de_arte import (
    composicoes_compativeis,
    escolher_familia,
    resumir_direcao_renderizada,
)
from suno.pacote.fotos import FotoDoSlide, acomodar_fotos, resolver_fotos
from suno.pacote.diretor_de_arte_ia import planejar_com_diretor_de_arte
from suno.pacote.historico_layouts import (
    NOME_DO_BANCO,
    RepositorioHistoricoLayouts,
    UsoDeLayout,
    usos_do_plano,
)
from suno.pacote.feedback_visual import RepositorioFeedbackVisual
from suno.pacote.referencias_visuais import RepositorioReferenciasVisuais
from suno.provedores.base import Provedor
from suno.pacote.legenda import montar_legenda
from suno.pacote.visual import conferir_imagens, julgar_folha_de_contato
from suno.video.atuacao import direcao_em_disco
from suno.video.plano import NOME_DO_PLANO, NOME_DO_PLANO_LEGIVEL, montar_plano, plano_em_markdown

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


def _video_ja_renderizado(pasta_do_pacote: Path, pasta_da_execucao: Path, audiencia: Audiencia, execucao: Execucao) -> Path | None:
    """O mp4 só entra no Pacote se alguém já rodou ``suno.cli video`` (ADR 0004)."""
    candidatos = (
        pasta_do_pacote / NOME_DO_VIDEO,
        pasta_da_execucao / f"video-{audiencia.value}.mp4",
        pasta_da_execucao / NOME_DO_VIDEO,
    )
    for candidato in candidatos:
        if candidato.exists():
            revisao = candidato.with_suffix(".revisao")
            if revisao.exists():
                if revisao.read_text(encoding="utf-8") != execucao.assinatura_da_celula(audiencia, Formato.ROTEIRO):
                    continue
            else:
                historico = execucao.historico(audiencia, Formato.ROTEIRO)
                if historico and historico.laudo_final and candidato.stat().st_mtime < historico.laudo_final.avaliado_em.timestamp():
                    continue
            return candidato
    return None


def _medir_video_se_disponivel(video: Path, duracao_alvo_s: int | None = None) -> list:
    """Duração, proporção e áudio do mp4 já renderizado (ADR 0014) — sempre ligada, mas só entra
    no Pacote quando alguém rodou ``suno.cli video`` antes: este módulo não renderiza.

    ``suno.video.render`` importa ``imageio_ffmpeg`` só dentro de função, então
    ``from ... import medir_video`` nunca é o que falta sem o extra ``video`` — quem levanta o
    ``ImportError`` é a chamada em si, dentro de ``_ffmpeg_exe()`` (achado do revisor de erros,
    2026-09-19: o ``try`` errado guardava o import, não a chamada, e ``montar_pacote`` quebrava).
    """
    from suno.video.render import medir_video

    try:
        return medir_video(video, duracao_alvo_s)
    except ImportError:
        _REGISTRO.warning(
            "%s existe, mas o extra \"video\" não está instalado (uv sync --extra video); "
            "o Pacote sai sem as medições de duração/proporção/áudio.",
            video,
        )
        return []


def _montar_uma(
    execucao: Execucao,
    celula: Celula,
    pasta_do_pacote: Path,
    pasta_da_execucao: Path,
    historico_layouts: tuple[str, ...] = (),
    referencias_aprovadas: tuple[ReferenciaVisual, ...] = (),
    provedor_direcao: Provedor | None = None,
    provedor_visao: Provedor | None = None,
    sinais_humanos: dict[str, list[dict[str, int | str]]] | None = None,
    referencia_preferida: ReferenciaVisual | None = None,
    familia_visual: FamiliaVisual | None = None,
    biblioteca_de_fotos: BibliotecaDeImagens | None = None,
    buscar_fotos: bool = False,
    provedor_fotos: Provedor | None = None,
) -> PacotePublicacao:
    pasta_do_pacote.mkdir(parents=True, exist_ok=True)
    # Uma remontagem só volta a oferecer um manifesto depois de concluir todos os arquivos.
    (pasta_do_pacote / NOME_DO_REGISTRO).unlink(missing_ok=True)

    fotos: dict[int, FotoDoSlide] = {}
    imagens: list[ImagemSlide] = []
    folha: Path | None = None
    conferencia = ConferenciaVisual()
    direcao_de_arte = None
    video: Path | None = None

    familia = FamiliaVisual.SUNO_ESCURO
    if celula.formato is Formato.CARROSSEL:
        slides = celula.conteudo.slides or []
        # As famílias visuais só existem no motor de navegador; a reserva Pillow segue com o
        # layout escuro de sempre e não usa foto.
        com_familias = motor_de_render() == "puppeteer"
        if com_familias:
            fotos = resolver_fotos(
                slides,
                biblioteca_de_fotos,
                permitir_rede=buscar_fotos,
                # O juiz das fotos é um só para a dúvida; o Eval visual da folha continua opcional.
                provedor_visao=provedor_fotos or provedor_visao,
            )
        # O plano só enxerga a foto que de fato existe: sem ela, evita layout de foto.
        slides_do_plano = [
            slide if indice in fotos else slide.model_copy(update={"imagem": None})
            for indice, slide in enumerate(slides)
        ]
        if com_familias:
            familia = familia_visual or escolher_familia(
                slides_do_plano, historico_layouts, referencia_preferida
            )
        sem_layout = sorted(
            {s.tipo.value for s in slides_do_plano if not composicoes_compativeis(s, familia)}
        )
        if sem_layout:
            raise ValueError(
                f"a família {familia.value} não tem layout para os papéis: {', '.join(sem_layout)}"
            )
        # Foto achada vai para um slide cujo layout comporte foto; sem lugar, é descartada (e o
        # crédito some da legenda). Slide sem foto recebe um layout que não precisa dela.
        acomodadas = acomodar_fotos(
            slides,
            fotos,
            familia,
            lambda lista: planejar_com_diretor_de_arte(
                lista,
                referencias_aprovadas,
                historico_layouts,
                provedor=provedor_direcao,
                sinais_humanos=sinais_humanos,
                referencia_preferida=referencia_preferida,
                familia=familia,
            ),
        )
        for origem, destino in acomodadas.movidas:
            _REGISTRO.info("foto do slide %d realocada para o slide %d", origem + 1, destino + 1)
        for origem in acomodadas.descartadas:
            _REGISTRO.info("foto do slide %d não coube em nenhum layout: slide sem foto", origem + 1)
        fotos = acomodadas.fotos
        resultado_direcao = acomodadas.plano
        imagens = renderizar_carrossel(
            celula,
            execucao.ancoras,
            pasta_do_pacote,
            historico_layouts=historico_layouts,
            referencias_aprovadas=referencias_aprovadas,
            plano_direcao=tuple(resultado_direcao.escolhas),
            fotos={indice: foto.caminho for indice, foto in fotos.items()},
            paleta=execucao.paleta_visual if com_familias else None,
        )
        folha = folha_de_contato(imagens, pasta_do_pacote / NOME_DA_FOLHA)
        conferencia = conferir_imagens(imagens, execucao.ancoras)
        if provedor_visao is not None:
            try:
                conferencia = conferencia.model_copy(
                    update={
                        "juiz_visao": julgar_folha_de_contato(folha, provedor_visao),
                        "mensagem_juiz_visao": None,
                    }
                )
            except Exception as erro:  # noqa: BLE001 - o Eval opcional nunca bloqueia o Pacote
                _REGISTRO.warning("Eval visual indisponível: %s", erro)
                conferencia = conferencia.model_copy(
                    update={
                        "mensagem_juiz_visao": (
                            "Eval visual indisponível; a revisão humana continua obrigatória."
                        )
                    }
                )
        direcao_de_arte = resumir_direcao_renderizada(
            [Path(imagem.caminho).with_suffix(".json") for imagem in imagens],
            historico_layouts,
            origem_do_plano=resultado_direcao.origem,
            provedor=resultado_direcao.provedor,
            motivo_fallback=resultado_direcao.motivo_fallback,
            familia=familia if com_familias else None,
        )
    elif celula.formato is Formato.TEXTO_ANALITICO:
        (pasta_do_pacote / NOME_DO_TEXTO).write_text(celula.conteudo.texto or "", encoding="utf-8")
    else:
        if celula.conteudo.blocos:
            # O plano de edição (JSON para avatar + tabela legível) acompanha o Pacote: é o que
            # um humano cola num gerador de vídeo se não usar o mp4 local.
            direcao = direcao_em_disco(pasta_do_pacote, celula.conteudo, celula.audiencia, None)
            plano = montar_plano(celula.conteudo, celula.audiencia, direcao)
            (pasta_do_pacote / NOME_DO_PLANO).write_text(
                json.dumps(plano, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (pasta_do_pacote / NOME_DO_PLANO_LEGIVEL).write_text(
                plano_em_markdown(plano), encoding="utf-8"
            )
        video = _video_ja_renderizado(pasta_do_pacote, pasta_da_execucao, celula.audiencia, execucao)
        if video is not None:
            conferencia = ConferenciaVisual(
                medicoes=_medir_video_se_disponivel(video, celula.conteudo.duracao_alvo_s)
            )

    creditos = bloco_de_creditos([foto.imagem for foto in fotos.values()])
    legenda, hashtags = montar_legenda(celula, execucao.ancoras, creditos)
    (pasta_do_pacote / NOME_DA_LEGENDA).write_text(
        f"{legenda}\n\n{' '.join(hashtags)}\n", encoding="utf-8"
    )
    pacote = PacotePublicacao(
        execucao=execucao.identificador,
        assinatura_conteudo=execucao.assinatura_da_celula(celula.audiencia, celula.formato),
        audiencia=celula.audiencia,
        formato=celula.formato,
        legenda=legenda,
        hashtags=hashtags,
        imagens=imagens,
        fotos=[
            FotoDoPacote(
                indice=indice,
                arquivo=foto.caminho.name,
                assunto=foto.imagem.consulta,
                autor=foto.imagem.autor,
                licenca=foto.imagem.licenca,
                url_origem=foto.imagem.url_origem,
                credito=foto.credito(),
            )
            for indice, foto in sorted(fotos.items())
        ],
        folha_de_contato=folha,
        video=video,
        conferencia=conferencia,
        direcao_de_arte=direcao_de_arte,
    )
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=pasta_do_pacote,
                                     suffix=".tmp", delete=False) as aberto:
        temporario = Path(aberto.name)
        aberto.write(pacote.model_dump_json(indent=2))
    try:
        os.replace(temporario, pasta_do_pacote / NOME_DO_REGISTRO)
    finally:
        temporario.unlink(missing_ok=True)
    return pacote


def montar_pacote(
    identificador_execucao: str,
    pasta_execucoes: Path,
    *,
    alvo: tuple[Audiencia, Formato] | None = None,
    provedor_direcao: Provedor | None = None,
    provedor_visao: Provedor | None = None,
    familia_visual: FamiliaVisual | None = None,
    biblioteca_de_fotos: BibliotecaDeImagens | None = None,
    buscar_fotos: bool = False,
    provedor_fotos: Provedor | None = None,
) -> list[PacotePublicacao]:
    """Um Pacote por Célula aprovada, em ``<pasta_execucoes>/<id>/pacote/<audiencia>-<formato>/``.

    Célula reprovada nunca ganha Pacote: o que o Avaliador recusou não chega ao humano como
    pronto para publicar. Defeito de render achado pela conferência **não** tira o Pacote da
    lista — quem decide com essa lista na mão é o H5 (ADR 0014).
    """
    execucao = _ler_execucao(identificador_execucao, pasta_execucoes)
    pasta_da_execucao = pasta_execucoes / identificador_execucao
    raiz = pasta_da_execucao / NOME_DA_PASTA
    repositorio = RepositorioHistoricoLayouts(Path(pasta_execucoes) / NOME_DO_BANCO)
    repositorio_feedback = RepositorioFeedbackVisual(Path(pasta_execucoes) / NOME_DO_BANCO)
    referencias = tuple(
        RepositorioReferenciasVisuais(Path(pasta_execucoes) / NOME_DO_BANCO).listar(
            apenas_aprovadas=True
        )
    )
    referencia_preferida = None
    if execucao.referencia_visual is not None:
        referencia_preferida = next(
            (
                referencia
                for referencia in referencias
                if referencia.identificador == execucao.referencia_visual
            ),
            None,
        )
        if referencia_preferida is None:
            raise ValueError(
                "a referência visual escolhida na curadoria não está mais aprovada"
            )
        if referencia_preferida.composicao is not execucao.composicao_visual:
            raise ValueError(
                "a referência visual escolhida não pertence à composição da Saída"
            )
    if execucao.provedor_gerador == "falso":
        # A Demo não descobre serviços do ambiente nem busca fotos na rede.
        # Provedores explicitamente injetados continuam disponíveis nos testes.
        buscar_fotos = False
    if provedor_direcao is None and execucao.provedor_gerador != "falso":
        try:
            from suno.provedores.roteador import provedor_por_nome, roteador_para

            provedor_direcao = (
                roteador_para(PapelLLM.DIRETOR_ARTE)
                if execucao.provedor_gerador in {"falso", "roteador"}
                else provedor_por_nome(execucao.provedor_gerador)
            )
        except ErroProvedor as erro:
            _REGISTRO.warning("Diretor de Arte IA indisponível; usando regras: %s", erro)
    if provedor_visao is None and execucao.provedor_gerador != "falso":
        try:
            from suno.provedores.roteador import roteador_para

            provedor_visao = roteador_para(PapelLLM.JUIZ_VISAO)
        except ErroProvedor as erro:
            _REGISTRO.warning("Eval visual indisponível; revisão humana permanece: %s", erro)
    pacotes: list[PacotePublicacao] = []
    aprovadas: set[str] = set()
    historico_layouts: list[str] = [
        layout.value
        for layout in repositorio.recentes(excluir_execucao=identificador_execucao)
    ]
    usos_da_execucao: list[UsoDeLayout] = []
    sinais_humanos = repositorio_feedback.resumo_para_diretor(
        excluir_execucao=identificador_execucao
    )
    historicos = (
        execucao.celulas
        if alvo is None
        else [
            historico
            for historico in execucao.celulas
            if (historico.audiencia, historico.formato) == alvo
        ]
    )
    for historico in historicos:
        if not execucao.celula_liberada(historico.audiencia, historico.formato):
            continue
        celula = historico.celula_final
        if celula is None:
            continue
        nome = f"{historico.audiencia.value}-{historico.formato.value}"
        aprovadas.add(nome)
        pacote = _montar_uma(
            execucao,
            celula,
            raiz / nome,
            pasta_da_execucao,
            historico_layouts=tuple(historico_layouts),
            referencias_aprovadas=referencias,
            provedor_direcao=provedor_direcao,
            provedor_visao=provedor_visao,
            sinais_humanos=sinais_humanos,
            referencia_preferida=referencia_preferida,
            familia_visual=familia_visual,
            biblioteca_de_fotos=biblioteca_de_fotos,
            buscar_fotos=buscar_fotos,
            provedor_fotos=provedor_fotos,
        )
        pacotes.append(pacote)
        if pacote.direcao_de_arte is not None:
            usos = usos_do_plano(historico.audiencia.value, pacote.direcao_de_arte)
            usos_da_execucao.extend(usos)
            historico_layouts.extend(uso.composicao.value for uso in usos)
    if alvo is None:
        repositorio.substituir_execucao(identificador_execucao, usos_da_execucao)
        _remover_pacotes_obsoletos(raiz, aprovadas)
    elif alvo[1] is Formato.CARROSSEL:
        repositorio.substituir_audiencia(
            identificador_execucao, alvo[0].value, usos_da_execucao
        )
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
