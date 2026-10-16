"""Resolve o assunto de um slide em uma foto real, com crédito.

Ordem: (a) biblioteca local, só entrada aprovada; (b) com ``permitir_rede``, busca de imagens na
web (ADR 0032), com consultas próprias do mercado financeiro (ADR 0033); (c) nada.

Na web, o texto do resultado decide primeiro (``consulta.pontuar``): quem cita o assunto no nome
do arquivo, no título e na página é aprovado direto, sem LLM; quem cai em palavra proibida
(a vitamina B3) é descartado sem baixar. Só o resto, a dúvida, vai ao juiz de visão, e no máximo
``MAXIMO_DE_DUVIDAS`` vezes por assunto. Foto que ninguém conferiu fica gravada como pendente e
NÃO é devolvida: o slide só recebe imagem aprovada. Sem rede e sem acerto na biblioteca devolve
``None`` e nunca levanta.
"""

from __future__ import annotations

import io
import logging
import time
from typing import TYPE_CHECKING

import httpx
from PIL import Image, UnidentifiedImageError

from suno.dominio import ErroProvedor
from suno.imagens.biblioteca import BibliotecaDeImagens, EntradaDaImagem, identificador_de
from suno.imagens.consulta import PlanoDeBusca, Triagem, cita_assunto, planejar, pontuar
from suno.imagens.modelos import ImagemResolvida, Validacao
from suno.imagens.validacao import ImagemIlegivel, validar_relevancia
from suno.imagens.web import CandidatoDeImagem, ClienteWeb, FonteDeImagemIndisponivel, buscador_padrao

if TYPE_CHECKING:  # pragma: no cover - só para o verificador de tipos
    from suno.provedores import Provedor

_REGISTRO = logging.getLogger(__name__)

MAXIMO_DE_DUVIDAS = 3
PONTOS_MINIMOS_PARA_DUVIDA = 1  # sem nenhum indício no texto é lixo do buscador: nem gasta o juiz
LARGURA_MINIMA_PX = 800  # o slide tem 1080 de largura; abaixo disso a foto estoura em pixels
PROPORCAO_MINIMA = 0.4  # largura / altura: mais estreita que isso é banner vertical
PROPORCAO_MAXIMA = 2.5  # ...e mais larga que isso é banner horizontal
PAUSA_ENTRE_CONSULTAS_S = 1.0
_EXTENSAO_POR_FORMATO = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def resolver_imagem(
    consulta: str,
    biblioteca: BibliotecaDeImagens,
    *,
    contexto: str = "",
    permitir_rede: bool = False,
    cliente: httpx.Client | None = None,
    provedor_visao: Provedor | None = None,
    maximo_de_duvidas: int = MAXIMO_DE_DUVIDAS,
) -> ImagemResolvida | None:
    """A melhor foto aprovada para ``consulta``, ou ``None``.

    ``cliente`` é um ``httpx.Client`` injetável (os testes usam ``MockTransport``).
    ``provedor_visao`` só é chamado nos resultados que o texto não resolve; sem ele, a foto em
    dúvida é baixada e fica pendente de aprovação humana (``imagens aprovar <id>``).
    """
    plano = planejar(consulta)
    da_biblioteca = _da_biblioteca(consulta, plano, biblioteca)
    if da_biblioteca is not None:
        return da_biblioteca
    if not permitir_rede:
        return None
    return _buscar_na_web(
        plano,
        biblioteca,
        contexto=contexto,
        cliente=cliente,
        provedor_visao=provedor_visao,
        maximo_de_duvidas=maximo_de_duvidas,
    )


def _da_biblioteca(consulta: str, plano: PlanoDeBusca, biblioteca: BibliotecaDeImagens) -> ImagemResolvida | None:
    """A melhor foto aprovada da biblioteca que de fato cita o assunto.

    A busca da biblioteca casa por qualquer termo em comum, e uma foto do Banco Central voltava
    para "Federal Reserve" só por causa de "federal". O assunto do catálogo é quem confirma.
    """
    entradas = {e.arquivo: e for e in biblioteca.listar()}
    for imagem in biblioteca.buscar(consulta):
        entrada = entradas.get(imagem.arquivo.name)
        if entrada is not None and cita_assunto(" ".join(entrada.tags), plano):
            return imagem
    return None


def _buscar_na_web(
    plano: PlanoDeBusca,
    biblioteca: BibliotecaDeImagens,
    *,
    contexto: str,
    cliente: httpx.Client | None,
    provedor_visao: Provedor | None,
    maximo_de_duvidas: int,
) -> ImagemResolvida | None:
    web = buscador_padrao(cliente)
    vistos: set[str] = set()
    duvidas: list[tuple[Triagem, CandidatoDeImagem]] = []

    for posicao, consulta_web in enumerate(plano.consultas):
        if posicao:
            time.sleep(PAUSA_ENTRE_CONSULTAS_S)
        try:
            candidatos = web.buscar(consulta_web)
        except FonteDeImagemIndisponivel as erro:
            _REGISTRO.warning("busca de imagens indisponível para %r: %s", consulta_web, erro)
            continue
        triados: list[tuple[Triagem, CandidatoDeImagem]] = []
        for candidato in candidatos:
            if candidato.url_imagem not in vistos:
                vistos.add(candidato.url_imagem)
                triados.append((pontuar(candidato, plano), candidato))
        aprovaveis = sorted((a for a in triados if a[0].decisao == "aprovar"), key=lambda a: -a[0].pontos)
        for triagem, candidato in aprovaveis:
            achada = _aprovar_pelo_texto(candidato, triagem, plano.assunto, biblioteca, web)
            if achada is not None:
                return achada
        duvidas += [a for a in triados if a[0].decisao == "duvida" and a[0].pontos >= PONTOS_MINIMOS_PARA_DUVIDA]

    duvidas.sort(key=lambda a: -a[0].pontos)  # estável: empate mantém a ordem do buscador
    return _julgar_duvidas(duvidas, plano.assunto, contexto, biblioteca, web, provedor_visao, maximo_de_duvidas)


def _aprovar_pelo_texto(
    candidato: CandidatoDeImagem,
    triagem: Triagem,
    assunto: str,
    biblioteca: BibliotecaDeImagens,
    web: ClienteWeb,
) -> ImagemResolvida | None:
    conhecida = biblioteca.conhece_url(candidato.url_pagina)
    if conhecida is not None:
        if conhecida.rejeitada or not conhecida.aprovada:
            return None  # recusada, ou pendente: só um humano ou a visão resolvem
        entrada = biblioteca.acrescentar_tags(conhecida.id, [assunto])
        return biblioteca.resolvida(entrada, assunto)
    try:
        conteudo = web.baixar(candidato)
        extensao = _conferir_imagem(conteudo)
    except (FonteDeImagemIndisponivel, ImagemIlegivel) as erro:
        _REGISTRO.warning("candidato %s descartado: %s", candidato.titulo, erro)
        return None
    _REGISTRO.info("foto %r aprovada pelo texto (%d pontos: %s)", candidato.titulo, triagem.pontos, triagem.motivo)
    entrada = _gravar(biblioteca, candidato, conteudo, extensao, assunto, aprovada=True, validada_por="texto")
    return biblioteca.resolvida(entrada, assunto, origem="web")


def _julgar_duvidas(
    duvidas: list[tuple[Triagem, CandidatoDeImagem]],
    assunto: str,
    contexto: str,
    biblioteca: BibliotecaDeImagens,
    web: ClienteWeb,
    provedor_visao: Provedor | None,
    maximo: int,
) -> ImagemResolvida | None:
    julgadas = 0
    for _, candidato in duvidas:
        if julgadas >= maximo:
            break
        conhecida = biblioteca.conhece_url(candidato.url_pagina)
        if conhecida is not None:
            if conhecida.rejeitada or provedor_visao is None:
                continue
            julgadas += 1
            achada = _reaproveitar(conhecida, assunto, contexto, biblioteca, provedor_visao)
            if achada is not None:
                return achada
            continue

        try:
            conteudo = web.baixar(candidato)
            extensao = _conferir_imagem(conteudo)
        except (FonteDeImagemIndisponivel, ImagemIlegivel) as erro:
            # Download que falha ou imagem pequena não gasta chamada de visão: não conta no limite.
            _REGISTRO.warning("candidato %s descartado: %s", candidato.titulo, erro)
            continue
        julgadas += 1

        if provedor_visao is None:
            _gravar(biblioteca, candidato, conteudo, extensao, assunto, aprovada=False)
            _REGISTRO.warning(
                "foto %r baixada e pendente de aprovação humana (sem provedor de visão)", candidato.titulo
            )
            return None

        try:
            parecer = validar_relevancia(conteudo, assunto, contexto, provedor_visao)
        except (ErroProvedor, ImagemIlegivel) as erro:
            _gravar(biblioteca, candidato, conteudo, extensao, assunto, aprovada=False)
            _REGISTRO.warning("juiz de visão falhou (%s): foto %r ficou pendente", erro, candidato.titulo)
            return None
        if not parecer.aprovada:
            _REGISTRO.info("foto %r reprovada pela visão: %s", candidato.titulo, parecer.motivo)
            continue
        entrada = _gravar(biblioteca, candidato, conteudo, extensao, assunto, aprovada=True, validada_por="visao")
        return biblioteca.resolvida(entrada, assunto, origem="web")
    return None


def _reaproveitar(
    entrada: EntradaDaImagem,
    consulta: str,
    contexto: str,
    biblioteca: BibliotecaDeImagens,
    provedor_visao: Provedor,
) -> ImagemResolvida | None:
    """Foto que já está no disco mas não casou com a consulta: a visão decide se serve a este assunto."""
    caminho = biblioteca.pasta / entrada.arquivo
    try:
        parecer = validar_relevancia(caminho.read_bytes(), consulta, contexto, provedor_visao)
    except (OSError, ErroProvedor, ImagemIlegivel) as erro:
        _REGISTRO.warning("não deu para reavaliar %s: %s", entrada.id, erro)
        return None
    if not parecer.aprovada:
        return None
    if not entrada.aprovada:
        entrada = biblioteca.aprovar(entrada.id, validada_por="visao")
    entrada = biblioteca.acrescentar_tags(entrada.id, [consulta])
    return biblioteca.resolvida(entrada, consulta)


def _gravar(
    biblioteca: BibliotecaDeImagens,
    candidato: CandidatoDeImagem,
    conteudo: bytes,
    extensao: str,
    consulta: str,
    *,
    aprovada: bool,
    validada_por: Validacao = "visao",
) -> EntradaDaImagem:
    base = identificador_de(candidato.titulo)
    existentes = {e.id for e in biblioteca.listar()}
    identificador, n = base, 2
    while identificador in existentes:
        identificador, n = f"{base}-{n}", n + 1
    return biblioteca.adicionar(
        conteudo,
        identificador=identificador,
        extensao=extensao,
        tags=[consulta],
        titulo=candidato.titulo,
        autor=candidato.autor,
        licenca=candidato.licenca,
        url_origem=candidato.url_pagina,
        aprovada=aprovada,
        validada_por=validada_por if aprovada else None,
        consulta=consulta,
    )


def _conferir_imagem(conteudo: bytes) -> str:
    """A extensão certa pelo formato real dos bytes, se o tamanho e a proporção servirem a um slide."""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            formato = imagem.format or ""
            largura, altura = imagem.size
    except (UnidentifiedImageError, OSError, ValueError) as erro:
        raise ImagemIlegivel(f"não é uma imagem legível: {erro}") from erro
    if formato not in _EXTENSAO_POR_FORMATO:
        raise ImagemIlegivel(f"formato {formato or 'desconhecido'} não aceito")
    if largura < LARGURA_MINIMA_PX:
        raise ImagemIlegivel(f"largura de {largura}px, abaixo do mínimo de {LARGURA_MINIMA_PX}px")
    if not PROPORCAO_MINIMA <= largura / max(altura, 1) <= PROPORCAO_MAXIMA:
        raise ImagemIlegivel(f"proporção {largura}x{altura} é de banner, não de foto de slide")
    return _EXTENSAO_POR_FORMATO[formato]
