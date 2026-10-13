"""Verificação de relevância da foto por um juiz de visão (mesmo contrato de ``pacote.visual``).

A licença é checada em código (``commons.py``); aqui se checa o que código não vê: se a
foto de fato trata do assunto do slide e se não é imagem sensível ou de pessoa privada.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image, UnidentifiedImageError

from suno.dominio import Mensagem, PapelLLM, PedidoLLM
from suno.imagens.modelos import ParecerImagem

if TYPE_CHECKING:  # pragma: no cover - só para o verificador de tipos
    from suno.provedores import Provedor

LADO_MAXIMO_PX = 1024
ROTULO = "juiz-visao:imagem"

PAPEL_DO_JUIZ_DE_IMAGEM = (
    "Você confere se uma fotografia real, tirada da internet, serve para ilustrar um slide de"
    " Instagram sobre finanças. Ela serve quando mostra, ou evoca sem ambiguidade, o assunto"
    " pedido. Não serve quando é de outro assunto, de outro país quando o assunto é brasileiro,"
    " quando traz texto ou marca que contradiz o slide, ou quando é só decoração sem relação."
    " Marque 'inadequada' se a imagem for sensível, violenta, sexual ou mostrar uma pessoa"
    " privada reconhecível (figura pública em evento oficial é aceitável)."
    " Você NUNCA julga se o slide recomenda comprar ou vender: isso é checado em outro lugar."
)


class ImagemIlegivel(ValueError):
    """Os bytes não são uma imagem que o Pillow consiga abrir."""


def para_png(conteudo: bytes, *, lado_maximo: int = LADO_MAXIMO_PX) -> bytes:
    """Converte jpg/webp/png em PNG, reduzindo o maior lado para economizar tokens de visão."""
    try:
        with Image.open(io.BytesIO(conteudo)) as imagem:
            imagem.load()
            pronta = imagem.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as erro:
        raise ImagemIlegivel(f"não é uma imagem legível: {erro}") from erro
    pronta.thumbnail((lado_maximo, lado_maximo))
    saida = io.BytesIO()
    pronta.save(saida, format="PNG")
    return saida.getvalue()


def validar_relevancia(
    imagem: bytes,
    consulta: str,
    contexto: str,
    provedor: Provedor,
) -> ParecerImagem:
    """Uma chamada de visão: a foto (jpg ou png) ilustra a ``consulta`` no ``contexto`` do slide?

    Levanta ``ImagemIlegivel`` se os bytes não forem imagem e deixa subir o ``ErroProvedor``
    do provedor: quem chama decide que a foto fica pendente de aprovação humana.
    """
    pergunta = (
        f"Assunto pedido para a foto: {consulta!r}.\n"
        f"Contexto do slide: {contexto.strip() or '(sem contexto)'}\n"
        "Responda em JSON com 'relevante' (booleano: a foto ilustra o assunto), 'motivo' (uma"
        " frase) e 'inadequada' (booleano: sensível, violenta ou pessoa privada)."
    )
    pedido = PedidoLLM(
        papel=PapelLLM.JUIZ_VISAO,
        rotulo=ROTULO,
        mensagens=[
            Mensagem(autor="sistema", texto=PAPEL_DO_JUIZ_DE_IMAGEM),
            Mensagem(autor="usuario", texto=pergunta, imagem_png=para_png(imagem)),
        ],
        max_tokens=256,
        temperatura=0.0,
        esforco_raciocinio="baixo",
    )
    return provedor.completar_estruturado(pedido, ParecerImagem)
