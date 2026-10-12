"""As rotas da geração sob demanda: `POST /api/execucoes`, o andamento e a lista de Saídas.

Quase todos os testes usam o executor falso de `test_geracao.py`, que não chama o pipeline. O
último bloco roda o pipeline de verdade com o provedor falso da demo, sem rede, para provar que a
rota, o `Gerenciador` e `executar` conversam do mesmo jeito que a tela vai conversar.

ADR 0017.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from suno.api.app import criar_app
from tests.test_geracao import ATA, PASTA_ATAS, ExecutorFalso

CORPO = {
    "ata": ATA,
    "modo": "demo",
    "pedido": [
        {"audiencia": "iniciante", "formato": "carrossel"},
        {"audiencia": "iniciante", "formato": "roteiro"},
    ],
}


def _cliente(pasta: Path, executor=None, *, atas: Path = PASTA_ATAS) -> TestClient:
    # As Fontes ficam numa pasta à parte: nenhum teste enxerga o que alguém importou em data/fontes/.
    fontes = pasta.parent / f"{pasta.name}-fontes"
    return TestClient(
        criar_app(pasta, pasta_atas=atas, pasta_fontes=fontes, executar_fn=executor)
    )


def _gerenciador(cliente: TestClient):
    return cliente.app.state.gerenciador


# ---------------------------------------------------------------------------
# Pedir e acompanhar
# ---------------------------------------------------------------------------


def test_criar_a_saida_responde_202_com_o_andamento(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    cliente = _cliente(tmp_path, executor)

    resposta = cliente.post("/api/execucoes", json={**CORPO, "nome": "Saída de teste"})

    assert resposta.status_code == 202
    corpo = resposta.json()
    assert corpo["estado"] in ("na_fila", "gerando")
    assert corpo["nome"] == "Saída de teste"
    assert corpo["provedor"] == "falso"
    assert [c["etapa"] for c in corpo["celulas"]] == ["aguardando", "aguardando"]
    assert executor.comecou.wait(10)
    executor.liberar.set()
    assert _gerenciador(cliente).aguardar_ocioso()


def test_curadoria_visual_e_validada_e_chega_ao_pipeline(tmp_path: Path):
    executor = ExecutorFalso()
    cliente = _cliente(tmp_path, executor)

    resposta = cliente.post(
        "/api/execucoes",
        json={
            **CORPO,
            "composicao_visual": "editorial",
            "referencia_visual": "suno-editorial-cenario-de-juros",
        },
    )

    assert resposta.status_code == 202
    assert resposta.json()["composicao_visual"] == "editorial"
    assert resposta.json()["referencia_visual"] == "suno-editorial-cenario-de-juros"
    assert _gerenciador(cliente).aguardar_ocioso()
    assert executor.chamadas[0]["composicao_visual"].value == "editorial"
    assert executor.chamadas[0]["referencia_visual"] == "suno-editorial-cenario-de-juros"


def test_curadoria_visual_recusa_referencia_de_outra_composicao(tmp_path: Path):
    resposta = _cliente(tmp_path, ExecutorFalso()).post(
        "/api/execucoes",
        json={
            **CORPO,
            "composicao_visual": "minimalista",
            "referencia_visual": "suno-editorial-cenario-de-juros",
        },
    )

    assert resposta.status_code == 422
    assert "não pertence" in resposta.json()["detail"]


def test_o_andamento_responde_pelo_identificador(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    cliente = _cliente(tmp_path, executor)
    identificador = cliente.post("/api/execucoes", json=CORPO).json()["identificador"]
    assert executor.comecou.wait(10)

    resposta = cliente.get(f"/api/execucoes/{identificador}/andamento")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "gerando"
    assert corpo["fase"] == "gerando_celulas"
    assert [c["etapa"] for c in corpo["celulas"]] == ["gerando", "gerando"]
    executor.liberar.set()
    assert _gerenciador(cliente).aguardar_ocioso()
    assert cliente.get(f"/api/execucoes/{identificador}/andamento").json()["estado"] == "concluida"


def test_sem_andamento_a_rota_responde_404(tmp_path: Path):
    assert _cliente(tmp_path).get("/api/execucoes/nao-existe/andamento").status_code == 404


def test_o_segundo_pedido_fica_na_fila(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    cliente = _cliente(tmp_path, executor)
    cliente.post("/api/execucoes", json=CORPO)
    assert executor.comecou.wait(10)

    segundo = cliente.post("/api/execucoes", json=CORPO).json()

    assert segundo["estado"] == "na_fila"
    executor.liberar.set()
    assert _gerenciador(cliente).aguardar_ocioso()
    final = cliente.get(f"/api/execucoes/{segundo['identificador']}/andamento").json()
    assert final["estado"] == "concluida"


# ---------------------------------------------------------------------------
# A lista de Saídas e o resumo enxergam o que ainda não tem execucao.json
# ---------------------------------------------------------------------------


def test_a_lista_mostra_a_saida_em_geracao(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    cliente = _cliente(tmp_path, executor)
    identificador = cliente.post("/api/execucoes", json=CORPO).json()["identificador"]
    assert executor.comecou.wait(10)

    saidas = cliente.get("/api/execucoes").json()

    assert [s["identificador"] for s in saidas] == [identificador]
    saida = saidas[0]
    assert saida["status"] == "gerando"
    assert saida["total_celulas"] == 2
    assert saida["provedor"] == "falso"
    assert [(p["audiencia"], p["formato"], p["etapa"]) for p in saida["posicoes"]] == [
        ("iniciante", "carrossel", "gerando"),
        ("iniciante", "roteiro", "gerando"),
    ]
    assert all(p["destino"] is None and p["decisao"] is None for p in saida["posicoes"])
    executor.liberar.set()
    assert _gerenciador(cliente).aguardar_ocioso()


def test_o_resumo_funciona_antes_de_existir_a_execucao(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    cliente = _cliente(tmp_path, executor)
    identificador = cliente.post("/api/execucoes", json={**CORPO, "nome": "Em andamento"}).json()[
        "identificador"
    ]
    assert executor.comecou.wait(10)

    resposta = cliente.get(f"/api/execucoes/{identificador}/resumo")

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Em andamento"
    assert resposta.json()["status"] == "gerando"
    # A execução completa ainda não existe: nada de 500, é 404 como sempre.
    assert cliente.get(f"/api/execucoes/{identificador}").status_code == 404
    executor.liberar.set()
    assert _gerenciador(cliente).aguardar_ocioso()


def test_job_que_falhou_aparece_como_falhou_com_o_erro(tmp_path: Path):
    cliente = _cliente(tmp_path, ExecutorFalso(falha=RuntimeError("o provedor caiu")))
    identificador = cliente.post("/api/execucoes", json=CORPO).json()["identificador"]
    assert _gerenciador(cliente).aguardar_ocioso()

    saida = cliente.get(f"/api/execucoes/{identificador}/resumo").json()

    assert saida["status"] == "falhou"
    assert "o provedor caiu" in saida["erro"]


def test_no_reinicio_o_job_que_ficou_gerando_vira_interrompida(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    antigo = _cliente(tmp_path, executor)
    identificador = antigo.post("/api/execucoes", json=CORPO).json()["identificador"]
    assert executor.comecou.wait(10)

    novo = _cliente(tmp_path, ExecutorFalso())  # `criar_app` roda a recuperação no boot

    saida = novo.get(f"/api/execucoes/{identificador}/resumo").json()
    assert saida["status"] == "interrompida"
    assert "reiniciou" in saida["erro"]
    executor.liberar.set()
    assert _gerenciador(antigo).aguardar_ocioso()


def test_saida_antiga_sem_andamento_continua_na_lista(tmp_path: Path):
    from suno.gerador.execucao import gravar_execucao
    from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto
    from suno.dominio import Audiencia, Destino

    gravar_execucao(
        execucao_de_teste(historico_de_texto(Audiencia.INICIANTE, Destino.APROVADO)), tmp_path
    )
    cliente = _cliente(tmp_path)

    saidas = cliente.get("/api/execucoes").json()

    assert [s["status"] for s in saidas] == ["aguardando_revisao"]
    assert saidas[0]["posicoes"][0]["etapa"] is None
    assert cliente.get("/api/execucoes/exec-teste/andamento").status_code == 404


# ---------------------------------------------------------------------------
# Recusas
# ---------------------------------------------------------------------------


def test_ata_inexistente_responde_404(tmp_path: Path):
    resposta = _cliente(tmp_path, ExecutorFalso()).post(
        "/api/execucoes", json={**CORPO, "ata": "nao-existe"}
    )

    assert resposta.status_code == 404


@pytest.mark.parametrize(
    "pedido",
    [
        [],
        [
            {"audiencia": "iniciante", "formato": "carrossel"},
            {"audiencia": "iniciante", "formato": "carrossel"},
        ],
    ],
    ids=["vazio", "repetido"],
)
def test_pedido_vazio_ou_repetido_responde_422(tmp_path: Path, pedido):
    resposta = _cliente(tmp_path, ExecutorFalso()).post(
        "/api/execucoes", json={**CORPO, "pedido": pedido}
    )

    assert resposta.status_code == 422


def test_modo_desconhecido_responde_422(tmp_path: Path):
    resposta = _cliente(tmp_path, ExecutorFalso()).post(
        "/api/execucoes", json={**CORPO, "modo": "turbo"}
    )

    assert resposta.status_code == 422


def test_demo_sem_respostas_prontas_responde_422_com_o_motivo(tmp_path: Path):
    atas = tmp_path / "atas"
    atas.mkdir()
    (atas / "copom-999-2026-01-01.txt").write_text("Uma Ata sem demo.", encoding="utf-8")
    cliente = _cliente(tmp_path / "execucoes", ExecutorFalso(), atas=atas)

    resposta = cliente.post("/api/execucoes", json={**CORPO, "ata": "copom-999-2026-01-01"})

    assert resposta.status_code == 422
    assert "respostas prontas" in resposta.json()["detail"]


def test_real_sem_chave_responde_422(tmp_path: Path):
    resposta = _cliente(tmp_path, ExecutorFalso()).post(
        "/api/execucoes", json={**CORPO, "modo": "real"}
    )

    assert resposta.status_code == 422
    assert "chave" in resposta.json()["detail"]


def test_o_nome_nao_pode_passar_do_limite(tmp_path: Path):
    resposta = _cliente(tmp_path, ExecutorFalso()).post(
        "/api/execucoes", json={**CORPO, "nome": "x" * 121}
    )

    assert resposta.status_code == 422


# ---------------------------------------------------------------------------
# O pipeline de verdade, com o provedor falso da demo
# ---------------------------------------------------------------------------


def test_demo_de_duas_celulas_ponta_a_ponta(tmp_path: Path):
    cliente = _cliente(tmp_path)  # executor de verdade

    identificador = cliente.post("/api/execucoes", json={**CORPO, "nome": "Duas Células"}).json()[
        "identificador"
    ]
    assert _gerenciador(cliente).aguardar_ocioso(60)

    andamento = cliente.get(f"/api/execucoes/{identificador}/andamento").json()
    assert andamento["estado"] == "concluida"
    assert [c["etapa"] for c in andamento["celulas"]] == ["aprovada", "aprovada"]

    execucao = cliente.get(f"/api/execucoes/{identificador}").json()
    assert execucao["nome"] == "Duas Células"
    assert execucao["categoria"] == "copom"
    assert len(execucao["celulas"]) == 2
    assert len(execucao["pedido"]) == 2

    saida = cliente.get(f"/api/execucoes/{identificador}/resumo").json()
    assert saida["status"] == "aguardando_revisao"
    assert saida["total_celulas"] == 2
    assert [p["etapa"] for p in saida["posicoes"]] == [None, None]


def test_a_saida_gerada_se_decide_como_qualquer_outra(tmp_path: Path):
    cliente = _cliente(tmp_path)
    identificador = cliente.post("/api/execucoes", json=CORPO).json()["identificador"]
    assert _gerenciador(cliente).aguardar_ocioso(60)

    resposta = cliente.post(
        f"/api/execucoes/{identificador}/celulas/iniciante/carrossel/decisao",
        json={"estado": "aprovada", "revisor": "Lucas"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "aprovada"


# ---------------------------------------------------------------------------
# O que a tela precisa saber para habilitar Demo e Real
# ---------------------------------------------------------------------------


def test_a_ata_do_copom_280_diz_que_tem_demo(tmp_path: Path):
    atas = _cliente(tmp_path).get("/api/atas").json()

    assert [(a["identificador"], a["demo_disponivel"]) for a in atas] == [(ATA, True)]


def test_ata_sem_respostas_prontas_diz_que_nao_tem_demo(tmp_path: Path):
    pasta_atas = tmp_path / "atas"
    pasta_atas.mkdir()
    (pasta_atas / "copom-999-2026-01-01.txt").write_text("Uma Ata sem demo.", encoding="utf-8")

    atas = _cliente(tmp_path / "execucoes", atas=pasta_atas).get("/api/atas").json()

    assert atas[0]["demo_disponivel"] is False


def test_o_modo_real_so_esta_disponivel_com_chave_e_modelo(tmp_path: Path, monkeypatch):
    cliente = _cliente(tmp_path)
    assert cliente.get("/api/saude").json()["real_disponivel"] is False

    monkeypatch.setenv("GROQ_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GROQ_MODELO", "modelo-de-teste")

    assert cliente.get("/api/saude").json()["real_disponivel"] is True
