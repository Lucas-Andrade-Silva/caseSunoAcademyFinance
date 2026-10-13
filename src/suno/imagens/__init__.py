"""Fotos reais para os slides: biblioteca local aprovada, Wikimedia Commons como fonte única.

Só licença que permite reuso (CC0, domínio público, CC BY, CC BY-SA), crédito sempre
registrado e relevância verificada. A rede só é usada fora da demo (``permitir_rede``).
"""

from suno.imagens.biblioteca import BibliotecaDeImagens, EntradaDaImagem, ImagemInexistente
from suno.imagens.commons import CandidatoDeImagem, ClienteCommons, FonteDeImagemIndisponivel
from suno.imagens.creditos import bloco_de_creditos
from suno.imagens.modelos import ImagemResolvida, ParecerImagem
from suno.imagens.resolvedor import resolver_imagem
from suno.imagens.validacao import validar_relevancia

__all__ = [
    "BibliotecaDeImagens",
    "CandidatoDeImagem",
    "ClienteCommons",
    "EntradaDaImagem",
    "FonteDeImagemIndisponivel",
    "ImagemInexistente",
    "ImagemResolvida",
    "ParecerImagem",
    "bloco_de_creditos",
    "resolver_imagem",
    "validar_relevancia",
]
