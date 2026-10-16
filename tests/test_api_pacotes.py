"""Montar o Pacote de publicação pela interface: `POST .../pacotes/montar` e o estado da montagem.

`montar_pacote` percorre as Células aprovadas individualmente. Uma pendência em outra Célula da
Matriz não bloqueia o Pacote da que já foi aprovada.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from suno.api.app import criar_app
from suno.api.pacotes import Montador
from suno.dominio import Audiencia, Destino, Formato, MotivoReprovacao
from suno.pacote import carrossel_html
from suno.gerador.execucao import executar, gravar_execucao
from tests.construtores_de_execucao import execucao_de_teste, historico_de_texto
from tests.test_geracao import ATA, PASTA_ATAS

COPOM = PASTA_ATAS / f"{ATA}.pdf"
CARROSSEL = (Audiencia.INICIANTE, Formato.CARROSSEL)
ROTEIRO = (Audiencia.INICIANTE, Formato.ROTEIRO)
TEIMOSA = (Audiencia.INTERMEDIARIO, Formato.ROTEIRO)  # a que a demo manda para a fila humana


def _cliente(pasta: Path, **trocas) -> TestClient:
    return TestClient(
        criar_app(pasta, pasta_atas=PASTA_ATAS, pasta_fontes=pasta.parent / "fontes", **trocas)
    )


def _montador(cliente: TestClient) -> Montador:
    return cliente.app.state.montador


def test_montar_pela_api_gera_os_pacotes_das_celulas_aprovadas(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, ROTEIRO], identificador="saida-1")
    cliente = _cliente(tmp_path)

    resposta = cliente.post("/api/execucoes/saida-1/pacotes/montar")

    assert resposta.status_code == 202
    assert _montador(cliente).aguardar("saida-1", 60)
    estado = cliente.get("/api/execucoes/saida-1/pacotes/montagem").json()
    assert estado["estado"] == "ok"
    assert estado["total"] == 2
    pacotes = cliente.get("/api/execucoes/saida-1/pacotes").json()
    assert sorted((p["audiencia"], p["formato"]) for p in pacotes) == [
        ("iniciante", "carrossel"),
        ("iniciante", "roteiro"),
    ]
    carrossel = next(p for p in pacotes if p["formato"] == "carrossel")
    assert len(carrossel["imagens"]) > 0
    assert (tmp_path / "saida-1" / "pacote" / "iniciante-carrossel" / "legenda.txt").exists()


def test_antes_de_montar_o_estado_e_ocioso(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, ROTEIRO], identificador="saida-1")

    estado = _cliente(tmp_path).get("/api/execucoes/saida-1/pacotes/montagem").json()

    assert estado["estado"] == "ocioso"


def test_montagem_de_uma_celula_nao_monta_as_demais(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, ROTEIRO], identificador="saida-alvo")
    cliente = _cliente(tmp_path)

    resposta = cliente.post(
        "/api/execucoes/saida-alvo/pacotes/montar",
        params={"audiencia": "iniciante", "formato": "carrossel"},
    )

    assert resposta.status_code == 202
    assert _montador(cliente).aguardar("saida-alvo", 60)
    estado = cliente.get("/api/execucoes/saida-alvo/pacotes/montagem").json()
    assert estado["total"] == 1
    pacotes = cliente.get("/api/execucoes/saida-alvo/pacotes").json()
    assert [(p["audiencia"], p["formato"]) for p in pacotes] == [
        ("iniciante", "carrossel")
    ]


def test_celula_aprovada_monta_mesmo_com_outra_pendente_na_matriz(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, TEIMOSA], identificador="saida-2")
    cliente = _cliente(tmp_path)

    resposta = cliente.post("/api/execucoes/saida-2/pacotes/montar")

    assert resposta.status_code == 202
    assert _montador(cliente).aguardar("saida-2", 60)
    pacotes = cliente.get("/api/execucoes/saida-2/pacotes").json()
    assert [(p["audiencia"], p["formato"]) for p in pacotes] == [
        ("iniciante", "carrossel")
    ]


def test_aprovacao_humana_libera_apenas_o_pacote_da_celula(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, TEIMOSA], identificador="saida-3")
    cliente = _cliente(tmp_path)

    primeira = cliente.post("/api/execucoes/saida-3/pacotes/montar")
    assert primeira.status_code == 202
    assert _montador(cliente).aguardar("saida-3", timeout=60)
    nomes = {p.name for p in (tmp_path / "saida-3" / "pacote").iterdir()}
    assert nomes == {"iniciante-carrossel"}

    decisao = cliente.post(
        "/api/execucoes/saida-3/celulas/intermediario/roteiro/decisao",
        json={"estado": "aprovada", "revisor": "Ana"},
    )
    assert decisao.status_code == 200

    resposta = cliente.post(
        "/api/execucoes/saida-3/pacotes/montar",
        params={"audiencia": "intermediario", "formato": "roteiro"},
    )
    assert resposta.status_code == 202
    assert _montador(cliente).aguardar("saida-3", timeout=60)
    assert cliente.get("/api/execucoes/saida-3/pacotes/montagem").json()["total"] == 1
    nomes = {p.name for p in (tmp_path / "saida-3" / "pacote").iterdir()}
    assert {"iniciante-carrossel", "intermediario-roteiro"} <= nomes


def test_sem_celula_aprovada_pelo_laudo_responde_409(tmp_path: Path):
    gravar_execucao(
        execucao_de_teste(
            historico_de_texto(
                Audiencia.INICIANTE,
                Destino.REPROVADO_REVISAO_HUMANA,
                (MotivoReprovacao.DENSIDADE,),
            )
        ),
        tmp_path,
    )

    resposta = _cliente(tmp_path).post("/api/execucoes/exec-teste/pacotes/montar")

    assert resposta.status_code == 409
    assert "foi aprovada" in resposta.json()["detail"]


def test_execucao_inexistente_responde_404(tmp_path: Path):
    cliente = _cliente(tmp_path)

    assert cliente.post("/api/execucoes/nao-existe/pacotes/montar").status_code == 404
    assert cliente.get("/api/execucoes/nao-existe/pacotes/montagem").status_code == 404


def test_duas_montagens_da_mesma_saida_nao_rodam_juntas(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, ROTEIRO], identificador="saida-1")
    liberar = threading.Event()
    comecou = threading.Event()
    chamadas: list[str] = []

    def devagar(identificador, pasta):
        chamadas.append(identificador)
        comecou.set()
        assert liberar.wait(10)
        return []

    cliente = _cliente(tmp_path, montar_fn=devagar)

    cliente.post("/api/execucoes/saida-1/pacotes/montar")
    assert comecou.wait(10)
    segunda = cliente.post("/api/execucoes/saida-1/pacotes/montar")

    assert segunda.status_code == 202
    assert segunda.json()["estado"] == "rodando"
    liberar.set()
    assert _montador(cliente).aguardar("saida-1", 10)
    assert chamadas == ["saida-1"]


def test_falha_da_montagem_vira_erro_sem_derrubar_a_api(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, ROTEIRO], identificador="saida-1")

    def quebrar(identificador, pasta):
        raise RuntimeError("Pillow não achou a fonte")

    cliente = _cliente(tmp_path, montar_fn=quebrar)
    cliente.post("/api/execucoes/saida-1/pacotes/montar")
    assert _montador(cliente).aguardar("saida-1", 10)

    estado = cliente.get("/api/execucoes/saida-1/pacotes/montagem").json()

    assert estado["estado"] == "erro"
    assert "Pillow" in estado["mensagem"]
    assert cliente.get("/api/saude").status_code == 200


def test_montar_de_novo_depois_de_um_erro_funciona(tmp_path: Path):
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL, ROTEIRO], identificador="saida-1")
    falhas = [True]

    def uma_vez_quebra(identificador, pasta):
        if falhas:
            falhas.clear()
            raise RuntimeError("primeira vez falha")
        return []

    cliente = _cliente(tmp_path, montar_fn=uma_vez_quebra)
    cliente.post("/api/execucoes/saida-1/pacotes/montar")
    assert _montador(cliente).aguardar("saida-1", 10)
    assert cliente.get("/api/execucoes/saida-1/pacotes/montagem").json()["estado"] == "erro"

    cliente.post("/api/execucoes/saida-1/pacotes/montar")
    assert _montador(cliente).aguardar("saida-1", 10)

    assert cliente.get("/api/execucoes/saida-1/pacotes/montagem").json()["estado"] == "ok"


@pytest.mark.skipif(not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado")
def test_montar_com_referencia_visual_troca_o_design_da_saida_antes_de_montar(tmp_path: Path, monkeypatch):
    from suno.gerador.execucao import carregar_execucao

    monkeypatch.setenv("SUNO_RENDER", "puppeteer")

    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL], identificador="saida-design")
    cliente = _cliente(tmp_path)
    referencias = cliente.get("/api/referencias-visuais").json()
    noticia = next(r for r in referencias if r["composicao"].startswith("noticia"))

    resposta = cliente.post(
        "/api/execucoes/saida-design/pacotes/montar",
        params={"audiencia": "iniciante", "formato": "carrossel", "referencia_visual": noticia["identificador"]},
    )

    assert resposta.status_code == 202
    assert _montador(cliente).aguardar("saida-design", 90)
    gravada = carregar_execucao("saida-design", tmp_path)
    assert gravada.referencia_visual == noticia["identificador"]
    assert gravada.composicao_visual.value == noticia["composicao"]
    carrossel = next(p for p in cliente.get("/api/execucoes/saida-design/pacotes").json() if p["formato"] == "carrossel")
    assert carrossel["direcao_de_arte"]["familia"] == "noticia"


def test_montar_com_referencia_inexistente_responde_422_sem_mexer_na_saida(tmp_path: Path):
    from suno.gerador.execucao import carregar_execucao

    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL], identificador="saida-design")
    cliente = _cliente(tmp_path)

    resposta = cliente.post(
        "/api/execucoes/saida-design/pacotes/montar",
        params={"audiencia": "iniciante", "formato": "carrossel", "referencia_visual": "nao-existe"},
    )

    assert resposta.status_code == 422
    assert carregar_execucao("saida-design", tmp_path).referencia_visual is None


FLORESTA = "#0C1A14,#F1FBF5,#3DDC84,#1B6B45"


@pytest.mark.skipif(not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado")
def test_montar_com_paleta_recolore_e_a_previa_troca_de_paleta_sem_montar(tmp_path: Path, monkeypatch):
    from suno.gerador.execucao import carregar_execucao

    monkeypatch.setenv("SUNO_RENDER", "puppeteer")
    executar(COPOM, "falso", tmp_path, pedido=[CARROSSEL], identificador="saida-paleta")
    cliente = _cliente(tmp_path)
    referencias = cliente.get("/api/referencias-visuais").json()
    dados = next(r for r in referencias if r["composicao"].startswith("dados"))

    resposta = cliente.post(
        "/api/execucoes/saida-paleta/pacotes/montar",
        params={
            "audiencia": "iniciante",
            "formato": "carrossel",
            "referencia_visual": dados["identificador"],
            "paleta": FLORESTA,
        },
    )

    assert resposta.status_code == 202
    assert _montador(cliente).aguardar("saida-paleta", 90)
    assert carregar_execucao("saida-paleta", tmp_path).paleta_visual.destaque == "#3DDC84"
    previa = cliente.get(
        "/api/execucoes/saida-paleta/pacotes/iniciante/carrossel/1/previa",
        params={"paleta": "#07252B,#EAFBFF,#FF6B6B,#0E5C6B"},
    )
    assert previa.status_code == 200
    assert "#07252b" in previa.text
    assert "file://" not in previa.text


def test_previa_da_referencia_recolore_o_exemplo(tmp_path: Path):
    cliente = _cliente(tmp_path)
    referencias = cliente.get("/api/referencias-visuais").json()
    dados = next(r for r in referencias if r["composicao"] == "dados_texto_grande")

    original = cliente.get(f"/api/referencias-visuais/{dados['identificador']}/previa")
    recolorida = cliente.get(
        f"/api/referencias-visuais/{dados['identificador']}/previa", params={"paleta": FLORESTA}
    )

    assert original.status_code == recolorida.status_code == 200
    assert "#b80000" in original.text
    assert "#b80000" not in recolorida.text
    assert "#3ddc84" in recolorida.text
    assert "data:font/woff2;base64," in recolorida.text
    assert "file://" not in recolorida.text


def test_paleta_invalida_responde_422(tmp_path: Path):
    cliente = _cliente(tmp_path)
    referencias = cliente.get("/api/referencias-visuais").json()
    dados = next(r for r in referencias if r["composicao"] == "dados_texto_grande")

    resposta = cliente.get(
        f"/api/referencias-visuais/{dados['identificador']}/previa", params={"paleta": "verde"}
    )

    assert resposta.status_code == 422
