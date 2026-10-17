"""Importar um PDF ou um texto: vira uma Ata da Origem "importados", com categoria `importada`.

O que entra é validado pelos bytes, não pela extensão nem pelo Content-Type: o cabeçalho mente
(pesquisa §1). Nada aqui toca a rede.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier

import pytest

from suno.dominio import CategoriaDaAta
from suno.ingestao.pdf import carregar_ata
from suno.origens.importacao import LIMITE_DO_ARQUIVO, ArquivoRecusado, importar

ARQUIVO_DO_COPOM = Path(__file__).resolve().parent.parent / "data" / "atas" / "copom-280-2026-08-05.pdf"
TEXTO = (
    "Comunicado da Empresa Exemplo S.A.\n"
    "Em 8 de outubro de 2026 o conselho aprovou a aquisição de 100% das ações da Outra S.A. "
    "pelo valor de R$ 1,5 bilhão."
)


def _importar(pasta: Path, conteudo: bytes = TEXTO.encode("utf-8"), **trocas):
    argumentos = {
        "conteudo": conteudo,
        "titulo": "Empresa Exemplo · aquisição",
        "data_referencia": date(2026, 10, 8),
    }
    argumentos.update(trocas)
    return importar(pasta, **argumentos)


def test_texto_vira_ata_importada_com_txt_e_json(tmp_path: Path):
    ata = _importar(tmp_path)

    assert ata.categoria is CategoriaDaAta.IMPORTADA
    assert ata.origem == "importados"
    assert ata.titulo == "Empresa Exemplo · aquisição"
    assert ata.data_referencia == date(2026, 10, 8)
    assert "R$ 1,5 bilhão" in ata.texto
    pasta = tmp_path / "importados"
    assert (pasta / f"{ata.identificador}.txt").exists()
    metadados = json.loads((pasta / f"{ata.identificador}.json").read_text(encoding="utf-8"))
    assert metadados["categoria"] == "importada"
    assert metadados["origem"] == "importados"
    assert metadados["data_referencia"] == "2026-10-08"


def test_a_ata_importada_carrega_de_volta_do_disco(tmp_path: Path):
    ata = _importar(tmp_path)

    de_volta = carregar_ata(tmp_path / "importados" / f"{ata.identificador}.txt")

    assert de_volta.identificador == ata.identificador
    assert de_volta.categoria is CategoriaDaAta.IMPORTADA


def test_arquivo_paginado_vira_arquivo_mais_texto_extraido(tmp_path: Path):
    ata = _importar(tmp_path, conteudo=ARQUIVO_DO_COPOM.read_bytes(), titulo="Ata de teste")

    pasta = tmp_path / "importados"
    assert (pasta / f"{ata.identificador}.pdf").exists()
    assert (pasta / f"{ata.identificador}.txt").exists()
    assert "Copom" in ata.texto
    assert ata.categoria is CategoriaDaAta.IMPORTADA


def test_o_identificador_sai_do_titulo_sem_acento_nem_barra(tmp_path: Path):
    ata = _importar(tmp_path, titulo="Ação & Fusão / Cia. São Paulo — 2026")

    assert ata.identificador.startswith("acao-fusao-cia-sao-paulo-2026")
    assert "/" not in ata.identificador and " " not in ata.identificador
    assert ata.identificador.endswith("20261008")


def test_dois_com_o_mesmo_titulo_nao_se_sobrescrevem(tmp_path: Path):
    primeira = _importar(tmp_path)
    segunda = _importar(tmp_path, conteudo=b"Outro texto com R$ 2 milhoes em 8 de outubro de 2026.")

    assert primeira.identificador != segunda.identificador
    assert "R$ 1,5 bilhão" in carregar_ata(
        tmp_path / "importados" / f"{primeira.identificador}.txt"
    ).texto


def test_importacoes_concorrentes_preservam_cada_ata(tmp_path: Path):
    quantidade = 8
    pasta = tmp_path / "importados"
    pasta.mkdir()
    inicio = Barrier(quantidade)
    textos = [f"Comunicado {indice}: operação de R$ {indice + 1} milhões." for indice in range(quantidade)]

    def enviar(texto: str):
        inicio.wait(timeout=10)
        return _importar(tmp_path, conteudo=texto.encode("utf-8"))

    with ThreadPoolExecutor(max_workers=quantidade) as trabalhadores:
        atas = list(trabalhadores.map(enviar, textos))

    assert len({ata.identificador for ata in atas}) == quantidade
    assert len(list(pasta.glob("*.txt"))) == quantidade
    assert len(list(pasta.glob("*.json"))) == quantidade
    for ata, texto in zip(atas, textos, strict=True):
        assert ata.texto == texto
        assert carregar_ata(pasta / f"{ata.identificador}.txt").texto == texto


def test_sem_data_vale_hoje(tmp_path: Path):
    ata = _importar(tmp_path, data_referencia=None, hoje=date(2026, 10, 9))

    assert ata.data_referencia == date(2026, 10, 9)


@pytest.mark.parametrize(
    ("conteudo", "trecho"),
    [
        (b"", "vazio"),
        (b"   \n\t  ", "vazio"),
        (b"\xff\xfe\x00\x01\x80\x81binario", "PDF nem texto"),
        (b"%PDF-1.4 isto nao e um pdf de verdade", "ilegível"),
    ],
    ids=["vazio", "so-espaco", "binario", "pdf-falso"],
)
def test_arquivo_invalido_e_recusado_sem_deixar_rastro(tmp_path: Path, conteudo: bytes, trecho: str):
    with pytest.raises(ArquivoRecusado, match=trecho):
        _importar(tmp_path, conteudo=conteudo)

    assert not (tmp_path / "importados").exists() or not any((tmp_path / "importados").iterdir())


def test_arquivo_grande_demais_e_recusado(tmp_path: Path):
    with pytest.raises(ArquivoRecusado, match="15 MB"):
        _importar(tmp_path, conteudo=b"a" * (LIMITE_DO_ARQUIVO + 1))


def test_titulo_vazio_e_recusado(tmp_path: Path):
    with pytest.raises(ArquivoRecusado, match="título"):
        _importar(tmp_path, titulo="   ")


def test_titulo_enorme_e_recusado(tmp_path: Path):
    with pytest.raises(ArquivoRecusado, match="título"):
        _importar(tmp_path, titulo="x" * 201)
