"""Cliente do Wikimedia Commons: a única fonte de fotos da internet do projeto.

Só entra foto com licença que permite reuso comercial e adaptação: CC0, domínio público,
CC BY e CC BY-SA. NC, ND e qualquer outra são descartadas aqui, antes de a imagem existir
para o resto do sistema. Roda antes da demo, nunca durante (CLAUDE.md): quem chama decide
se ``permitir_rede``. Sem chave e sem login; o User-Agent identifica o projeto.
"""

from __future__ import annotations

import html
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

URL_DA_API = "https://commons.wikimedia.org/w/api.php"
LARGURA_MINIMA = 900
LARGURA_DA_MINIATURA = 1200
LIMITE_PADRAO = 12
TIMEOUT_S = 30.0
CONTATO_PADRAO = "SunoContentCase/0.1 (projeto academico; contato: lucas.silva@estimulo.org)"
MIMES_ACEITOS = frozenset({"image/jpeg", "image/png", "image/webp"})

_LICENCA_LIVRE = re.compile(
    r"""^(
        CC0(\s+1\.0)?
      | Public\s+domain
      | PD(-[\w.-]+)?
      | CC\s+BY(-SA)?\s+\d(\.\d)?(\s+[A-Za-z]{2,4})?
    )$""",
    re.IGNORECASE | re.VERBOSE,
)
_BLOCOS_SEM_TEXTO = re.compile(r"<(style|script)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")
_RESTO_DE_MODELO_DA_WIKI = re.compile(r"\s*(\.mw-parser-output|Wikidata has entry).*$", re.DOTALL)
_ESPACOS = re.compile(r"\s+")
_AUTOR_DESCONHECIDO = re.compile(r"^unknown( author)?$", re.IGNORECASE)
AUTOR_NAO_INFORMADO = "Autor desconhecido"
_TAMANHO_MAXIMO_DO_AUTOR = 120


class FonteDeImagemIndisponivel(Exception):
    """O Commons não respondeu, respondeu erro ou devolveu algo que não é a API. Nunca é fatal."""


class CandidatoDeImagem(BaseModel):
    """Uma foto do Commons que passou nos filtros de licença e tamanho."""

    model_config = ConfigDict(frozen=True)

    titulo: str
    autor: str
    licenca: str
    url_pagina: str
    url_miniatura: str
    largura: int
    altura: int
    consulta: str


def licenca_permitida(licenca: str) -> bool:
    """CC0, domínio público, CC BY x.y ou CC BY-SA x.y. NC, ND e o resto são recusados."""
    return bool(_LICENCA_LIVRE.match(licenca.strip()))


def limpar_autor(bruto: str) -> str:
    """O campo ``Artist`` do Commons vem em HTML (às vezes com ``<style>``): devolve só o nome."""
    sem_blocos = _BLOCOS_SEM_TEXTO.sub(" ", html.unescape(bruto))
    texto = _ESPACOS.sub(" ", _TAGS.sub(" ", html.unescape(sem_blocos))).strip()
    texto = _RESTO_DE_MODELO_DA_WIKI.sub("", texto)  # CSS e avisos de modelo que escapam das tags
    metade = len(texto) // 2
    meio = texto.find(" ", metade - 1)
    if metade and len(texto) % 2 == 0 and texto[:metade] == texto[metade:]:
        texto = texto[:metade]  # dois <span> com o mesmo nome, colados
    elif meio > 0 and texto[:meio] == texto[meio + 1 :]:
        texto = texto[:meio]  # ...ou separados por espaço
    if not texto or _AUTOR_DESCONHECIDO.match(texto):
        return AUTOR_NAO_INFORMADO
    return texto[:_TAMANHO_MAXIMO_DO_AUTOR].strip()


def agente_de_usuario() -> str:
    """``SUNO_CONTATO`` se trouxer e-mail ou URL; a política da Wikimedia recusa (403) UA sem contato."""
    contato = os.environ.get("SUNO_CONTATO", "")
    return contato if ("@" in contato or "http" in contato) else CONTATO_PADRAO


def cliente_padrao() -> httpx.Client:
    """O ``httpx.Client`` de produção. Os testes injetam um com ``MockTransport``."""
    return httpx.Client(headers={"User-Agent": agente_de_usuario()}, timeout=TIMEOUT_S, follow_redirects=True)


class ClienteCommons:
    """Busca e baixa fotos livres. Todo erro de rede ou de formato vira ``FonteDeImagemIndisponivel``."""

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        *,
        url_da_api: str = URL_DA_API,
        largura_minima: int = LARGURA_MINIMA,
        largura_da_miniatura: int = LARGURA_DA_MINIATURA,
    ) -> None:
        self._cliente = cliente
        self.url_da_api = url_da_api
        self.largura_minima = largura_minima
        self.largura_da_miniatura = largura_da_miniatura

    def _com_cliente(self) -> tuple[httpx.Client, bool]:
        if self._cliente is not None:
            return self._cliente, False
        return cliente_padrao(), True

    def buscar(self, consulta: str, *, limite: int = LIMITE_PADRAO) -> list[CandidatoDeImagem]:
        """Candidatos com licença livre e largura mínima, na ordem de relevância do Commons."""
        parametros: dict[str, Any] = {
            "action": "query",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrlimit": limite,
            "gsrsearch": f"{consulta} filetype:bitmap",
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": self.largura_da_miniatura,
            "format": "json",
            "formatversion": 2,
        }
        dados = self._obter_json(parametros)
        paginas = dados.get("query", {}).get("pages", [])
        if isinstance(paginas, dict):  # formatversion 1: dicionário por id
            paginas = list(paginas.values())
        paginas = sorted((p for p in paginas if isinstance(p, dict)), key=lambda p: p.get("index", 0))
        candidatos: list[CandidatoDeImagem] = []
        for pagina in paginas:
            candidato = self._candidato(pagina, consulta)
            if candidato is not None:
                candidatos.append(candidato)
        return candidatos

    def baixar_miniatura(self, candidato: CandidatoDeImagem) -> bytes:
        """Os bytes da miniatura (largura 1200 por padrão)."""
        cliente, fechar = self._com_cliente()
        try:
            resposta = cliente.get(candidato.url_miniatura)
            resposta.raise_for_status()
            conteudo = resposta.content
        except httpx.HTTPError as erro:
            raise FonteDeImagemIndisponivel(f"falha ao baixar {candidato.url_miniatura}: {erro}") from erro
        finally:
            if fechar:
                cliente.close()
        if not conteudo:
            raise FonteDeImagemIndisponivel(f"resposta vazia ao baixar {candidato.url_miniatura}")
        return conteudo

    # -- interno ------------------------------------------------------------

    def _obter_json(self, parametros: dict[str, Any]) -> dict[str, Any]:
        cliente, fechar = self._com_cliente()
        try:
            resposta = cliente.get(self.url_da_api, params=parametros)
            resposta.raise_for_status()
            dados = resposta.json()
        except httpx.HTTPError as erro:
            raise FonteDeImagemIndisponivel(f"Commons indisponível: {erro}") from erro
        except ValueError as erro:
            raise FonteDeImagemIndisponivel(f"Commons devolveu algo que não é JSON: {erro}") from erro
        finally:
            if fechar:
                cliente.close()
        if not isinstance(dados, dict):
            raise FonteDeImagemIndisponivel("Commons devolveu JSON fora do formato esperado")
        if "error" in dados:
            informacao = dados["error"].get("info", "") if isinstance(dados["error"], dict) else dados["error"]
            raise FonteDeImagemIndisponivel(f"a API do Commons recusou o pedido: {informacao}")
        return dados

    def _candidato(self, pagina: dict[str, Any], consulta: str) -> CandidatoDeImagem | None:
        informacoes = pagina.get("imageinfo") or []
        if not informacoes or not isinstance(informacoes[0], dict):
            return None
        info = informacoes[0]
        meta = info.get("extmetadata") or {}
        licenca = _valor(meta, "LicenseShortName")
        if not licenca_permitida(licenca):
            return None
        if _valor(meta, "NonFree").lower() == "true" or _valor(meta, "Restrictions"):
            return None  # uso não livre, ou restrição (marca, direito de personalidade)
        mime = str(info.get("mime", ""))
        if mime and mime not in MIMES_ACEITOS:
            return None
        largura, altura = int(info.get("width") or 0), int(info.get("height") or 0)
        miniatura, pagina_url = info.get("thumburl"), info.get("descriptionurl")
        if largura < self.largura_minima or not miniatura or not pagina_url:
            return None
        titulo = str(pagina.get("title", "")).removeprefix("File:")
        return CandidatoDeImagem(
            titulo=titulo,
            autor=limpar_autor(_valor(meta, "Artist")),
            licenca=licenca,
            url_pagina=pagina_url,
            url_miniatura=miniatura,
            largura=largura,
            altura=altura,
            consulta=consulta,
        )


def _valor(meta: dict[str, Any], chave: str) -> str:
    campo = meta.get(chave) or {}
    return str(campo.get("value", "")).strip() if isinstance(campo, dict) else ""
