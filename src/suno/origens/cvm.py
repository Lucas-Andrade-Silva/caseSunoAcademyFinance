"""Adaptador dos Fatos Relevantes da CVM, pelos dados abertos (IPE). Nunca roda no meio de uma
execução: é o "Atualizar fontes" da interface, e falha sem derrubar a tela.

O que a pesquisa (docs/research/viabilidade-tecnica.md) descobriu e este módulo respeita:

- ``ipe_cia_aberta_<ano>.zip`` traz um CSV ``;`` em latin-1 só com metadados; o texto está a um
  segundo salto, em ``Link_Download`` (RAD), que entrega PDF com ``Content-Type: text/html``:
  PDF se detecta pelos bytes ``%PDF``.
- O zip do ano corrente pode estar 404 (o de 2026 estava): tenta o ano anterior.
- ``Crawl-Delay: 10`` no ``robots.txt``: 10 s entre requisições ao portal.

ADR 0006.
"""

from __future__ import annotations

import csv
import io
import logging
import time
import zipfile
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from suno.dominio import Ata, CategoriaDaAta
from suno.ingestao.bcb import ErroDeIngestao, _user_agent
from suno.ingestao.pdf import carregar_ata, eh_pdf, gravar_ao_lado

_registro = logging.getLogger(__name__)

URL_DO_ZIP = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip"
ESPERA_ENTRE_REQUISICOES_S = 10.0
CATEGORIA_NO_CSV = "Fato Relevante"
ORIGEM_DA_CVM = "cvm_fatos_relevantes"
TITULO_MAXIMO = 150


def _cliente_padrao() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": _user_agent()}, timeout=60.0, follow_redirects=True)


def _linhas_do_zip(
    conteudo: bytes, aceitar: Callable[[dict[str, str]], bool] | None = None
) -> list[dict[str, str]]:
    """As linhas do CSV que ``aceitar`` deixa passar (padrão: Fatos Relevantes), com Link e
    Protocolo, da mais recente à mais antiga."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as arquivo:
        nomes = [n for n in arquivo.namelist() if n.lower().endswith(".csv")]
        if not nomes:
            return []
        texto = arquivo.read(nomes[0]).decode("latin-1")
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
    fatos = [
        linha
        for linha in leitor
        if (aceitar(linha) if aceitar else (linha.get("Categoria") or "").strip() == CATEGORIA_NO_CSV)
        and (linha.get("Link_Download") or "").strip()
        and (linha.get("Protocolo_Entrega") or "").strip()
    ]
    return sorted(fatos, key=lambda linha: linha.get("Data_Entrega") or "", reverse=True)


def _baixar_o_zip(cliente: httpx.Client, hoje: date) -> list[dict[str, str]]:
    """O primeiro zip (do ano, senão do anterior) que existe e traz Fatos Relevantes."""
    encontrou_algum = False
    for ano in (hoje.year, hoje.year - 1):
        try:
            resposta = cliente.get(URL_DO_ZIP.format(ano=ano))
        except httpx.HTTPError as erro:
            raise ErroDeIngestao(f"falha ao falar com a CVM: {erro}") from erro
        if resposta.status_code == 404:
            continue
        if resposta.status_code != 200:
            raise ErroDeIngestao(f"a CVM respondeu {resposta.status_code} ao baixar o zip de {ano}")
        encontrou_algum = True
        try:
            fatos = _linhas_do_zip(resposta.content)
        except (zipfile.BadZipFile, UnicodeDecodeError) as erro:
            raise ErroDeIngestao(f"o zip de {ano} da CVM veio quebrado: {erro}") from erro
        if fatos:
            return fatos
    if not encontrou_algum:
        raise ErroDeIngestao(
            f"a CVM não publicou o arquivo de Fatos Relevantes de {hoje.year} nem o de {hoje.year - 1}"
        )
    return []


def _data_da_linha(linha: dict[str, str], hoje: date) -> date:
    for campo in ("Data_Entrega", "Data_Referencia"):
        bruto = (linha.get(campo) or "").strip()[:10]
        try:
            return date.fromisoformat(bruto)
        except ValueError:
            continue
    return hoje


def buscar_fatos_relevantes(
    pasta_fontes: Path,
    *,
    quantidade: int = 5,
    cliente: httpx.Client | None = None,
    dormir: Callable[[float], None] = time.sleep,
    hoje: date | None = None,
) -> list[Ata]:
    """Baixa os ``quantidade`` Fatos Relevantes mais recentes que ainda não estão em disco.

    Grava ``<pasta_fontes>/cvm_fatos_relevantes/cvm-<protocolo>.{pdf,txt,json}``. Devolve só as
    Atas novas. Sem rede, ou sem nenhum documento baixável, levanta ``ErroDeIngestao``; o que já
    estava em disco nunca é apagado.
    """
    hoje = hoje or datetime.now(timezone.utc).date()
    proprio = cliente is None
    cliente = cliente or _cliente_padrao()
    destino = Path(pasta_fontes) / ORIGEM_DA_CVM
    novas: list[Ata] = []
    falhas: list[str] = []
    try:
        fatos = _baixar_o_zip(cliente, hoje)[:quantidade]
        for linha in fatos:
            identificador = f"cvm-{linha['Protocolo_Entrega'].strip()}"
            if (destino / f"{identificador}.pdf").exists():
                continue
            dormir(ESPERA_ENTRE_REQUISICOES_S)
            link = linha["Link_Download"].strip()
            try:
                resposta = cliente.get(link)
            except httpx.HTTPError as erro:
                falhas.append(f"{identificador}: {erro}")
                continue
            if resposta.status_code != 200:
                falhas.append(f"{identificador}: a CVM respondeu {resposta.status_code}")
                continue
            if not eh_pdf(resposta.content):
                falhas.append(f"{identificador}: o documento não é PDF pelos bytes")
                continue
            try:
                novas.append(_gravar(destino, identificador, linha, link, resposta.content, hoje))
            except ErroDeIngestao as erro:
                falhas.append(str(erro))
    finally:
        if proprio:
            cliente.close()
    if falhas and not novas:
        raise ErroDeIngestao("nenhum Fato Relevante baixado: " + "; ".join(falhas[:3]))
    for falha in falhas:
        _registro.warning("Fato Relevante pulado: %s", falha)
    return novas


def _gravar(
    destino: Path, identificador: str, linha: dict[str, str], link: str, conteudo: bytes, hoje: date
) -> Ata:
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{identificador}.pdf"
    empresa = (linha.get("Nome_Companhia") or "").strip() or "Companhia aberta"
    assunto = (linha.get("Assunto") or "").strip() or CATEGORIA_NO_CSV
    metadados: dict[str, Any] = {
        "identificador": identificador,
        "titulo": f"{empresa} · {assunto}"[:TITULO_MAXIMO],
        "data_referencia": _data_da_linha(linha, hoje).isoformat(),
        "origem_url": link,
        "categoria": CategoriaDaAta.COMUNICADO_RELEVANTE.value,
        "origem": ORIGEM_DA_CVM,
        "buscada_em": hoje.isoformat(),
        "idioma": "pt",
    }
    caminho.write_bytes(conteudo)
    try:
        gravar_ao_lado(caminho, metadados)
    except Exception as erro:  # noqa: BLE001 - PDF quebrado não deixa rastro pela metade
        for sufixo in (".pdf", ".txt", ".json"):
            caminho.with_suffix(sufixo).unlink(missing_ok=True)
        raise ErroDeIngestao(f"{identificador}: o PDF da CVM veio ilegível: {erro}") from erro
    return carregar_ata(caminho)
