"""A biblioteca local de fotos: ``data/imagens/`` com um ``indice.json`` versionado.

A demo roda sem rede (CLAUDE.md), então tudo que veio da internet mora aqui, com autor,
licença e página de origem. Só entrada ``aprovada`` sai numa busca comum: foto que ninguém
(humano ou visão) conferiu fica no índice, mas não chega ao slide.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field

from suno.imagens.modelos import ImagemResolvida, Origem, Validacao
from suno.imagens.texto import sem_acento, termos

_REGISTRO = logging.getLogger(__name__)

NOME_DO_INDICE = "indice.json"
PASTA_PADRAO = Path("data/imagens")
PESO_DA_TAG = 2
PESO_DO_TITULO = 1


class ImagemInexistente(KeyError):
    """O id não está no índice."""


class EntradaDaImagem(BaseModel):
    """Uma linha do ``indice.json``."""

    id: str
    arquivo: str = Field(description="Nome do arquivo dentro da pasta da biblioteca.")
    tags: list[str] = Field(default_factory=list)
    titulo: str
    autor: str
    licenca: str
    url_origem: str
    aprovada: bool = False
    rejeitada: bool = Field(default=False, description="Recusada de propósito: não volta a ser candidata.")
    validada_por: Validacao | None = None
    consulta: str = ""
    largura: int = 0
    altura: int = 0


def identificador_de(texto: str) -> str:
    """Um id estável e legível a partir de um título ou apelido."""
    base = re.sub(r"[^a-z0-9]+", "-", sem_acento(texto)).strip("-")
    return base[:60].strip("-") or "imagem"


class BibliotecaDeImagens:
    """Lê e escreve ``<pasta>/indice.json``. Escrita atômica; seguro entre threads."""

    def __init__(self, pasta: Path | str = PASTA_PADRAO) -> None:
        self.pasta = Path(pasta)
        self._trava = threading.RLock()

    @property
    def caminho_do_indice(self) -> Path:
        return self.pasta / NOME_DO_INDICE

    # -- leitura ------------------------------------------------------------

    def listar(self) -> list[EntradaDaImagem]:
        with self._trava:
            return self._ler()

    def obter(self, identificador: str) -> EntradaDaImagem:
        for entrada in self.listar():
            if entrada.id == identificador:
                return entrada
        raise ImagemInexistente(identificador)

    def conhece_url(self, url_origem: str) -> EntradaDaImagem | None:
        """A entrada que já veio dessa página do Commons, em qualquer estado."""
        return next((e for e in self.listar() if e.url_origem == url_origem), None)

    def buscar(self, consulta: str, *, apenas_aprovadas: bool = True) -> list[ImagemResolvida]:
        """Fotos ordenadas pela sobreposição de termos entre a consulta e tags + título.

        Tag vale dois pontos e título um (termo que já é tag não pontua duas vezes). Empate
        mantém a ordem do índice. Sem nenhum termo em comum a foto não aparece, e foto
        rejeitada nunca aparece.
        """
        pedidos = set(termos(consulta))
        if not pedidos:
            return []
        pontuadas: list[tuple[int, int, EntradaDaImagem]] = []
        for posicao, entrada in enumerate(self.listar()):
            if entrada.rejeitada or (apenas_aprovadas and not entrada.aprovada):
                continue
            nas_tags = set(termos(" ".join(entrada.tags)))
            no_titulo = set(termos(entrada.titulo)) - nas_tags
            pontos = PESO_DA_TAG * len(pedidos & nas_tags) + PESO_DO_TITULO * len(pedidos & no_titulo)
            if pontos and self._arquivo_existe(entrada):
                pontuadas.append((pontos, posicao, entrada))
        pontuadas.sort(key=lambda item: (-item[0], item[1]))
        return [self.resolvida(entrada, consulta) for _, _, entrada in pontuadas]

    def resolvida(self, entrada: EntradaDaImagem, consulta: str, *, origem: Origem = "biblioteca") -> ImagemResolvida:
        """A entrada do índice como ``ImagemResolvida`` (largura e altura lidas se faltarem)."""
        caminho = self.pasta / entrada.arquivo
        largura, altura = entrada.largura, entrada.altura
        if not (largura and altura):
            largura, altura = _dimensoes(caminho)
        return ImagemResolvida(
            arquivo=caminho,
            titulo=entrada.titulo,
            autor=entrada.autor,
            licenca=entrada.licenca,
            url_origem=entrada.url_origem,
            consulta=consulta,
            origem=origem,
            validada_por=entrada.validada_por,
            largura=largura,
            altura=altura,
        )

    # -- escrita ------------------------------------------------------------

    def adicionar(
        self,
        conteudo: bytes,
        *,
        identificador: str,
        extensao: str = "jpg",
        tags: list[str],
        titulo: str,
        autor: str,
        licenca: str,
        url_origem: str,
        aprovada: bool = False,
        validada_por: Validacao | None = None,
        consulta: str = "",
    ) -> EntradaDaImagem:
        """Grava o arquivo e a linha do índice. Id repetido é erro: nada é sobrescrito em silêncio."""
        nome = f"{identificador}.{extensao.lstrip('.').lower()}"
        with self._trava:
            entradas = self._ler()
            if any(e.id == identificador for e in entradas):
                raise ValueError(f"já existe imagem com id {identificador!r} na biblioteca")
            destino = self.pasta / nome
            _gravar_atomico(destino, conteudo)
            largura, altura = _dimensoes(destino)
            entrada = EntradaDaImagem(
                id=identificador,
                arquivo=nome,
                tags=tags,
                titulo=titulo,
                autor=autor,
                licenca=licenca,
                url_origem=url_origem,
                aprovada=aprovada,
                validada_por=validada_por if aprovada else None,
                consulta=consulta,
                largura=largura,
                altura=altura,
            )
            entradas.append(entrada)
            self._gravar(entradas)
            return entrada

    def aprovar(self, identificador: str, *, validada_por: Validacao = "humano") -> EntradaDaImagem:
        """A foto passa a valer. Por padrão é decisão humana; o resolvedor usa ``visao``."""
        return self._alterar(identificador, aprovada=True, rejeitada=False, validada_por=validada_por)

    def rejeitar(self, identificador: str) -> EntradaDaImagem:
        """Decisão humana: a foto sai de circulação e não volta como candidata."""
        return self._alterar(identificador, aprovada=False, rejeitada=True, validada_por=None)

    def acrescentar_tags(self, identificador: str, tags: list[str]) -> EntradaDaImagem:
        """Soma tags novas (sem repetir): a foto passa a ser achada por mais um assunto."""
        atual = self.obter(identificador)
        novas = [t for t in tags if t not in atual.tags]
        return self._alterar(identificador, tags=[*atual.tags, *novas]) if novas else atual

    # -- interno ------------------------------------------------------------

    def _alterar(self, identificador: str, **campos: object) -> EntradaDaImagem:
        with self._trava:
            entradas = self._ler()
            for posicao, entrada in enumerate(entradas):
                if entrada.id == identificador:
                    entradas[posicao] = entrada.model_copy(update=campos)
                    self._gravar(entradas)
                    return entradas[posicao]
        raise ImagemInexistente(identificador)

    def _arquivo_existe(self, entrada: EntradaDaImagem) -> bool:
        existe = (self.pasta / entrada.arquivo).is_file()
        if not existe:
            _REGISTRO.warning("imagem %s está no índice mas o arquivo %s sumiu", entrada.id, entrada.arquivo)
        return existe

    def _ler(self) -> list[EntradaDaImagem]:
        caminho = self.caminho_do_indice
        if not caminho.is_file():
            return []
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
        return [EntradaDaImagem.model_validate(item) for item in bruto]

    def _gravar(self, entradas: list[EntradaDaImagem]) -> None:
        texto = json.dumps([e.model_dump(mode="json") for e in entradas], ensure_ascii=False, indent=2)
        _gravar_atomico(self.caminho_do_indice, (texto + "\n").encode("utf-8"))


def _gravar_atomico(destino: Path, conteudo: bytes) -> None:
    """Escreve num temporário ao lado e troca por ``os.replace``: ninguém lê arquivo pela metade."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(dir=destino.parent, prefix=f".{destino.name}.", suffix=".tmp")
    try:
        with os.fdopen(descritor, "wb") as arquivo:
            arquivo.write(conteudo)
        os.replace(temporario, destino)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


def _dimensoes(caminho: Path) -> tuple[int, int]:
    try:
        with Image.open(caminho) as imagem:
            return imagem.size
    except (OSError, ValueError):
        return 0, 0
