"""Resolve o assunto de um slide em uma foto real, com licença e crédito.

Ordem: (a) biblioteca local, só entrada aprovada; (b) com ``permitir_rede``, Wikimedia Commons,
conferido por um juiz de visão; (c) nada. Foto que ninguém conferiu fica gravada como pendente
e NÃO é devolvida: o desenho é seguro por construção, o slide só recebe imagem aprovada.
Sem rede e sem acerto na biblioteca devolve ``None`` e nunca levanta.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import httpx
from PIL import Image, UnidentifiedImageError

from suno.dominio import ErroProvedor
from suno.imagens.biblioteca import BibliotecaDeImagens, EntradaDaImagem, identificador_de
from suno.imagens.commons import CandidatoDeImagem, ClienteCommons, FonteDeImagemIndisponivel
from suno.imagens.modelos import ImagemResolvida
from suno.imagens.validacao import ImagemIlegivel, validar_relevancia

if TYPE_CHECKING:  # pragma: no cover - só para o verificador de tipos
    from suno.provedores import Provedor

_REGISTRO = logging.getLogger(__name__)

MAXIMO_DE_CANDIDATOS = 5
_EXTENSAO_POR_FORMATO = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def resolver_imagem(
    consulta: str,
    biblioteca: BibliotecaDeImagens,
    *,
    contexto: str = "",
    permitir_rede: bool = False,
    cliente: httpx.Client | None = None,
    provedor_visao: Provedor | None = None,
    maximo_de_candidatos: int = MAXIMO_DE_CANDIDATOS,
) -> ImagemResolvida | None:
    """A melhor foto aprovada para ``consulta``, ou ``None``.

    ``cliente`` é um ``httpx.Client`` injetável (os testes usam ``MockTransport``).
    ``provedor_visao`` valida a relevância; sem ele, a foto baixada fica pendente de aprovação
    humana (``imagens aprovar <id>``) e a chamada devolve ``None``.
    """
    achadas = biblioteca.buscar(consulta)
    if achadas:
        return achadas[0]
    if not permitir_rede:
        return None
    return _buscar_no_commons(
        consulta,
        biblioteca,
        contexto=contexto,
        cliente=cliente,
        provedor_visao=provedor_visao,
        maximo=maximo_de_candidatos,
    )


def _buscar_no_commons(
    consulta: str,
    biblioteca: BibliotecaDeImagens,
    *,
    contexto: str,
    cliente: httpx.Client | None,
    provedor_visao: Provedor | None,
    maximo: int,
) -> ImagemResolvida | None:
    commons = ClienteCommons(cliente)
    try:
        candidatos = commons.buscar(consulta)
    except FonteDeImagemIndisponivel as erro:
        _REGISTRO.warning("Commons indisponível para %r: %s", consulta, erro)
        return None

    avaliadas = 0
    for candidato in candidatos:
        if avaliadas >= maximo:
            break
        conhecida = biblioteca.conhece_url(candidato.url_pagina)
        if conhecida is not None:
            if conhecida.rejeitada or provedor_visao is None:
                continue  # recusada, ou pendente que só um humano ou a visão aprova
            avaliadas += 1
            achada = _reaproveitar(conhecida, consulta, contexto, biblioteca, provedor_visao)
            if achada is not None:
                return achada
            continue

        avaliadas += 1
        try:
            conteudo = commons.baixar_miniatura(candidato)
            extensao = _extensao(conteudo)
        except (FonteDeImagemIndisponivel, ImagemIlegivel) as erro:
            _REGISTRO.warning("candidato %s descartado: %s", candidato.titulo, erro)
            continue

        if provedor_visao is None:
            _gravar(biblioteca, candidato, conteudo, extensao, consulta, aprovada=False)
            _REGISTRO.warning(
                "foto %r baixada e pendente de aprovação humana (sem provedor de visão)", candidato.titulo
            )
            return None

        try:
            parecer = validar_relevancia(conteudo, consulta, contexto, provedor_visao)
        except (ErroProvedor, ImagemIlegivel) as erro:
            _gravar(biblioteca, candidato, conteudo, extensao, consulta, aprovada=False)
            _REGISTRO.warning("juiz de visão falhou (%s): foto %r ficou pendente", erro, candidato.titulo)
            return None
        if not parecer.aprovada:
            _REGISTRO.info("foto %r reprovada pela visão: %s", candidato.titulo, parecer.motivo)
            continue
        entrada = _gravar(biblioteca, candidato, conteudo, extensao, consulta, aprovada=True)
        return biblioteca.resolvida(entrada, consulta, origem="commons")
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
) -> EntradaDaImagem:
    base = identificador_de(candidato.titulo.rsplit(".", 1)[0])
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
        validada_por="visao" if aprovada else None,
        consulta=consulta,
    )


def _extensao(conteudo: bytes) -> str:
    """A extensão certa pelo formato real dos bytes (o Commons serve webp com nome .jpg)."""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            formato = imagem.format or ""
    except (UnidentifiedImageError, OSError, ValueError) as erro:
        raise ImagemIlegivel(f"não é uma imagem legível: {erro}") from erro
    if formato not in _EXTENSAO_POR_FORMATO:
        raise ImagemIlegivel(f"formato {formato or 'desconhecido'} não aceito")
    return _EXTENSAO_POR_FORMATO[formato]
