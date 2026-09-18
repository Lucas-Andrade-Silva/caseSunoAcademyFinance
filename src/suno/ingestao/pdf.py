"""Leitura do arquivo da Ata. PDF é reconhecido pelos primeiros bytes (`%PDF`), nunca pelo
cabeçalho HTTP, que mente. Extração com pypdf (BSD-3).

ADR 0006.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pypdf

from suno.dominio import Ata

_ASSINATURA = b"%PDF"
# 'copom-<numero>-<aaaa>-<mm>-<dd>', o padrão de nome usado em data/atas/.
_PADRAO_IDENTIFICADOR = re.compile(r"^copom-(\d+)-(\d{4})-(\d{2})-(\d{2})$")


def eh_pdf(caminho_ou_bytes: Path | bytes) -> bool:
    """Verdadeiro se os primeiros bytes forem a assinatura ``%PDF``. Nunca confia em
    extensão nem em Content-Type — o cabeçalho HTTP mente (pesquisa §1)."""
    if isinstance(caminho_ou_bytes, (bytes, bytearray)):
        cabecalho = bytes(caminho_ou_bytes[:4])
    else:
        with Path(caminho_ou_bytes).open("rb") as arquivo:
            cabecalho = arquivo.read(4)
    return cabecalho == _ASSINATURA


def _paginas(caminho: Path) -> list[str]:
    leitor = pypdf.PdfReader(caminho)
    return [pagina.extract_text() or "" for pagina in leitor.pages]


def _limpar(paginas: list[str]) -> str:
    """Junta páginas com linha dupla; colapsa espaços antes de quebra e três ou mais
    quebras seguidas. É a mesma limpeza usada para gerar os .txt versionados em
    ``data/atas/`` (conferido byte a byte contra ``copom-280-2026-08-05.txt``)."""
    texto = "\n\n".join(paginas)
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto


def extrair_texto(caminho: Path) -> str:
    """Extrai o texto de todas as páginas com pypdf."""
    caminho = Path(caminho)
    if not eh_pdf(caminho):
        raise ValueError(f"{caminho} não é um PDF (assinatura %PDF ausente nos primeiros bytes)")
    return _limpar(_paginas(caminho))


def _do_identificador(identificador: str) -> tuple[int | None, date | None]:
    """Deriva reunião e data do padrão 'copom-<n>-<aaaa-mm-dd>', quando o nome bate."""
    casamento = _PADRAO_IDENTIFICADOR.match(identificador)
    if not casamento:
        return None, None
    numero, ano, mes, dia = casamento.groups()
    return int(numero), date(int(ano), int(mes), int(dia))


def carregar_ata(caminho: Path) -> Ata:
    """Lê o .pdf (ou o .txt já extraído ao lado) e o .json de metadados; devolve a Ata.

    Para .pdf, usa o .txt irmão se existir, senão extrai na hora. O .json irmão, quando
    existe, é a fonte de titulo/reuniao/data_referencia/origem_url; sem ele, deriva
    identificador do nome do arquivo e reuniao/data_referencia do padrão
    'copom-<n>-<aaaa-mm-dd>' quando possível. Preenche ``Ata.arquivo`` com o caminho do
    PDF (None quando a entrada é só um .txt solto).
    """
    caminho = Path(caminho)
    sufixo = caminho.suffix.lower()
    if sufixo not in (".pdf", ".txt"):
        raise ValueError(f"formato não suportado: {caminho.suffix!r} (use .pdf ou .txt)")

    identificador = caminho.stem
    caminho_txt = caminho.with_suffix(".txt")
    caminho_json = caminho.with_suffix(".json")
    arquivo_original = caminho if sufixo == ".pdf" else None

    if sufixo == ".pdf":
        texto = caminho_txt.read_text(encoding="utf-8") if caminho_txt.exists() else extrair_texto(caminho)
    else:
        texto = caminho.read_text(encoding="utf-8")

    metadados: dict[str, Any] = {}
    if caminho_json.exists():
        metadados = json.loads(caminho_json.read_text(encoding="utf-8"))

    reuniao_do_nome, data_do_nome = _do_identificador(identificador)
    reuniao = metadados.get("reuniao", reuniao_do_nome)

    data_bruta = metadados.get("data_referencia")
    data_referencia = date.fromisoformat(data_bruta) if data_bruta else data_do_nome
    if data_referencia is None:
        raise ValueError(
            f"sem data_referencia para {caminho}: não há .json irmão e o nome não segue "
            "o padrão copom-<numero>-<aaaa>-<mm>-<dd>"
        )

    return Ata(
        identificador=metadados.get("identificador", identificador),
        titulo=metadados.get("titulo", identificador),
        reuniao=reuniao,
        data_referencia=data_referencia,
        origem_url=metadados.get("origem_url"),
        arquivo=arquivo_original,
        texto=texto,
        idioma=metadados.get("idioma", "pt"),
    )


def gravar_ao_lado(caminho: Path, metadados: dict[str, Any]) -> tuple[Path, Path]:
    """Grava o .txt (texto extraído) e o .json (metadados) irmãos de ``caminho``.

    Usado por ``bcb.buscar_ata``: o chamador informa o que só ele sabe (identificador,
    titulo, reuniao, data_referencia, origem_url, origem_api, buscada_em, idioma); esta
    função completa o que vem da extração — sha256_pdf, paginas, caracteres, extrator —
    com as mesmas chaves do exemplo em ``data/atas/``.
    """
    caminho = Path(caminho)
    paginas = _paginas(caminho)
    texto = _limpar(paginas)
    completos = {
        **metadados,
        "sha256_pdf": hashlib.sha256(caminho.read_bytes()).hexdigest(),
        "paginas": len(paginas),
        "caracteres": len(texto),
        "extrator": f"pypdf {pypdf.__version__}",
    }
    caminho_txt = caminho.with_suffix(".txt")
    caminho_json = caminho.with_suffix(".json")
    caminho_txt.write_text(texto, encoding="utf-8")
    caminho_json.write_text(json.dumps(completos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return caminho_txt, caminho_json
