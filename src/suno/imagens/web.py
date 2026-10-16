"""Clientes de busca de imagens na web: a fonte de fotos do MVP (ADR 0032, ADR 0033).

Duas fontes, a mesma interface (``buscar`` e ``baixar``):

- ``ClienteSerper``: resultados do Google Imagens pela API do Serper.dev, com chave gratuita em
  ``SERPER_API_KEY``. É a fonte confiável.
- ``ClienteWeb``: Bing Imagens por HTTP, sem chave. É a reserva. O Bing reconhece robô e serve
  resultados falsos (tintas para "Federal Reserve") em boa parte das consultas; o filtro de texto
  de ``consulta.pontuar`` segura quase tudo, mas a reserva rende pouco.

O próprio Google Imagens bloqueia navegador automatizado com CAPTCHA, e o projeto não contorna
CAPTCHA nem disfarça robô. Nenhuma licença é verificada: a decisão
é do projeto (MVP, fora de produção) e fica registrada em ``SEM_LICENCA``, que sai no crédito de
cada foto. Quem garante que a foto serve ao assunto é o juiz de visão, não este módulo.
Roda antes da demo, nunca durante (CLAUDE.md): quem chama decide se ``permitir_rede``.
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from urllib.parse import quote, urlparse

import httpx
from pydantic import BaseModel, ConfigDict

URL_DA_BUSCA = "https://www.bing.com/images/search"
LIMITE_PADRAO = 20
MINIMO_ESPERADO = 5  # abaixo disso o Bing serviu a página degradada (1 resultado) e vale tentar de novo
TENTATIVAS = 4
PAUSA_ENTRE_TENTATIVAS_S = 1.5
TIMEOUT_S = 20.0
TAMANHO_MAXIMO_BYTES = 12 * 1024 * 1024
SEM_LICENCA = "licença não verificada (MVP)"
AGENTE_DE_USUARIO = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
# Bancos de imagem pagos servem a foto com marca d'água: o juiz de visão gastaria cota à toa.
DOMINIOS_COM_MARCA_DAGUA = (
    "istockphoto.com",
    "shutterstock.com",
    "gettyimages.com",
    "alamy.com",
    "depositphotos.com",
    "dreamstime.com",
    "123rf.com",
    "adobestock.com",
    "stock.adobe.com",
    "freepik.com",
    "pngtree.com",
)

_METADADOS_DO_RESULTADO = re.compile(r'\sm="([^"]+)"')


class FonteDeImagemIndisponivel(Exception):
    """O buscador não respondeu, respondeu erro ou devolveu algo que não é a página esperada."""


class CandidatoDeImagem(BaseModel):
    """Um resultado da busca: a imagem, a página onde ela está e o que a página diz dela."""

    model_config = ConfigDict(frozen=True)

    titulo: str
    autor: str  # o domínio do site de origem; é o crédito possível sem licença
    licenca: str
    url_pagina: str
    url_imagem: str
    consulta: str


def dominio_de(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.")


def _de_banco_pago(dominio: str) -> bool:
    return any(dominio == d or dominio.endswith("." + d) for d in DOMINIOS_COM_MARCA_DAGUA)


def cliente_padrao() -> httpx.Client:
    """O ``httpx.Client`` de produção. Os testes injetam um com ``MockTransport``."""
    return httpx.Client(
        headers={"User-Agent": AGENTE_DE_USUARIO, "Accept-Language": "pt-BR,pt;q=0.9"},
        timeout=TIMEOUT_S,
        follow_redirects=True,
    )


class ClienteWeb:
    """Busca e baixa imagens. Todo erro de rede ou de formato vira ``FonteDeImagemIndisponivel``."""

    def __init__(
        self,
        cliente: httpx.Client | None = None,
        *,
        url_da_busca: str = URL_DA_BUSCA,
        pausa_s: float = PAUSA_ENTRE_TENTATIVAS_S,
    ) -> None:
        self._cliente = cliente
        self.url_da_busca = url_da_busca
        self.pausa_s = pausa_s

    def _com_cliente(self) -> tuple[httpx.Client, bool]:
        if self._cliente is not None:
            return self._cliente, False
        return cliente_padrao(), True

    def buscar(self, consulta: str, *, limite: int = LIMITE_PADRAO) -> list[CandidatoDeImagem]:
        """Resultados na ordem do buscador, sem repetir imagem e sem banco de imagem com marca d'água.

        O Bing às vezes serve uma página degradada, com um único resultado, para a mesma
        requisição que minutos antes devolveu 25: com poucos resultados, tenta de novo.
        """
        melhor: list[CandidatoDeImagem] = []
        for tentativa in range(TENTATIVAS):
            if tentativa:
                time.sleep(self.pausa_s * tentativa)
            candidatos = self._buscar_uma_vez(consulta, limite)
            if len(candidatos) > len(melhor):
                melhor = candidatos
            if len(melhor) >= MINIMO_ESPERADO:
                break
        return melhor

    def _buscar_uma_vez(self, consulta: str, limite: int) -> list[CandidatoDeImagem]:
        cliente, fechar = self._com_cliente()
        try:
            resposta = cliente.get(
                self.url_da_busca,
                params={"q": consulta, "form": "HDRSC2", "qft": "+filterui:imagesize-large", "first": 1},
            )
            resposta.raise_for_status()
            pagina = resposta.content.decode("utf-8", errors="replace")
        except (httpx.HTTPError, httpx.InvalidURL) as erro:
            raise FonteDeImagemIndisponivel(f"busca de imagens indisponível: {erro}") from erro
        finally:
            if fechar:
                cliente.close()
        return self._candidatos(pagina, consulta, limite)

    def baixar(self, candidato: CandidatoDeImagem) -> bytes:
        """Os bytes da imagem original. Hotlink bloqueado, erro e arquivo gigante viram exceção tipada."""
        cliente, fechar = self._com_cliente()
        try:
            referer = quote(candidato.url_pagina, safe=":/?&=%#+~@!$',;[]()*-._")  # cabeçalho só aceita ASCII
            resposta = cliente.get(candidato.url_imagem, headers={"Referer": referer})
            resposta.raise_for_status()
            conteudo = resposta.content
        except (httpx.HTTPError, httpx.InvalidURL, UnicodeError) as erro:
            raise FonteDeImagemIndisponivel(f"falha ao baixar {candidato.url_imagem}: {erro}") from erro
        finally:
            if fechar:
                cliente.close()
        if not conteudo:
            raise FonteDeImagemIndisponivel(f"resposta vazia ao baixar {candidato.url_imagem}")
        if len(conteudo) > TAMANHO_MAXIMO_BYTES:
            raise FonteDeImagemIndisponivel(f"{candidato.url_imagem} passa de {TAMANHO_MAXIMO_BYTES} bytes")
        return conteudo

    # -- interno ------------------------------------------------------------

    @staticmethod
    def _candidatos(pagina: str, consulta: str, limite: int) -> list[CandidatoDeImagem]:
        achados = _METADADOS_DO_RESULTADO.findall(pagina)
        if not achados and "imgpt" not in pagina and "b_content" not in pagina:
            raise FonteDeImagemIndisponivel("o buscador devolveu algo que não é a página de resultados")
        candidatos: list[CandidatoDeImagem] = []
        vistas: set[str] = set()
        for bruto in achados:
            try:
                dados = json.loads(html.unescape(bruto))
            except ValueError:
                continue
            if not isinstance(dados, dict):
                continue
            url_imagem, url_pagina = str(dados.get("murl", "")), str(dados.get("purl", ""))
            if not url_imagem.startswith(("http://", "https://")) or url_imagem in vistas:
                continue
            dominio = dominio_de(url_pagina) or dominio_de(url_imagem)
            if not dominio or _de_banco_pago(dominio) or _de_banco_pago(dominio_de(url_imagem)):
                continue
            vistas.add(url_imagem)
            candidatos.append(
                CandidatoDeImagem(
                    titulo=" ".join(str(dados.get("t", "")).split()) or url_imagem.rsplit("/", 1)[-1],
                    autor=dominio,
                    licenca=SEM_LICENCA,
                    url_pagina=url_pagina or url_imagem,
                    url_imagem=url_imagem,
                    consulta=consulta,
                )
            )
            if len(candidatos) >= limite:
                break
        return candidatos


URL_DO_SERPER = "https://google.serper.dev/images"
LARGURA_MINIMA_DO_SERPER = 800
MINIMO_DE_FOTOS = 3  # abaixo disso o filtro de foto esvaziou o assunto: vale a busca sem filtro


class ClienteSerper(ClienteWeb):
    """Google Imagens pela API do Serper.dev. Informa o tamanho antes do download."""

    def __init__(self, chave: str, cliente: httpx.Client | None = None, *, url_da_busca: str = URL_DO_SERPER) -> None:
        super().__init__(cliente, url_da_busca=url_da_busca)
        self._chave = chave

    def buscar(self, consulta: str, *, limite: int = LIMITE_PADRAO) -> list[CandidatoDeImagem]:
        """Só fotos (filtro de tipo do Google, que tira tabela, infográfico e clipart), menos na busca
        de logo, que não é foto. Se vierem poucas fotos, repete sem o filtro."""
        quer_logo = "logo" in consulta.lower().split()
        if not quer_logo:
            fotos = self._buscar(consulta, limite, somente_fotos=True)
            if len(fotos) >= MINIMO_DE_FOTOS:
                return fotos
        return self._buscar(consulta, limite, somente_fotos=False)

    def _buscar(self, consulta: str, limite: int, *, somente_fotos: bool) -> list[CandidatoDeImagem]:
        cliente, fechar = self._com_cliente()
        corpo: dict = {"q": consulta, "gl": "br", "hl": "pt-br", "num": 30}
        if somente_fotos:
            corpo["tbs"] = "itp:photo"
        try:
            resposta = cliente.post(self.url_da_busca, headers={"X-API-KEY": self._chave}, json=corpo)
            if resposta.status_code in (401, 403):
                raise FonteDeImagemIndisponivel("o Serper recusou a chave (SERPER_API_KEY)")
            resposta.raise_for_status()
            dados = resposta.json()
        except httpx.HTTPError as erro:
            raise FonteDeImagemIndisponivel(f"Serper indisponível: {erro}") from erro
        except ValueError as erro:
            raise FonteDeImagemIndisponivel(f"o Serper devolveu algo que não é JSON: {erro}") from erro
        finally:
            if fechar:
                cliente.close()
        if not isinstance(dados, dict) or not isinstance(dados.get("images", []), list):
            raise FonteDeImagemIndisponivel("o Serper devolveu JSON fora do formato esperado")
        candidatos: list[CandidatoDeImagem] = []
        vistas: set[str] = set()
        for item in dados.get("images", []):
            if not isinstance(item, dict):
                continue
            url_imagem, url_pagina = str(item.get("imageUrl", "")), str(item.get("link", ""))
            largura = item.get("imageWidth")
            if not url_imagem.startswith(("http://", "https://")) or url_imagem in vistas:
                continue
            if isinstance(largura, int) and largura < LARGURA_MINIMA_DO_SERPER:
                continue
            dominio = dominio_de(url_pagina) or dominio_de(url_imagem)
            if not dominio or _de_banco_pago(dominio) or _de_banco_pago(dominio_de(url_imagem)):
                continue
            vistas.add(url_imagem)
            candidatos.append(
                CandidatoDeImagem(
                    titulo=" ".join(str(item.get("title", "")).split()) or url_imagem.rsplit("/", 1)[-1],
                    autor=dominio,
                    licenca=SEM_LICENCA,
                    url_pagina=url_pagina or url_imagem,
                    url_imagem=url_imagem,
                    consulta=consulta,
                )
            )
            if len(candidatos) >= limite:
                break
        return candidatos


def buscador_padrao(cliente: httpx.Client | None = None) -> ClienteWeb:
    """O Serper (Google Imagens) se houver ``SERPER_API_KEY``; senão o Bing, que rende pouco."""
    chave = os.environ.get("SERPER_API_KEY", "").strip()
    return ClienteSerper(chave, cliente) if chave else ClienteWeb(cliente)
