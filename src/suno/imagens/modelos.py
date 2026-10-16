"""Os tipos do pacote de imagens: a foto resolvida e o parecer de relevância."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Origem = Literal["biblioteca", "web"]
Validacao = Literal["humano", "visao", "texto"]

_SEM_CREDITO = re.compile(r"^(CC0|Public domain|PD)\b", re.IGNORECASE)


class ImagemResolvida(BaseModel):
    """Uma foto real, com o crédito que a acompanha (a licença só é conhecida nas fotos semeadas)."""

    model_config = ConfigDict(frozen=True)

    arquivo: Path
    titulo: str
    autor: str
    licenca: str = Field(description="Nome curto da licença, como 'CC BY 2.0', ou 'licença não verificada (MVP)'.")
    url_origem: str = Field(description="A página onde a imagem foi encontrada.")
    consulta: str = Field(description="O assunto que a pessoa (ou o slide) pediu.")
    origem: Origem
    validada_por: Validacao | None = None
    largura: int = 0
    altura: int = 0

    def credito_obrigatorio(self) -> bool:
        """Domínio público e CC0 dispensam crédito; o resto o exige."""
        return not _SEM_CREDITO.match(self.licenca.strip())

    def credito(self) -> str:
        """``Foto: <autor> / <licença> / <url>``. Sai sempre, mesmo quando a licença não exige."""
        return f"Foto: {self.autor} / {self.licenca} / {self.url_origem}"


class ParecerImagem(BaseModel):
    """O que o juiz de visão disse da foto para o assunto do slide."""

    relevante: bool = Field(description="A foto mostra, ou ilustra sem ambiguidade, o assunto pedido.")
    motivo: str = Field(default="", description="Uma frase curta explicando a decisão.")
    inadequada: bool = Field(
        default=False,
        description="Imagem sensível, violenta ou com pessoa privada reconhecível.",
    )

    @property
    def aprovada(self) -> bool:
        return self.relevante and not self.inadequada
