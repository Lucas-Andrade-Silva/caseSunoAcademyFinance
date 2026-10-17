"""Importar um PDF ou um texto: vira uma Ata da Origem "importados" (categoria ``importada``).

O tipo do arquivo sai dos bytes, nunca da extensão nem do Content-Type (pesquisa §1). Nada fica
em disco quando o arquivo é recusado.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path

from suno.dominio import Ata, CategoriaDaAta
from suno.ingestao.pdf import carregar_ata, eh_pdf, gravar_ao_lado

LIMITE_DO_ARQUIVO = 15 * 1024 * 1024
TITULO_MAXIMO = 200
ORIGEM_DOS_IMPORTADOS = "importados"
PEDACOS_DO_IDENTIFICADOR = 60


class ArquivoRecusado(ValueError):
    """O arquivo importado não serve; a mensagem é a frase que a tela mostra."""


class ArquivoGrandeDemais(ArquivoRecusado):
    """Passou do limite de tamanho: a API responde 413 em vez de 422."""


def _slug(titulo: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
    return limpo[:PEDACOS_DO_IDENTIFICADOR].strip("-") or "documento"


def _reservar_identificador(pasta: Path, titulo: str, data: date) -> str:
    """Reserva o nome criando o JSON exclusivamente, inclusive entre processos."""
    base = f"{_slug(titulo)}-{data:%Y%m%d}"
    candidato, numero = base, 1
    while True:
        if not any((pasta / f"{candidato}{sufixo}").exists() for sufixo in (".pdf", ".txt", ".json")):
            try:
                (pasta / f"{candidato}.json").touch(exist_ok=False)
            except FileExistsError:
                pass  # outra importação reservou depois da consulta
            else:
                return candidato
        numero += 1
        candidato = f"{base}-{numero}"


def _texto_utf8(conteudo: bytes) -> str:
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ArquivoRecusado("o arquivo não é PDF nem texto UTF-8") from None
    if "\x00" in texto:
        raise ArquivoRecusado("o arquivo não é PDF nem texto UTF-8")
    return texto


def importar(
    pasta_fontes: Path,
    *,
    conteudo: bytes,
    titulo: str,
    data_referencia: date | None,
    hoje: date | None = None,
) -> Ata:
    """Grava o arquivo em ``<pasta_fontes>/importados/`` e devolve a Ata. Recusa sem deixar rastro."""
    rotulo = titulo.strip()
    if not rotulo:
        raise ArquivoRecusado("o título não pode ficar vazio")
    if len(rotulo) > TITULO_MAXIMO:
        raise ArquivoRecusado(f"o título passa de {TITULO_MAXIMO} caracteres")
    if len(conteudo) > LIMITE_DO_ARQUIVO:
        raise ArquivoGrandeDemais(f"o arquivo passa de {LIMITE_DO_ARQUIVO // (1024 * 1024)} MB")
    if not conteudo.strip():
        raise ArquivoRecusado("o arquivo está vazio")

    paginado = eh_pdf(conteudo)
    texto = None if paginado else _texto_utf8(conteudo)
    if texto is not None and not texto.strip():
        raise ArquivoRecusado("o arquivo está vazio")

    data = data_referencia or hoje or date.today()
    pasta = Path(pasta_fontes) / ORIGEM_DOS_IMPORTADOS
    criou_a_pasta = not pasta.exists()
    pasta.mkdir(parents=True, exist_ok=True)
    identificador = _reservar_identificador(pasta, rotulo, data)
    metadados = {
        "identificador": identificador,
        "titulo": rotulo,
        "data_referencia": data.isoformat(),
        "categoria": CategoriaDaAta.IMPORTADA.value,
        "origem": ORIGEM_DOS_IMPORTADOS,
        "idioma": "pt",
        "importada_em": datetime.now(timezone.utc).isoformat(),
    }
    # A reserva pertence a esta importação. Inclui os auxiliares antes de gravar:
    # uma falha entre o TXT e o JSON também precisa remover o arquivo parcial.
    # Libera o nome por último, depois de remover os parciais.
    escritos = [pasta / f"{identificador}{sufixo}" for sufixo in (".pdf", ".txt", ".json")]
    try:
        if paginado:
            caminho = pasta / f"{identificador}.pdf"
            caminho.write_bytes(conteudo)
            try:
                caminho_txt, caminho_json = gravar_ao_lado(caminho, metadados)
            except Exception:  # noqa: BLE001 - pypdf levanta tipos variados para PDF quebrado
                raise ArquivoRecusado("o PDF está ilegível") from None
            if not caminho_txt.read_text(encoding="utf-8").strip():
                raise ArquivoRecusado("o PDF não tem texto (parece escaneado)")
        else:
            caminho = pasta / f"{identificador}.txt"
            caminho.write_text(texto or "", encoding="utf-8")
            caminho_json = caminho.with_suffix(".json")
            completos = {
                **metadados,
                "sha256": hashlib.sha256(conteudo).hexdigest(),
                "caracteres": len(texto or ""),
            }
            caminho_json.write_text(
                json.dumps(completos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        return carregar_ata(caminho)
    except BaseException:
        for arquivo in escritos:
            arquivo.unlink(missing_ok=True)
        if criou_a_pasta:
            try:
                pasta.rmdir()
            except OSError:
                pass
        raise
