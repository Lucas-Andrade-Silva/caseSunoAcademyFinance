"""Fotos reais para os slides: biblioteca local aprovada e busca de imagens na web (ADR 0032).

Crédito sempre registrado e relevância verificada por um juiz de visão. A licença NÃO é
verificada nas fotos da web: é decisão de MVP. A rede só é usada fora da demo (``permitir_rede``).
"""

from suno.imagens.biblioteca import BibliotecaDeImagens, EntradaDaImagem, ImagemInexistente
from suno.imagens.creditos import bloco_de_creditos
from suno.imagens.modelos import ImagemResolvida, ParecerImagem
from suno.imagens.resolvedor import resolver_imagem
from suno.imagens.validacao import validar_relevancia
from suno.imagens.web import CandidatoDeImagem, ClienteSerper, ClienteWeb, FonteDeImagemIndisponivel, buscador_padrao

__all__ = [
    "BibliotecaDeImagens",
    "CandidatoDeImagem",
    "ClienteSerper",
    "ClienteWeb",
    "EntradaDaImagem",
    "FonteDeImagemIndisponivel",
    "ImagemInexistente",
    "ImagemResolvida",
    "ParecerImagem",
    "bloco_de_creditos",
    "buscador_padrao",
    "resolver_imagem",
    "validar_relevancia",
]
