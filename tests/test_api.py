"""A API FastAPI: lê do disco o mesmo ``execucao.json`` e ``pacote.json`` que o Gerador e o
Pacote gravam. ``TestClient`` usa transporte em processo — a trava de rede (ADR 0001) não
entra em jogo, e por isso nenhum teste aqui precisa dela.

O que estes testes protegem:

- a tela lê exatamente o arquivo que o pytest lê (ADR 0006), campo a campo;
- Célula inexistente dá 404, nunca lista vazia disfarçada de sucesso;
- as três filas humanas (H3, H4, H5) separam certo a partir do mesmo ``execucao.json``;
- ``POST .../resolver`` é a única escrita, e uma leitura seguinte enxerga o resultado;
- ``/arquivos/`` nunca escapa da pasta da execução;
- a demo versionada em ``data/execucoes/demo-copom-280/`` é a execução que a banca vê.

ADR 0005.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from suno.api.app import criar_app
from suno.dominio import (
    AncoraNumerica,
    Ancoras,
    Audiencia,
    BlocoFala,
    Celula,
    ConferenciaVisual,
    Conteudo,
    Correcao,
    Destino,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    Laudo,
    Medida,
    Metrica,
    MotivoReprovacao,
    PacotePublicacao,
    Pendencia,
    Slide,
    Tentativa,
    Unidade,
)
from suno.gerador.execucao import carregar_execucao

IDENTIFICADOR = "copom-280-2026-08-05-0001"

ANCORA_DA_SELIC = AncoraNumerica(
    chave="selic_decidida",
    rotulo="Selic decidida",
    valor_literal="14,00",
    valor=14.0,
    unidade=Unidade.PERCENTUAL_AO_ANO,
    trecho="O Copom decidiu reduzir a taxa Selic para 14,00% a.a.",
)
ANCORA_DO_PLACAR = AncoraNumerica(
    chave="placar_votacao",
    rotulo="Placar da votação",
    valor_literal="7 a 0",
    valor=7.0,
    unidade=Unidade.VOTOS,
    trecho="A decisão foi tomada por 7 votos a 0.",
)


def _laudo_aprovado(celula: Celula) -> Laudo:
    return Laudo(
        audiencia=celula.audiencia,
        formato=celula.formato,
        medidas=[Medida(metrica=Metrica.ADERENCIA, valor=1.0, atingiu=True)],
        destino=Destino.APROVADO,
    )


def _laudo_reprovado_corrigivel(celula: Celula) -> Laudo:
    return Laudo(
        audiencia=celula.audiencia,
        formato=celula.formato,
        medidas=[Medida(metrica=Metrica.FLESCH_BR, valor=18.0, atingiu=False)],
        destino=Destino.REPROVADO_CORRIGIVEL,
        motivos=[MotivoReprovacao.FLESCH_BR],
        correcoes=[
            Correcao(
                metrica=Metrica.FLESCH_BR,
                valor_medido=18.0,
                faixa=None,
                distancia=7.0,
                instrucao="Flesch-BR medido 18,0; abaixo do Limiar da Audiência.",
            )
        ],
    )


def _celula_carrossel(audiencia: Audiencia) -> Celula:
    corpo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[
            Slide(titulo="A Selic caiu", corpo="Veja o novo patamar.", dado="selic_decidida"),
            Slide(titulo="Como foi a votação", corpo="Unanimidade.", dado="placar_votacao"),
        ],
        ancoras_citadas=["selic_decidida", "placar_votacao"],
    )
    return Celula(audiencia=audiencia, formato=Formato.CARROSSEL, conteudo=corpo)


def _celula_roteiro(audiencia: Audiencia) -> Celula:
    corpo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[BlocoFala(inicio_s=0, fim_s=6, fala="Os juros caíram.")],
    )
    return Celula(audiencia=audiencia, formato=Formato.ROTEIRO, conteudo=corpo)


@pytest.fixture
def ancoras() -> Ancoras:
    return Ancoras(
        ata="copom-280-2026-08-05",
        numericas=[ANCORA_DA_SELIC, ANCORA_DO_PLACAR],
    )


@pytest.fixture
def execucao_construida(ancoras: Ancoras) -> Execucao:
    """Uma Execução com uma Célula aprovada e uma na fila H4 — o suficiente para as três filas."""
    aprovada = _celula_carrossel(Audiencia.INICIANTE)
    teimosa = _celula_roteiro(Audiencia.INTERMEDIARIO)

    historico_aprovado = HistoricoCelula(
        audiencia=aprovada.audiencia,
        formato=aprovada.formato,
        tentativas=[Tentativa(rodada=0, celula=aprovada, laudo=_laudo_aprovado(aprovada))],
        destino_final=Destino.APROVADO,
        provedores_usados=["falso"],
    )
    historico_h4 = HistoricoCelula(
        audiencia=teimosa.audiencia,
        formato=teimosa.formato,
        tentativas=[
            Tentativa(rodada=0, celula=teimosa, laudo=_laudo_reprovado_corrigivel(teimosa)),
            Tentativa(rodada=1, celula=teimosa, laudo=_laudo_reprovado_corrigivel(teimosa)),
            Tentativa(rodada=2, celula=teimosa, laudo=_laudo_reprovado_corrigivel(teimosa)),
        ],
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
        provedores_usados=["falso"],
    )

    return Execucao(
        identificador=IDENTIFICADOR,
        ata="copom-280-2026-08-05",
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        concluida_em=datetime(2026, 8, 6, 12, 4, tzinfo=timezone.utc),
        ancoras=ancoras,
        celulas=[historico_aprovado, historico_h4],
        pendencias=[
            Pendencia(
                fila=FilaHumana.H4_REVISAO,
                audiencia=teimosa.audiencia,
                formato=teimosa.formato,
                motivo="flesch_br",
            )
        ],
    )


@pytest.fixture
def pacote_construido() -> PacotePublicacao:
    return PacotePublicacao(
        execucao=IDENTIFICADOR,
        audiencia=Audiencia.INICIANTE,
        formato=Formato.CARROSSEL,
        legenda="A Selic caiu para 14,00% a.a.\n\nConteúdo informativo. Não é recomendação.",
        hashtags=["#copom", "#selic"],
        imagens=[],
        conferencia=ConferenciaVisual(),
        aprovado_por_humano=False,
    )


@pytest.fixture
def execucao_em_disco(
    pasta_execucoes: Path, execucao_construida: Execucao, pacote_construido: PacotePublicacao
) -> Path:
    """Grava ``execucao.json`` e um ``pacote.json`` à mão, do mesmo jeito que o pytest lê."""
    raiz = pasta_execucoes / IDENTIFICADOR
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "execucao.json").write_text(
        execucao_construida.model_dump_json(indent=2), encoding="utf-8"
    )

    pasta_pacote = raiz / "pacote" / "iniciante-carrossel"
    pasta_pacote.mkdir(parents=True, exist_ok=True)
    (pasta_pacote / "pacote.json").write_text(
        pacote_construido.model_dump_json(indent=2), encoding="utf-8"
    )
    (pasta_pacote / "slide-01.png").write_bytes(b"\x89PNG\r\n\x1a\n falso png")

    return pasta_execucoes


@pytest.fixture
def cliente(execucao_em_disco: Path) -> TestClient:
    app = criar_app(execucao_em_disco)
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1 — a tela lê o mesmo arquivo que o pytest lê
# ---------------------------------------------------------------------------


def test_lista_de_execucoes_traz_o_identificador(cliente: TestClient) -> None:
    resposta = cliente.get("/api/execucoes")

    assert resposta.status_code == 200
    identificadores = [resumo["identificador"] for resumo in resposta.json()]
    assert identificadores == [IDENTIFICADOR]


def test_execucao_devolvida_bate_campo_a_campo_com_o_arquivo_em_disco(
    cliente: TestClient, execucao_em_disco: Path
) -> None:
    do_disco = json.loads(
        (execucao_em_disco / IDENTIFICADOR / "execucao.json").read_text(encoding="utf-8")
    )

    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["identificador"] == do_disco["identificador"] == IDENTIFICADOR
    assert corpo["ata"] == do_disco["ata"]
    assert corpo["provedor_gerador"] == do_disco["provedor_gerador"]
    assert corpo["ancoras"] == do_disco["ancoras"]
    assert corpo["celulas"] == do_disco["celulas"]
    assert corpo["pendencias"] == do_disco["pendencias"]


def test_execucao_inexistente_da_404(cliente: TestClient) -> None:
    resposta = cliente.get("/api/execucoes/nao-existe")
    assert resposta.status_code == 404


def test_ancoras_da_execucao(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/ancoras")
    assert resposta.status_code == 200
    chaves = {a["chave"] for a in resposta.json()["numericas"]}
    assert chaves == {"selic_decidida", "placar_votacao"}


# ---------------------------------------------------------------------------
# 2 — Célula existente e inexistente
# ---------------------------------------------------------------------------


def test_celula_existente_devolve_o_historico(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/celulas/iniciante/carrossel")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["audiencia"] == "iniciante"
    assert corpo["formato"] == "carrossel"
    assert corpo["destino_final"] == "aprovado"
    assert len(corpo["tentativas"]) == 1


def test_celula_inexistente_da_404(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/celulas/avancado/texto_analitico")
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# 3 — Âncoras ao lado da Célula
# ---------------------------------------------------------------------------


def test_ancoras_da_celula_traz_so_as_citadas_com_trecho(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/celulas/iniciante/carrossel/ancoras")

    assert resposta.status_code == 200
    corpo = resposta.json()
    chaves = {a["chave"] for a in corpo}
    assert chaves == {"selic_decidida", "placar_votacao"}
    for ancora in corpo:
        assert ancora["trecho"]


def test_ancoras_da_celula_sem_citacao_vem_vazia(cliente: TestClient) -> None:
    """O Roteiro da fixture não preenche ``ancoras_citadas``."""
    resposta = cliente.get(
        f"/api/execucoes/{IDENTIFICADOR}/celulas/intermediario/roteiro/ancoras"
    )
    assert resposta.status_code == 200
    assert resposta.json() == []


# ---------------------------------------------------------------------------
# 4 — as três filas separadas
# ---------------------------------------------------------------------------


def test_filas_separa_h3_h4_h5_no_cenario_da_fixture(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/filas")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["h3_desempate"] == [], "a fixture não liga o comitê: sem desempate"

    assert len(corpo["h4_revisao"]) == 1
    pendencia_h4 = corpo["h4_revisao"][0]
    assert pendencia_h4["fila"] == "h4_revisao"
    assert (pendencia_h4["audiencia"], pendencia_h4["formato"]) == ("intermediario", "roteiro")
    assert pendencia_h4["resolvida"] is False

    assert len(corpo["h5_aprovacao_pacote"]) == 1
    pendencia_h5 = corpo["h5_aprovacao_pacote"][0]
    assert pendencia_h5["fila"] == "h5_aprovacao_pacote"
    assert (pendencia_h5["audiencia"], pendencia_h5["formato"]) == ("iniciante", "carrossel")


# ---------------------------------------------------------------------------
# 5 — resolver grava, e uma leitura seguinte mostra ``resolvida=True``
# ---------------------------------------------------------------------------


def test_resolver_pendencia_grava_e_a_leitura_seguinte_confirma(
    cliente: TestClient, execucao_em_disco: Path
) -> None:
    resposta = cliente.post(
        f"/api/execucoes/{IDENTIFICADOR}/filas/h4/0/resolver",
        json={"decisao": "reescrita à mão, aprovada"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["resolvida"] is True
    assert resposta.json()["decisao"] == "reescrita à mão, aprovada"

    de_volta = carregar_execucao(IDENTIFICADOR, execucao_em_disco)
    assert de_volta.pendencias[0].resolvida is True
    assert de_volta.pendencias[0].decisao == "reescrita à mão, aprovada"

    segunda_leitura = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/filas")
    assert segunda_leitura.json()["h4_revisao"][0]["resolvida"] is True


def test_resolver_indice_fora_da_fila_da_404(cliente: TestClient) -> None:
    resposta = cliente.post(
        f"/api/execucoes/{IDENTIFICADOR}/filas/h4/9/resolver", json={"decisao": "x"}
    )
    assert resposta.status_code == 404


def test_aprovar_pacote_grava_e_a_leitura_seguinte_confirma(
    cliente: TestClient, execucao_em_disco: Path
) -> None:
    antes = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/pacotes").json()
    assert antes[0]["aprovado_por_humano"] is False

    resposta = cliente.post(
        f"/api/execucoes/{IDENTIFICADOR}/pacotes/iniciante/carrossel/aprovar"
    )

    assert resposta.status_code == 200
    assert resposta.json()["aprovado_por_humano"] is True

    depois = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/pacotes").json()
    assert depois[0]["aprovado_por_humano"] is True

    filas = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/filas").json()
    assert filas["h5_aprovacao_pacote"] == [], "aprovado não fica mais pendente em H5"


# ---------------------------------------------------------------------------
# 6 — ``/arquivos/`` nunca escapa da pasta
# ---------------------------------------------------------------------------


def test_arquivo_do_pacote_e_servido(cliente: TestClient) -> None:
    resposta = cliente.get(
        f"/api/execucoes/{IDENTIFICADOR}/arquivos/pacote/iniciante-carrossel/slide-01.png"
    )
    assert resposta.status_code == 200
    assert resposta.content.startswith(b"\x89PNG")


def test_arquivo_com_travessia_de_pasta_nunca_sai_da_pasta(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/arquivos/../../etc/passwd")
    assert resposta.status_code in (400, 404)


def test_arquivo_inexistente_da_404(cliente: TestClient) -> None:
    resposta = cliente.get(f"/api/execucoes/{IDENTIFICADOR}/arquivos/pacote/nao-existe.png")
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# 7 — /api/atas lista a Ata 280 do repositório
# ---------------------------------------------------------------------------


def test_lista_de_atas_traz_a_ata_280_do_repositorio(pasta_execucoes: Path) -> None:
    app = criar_app(pasta_execucoes)
    cliente_local = TestClient(app)

    resposta = cliente_local.get("/api/atas")

    assert resposta.status_code == 200
    identificadores = {ata["identificador"] for ata in resposta.json()}
    assert "copom-280-2026-08-05" in identificadores
    achada = next(a for a in resposta.json() if a["identificador"] == "copom-280-2026-08-05")
    assert "texto" not in achada


def test_ata_por_identificador_traz_o_texto(pasta_execucoes: Path) -> None:
    app = criar_app(pasta_execucoes)
    cliente_local = TestClient(app)

    resposta = cliente_local.get("/api/atas/copom-280-2026-08-05")

    assert resposta.status_code == 200
    assert len(resposta.json()["texto"]) > 100


def test_ata_inexistente_da_404(pasta_execucoes: Path) -> None:
    app = criar_app(pasta_execucoes)
    cliente_local = TestClient(app)

    resposta = cliente_local.get("/api/atas/nao-existe")
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# 8 — o OpenAPI carrega os schemas do domínio
# ---------------------------------------------------------------------------


def test_openapi_contem_os_schemas_do_dominio(cliente: TestClient) -> None:
    schema = cliente.app.openapi()
    nomes = set(schema["components"]["schemas"])
    for esperado in ("Execucao", "Laudo", "Pendencia", "PacotePublicacao"):
        assert esperado in nomes, f"{esperado} não está no OpenAPI"


def test_saude_conta_as_execucoes(cliente: TestClient) -> None:
    resposta = cliente.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True, "execucoes": 1}


# ---------------------------------------------------------------------------
# Robustez: concorrência no H4 e leitura de execução ilegível
# (achados do revisor de erros, 2026-09-19)
# ---------------------------------------------------------------------------


def test_seis_resolucoes_h4_concorrentes_nao_perdem_nenhuma(
    pasta_execucoes: Path, execucao_construida: Execucao
) -> None:
    """Antes da trava, seis `POST .../resolver` disparados juntos perdiam quatro decisões sem
    erro nenhum — o arquivo era lido, alterado e regravado sem exclusão mútua."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    seis_pendencias = [
        Pendencia(
            fila=FilaHumana.H4_REVISAO,
            audiencia=Audiencia.INTERMEDIARIO,
            formato=Formato.ROTEIRO,
            motivo="flesch_br",
        )
        for _ in range(6)
    ]
    execucao = execucao_construida.model_copy(update={"pendencias": seis_pendencias})
    raiz = pasta_execucoes / IDENTIFICADOR
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "execucao.json").write_text(execucao.model_dump_json(indent=2), encoding="utf-8")
    app = criar_app(pasta_execucoes)
    cliente_local = TestClient(app)

    barreira = Barrier(6)

    def resolver(indice: int) -> int:
        barreira.wait()
        resposta = cliente_local.post(
            f"/api/execucoes/{IDENTIFICADOR}/filas/h4/{indice}/resolver",
            json={"decisao": f"decisão {indice}"},
        )
        return resposta.status_code

    with ThreadPoolExecutor(max_workers=6) as executor:
        status = list(executor.map(resolver, range(6)))

    assert all(codigo == 200 for codigo in status)
    de_volta = carregar_execucao(IDENTIFICADOR, pasta_execucoes)
    assert sum(1 for p in de_volta.pendencias if p.resolvida) == 6, "as seis sobrevivem"


def test_execucao_ilegivel_sai_da_listagem_mas_da_409_na_leitura_direta(
    pasta_execucoes: Path,
) -> None:
    """Uma escrita interrompida deixa um `execucao.json` que não bate com o domínio (o real
    exemplo do revisor: ``{"nao": "e uma execucao"}``). Isso não pode derrubar a listagem
    inteira nem virar 500."""
    quebrada = pasta_execucoes / "quebrada"
    quebrada.mkdir(parents=True)
    (quebrada / "execucao.json").write_text('{"nao": "e uma execucao"}', encoding="utf-8")
    app = criar_app(pasta_execucoes)
    cliente_local = TestClient(app)

    listagem = cliente_local.get("/api/execucoes")
    assert listagem.status_code == 200
    assert "quebrada" not in {resumo["identificador"] for resumo in listagem.json()}

    direta = cliente_local.get("/api/execucoes/quebrada")
    assert direta.status_code == 409


def test_identificador_com_caractere_invalido_no_windows_da_404_nao_500(
    pasta_execucoes: Path,
) -> None:
    app = criar_app(pasta_execucoes)
    cliente_local = TestClient(app)
    resposta = cliente_local.get('/api/execucoes/a"b')
    assert resposta.status_code == 404


# ---------------------------------------------------------------------------
# A demo versionada — a execução que a banca vê
# ---------------------------------------------------------------------------


def _pasta_execucoes_do_repositorio() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "execucoes"


def test_a_demo_versionada_sobe_na_api_e_bate_com_o_disco() -> None:
    pasta = _pasta_execucoes_do_repositorio()
    app = criar_app(pasta)
    cliente_local = TestClient(app)
    identificador = "demo-copom-280"

    do_disco = json.loads((pasta / identificador / "execucao.json").read_text(encoding="utf-8"))

    resposta = cliente_local.get(f"/api/execucoes/{identificador}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["identificador"] == do_disco["identificador"]
    assert corpo["ata"] == do_disco["ata"]
    assert len(corpo["celulas"]) == len(do_disco["celulas"])
    assert corpo["pendencias"] == do_disco["pendencias"]

    pacotes = cliente_local.get(f"/api/execucoes/{identificador}/pacotes")
    assert pacotes.status_code == 200
    assert len(pacotes.json()) == 8, "oito Células aprovadas na demo ganham Pacote"
