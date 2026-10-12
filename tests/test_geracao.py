"""O `Gerenciador`: um job por vez, `andamento.json` ao lado de `execucao.json`, recuperação no boot.

O executor é um falso controlável: nada aqui chama o pipeline nem a rede. A integração com o
pipeline de verdade (provedor falso da demo) fica em `tests/test_api_geracao.py`.

ADR 0017.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from suno.api.geracao import (
    NOME_DO_ANDAMENTO,
    AtaNaoEncontrada,
    Gerenciador,
    ModoDeGeracao,
    PedidoRecusado,
    ler_andamento,
)
from suno.origens.repositorio import RepositorioDeAtas
from suno.dominio import (
    Ancoras,
    Andamento,
    Audiencia,
    EstadoDoAndamento,
    EtapaDaCelula,
    Execucao,
    FaseDaExecucao,
    Formato,
    PosicaoDaMatriz,
)

ATA = "copom-280-2026-08-05"
RAIZ = Path(__file__).resolve().parent.parent
PASTA_ATAS = RAIZ / "data" / "atas"

CARROSSEL = PosicaoDaMatriz(audiencia=Audiencia.INICIANTE, formato=Formato.CARROSSEL)
ROTEIRO = PosicaoDaMatriz(audiencia=Audiencia.INICIANTE, formato=Formato.ROTEIRO)


class ExecutorFalso:
    """Imita `executar`: avisa as fases e as Células e devolve uma Execucao mínima."""

    def __init__(self, *, bloquear: bool = False, falha: BaseException | None = None) -> None:
        self.bloquear = bloquear
        self.falha = falha
        self.chamadas: list[dict] = []
        self.comecou = threading.Event()
        self.liberar = threading.Event()

    def __call__(self, caminho_ata, provedor, pasta_execucoes, **argumentos) -> Execucao:
        caminhos = (
            [Path(caminho_ata)]
            if isinstance(caminho_ata, (str, Path))
            else [Path(c) for c in caminho_ata]
        )
        self.chamadas.append(
            {
                "ata": caminhos[0].stem,
                "atas": [c.stem for c in caminhos],
                "provedor": provedor,
                **argumentos,
            }
        )
        argumentos["ao_mudar_fase"](FaseDaExecucao.GERANDO_CELULAS)
        for audiencia, formato in argumentos["pedido"]:
            argumentos["ao_andar"](audiencia, formato, EtapaDaCelula.GERANDO, 0)
        self.comecou.set()
        if self.bloquear:
            assert self.liberar.wait(10), "o teste esqueceu de liberar o executor"
        if self.falha is not None:
            raise self.falha
        for audiencia, formato in argumentos["pedido"]:
            argumentos["ao_andar"](audiencia, formato, EtapaDaCelula.APROVADA, 0)
        return Execucao(
            identificador=argumentos["identificador"],
            ata=caminhos[0].stem,
            provedor_gerador=provedor,
            iniciada_em=datetime.now(timezone.utc),
            ancoras=Ancoras(ata=caminhos[0].stem),
        )


def _gerenciador(tmp_path: Path, executor: ExecutorFalso) -> Gerenciador:
    return Gerenciador(tmp_path, pasta_atas=PASTA_ATAS, executar_fn=executor)


def _pedir(gerenciador: Gerenciador, **trocas) -> Andamento:
    argumentos = {
        "ata": ATA,
        "modo": ModoDeGeracao.DEMO,
        "pedido": [CARROSSEL, ROTEIRO],
        "nome": None,
        "comite": False,
    }
    argumentos.update(trocas)
    return gerenciador.pedir(**argumentos)


def test_o_pedido_entra_na_fila_e_o_job_conclui(tmp_path: Path):
    executor = ExecutorFalso()
    gerenciador = _gerenciador(tmp_path, executor)

    andamento = _pedir(gerenciador, nome="Minha Saída")

    assert andamento.estado is EstadoDoAndamento.NA_FILA
    assert andamento.nome == "Minha Saída"
    assert andamento.identificador.startswith(f"{ATA}-falso-")
    assert [c.etapa for c in andamento.celulas] == [EtapaDaCelula.AGUARDANDO] * 2
    assert gerenciador.aguardar_ocioso()

    final = gerenciador.andamento(andamento.identificador)
    assert final is not None
    assert final.estado is EstadoDoAndamento.CONCLUIDA
    assert final.concluido_em is not None
    assert [c.etapa for c in final.celulas] == [EtapaDaCelula.APROVADA] * 2
    assert executor.chamadas[0]["identificador"] == andamento.identificador
    assert executor.chamadas[0]["provedor"] == "falso"
    assert executor.chamadas[0]["nome"] == "Minha Saída"
    assert executor.chamadas[0]["pedido"] == [
        (Audiencia.INICIANTE, Formato.CARROSSEL),
        (Audiencia.INICIANTE, Formato.ROTEIRO),
    ]


def test_o_andamento_vai_para_o_disco_ao_lado_da_execucao(tmp_path: Path):
    gerenciador = _gerenciador(tmp_path, ExecutorFalso())

    andamento = _pedir(gerenciador)
    assert gerenciador.aguardar_ocioso()

    arquivo = tmp_path / andamento.identificador / NOME_DO_ANDAMENTO
    assert arquivo.exists()
    do_disco = ler_andamento(tmp_path, andamento.identificador)
    assert do_disco is not None
    assert do_disco.estado is EstadoDoAndamento.CONCLUIDA
    assert not list((tmp_path / andamento.identificador).glob("*.tmp"))


def test_so_um_job_roda_por_vez(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    gerenciador = _gerenciador(tmp_path, executor)

    primeiro = _pedir(gerenciador)
    assert executor.comecou.wait(10)
    segundo = _pedir(gerenciador)

    assert gerenciador.andamento(primeiro.identificador).estado is EstadoDoAndamento.GERANDO
    assert gerenciador.andamento(segundo.identificador).estado is EstadoDoAndamento.NA_FILA
    assert len(executor.chamadas) == 1

    executor.liberar.set()
    assert gerenciador.aguardar_ocioso()

    assert [c["identificador"] for c in executor.chamadas] == [
        primeiro.identificador,
        segundo.identificador,
    ]
    assert gerenciador.andamento(segundo.identificador).estado is EstadoDoAndamento.CONCLUIDA


def test_as_etapas_chegam_ao_arquivo_enquanto_o_job_roda(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    gerenciador = _gerenciador(tmp_path, executor)

    andamento = _pedir(gerenciador)
    assert executor.comecou.wait(10)

    no_disco = ler_andamento(tmp_path, andamento.identificador)
    assert no_disco is not None
    assert no_disco.estado is EstadoDoAndamento.GERANDO
    assert no_disco.fase is FaseDaExecucao.GERANDO_CELULAS
    assert [c.etapa for c in no_disco.celulas] == [EtapaDaCelula.GERANDO] * 2

    executor.liberar.set()
    assert gerenciador.aguardar_ocioso()


def test_executor_que_levanta_vira_falhou_sem_credencial(tmp_path: Path):
    executor = ExecutorFalso(falha=RuntimeError("deu ruim: api_key=AIzaSyAbcdefghijklmnop123"))
    gerenciador = _gerenciador(tmp_path, executor)

    andamento = _pedir(gerenciador)
    assert gerenciador.aguardar_ocioso()

    final = gerenciador.andamento(andamento.identificador)
    assert final is not None
    assert final.estado is EstadoDoAndamento.FALHOU
    assert final.erro is not None and "deu ruim" in final.erro
    assert "AIza" not in final.erro


def test_job_que_falha_nao_trava_a_fila(tmp_path: Path):
    executor = ExecutorFalso(falha=RuntimeError("primeiro quebra"))
    gerenciador = _gerenciador(tmp_path, executor)
    primeiro = _pedir(gerenciador)
    assert gerenciador.aguardar_ocioso()

    executor.falha = None
    segundo = _pedir(gerenciador)
    assert gerenciador.aguardar_ocioso()

    assert gerenciador.andamento(primeiro.identificador).estado is EstadoDoAndamento.FALHOU
    assert gerenciador.andamento(segundo.identificador).estado is EstadoDoAndamento.CONCLUIDA


def test_no_boot_o_que_estava_gerando_vira_interrompida(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    antigo = _gerenciador(tmp_path, executor)
    gerando = _pedir(antigo)
    assert executor.comecou.wait(10)
    na_fila = _pedir(antigo)

    # Um servidor novo sobre a mesma pasta: o job do antigo morreu com ele.
    novo = _gerenciador(tmp_path, ExecutorFalso())
    recuperados = novo.recuperar_interrompidos()

    assert sorted(recuperados) == sorted([gerando.identificador, na_fila.identificador])
    for identificador in recuperados:
        andamento = novo.andamento(identificador)
        assert andamento is not None
        assert andamento.estado is EstadoDoAndamento.INTERROMPIDA
        assert andamento.erro is not None and "reiniciou" in andamento.erro

    executor.liberar.set()
    assert antigo.aguardar_ocioso()


def test_recuperar_nao_mexe_no_que_ja_terminou(tmp_path: Path):
    primeiro = _gerenciador(tmp_path, ExecutorFalso())
    concluido = _pedir(primeiro)
    assert primeiro.aguardar_ocioso()

    segundo = _gerenciador(tmp_path, ExecutorFalso())

    assert segundo.recuperar_interrompidos() == []
    assert segundo.andamento(concluido.identificador).estado is EstadoDoAndamento.CONCLUIDA


def test_dois_pedidos_no_mesmo_segundo_nao_colidem(tmp_path: Path):
    executor = ExecutorFalso(bloquear=True)
    gerenciador = _gerenciador(tmp_path, executor)

    ids = {_pedir(gerenciador).identificador for _ in range(4)}

    assert len(ids) == 4
    executor.liberar.set()
    assert gerenciador.aguardar_ocioso()


def test_listar_junta_o_que_esta_em_memoria_e_o_que_so_esta_no_disco(tmp_path: Path):
    antigo = _gerenciador(tmp_path, ExecutorFalso())
    do_disco = _pedir(antigo)
    assert antigo.aguardar_ocioso()

    novo = _gerenciador(tmp_path, ExecutorFalso())
    em_memoria = _pedir(novo)
    assert novo.aguardar_ocioso()

    assert {a.identificador for a in novo.listar()} == {
        do_disco.identificador,
        em_memoria.identificador,
    }


def test_sem_andamento_devolve_none(tmp_path: Path):
    assert _gerenciador(tmp_path, ExecutorFalso()).andamento("nao-existe") is None


# ---------------------------------------------------------------------------
# Recusas antes de enfileirar
# ---------------------------------------------------------------------------


def test_pedido_vazio_e_recusado(tmp_path: Path):
    with pytest.raises(PedidoRecusado, match="ao menos uma Célula"):
        _pedir(_gerenciador(tmp_path, ExecutorFalso()), pedido=[])


def test_posicao_repetida_e_recusada(tmp_path: Path):
    with pytest.raises(PedidoRecusado, match="repetida"):
        _pedir(_gerenciador(tmp_path, ExecutorFalso()), pedido=[CARROSSEL, CARROSSEL])


def test_ata_inexistente_e_recusada(tmp_path: Path):
    with pytest.raises(AtaNaoEncontrada):
        _pedir(_gerenciador(tmp_path, ExecutorFalso()), ata="nao-existe")


def test_nome_comprido_demais_e_recusado(tmp_path: Path):
    with pytest.raises(PedidoRecusado, match="120"):
        _pedir(_gerenciador(tmp_path, ExecutorFalso()), nome="x" * 121)


def test_demo_sem_respostas_prontas_e_recusada_com_o_motivo(tmp_path: Path):
    atas = tmp_path / "atas"
    atas.mkdir()
    (atas / "copom-999-2026-01-01.txt").write_text("Texto de uma Ata sem demo.", encoding="utf-8")
    gerenciador = Gerenciador(tmp_path / "execucoes", pasta_atas=atas, executar_fn=ExecutorFalso())

    with pytest.raises(PedidoRecusado, match="respostas prontas"):
        _pedir(gerenciador, ata="copom-999-2026-01-01")


def test_real_sem_chave_no_ambiente_e_recusado(tmp_path: Path):
    with pytest.raises(PedidoRecusado, match="chave"):
        _pedir(_gerenciador(tmp_path, ExecutorFalso()), modo=ModoDeGeracao.REAL)


def test_real_com_chave_e_aceito_e_usa_o_roteador(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODELO", "modelo-de-teste")
    executor = ExecutorFalso()
    gerenciador = _gerenciador(tmp_path, executor)

    andamento = _pedir(gerenciador, modo=ModoDeGeracao.REAL)
    assert gerenciador.aguardar_ocioso()

    assert andamento.provedor == "roteador"
    assert executor.chamadas[0]["provedor"] == "roteador"


def test_ata_cuja_extracao_vai_falhar_e_recusada_antes_de_gastar_cota(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setenv("GEMINI_MODELO", "modelo-de-teste")
    fontes = tmp_path / "fontes" / "importados"
    fontes.mkdir(parents=True)
    (fontes / "sem-numero.txt").write_text(
        "São Paulo, 8 de outubro de 2026. A companhia pediu o cancelamento do registro.",
        encoding="utf-8",
    )
    (fontes / "sem-numero.json").write_text(
        '{"titulo": "Sem número", "data_referencia": "2026-10-08", '
        '"categoria": "importada", "origem": "importados"}',
        encoding="utf-8",
    )
    executor = ExecutorFalso()
    gerenciador = Gerenciador(
        tmp_path / "execucoes",
        pasta_atas=PASTA_ATAS,
        executar_fn=executor,
        repositorio=RepositorioDeAtas(PASTA_ATAS, tmp_path / "fontes"),
    )

    with pytest.raises(PedidoRecusado, match="número com unidade"):
        _pedir(gerenciador, ata="sem-numero", modo=ModoDeGeracao.REAL)

    assert executor.chamadas == []
