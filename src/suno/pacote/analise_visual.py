"""Upload seguro e análise multimodal estrutural de uma referência autorizada."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from suno.dominio import (
    AnaliseVisualReferencia,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    ReferenciaVisual,
)
from suno.provedores.base import Provedor

LIMITE_DA_IMAGEM = 10 * 1024 * 1024
MAXIMO_DE_PIXELS = 24_000_000
MAXIMO_DO_LADO = 1600


class ImagemReferenciaInvalida(ValueError):
    pass


def normalizar_imagem(conteudo: bytes, destino: Path) -> Path:
    """Valida, remove metadados e grava PNG limitado, sem preservar o arquivo remoto bruto."""
    if not conteudo:
        raise ImagemReferenciaInvalida("a imagem está vazia")
    if len(conteudo) > LIMITE_DA_IMAGEM:
        raise ImagemReferenciaInvalida("a imagem passa de 10 MB")
    try:
        with Image.open(io.BytesIO(conteudo)) as aberta:
            if aberta.width * aberta.height > MAXIMO_DE_PIXELS:
                raise ImagemReferenciaInvalida("a imagem tem pixels demais")
            imagem = ImageOps.exif_transpose(aberta).convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ImagemReferenciaInvalida("o arquivo não é uma imagem PNG, JPEG ou WebP válida") from None
    imagem.thumbnail((MAXIMO_DO_LADO, MAXIMO_DO_LADO), Image.Resampling.LANCZOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    imagem.save(temporario, format="PNG", optimize=True)
    temporario.replace(destino)
    return destino


def analisar_referencia_visual(
    caminho: Path,
    referencia: ReferenciaVisual,
    provedor: Provedor,
) -> AnaliseVisualReferencia:
    pedido = PedidoLLM(
        papel=PapelLLM.ANALISTA_VISUAL,
        rotulo=f"analise_visual:{referencia.identificador}",
        mensagens=[
            Mensagem(
                autor="sistema",
                texto=(
                    "Você analisa uma referência autorizada de design financeiro. Extraia apenas "
                    "padrões estruturais reutilizáveis: composição, hierarquia, densidade, imagem, "
                    "fundo, elementos e ordem do conteúdo. Não transcreva marcas, não copie texto, "
                    "não recomende ativos e não invente números. Use termos curtos em snake_case e "
                    "responda somente no schema solicitado."
                ),
            ),
            Mensagem(
                autor="usuario",
                texto=(
                    f"Tema informado: {referencia.tema}. Composição inicialmente associada: "
                    f"{referencia.composicao.value}. Analise a imagem para revisão humana."
                ),
                imagem_png=caminho.read_bytes(),
            ),
        ],
        max_tokens=900,
        temperatura=0.0,
        esforco_raciocinio="baixo",
    )
    return provedor.completar_estruturado(pedido, AnaliseVisualReferencia)


__all__ = [
    "ImagemReferenciaInvalida",
    "LIMITE_DA_IMAGEM",
    "analisar_referencia_visual",
    "normalizar_imagem",
]
