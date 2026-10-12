"""As rotas das Fontes: catálogo com resumo, liga e desliga, importar, atualizar e a sugestão.

Sem rede: o atualizador recebe funções falsas no lugar do BCB e da CVM, e a geração usa o executor
falso de `test_geracao.py`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from suno.api.app import criar_app
from suno.ingestao.bcb import ErroDeIngestao
from suno.origens.atualizacao import Atualizador
from suno.origens.importacao import LIMITE_DO_ARQUIVO
from tests.test_geracao import ATA, PASTA_ATAS, ExecutorFalso

ARQUIVO_DO_COPOM = PASTA_ATAS / f"{ATA}.pdf"
TEXTO = (
    "Comunicado da Empresa Exemplo S.A. Em 8 de outubro de 2026 o conselho aprovou a aquisição "
    "de 100% das ações da Outra S.A. pelo valor de R$ 1,5 bilhão."
)


def _cliente(tmp_path: Path, *, executor=None, atualizador: Atualizador | None = None) -> TestClient:
    return TestClient(
        criar_app(
            tmp_path / "execucoes",
            pasta_atas=PASTA_ATAS,
            pasta_fontes=tmp_path / "fontes",
            executar_fn=executor,
            atualizador=atualizador,
        )
    )


def _importar_texto(cliente: TestClient, titulo: str = "Nota da Empresa Exemplo") -> dict:
    resposta = cliente.post(
        "/api/fontes/importar",
        params={"titulo": titulo, "data_referencia": "2026-10-08"},
        content=TEXTO.encode("utf-8"),
        headers={"content-type": "text/plain"},
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ---------------------------------------------------------------------------
# O catálogo
# ---------------------------------------------------------------------------


def test_a_lista_traz_a_copom_280_com_resumo_e_a_cvm_desligada(tmp_path: Path):
    corpo = _cliente(tmp_path).get("/api/fontes").json()

    origens = {o["id"]: o for o in corpo["origens"]}
    assert list(origens) == ["copom", "cvm_fatos_relevantes", "releases_b3", "importados"]
    assert origens["copom"]["ativa"] is True
    ata = origens["copom"]["atas"][0]
    assert ata["identificador"] == ATA
    assert ata["resumo"].startswith("O Copom decidiu reduzir a taxa básica")
    assert ata["calibrada"] is True and ata["demo_disponivel"] is True
    assert origens["cvm_fatos_relevantes"]["ativa"] is False
    assert origens["cvm_fatos_relevantes"]["atas"] == []
    assert origens["releases_b3"]["disponivel"] is False
    assert origens["releases_b3"]["aviso"] == "em breve"
    assert corpo["atualizacao"]["estado"] == "ocioso"


def test_ligar_e_desligar_persiste_no_disco(tmp_path: Path):
    cliente = _cliente(tmp_path)

    resposta = cliente.patch("/api/fontes/cvm_fatos_relevantes", json={"ativa": True})

    assert resposta.status_code == 200
    assert resposta.json()["ativa"] is True
    outro = _cliente(tmp_path)
    origens = {o["id"]: o for o in outro.get("/api/fontes").json()["origens"]}
    assert origens["cvm_fatos_relevantes"]["ativa"] is True

    desligada = outro.patch("/api/fontes/cvm_fatos_relevantes", json={"ativa": False})
    assert desligada.json()["ativa"] is False


def test_origem_indisponivel_responde_409(tmp_path: Path):
    resposta = _cliente(tmp_path).patch("/api/fontes/releases_b3", json={"ativa": True})

    assert resposta.status_code == 409
    assert "em breve" in resposta.json()["detail"]


def test_origem_desconhecida_responde_404(tmp_path: Path):
    assert _cliente(tmp_path).patch("/api/fontes/nao-existe", json={"ativa": True}).status_code == 404


# ---------------------------------------------------------------------------
# Importar
# ---------------------------------------------------------------------------


def test_importar_texto_aparece_na_lista(tmp_path: Path):
    cliente = _cliente(tmp_path)

    ata = _importar_texto(cliente)

    assert ata["categoria"] == "importada"
    assert ata["origem"] == "importados"
    assert ata["calibrada"] is False and ata["demo_disponivel"] is False
    origens = {o["id"]: o for o in cliente.get("/api/fontes").json()["origens"]}
    assert [a["identificador"] for a in origens["importados"]["atas"]] == [ata["identificador"]]


def test_importar_arquivo_paginado(tmp_path: Path):
    resposta = _cliente(tmp_path).post(
        "/api/fontes/importar",
        params={"titulo": "Ata em PDF", "data_referencia": "2026-08-05"},
        content=ARQUIVO_DO_COPOM.read_bytes(),
        headers={"content-type": "application/pdf"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["categoria"] == "importada"


def test_importar_arquivo_binario_responde_422(tmp_path: Path):
    resposta = _cliente(tmp_path).post(
        "/api/fontes/importar",
        params={"titulo": "Binário"},
        content=b"\xff\xfe\x00\x01\x80\x81lixo",
        headers={"content-type": "application/octet-stream"},
    )

    assert resposta.status_code == 422
    assert "PDF nem texto" in resposta.json()["detail"]


def test_importar_arquivo_enorme_responde_413(tmp_path: Path):
    resposta = _cliente(tmp_path).post(
        "/api/fontes/importar",
        params={"titulo": "Gigante"},
        content=b"a" * (LIMITE_DO_ARQUIVO + 1),
        headers={"content-type": "text/plain"},
    )

    assert resposta.status_code == 413


def test_importar_sem_titulo_responde_422(tmp_path: Path):
    resposta = _cliente(tmp_path).post(
        "/api/fontes/importar",
        params={"titulo": "  "},
        content=TEXTO.encode("utf-8"),
        headers={"content-type": "text/plain"},
    )

    assert resposta.status_code == 422


# ---------------------------------------------------------------------------
# Gerar a partir de uma Ata de fora do Copom
# ---------------------------------------------------------------------------


def test_ata_importada_vira_escolha_valida_e_a_saida_nasce_nao_calibrada(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODELO", "modelo-de-teste")
    executor = ExecutorFalso()
    cliente = _cliente(tmp_path, executor=executor)
    ata = _importar_texto(cliente)

    resposta = cliente.post(
        "/api/execucoes",
        json={
            "ata": ata["identificador"],
            "modo": "real",
            "pedido": [{"audiencia": "iniciante", "formato": "carrossel"}],
        },
    )

    assert resposta.status_code == 202
    assert resposta.json()["categoria"] == "importada"
    cliente.app.state.gerenciador.aguardar_ocioso()
    saidas = cliente.get("/api/execucoes").json()
    assert [s["categoria"] for s in saidas] == ["importada"]
    assert executor.chamadas[0]["ata"] == ata["identificador"]


def test_demo_para_ata_importada_responde_422(tmp_path: Path):
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    ata = _importar_texto(cliente)

    resposta = cliente.post(
        "/api/execucoes",
        json={
            "ata": ata["identificador"],
            "modo": "demo",
            "pedido": [{"audiencia": "iniciante", "formato": "carrossel"}],
        },
    )

    assert resposta.status_code == 422
    assert "respostas prontas" in resposta.json()["detail"]


def test_as_atas_da_lista_antiga_incluem_as_importadas(tmp_path: Path):
    cliente = _cliente(tmp_path)
    ata = _importar_texto(cliente)

    identificadores = [a["identificador"] for a in cliente.get("/api/atas").json()]

    assert ata["identificador"] in identificadores and ATA in identificadores


# ---------------------------------------------------------------------------
# A sugestão da curadoria
# ---------------------------------------------------------------------------


def test_a_sugestao_e_a_ata_do_copom_280_com_o_motivo(tmp_path: Path):
    corpo = _cliente(tmp_path).get("/api/curadoria/sugestoes").json()

    destaque = corpo["destaque_unico"]
    assert [a["identificador"] for a in destaque["itens"]] == [ATA]
    assert "mais recente" in destaque["motivo"]
    assert corpo["visao_unida"] is None


def test_a_sugestao_inclui_a_origem_ligada_e_ignora_a_desligada(tmp_path: Path):
    cliente = _cliente(tmp_path)
    ata = _importar_texto(cliente)  # data 2026-10-08, mais recente que a Ata do Copom

    assert cliente.get("/api/curadoria/sugestoes").json()["destaque_unico"]["itens"][0][
        "identificador"
    ] == ata["identificador"]

    cliente.patch("/api/fontes/importados", json={"ativa": False})

    assert cliente.get("/api/curadoria/sugestoes").json()["destaque_unico"]["itens"][0][
        "identificador"
    ] == ATA


# ---------------------------------------------------------------------------
# Atualizar fontes
# ---------------------------------------------------------------------------


def test_atualizar_sem_rede_devolve_o_erro_sem_derrubar_a_listagem(tmp_path: Path):
    def cair(destino):
        raise ErroDeIngestao("falha ao listar Atas no BCB: sem rede")

    atualizador = Atualizador(
        PASTA_ATAS,
        tmp_path / "fontes",
        buscar_copom=cair,
        buscar_cvm=lambda destino: [],
    )
    cliente = _cliente(tmp_path, atualizador=atualizador)

    inicio = cliente.post("/api/fontes/atualizar")
    assert inicio.status_code == 202
    assert atualizador.aguardar(10)

    estado = cliente.get("/api/fontes/atualizacao").json()
    assert estado["estado"] == "erro"
    assert "sem rede" in estado["mensagem"]
    listagem = cliente.get("/api/fontes")
    assert listagem.status_code == 200
    assert listagem.json()["atualizacao"]["estado"] == "erro"


def test_gerar_de_ata_sem_numero_responde_422_antes_de_gastar_cota(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODELO", "modelo-de-teste")
    executor = ExecutorFalso()
    cliente = _cliente(tmp_path, executor=executor)
    resposta = cliente.post(
        "/api/fontes/importar",
        params={"titulo": "Pedido de cancelamento", "data_referencia": "2026-10-02"},
        content="São Paulo, 2 de outubro de 2026. A companhia pediu o cancelamento do registro.".encode(),
        headers={"content-type": "text/plain"},
    )
    ata = resposta.json()
    assert ata["extracao_completa"] is False

    pedido = cliente.post(
        "/api/execucoes",
        json={
            "ata": ata["identificador"],
            "modo": "real",
            "pedido": [{"audiencia": "iniciante", "formato": "carrossel"}],
        },
    )

    assert pedido.status_code == 422
    assert "número com unidade" in pedido.json()["detail"]
    assert executor.chamadas == []


# ---------------------------------------------------------------------------
# Visão unida
# ---------------------------------------------------------------------------


def _com_chave(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODELO", "modelo-de-teste")


def _duas_atas(cliente: TestClient) -> tuple[str, str]:
    primeira = _importar_texto(cliente, "Aquisição da Empresa Exemplo")
    segunda = _importar_texto(cliente, "Emissão da Companhia Modelo")
    return primeira["identificador"], segunda["identificador"]


PEDIDO = [{"audiencia": "iniciante", "formato": "carrossel"}]


def test_visao_unida_responde_202_e_a_saida_nasce_unida(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    executor = ExecutorFalso()
    cliente = _cliente(tmp_path, executor=executor)
    a, b = _duas_atas(cliente)

    resposta = cliente.post("/api/execucoes", json={"itens": [a, b], "modo": "real", "pedido": PEDIDO})

    assert resposta.status_code == 202, resposta.text
    corpo = resposta.json()
    assert corpo["categoria"] == "unida"
    assert corpo["atas"] == [a, b]
    assert corpo["ata"].startswith("uniao-")
    cliente.app.state.gerenciador.aguardar_ocioso()
    assert executor.chamadas[0]["atas"] == [a, b]
    saida = cliente.get("/api/execucoes").json()[0]
    assert saida["categoria"] == "unida"
    assert saida["atas"] == [a, b]


def test_visao_unida_em_demo_responde_422(tmp_path: Path):
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    a, b = _duas_atas(cliente)

    resposta = cliente.post("/api/execucoes", json={"itens": [a, b], "modo": "demo", "pedido": PEDIDO})

    assert resposta.status_code == 422
    assert "Demo" in resposta.json()["detail"]


def test_visao_unida_com_uma_ata_so_responde_422(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    a, _ = _duas_atas(cliente)

    resposta = cliente.post("/api/execucoes", json={"itens": [a], "modo": "real", "pedido": PEDIDO})

    assert resposta.status_code == 422
    assert "de 2 a 5" in resposta.json()["detail"]


def test_ata_e_itens_juntos_ou_nenhum_responde_422(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    a, b = _duas_atas(cliente)

    juntos = cliente.post(
        "/api/execucoes", json={"ata": a, "itens": [a, b], "modo": "real", "pedido": PEDIDO}
    )
    nenhum = cliente.post("/api/execucoes", json={"modo": "real", "pedido": PEDIDO})

    assert juntos.status_code == 422
    assert nenhum.status_code == 422


def test_visao_unida_com_ata_inexistente_responde_404(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    a, _ = _duas_atas(cliente)

    resposta = cliente.post(
        "/api/execucoes", json={"itens": [a, "nao-existe"], "modo": "real", "pedido": PEDIDO}
    )

    assert resposta.status_code == 404


def test_visao_unida_com_ata_sem_numero_responde_422(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    a, _ = _duas_atas(cliente)
    sem_numero = cliente.post(
        "/api/fontes/importar",
        params={"titulo": "Pedido de cancelamento", "data_referencia": "2026-10-02"},
        content="São Paulo, 2 de outubro de 2026. A companhia pediu o cancelamento.".encode(),
        headers={"content-type": "text/plain"},
    ).json()

    resposta = cliente.post(
        "/api/execucoes",
        json={"itens": [a, sem_numero["identificador"]], "modo": "real", "pedido": PEDIDO},
    )

    assert resposta.status_code == 422
    assert sem_numero["identificador"] in resposta.json()["detail"]


def test_visao_unida_com_mais_de_cinco_responde_422(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    ids = [_importar_texto(cliente, f"Comunicado {n}")["identificador"] for n in range(6)]

    resposta = cliente.post("/api/execucoes", json={"itens": ids, "modo": "real", "pedido": PEDIDO})

    assert resposta.status_code == 422
    assert "de 2 a 5" in resposta.json()["detail"]


def test_visao_unida_com_ata_repetida_responde_422(tmp_path: Path, monkeypatch):
    _com_chave(monkeypatch)
    cliente = _cliente(tmp_path, executor=ExecutorFalso())
    a, _ = _duas_atas(cliente)

    resposta = cliente.post("/api/execucoes", json={"itens": [a, a], "modo": "real", "pedido": PEDIDO})

    assert resposta.status_code == 422
    assert "repetida" in resposta.json()["detail"]


def test_a_sugestao_traz_a_visao_unida_quando_ha_ao_menos_duas_atas(tmp_path: Path):
    cliente = _cliente(tmp_path)
    assert cliente.get("/api/curadoria/sugestoes").json()["visao_unida"] is None  # só o Copom

    _duas_atas(cliente)
    corpo = cliente.get("/api/curadoria/sugestoes").json()

    visao = corpo["visao_unida"]
    assert len(visao["itens"]) == 3  # as duas importadas e a Ata do Copom
    assert "3 itens" in visao["motivo"]
    assert corpo["destaque_unico"] is not None
