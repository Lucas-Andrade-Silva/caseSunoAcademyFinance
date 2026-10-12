"""O adaptador dos Fatos Relevantes da CVM (dados abertos, IPE) e o job "Atualizar fontes".

Tudo com `httpx.MockTransport`: a suíte roda offline. O que a pesquisa descobriu e os testes
travam: o CSV é `;` em latin-1, o RAD entrega PDF com `Content-Type: text/html`, o zip do ano
corrente pode estar 404 e a CVM pede 10 s entre requisições (`Crawl-Delay`).
"""

from __future__ import annotations

import io
import json
import threading
import zipfile
from datetime import date
from pathlib import Path

import httpx
import pytest

from suno.dominio import CategoriaDaAta
from suno.ingestao.bcb import ErroDeIngestao
from suno.origens.atualizacao import Atualizador
from suno.origens.cvm import ESPERA_ENTRE_REQUISICOES_S, buscar_fatos_relevantes

ARQUIVO_PAGINADO = (
    Path(__file__).resolve().parent.parent / "data" / "atas" / "copom-280-2026-08-05.pdf"
).read_bytes()
HOJE = date(2026, 10, 9)
CABECALHO = (
    "CNPJ_Companhia;Nome_Companhia;Codigo_CVM;Data_Referencia;Categoria;Tipo;Especie;Assunto;"
    "Data_Entrega;Tipo_Apresentacao;Protocolo_Entrega;Versao;Link_Download"
)


def _linha(protocolo: str, protocolada_em: str, categoria: str = "Fato Relevante", empresa: str = "Cia. São Paulo S.A.") -> str:
    return (
        f"00.000.000/0001-00;{empresa};1234;{protocolada_em};{categoria};;;Aquisição de participação;"
        f"{protocolada_em};AP - Apresentacao;{protocolo};1;https://rad.cvm.gov.br/doc/{protocolo}"
    )


def _zip(linhas: list[str]) -> bytes:
    corpo = "\n".join([CABECALHO, *linhas]).encode("latin-1")
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        arquivo.writestr("ipe_cia_aberta_2025.csv", corpo)
    return memoria.getvalue()


class Servidor:
    """Um servidor de mentira: o zip de cada ano e o corpo de cada documento."""

    def __init__(self, zips: dict[int, bytes | int], documentos: dict[str, bytes] | None = None):
        self.zips = zips
        self.documentos = documentos or {}
        self.pedidos: list[str] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        url = str(pedido.url)
        self.pedidos.append(url)
        if "ipe_cia_aberta_" in url:
            ano = int(url.rsplit("_", 1)[1].split(".")[0])
            corpo = self.zips.get(ano, 404)
            if isinstance(corpo, int):
                return httpx.Response(corpo)
            return httpx.Response(200, content=corpo, headers={"content-type": "application/zip"})
        protocolo = url.rsplit("/", 1)[1]
        if protocolo in self.documentos:
            # O RAD mente no Content-Type: diz text/html e entrega PDF.
            return httpx.Response(
                200, content=self.documentos[protocolo], headers={"content-type": "text/html"}
            )
        return httpx.Response(404)

    def cliente(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))


def _buscar(pasta: Path, servidor: Servidor, **trocas):
    esperas: list[float] = []
    argumentos = {
        "quantidade": 5,
        "cliente": servidor.cliente(),
        "dormir": esperas.append,
        "hoje": HOJE,
    }
    argumentos.update(trocas)
    atas = buscar_fatos_relevantes(pasta, **argumentos)
    return atas, esperas


def test_baixa_os_fatos_mais_recentes_e_ignora_outras_categorias(tmp_path: Path):
    servidor = Servidor(
        {2026: _zip([
            _linha("111", "2026-09-01"),
            _linha("222", "2026-10-05"),
            _linha("333", "2026-10-07", categoria="Comunicado ao Mercado"),
            _linha("444", "2026-08-15"),
        ])},
        {"111": ARQUIVO_PAGINADO, "222": ARQUIVO_PAGINADO, "444": ARQUIVO_PAGINADO},
    )

    atas, _ = _buscar(tmp_path, servidor, quantidade=2)

    assert [a.identificador for a in atas] == ["cvm-222", "cvm-111"]
    pasta = tmp_path / "cvm_fatos_relevantes"
    for identificador in ("cvm-222", "cvm-111"):
        assert (pasta / f"{identificador}.pdf").exists()
        assert (pasta / f"{identificador}.txt").exists()
        assert (pasta / f"{identificador}.json").exists()
    assert not (pasta / "cvm-333.pdf").exists()
    assert not (pasta / "cvm-444.pdf").exists()


def test_a_ata_baixada_leva_categoria_origem_e_titulo_com_acento(tmp_path: Path):
    servidor = Servidor({2026: _zip([_linha("222", "2026-10-05")])}, {"222": ARQUIVO_PAGINADO})

    atas, _ = _buscar(tmp_path, servidor)

    ata = atas[0]
    assert ata.categoria is CategoriaDaAta.COMUNICADO_RELEVANTE
    assert ata.origem == "cvm_fatos_relevantes"
    assert ata.titulo == "Cia. São Paulo S.A. · Aquisição de participação"
    assert ata.data_referencia == date(2026, 10, 5)
    metadados = json.loads(
        (tmp_path / "cvm_fatos_relevantes" / "cvm-222.json").read_text(encoding="utf-8")
    )
    assert metadados["origem_url"] == "https://rad.cvm.gov.br/doc/222"


def test_detecta_o_formato_pelos_bytes_mesmo_com_content_type_de_html(tmp_path: Path):
    servidor = Servidor({2026: _zip([_linha("222", "2026-10-05")])}, {"222": ARQUIVO_PAGINADO})

    atas, _ = _buscar(tmp_path, servidor)

    assert len(atas) == 1
    assert "Copom" in atas[0].texto


def test_cai_para_o_ano_anterior_quando_o_zip_do_ano_da_404(tmp_path: Path):
    servidor = Servidor({2026: 404, 2025: _zip([_linha("222", "2025-12-05")])}, {"222": ARQUIVO_PAGINADO})

    atas, _ = _buscar(tmp_path, servidor)

    assert [a.identificador for a in atas] == ["cvm-222"]
    assert any("ipe_cia_aberta_2026" in u for u in servidor.pedidos)
    assert any("ipe_cia_aberta_2025" in u for u in servidor.pedidos)


def test_espera_dez_segundos_antes_de_cada_arquivo(tmp_path: Path):
    servidor = Servidor(
        {2026: _zip([_linha("111", "2026-09-01"), _linha("222", "2026-10-05")])},
        {"111": ARQUIVO_PAGINADO, "222": ARQUIVO_PAGINADO},
    )

    _, esperas = _buscar(tmp_path, servidor)

    assert ESPERA_ENTRE_REQUISICOES_S == 10.0
    assert esperas == [10.0, 10.0]


def test_o_que_ja_foi_baixado_nao_baixa_de_novo_nem_espera(tmp_path: Path):
    servidor = Servidor({2026: _zip([_linha("222", "2026-10-05")])}, {"222": ARQUIVO_PAGINADO})
    _buscar(tmp_path, servidor)
    servidor.pedidos.clear()

    atas, esperas = _buscar(tmp_path, servidor)

    assert atas == []
    assert esperas == []
    assert not any(u.endswith("/222") for u in servidor.pedidos)


def test_arquivo_que_nao_e_paginado_e_pulado_e_os_outros_seguem(tmp_path: Path):
    servidor = Servidor(
        {2026: _zip([_linha("111", "2026-09-01"), _linha("222", "2026-10-05")])},
        {"111": ARQUIVO_PAGINADO, "222": b"<html>pagina de erro do RAD</html>"},
    )

    atas, _ = _buscar(tmp_path, servidor)

    assert [a.identificador for a in atas] == ["cvm-111"]
    assert not (tmp_path / "cvm_fatos_relevantes" / "cvm-222.pdf").exists()


def test_arquivo_com_404_e_pulado(tmp_path: Path):
    servidor = Servidor(
        {2026: _zip([_linha("111", "2026-09-01"), _linha("222", "2026-10-05")])}, {"111": ARQUIVO_PAGINADO}
    )

    atas, _ = _buscar(tmp_path, servidor)

    assert [a.identificador for a in atas] == ["cvm-111"]


def test_sem_rede_vira_erro_de_ingestao_e_nao_apaga_o_que_existia(tmp_path: Path):
    existente = tmp_path / "cvm_fatos_relevantes"
    existente.mkdir()
    (existente / "cvm-antigo.txt").write_text("texto antigo", encoding="utf-8")

    def sem_rede(pedido: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede", request=pedido)

    cliente = httpx.Client(transport=httpx.MockTransport(sem_rede))

    with pytest.raises(ErroDeIngestao, match="CVM"):
        buscar_fatos_relevantes(tmp_path, cliente=cliente, dormir=lambda s: None, hoje=HOJE)

    assert (existente / "cvm-antigo.txt").read_text(encoding="utf-8") == "texto antigo"


def test_os_dois_anos_em_404_vira_erro_com_o_motivo(tmp_path: Path):
    servidor = Servidor({2026: 404, 2025: 404})

    with pytest.raises(ErroDeIngestao, match="não publicou"):
        _buscar(tmp_path, servidor)


def test_zip_sem_comunicado_relevante_tenta_o_ano_anterior(tmp_path: Path):
    servidor = Servidor(
        {
            2026: _zip([_linha("333", "2026-10-07", categoria="Comunicado ao Mercado")]),
            2025: _zip([_linha("222", "2025-12-05")]),
        },
        {"222": ARQUIVO_PAGINADO},
    )

    atas, _ = _buscar(tmp_path, servidor)

    assert [a.identificador for a in atas] == ["cvm-222"]


# ---------------------------------------------------------------------------
# "Atualizar fontes"
# ---------------------------------------------------------------------------


def _catalogo(tmp_path: Path, ligar_cvm: bool) -> Path:
    pasta = tmp_path / "fontes"
    pasta.mkdir()
    (pasta / "preferencias.json").write_text(
        json.dumps({"ativas": {"cvm_fatos_relevantes": ligar_cvm}}), encoding="utf-8"
    )
    return pasta


def test_atualizar_roda_so_as_origens_ligadas(tmp_path: Path):
    chamadas: list[str] = []
    atualizador = Atualizador(
        tmp_path / "atas",
        _catalogo(tmp_path, ligar_cvm=False),
        buscar_copom=lambda destino: chamadas.append("copom") or _ata_falsa("copom-281-2026-09-16"),
        buscar_cvm=lambda destino: chamadas.append("cvm") or [],
    )

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    assert chamadas == ["copom"]
    assert atualizador.estado().estado == "ok"


def test_atualizar_com_a_cvm_ligada_busca_as_duas(tmp_path: Path):
    chamadas: list[str] = []
    atualizador = Atualizador(
        tmp_path / "atas",
        _catalogo(tmp_path, ligar_cvm=True),
        buscar_copom=lambda destino: chamadas.append("copom") or _ata_falsa("copom-281-2026-09-16"),
        buscar_cvm=lambda destino: chamadas.append("cvm") or [_ata_falsa("cvm-1"), _ata_falsa("cvm-2")],
    )

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    assert chamadas == ["copom", "cvm"]
    estado = atualizador.estado()
    assert estado.estado == "ok"
    assert estado.novos == 3


def test_sem_rede_o_estado_vira_erro_com_a_mensagem_e_nao_levanta(tmp_path: Path):
    def cair(destino):
        raise ErroDeIngestao("falha ao listar Atas no BCB: sem rede")

    atualizador = Atualizador(
        tmp_path / "atas",
        _catalogo(tmp_path, ligar_cvm=False),
        buscar_copom=cair,
        buscar_cvm=lambda destino: [],
    )

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert estado.estado == "erro"
    assert "sem rede" in estado.mensagem


def test_uma_origem_que_falha_nao_impede_a_outra(tmp_path: Path):
    def cair(destino):
        raise ErroDeIngestao("BCB fora do ar")

    atualizador = Atualizador(
        tmp_path / "atas",
        _catalogo(tmp_path, ligar_cvm=True),
        buscar_copom=cair,
        buscar_cvm=lambda destino: [_ata_falsa("cvm-1")],
    )

    atualizador.iniciar()
    assert atualizador.aguardar(10)

    estado = atualizador.estado()
    assert estado.estado == "erro"
    assert estado.novos == 1
    assert "BCB fora do ar" in estado.mensagem


def test_nao_inicia_duas_atualizacoes_ao_mesmo_tempo(tmp_path: Path):
    liberar = threading.Event()
    comecou = threading.Event()
    chamadas: list[int] = []

    def devagar(destino):
        chamadas.append(1)
        comecou.set()
        assert liberar.wait(10)
        return _ata_falsa("copom-281-2026-09-16")

    atualizador = Atualizador(
        tmp_path / "atas",
        _catalogo(tmp_path, ligar_cvm=False),
        buscar_copom=devagar,
        buscar_cvm=lambda destino: [],
    )

    atualizador.iniciar()
    assert comecou.wait(10)
    segundo = atualizador.iniciar()

    assert segundo.estado == "rodando"
    liberar.set()
    assert atualizador.aguardar(10)
    assert len(chamadas) == 1


def test_antes_de_atualizar_o_estado_e_ocioso(tmp_path: Path):
    atualizador = Atualizador(
        tmp_path / "atas",
        _catalogo(tmp_path, ligar_cvm=False),
        buscar_copom=lambda d: _ata_falsa("x"),
        buscar_cvm=lambda d: [],
    )

    assert atualizador.estado().estado == "ocioso"


def _ata_falsa(identificador: str):
    from suno.dominio import Ata

    return Ata(
        identificador=identificador,
        titulo=identificador,
        data_referencia=date(2026, 9, 16),
        texto="texto",
    )
