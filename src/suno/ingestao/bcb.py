"""Busca de Atas na API não documentada do BCB. Nunca roda no meio de uma execução.
User-Agent identificado (SUNO_CONTATO), cerca de uma requisição por segundo.

ADR 0006.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from suno.dominio import Ata
from suno.ingestao.pdf import carregar_ata, eh_pdf, gravar_ao_lado

_BASE_URL = "https://www.bcb.gov.br"
_URL_LISTAR = f"{_BASE_URL}/api/servico/sitebcb/atascopom/ultimas"
_CONTATO_PADRAO = "SunoContent/0.1 (case academico; contato via repositorio)"
# '280ª Reunião - 4-5 agosto, 2026' -> 280.
_PADRAO_TITULO = re.compile(r"^\s*(\d+)ª")


class ErroDeIngestao(Exception):
    """Falha ao buscar ou validar uma Ata na origem (ADR 0006)."""


def _user_agent() -> str:
    return os.environ.get("SUNO_CONTATO", _CONTATO_PADRAO)


def _cliente_padrao() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": _user_agent()}, timeout=30.0)


def _numero_da_reuniao(titulo: str) -> int | None:
    casamento = _PADRAO_TITULO.match(titulo)
    return int(casamento.group(1)) if casamento else None


def listar_atas(quantidade: int = 10, *, cliente: httpx.Client | None = None) -> list[dict]:
    """Lista as últimas Atas do Copom, como a API devolve.

    Cada registro ganha ``reuniao`` (int, extraído do Titulo) e ``data_referencia`` (date,
    de DataReferencia), além dos campos originais da API (pesquisa §1). O parâmetro
    ``filtro=`` vazio é obrigatório — sem ele o endpoint responde 400/500.
    """
    proprio = cliente is None
    cliente = cliente or _cliente_padrao()
    try:
        try:
            resposta = cliente.get(_URL_LISTAR, params={"quantidade": quantidade, "filtro": ""})
        except httpx.HTTPError as erro:
            raise ErroDeIngestao(f"falha ao listar Atas no BCB: {erro}") from erro
        if resposta.status_code != 200:
            raise ErroDeIngestao(f"BCB respondeu {resposta.status_code} ao listar Atas")
        try:
            corpo = resposta.json()
        except ValueError as erro:
            raise ErroDeIngestao(f"resposta da API do BCB não é JSON válido: {erro}") from erro

        resultado: list[dict] = []
        for bruto in corpo.get("conteudo", []):
            registro = dict(bruto)
            registro["reuniao"] = _numero_da_reuniao(registro.get("Titulo", ""))
            data_bruta = registro.get("DataReferencia")
            registro["data_referencia"] = datetime.fromisoformat(data_bruta).date() if data_bruta else None
            resultado.append(registro)
        return resultado
    finally:
        if proprio:
            cliente.close()


def buscar_ata(
    destino: Path,
    reuniao: int | None = None,
    *,
    cliente: httpx.Client | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> Ata:
    """Baixa o arquivo da reunião pedida (ou da mais recente) e grava PDF, texto e
    metadados ao lado, em ``destino``. Espera ``dormir(1.0)`` entre a listagem e o
    download; confere os bytes baixados com ``eh_pdf`` porque o Content-Type mente
    (pesquisa §1)."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    proprio = cliente is None
    cliente = cliente or _cliente_padrao()
    try:
        quantidade = 10 if reuniao is None else 500
        registros = listar_atas(quantidade=quantidade, cliente=cliente)
        if not registros:
            raise ErroDeIngestao("a API do BCB não devolveu nenhuma Ata")

        if reuniao is None:
            escolhido = max(registros, key=lambda r: r["data_referencia"] or date.min)
        else:
            candidatos = [r for r in registros if r["reuniao"] == reuniao]
            if not candidatos:
                raise ErroDeIngestao(f"reunião {reuniao} não encontrada nas últimas Atas do BCB")
            escolhido = candidatos[0]

        dormir(1.0)

        url_arquivo = _BASE_URL + escolhido["Url"]
        try:
            resposta = cliente.get(url_arquivo)
        except httpx.HTTPError as erro:
            raise ErroDeIngestao(f"falha ao baixar o arquivo da Ata: {erro}") from erro
        if resposta.status_code != 200:
            raise ErroDeIngestao(f"BCB respondeu {resposta.status_code} ao baixar {url_arquivo}")

        corpo_binario = resposta.content
        if not eh_pdf(corpo_binario):
            raise ErroDeIngestao(
                f"o corpo baixado de {url_arquivo} não é um PDF pelos bytes "
                "(o Content-Type da resposta não é confiável — pesquisa §1)"
            )

        identificador = f"copom-{escolhido['reuniao']}-{escolhido['data_referencia'].isoformat()}"
        caminho_arquivo = destino / f"{identificador}.pdf"
        caminho_arquivo.write_bytes(corpo_binario)

        metadados: dict[str, Any] = {
            "identificador": identificador,
            "titulo": escolhido.get("Titulo"),
            "reuniao": escolhido["reuniao"],
            "data_referencia": escolhido["data_referencia"].isoformat(),
            "origem_url": url_arquivo,
            "origem_api": f"{_URL_LISTAR}?quantidade={quantidade}&filtro=",
            "buscada_em": datetime.now(timezone.utc).date().isoformat(),
            "idioma": "pt",
        }
        gravar_ao_lado(caminho_arquivo, metadados)

        return carregar_ata(caminho_arquivo)
    finally:
        if proprio:
            cliente.close()
