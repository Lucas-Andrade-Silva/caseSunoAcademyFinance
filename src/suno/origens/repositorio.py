"""Onde as Atas moram e como achá-las.

O Copom fica em ``data/atas/`` (versionado: a demo roda sem rede). As demais Origens ficam em
``data/fontes/<origem>/``, fora do git. Cada Ata é ``<id>.pdf`` ou ``<id>.txt`` com um ``<id>.json``
de metadados ao lado, o mesmo formato que ``suno.ingestao.pdf.carregar_ata`` lê.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from suno.dominio import Ata
from suno.gerador.execucao import NOME_DE_PASTA, PASTA_RESPOSTAS_PRONTAS
from suno.ingestao.pdf import carregar_ata
from suno.origens.catalogo import Origem
from suno.origens.resumo import ResumoDaAta, resumir_ata

_registro = logging.getLogger(__name__)

SUFIXOS_DE_ATA = (".pdf", ".txt")
ORIGEM_DAS_ATAS_DO_COPOM = "copom"


def _assinatura_da_ata(caminho: Path) -> tuple[tuple[int, int] | None, ...]:
    """Inclui todos os arquivos lidos, inclusive auxiliares que ainda não existem."""
    arquivos = [caminho, caminho.with_suffix(".json")]
    if caminho.suffix == ".pdf":
        arquivos.append(caminho.with_suffix(".txt"))
    assinatura: list[tuple[int, int] | None] = []
    for arquivo in arquivos:
        try:
            estado = arquivo.stat()
        except FileNotFoundError:
            assinatura.append(None)
        else:
            assinatura.append((estado.st_mtime_ns, estado.st_size))
    return tuple(assinatura)


@lru_cache(maxsize=512)
def _ata_em_cache(
    caminho: str, assinatura: tuple[tuple[int, int] | None, ...], origem_da_pasta: str
) -> Ata:
    """Carrega a Ata; alterações no original ou nos auxiliares invalidam o cache."""
    ata = carregar_ata(Path(caminho))
    sem_origem_no_json = not _json_tem_origem(Path(caminho))
    return ata.model_copy(update={"origem": origem_da_pasta}) if sem_origem_no_json else ata


@lru_cache(maxsize=512)
def _resumo_em_cache(
    caminho: str, assinatura: tuple[tuple[int, int] | None, ...], origem_da_pasta: str, demo: bool
) -> ResumoDaAta:
    """O resumo custa uma varredura de números no texto inteiro: só refaz se o arquivo mudar."""
    ata = _ata_em_cache(caminho, assinatura, origem_da_pasta)
    return resumir_ata(ata, demo_disponivel=demo)


def _json_tem_origem(caminho: Path) -> bool:
    try:
        bruto = json.loads(caminho.with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(bruto, dict) and "origem" in bruto


class RepositorioDeAtas:
    def __init__(self, pasta_atas: Path, pasta_fontes: Path) -> None:
        self._pasta_atas = Path(pasta_atas)
        self._pasta_fontes = Path(pasta_fontes)

    # -- onde estão ---------------------------------------------------------

    def _pastas(self) -> list[tuple[Path, str]]:
        """Cada pasta com Atas e a Origem que ela implica: ``data/atas`` é o Copom."""
        pastas = [(self._pasta_atas, ORIGEM_DAS_ATAS_DO_COPOM)]
        if self._pasta_fontes.exists():
            pastas += [
                (pasta, pasta.name)
                for pasta in sorted(self._pasta_fontes.iterdir())
                if pasta.is_dir()
            ]
        return pastas

    def arquivo(self, identificador: str) -> Path | None:
        """O ``.pdf`` ou ``.txt`` da Ata. Identificador com barra, ``..`` ou vazio nunca acha."""
        achado = self._achar(identificador)
        return achado[0] if achado else None

    def _achar(self, identificador: str) -> tuple[Path, str] | None:
        if not NOME_DE_PASTA.match(identificador):
            return None
        for pasta, origem in self._pastas():
            for sufixo in SUFIXOS_DE_ATA:
                caminho = pasta / f"{identificador}{sufixo}"
                if caminho.exists():
                    return caminho, origem
        return None

    def identificadores(self) -> list[str]:
        encontrados: set[str] = set()
        for pasta, _ in self._pastas():
            if pasta.exists():
                encontrados |= {
                    caminho.stem for caminho in pasta.iterdir() if caminho.suffix in SUFIXOS_DE_ATA
                }
        return sorted(encontrados)

    # -- o que são ----------------------------------------------------------

    def carregar(self, identificador: str) -> Ata | None:
        achado = self._achar(identificador)
        if achado is None:
            return None
        caminho, origem = achado
        try:
            return _ata_em_cache(str(caminho), _assinatura_da_ata(caminho), origem)
        except (OSError, ValueError, KeyError, ValidationError) as erro:
            _registro.warning("Ata %r ilegível, fora da lista: %s", identificador, erro)
            return None

    def resumir(self, identificador: str) -> ResumoDaAta | None:
        ata = self.carregar(identificador)
        achado = self._achar(identificador)
        if ata is None or achado is None:
            return None
        caminho, origem = achado
        demo = (PASTA_RESPOSTAS_PRONTAS / f"{ata.identificador}.json").exists()
        return _resumo_em_cache(str(caminho), _assinatura_da_ata(caminho), origem, demo)

    def itens_da_origem(self, origem: Origem) -> list[ResumoDaAta]:
        """As Atas da Origem, da mais recente para a mais antiga."""
        resumos = [r for r in (self.resumir(i) for i in self.identificadores()) if r is not None]
        daqui = [r for r in resumos if r.origem == origem.id]
        return sorted(daqui, key=lambda r: (r.data_referencia, r.identificador), reverse=True)
