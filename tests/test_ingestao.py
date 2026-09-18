"""Ingestão: leitura do arquivo versionado da Ata e busca no BCB, tudo sem rede
(`httpx.MockTransport` no lugar da API — ADR 0001, ADR 0006).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from suno.ingestao.bcb import ErroDeIngestao, buscar_ata, listar_atas
from suno.ingestao.pdf import carregar_ata, eh_pdf, extrair_texto

# Forma real da API (`GET .../atascopom/ultimas?quantidade=…&filtro=`), copiada de uma
# requisição de verdade em 18/09/2026: um registro da 280ª reunião e um da 279ª.
REGISTROS_EXEMPLO = {
    "conteudo": [
        {
            "DataReferencia": "2026-08-05T03:00:00Z",
            "ImagemCapa": "/content/publicacoes/PublishingImages/Capas/atascopom/capa-atascopom.png",
            "Titulo": "280ª Reunião - 4-5 agosto, 2026",
            "Url": "/content/copom/atascopom/Copom280-not20260805280.pdf",
            "LinkPagina": "/publicacoes/atascopom/05082026",
            "EsconderDataReferencia": True,
        },
        {
            "DataReferencia": "2026-06-17T03:00:00Z",
            "ImagemCapa": "/content/publicacoes/PublishingImages/Capas/atascopom/capa-atascopom.png",
            "Titulo": "279ª Reunião - 16-17 junho, 2026",
            "Url": "/content/copom/atascopom/Copom279-not20260617279.pdf",
            "LinkPagina": "/publicacoes/atascopom/17062026",
            "EsconderDataReferencia": True,
        },
    ]
}


def _transporte_listagem() -> httpx.MockTransport:
    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        assert "atascopom/ultimas" in str(requisicao.url)
        assert "filtro=" in str(requisicao.url)
        return httpx.Response(200, json=REGISTROS_EXEMPLO)

    return httpx.MockTransport(manipulador)


def _transporte_busca(corpo_arquivo: bytes) -> httpx.MockTransport:
    """Listagem normal; o download devolve ``corpo_arquivo`` sempre anunciado como
    ``Content-Type: application/pdf`` — verdadeiro ou não. É o teste do "cabeçalho mente"
    (pesquisa §1): quem chama decide se ``corpo_arquivo`` é um PDF de verdade ou não."""

    def manipulador(requisicao: httpx.Request) -> httpx.Response:
        if "atascopom/ultimas" in str(requisicao.url):
            return httpx.Response(200, json=REGISTROS_EXEMPLO)
        return httpx.Response(200, content=corpo_arquivo, headers={"Content-Type": "application/pdf"})

    return httpx.MockTransport(manipulador)


# ---------------------------------------------------------------------------
# ingestao/pdf.py
# ---------------------------------------------------------------------------


def test_reconhece_arquivo_original_pelos_bytes_e_rejeita_txt_renomeado(
    tmp_path: Path, caminho_ata: Path, caminho_ata_txt: Path
) -> None:
    assert eh_pdf(caminho_ata) is True

    disfarcado = tmp_path / "nao_e_arquivo_de_verdade.pdf"
    disfarcado.write_bytes(caminho_ata_txt.read_bytes())
    assert eh_pdf(disfarcado) is False


def test_extrair_texto_contem_selic_decidida_e_copom(caminho_ata: Path) -> None:
    texto = extrair_texto(caminho_ata)
    assert "14,00% a.a." in texto
    assert "Copom" in texto


def test_extrair_texto_levanta_valueerro_para_arquivo_sem_assinatura_valida(
    tmp_path: Path, caminho_ata_txt: Path
) -> None:
    disfarcado = tmp_path / "nao_e_arquivo_de_verdade.pdf"
    disfarcado.write_bytes(caminho_ata_txt.read_bytes())
    with pytest.raises(ValueError, match="não é um PDF"):
        extrair_texto(disfarcado)


def test_carregar_ata_do_arquivo_original_do_repositorio(caminho_ata: Path, texto_ata: str) -> None:
    ata = carregar_ata(caminho_ata)
    assert ata.reuniao == 280
    assert ata.data_referencia == date(2026, 8, 5)
    assert ata.identificador == "copom-280-2026-08-05"
    assert ata.texto == texto_ata
    assert ata.arquivo == caminho_ata


def test_carregar_ata_de_txt_solto_sem_json_deriva_do_nome(tmp_path: Path) -> None:
    caminho = tmp_path / "copom-999-2025-01-15.txt"
    caminho.write_text("Texto de uma Ata de teste, sem metadados ao lado.", encoding="utf-8")

    ata = carregar_ata(caminho)

    assert ata.identificador == "copom-999-2025-01-15"
    assert ata.reuniao == 999
    assert ata.data_referencia == date(2025, 1, 15)
    assert ata.texto == "Texto de uma Ata de teste, sem metadados ao lado."
    assert ata.arquivo is None


# ---------------------------------------------------------------------------
# ingestao/bcb.py
# ---------------------------------------------------------------------------


def test_listar_atas_extrai_reuniao_e_data_referencia() -> None:
    with httpx.Client(transport=_transporte_listagem()) as cliente:
        registros = listar_atas(cliente=cliente)

    assert len(registros) == 2
    por_reuniao = {registro["reuniao"]: registro for registro in registros}
    assert por_reuniao[280]["data_referencia"] == date(2026, 8, 5)
    assert por_reuniao[279]["data_referencia"] == date(2026, 6, 17)
    # Os campos originais da API continuam presentes, intactos.
    assert por_reuniao[280]["Titulo"] == "280ª Reunião - 4-5 agosto, 2026"


def test_buscar_ata_grava_arquivo_texto_e_metadados_e_devolve_a_ata_certa(
    tmp_path: Path, caminho_ata: Path
) -> None:
    bytes_arquivo = caminho_ata.read_bytes()
    esperas: list[float] = []

    with httpx.Client(transport=_transporte_busca(bytes_arquivo)) as cliente:
        ata = buscar_ata(tmp_path, reuniao=280, cliente=cliente, dormir=esperas.append)

    assert esperas == [1.0]  # espera entre listagem e download, nunca dorme de verdade
    assert ata.identificador == "copom-280-2026-08-05"
    assert ata.reuniao == 280
    assert ata.data_referencia == date(2026, 8, 5)
    assert "Copom" in ata.texto

    caminho_arquivo_gravado = tmp_path / "copom-280-2026-08-05.pdf"
    caminho_txto_gravado = tmp_path / "copom-280-2026-08-05.txt"
    caminho_metadados_gravado = tmp_path / "copom-280-2026-08-05.json"
    assert caminho_arquivo_gravado.read_bytes() == bytes_arquivo
    assert caminho_txto_gravado.exists()
    assert caminho_metadados_gravado.exists()

    metadados = json.loads(caminho_metadados_gravado.read_text(encoding="utf-8"))
    assert metadados["sha256_pdf"] == hashlib.sha256(bytes_arquivo).hexdigest()
    assert metadados["paginas"] == 5
    assert metadados["caracteres"] == len(ata.texto)
    assert metadados["extrator"].startswith("pypdf")
    assert metadados["origem_url"].endswith("Copom280-not20260805280.pdf")


def test_buscar_ata_mais_recente_quando_reuniao_nao_e_pedida(tmp_path: Path, caminho_ata: Path) -> None:
    bytes_arquivo = caminho_ata.read_bytes()
    with httpx.Client(transport=_transporte_busca(bytes_arquivo)) as cliente:
        ata = buscar_ata(tmp_path, cliente=cliente, dormir=lambda _segundos: None)
    assert ata.reuniao == 280  # a mais recente das duas do exemplo (280 > 279)


def test_buscar_ata_reuniao_inexistente_levanta_erro(tmp_path: Path, caminho_ata: Path) -> None:
    with httpx.Client(transport=_transporte_busca(caminho_ata.read_bytes())) as cliente:
        with pytest.raises(ErroDeIngestao, match="não encontrada"):
            buscar_ata(tmp_path, reuniao=999, cliente=cliente, dormir=lambda _segundos: None)


def test_buscar_ata_corpo_baixado_sem_assinatura_valida_levanta_erro_mesmo_com_cabecalho_mentiroso(
    tmp_path: Path,
) -> None:
    """O "cabeçalho mente": o servidor anuncia Content-Type: application/pdf para um corpo
    HTML. `eh_pdf` confere os bytes, não o cabeçalho (pesquisa §1, NÃO PODE do brief)."""
    corpo_html = b"<html><body>pagina de erro, nao um arquivo valido</body></html>"
    with httpx.Client(transport=_transporte_busca(corpo_html)) as cliente:
        with pytest.raises(ErroDeIngestao, match="não é um PDF"):
            buscar_ata(tmp_path, reuniao=280, cliente=cliente, dormir=lambda _segundos: None)

    # nada deve ter sido gravado em destino após a falha de validação
    assert list(tmp_path.iterdir()) == []


def test_buscar_ata_api_fora_do_ar_levanta_erro(tmp_path: Path) -> None:
    transporte = httpx.MockTransport(lambda requisicao: httpx.Response(503, text="indisponível"))
    with httpx.Client(transport=transporte) as cliente:
        with pytest.raises(ErroDeIngestao, match="503"):
            buscar_ata(tmp_path, cliente=cliente, dormir=lambda _segundos: None)
