"""A aba de configurações: o que se salva vale de verdade no roteador, no Jev, no checador e no limite."""

import pytest
from fastapi.testclient import TestClient

from suno import configuracoes
from suno.api.app import criar_app
from suno.avaliador.fidelidade import VerificadorDeFidelidade
from suno.avaliador.qualidade import AvaliadorDeQualidade
from suno.configuracoes import EntradaDeProvedor
from suno.dominio import PapelLLM
from suno.provedores import limitador
from suno.provedores.roteador import ProvedorTardio, roteador_para


@pytest.fixture
def cliente(tmp_path):
    return TestClient(criar_app(tmp_path / "execucoes", recuperar_ao_iniciar=False))


def _corpo(cliente):
    return cliente.get("/api/configuracoes").json()["configuracoes"]


def test_sem_arquivo_valem_o_ambiente_e_o_padrao(cliente):
    resposta = cliente.get("/api/configuracoes").json()
    assert resposta["salvas"] is False
    assert resposta["configuracoes"]["requisicoes_por_minuto"] == 0  # o conftest põe SUNO_RPM=0
    assert resposta["configuracoes"]["papeis"]["video"][0]["provedor"] == "groq"
    assert resposta["chaves"] == {"gemini": False, "groq": False, "jev": False}


def test_salvar_persiste_e_restaurar_volta_ao_ambiente(cliente):
    corpo = _corpo(cliente)
    corpo["requisicoes_por_minuto"] = 8
    corpo["fidelidade_ligada"] = False
    resposta = cliente.put("/api/configuracoes", json=corpo).json()
    assert resposta["salvas"] is True
    assert resposta["configuracoes"]["requisicoes_por_minuto"] == 8
    assert configuracoes.carregar().fidelidade_ligada is False
    voltou = cliente.delete("/api/configuracoes").json()
    assert voltou["salvas"] is False
    assert voltou["configuracoes"]["requisicoes_por_minuto"] == 0


@pytest.mark.parametrize(
    "mudanca",
    [
        {"jev_url": "http://exemplo.com"},
        {"requisicoes_por_minuto": -1},
        {"rodadas_de_correcao": 11},
        {"jev_limiar": 1.5},
        {"modelo_padrao": {"gemini": "dois nomes", "groq": "x"}},
    ],
)
def test_corpo_invalido_e_recusado(cliente, mudanca):
    corpo = {**_corpo(cliente), **mudanca}
    assert cliente.put("/api/configuracoes", json=corpo).status_code == 422
    assert cliente.get("/api/configuracoes").json()["salvas"] is False


def test_fila_vazia_ou_repetida_e_recusada(cliente):
    corpo = _corpo(cliente)
    corpo["papeis"]["video"] = []
    assert cliente.put("/api/configuracoes", json=corpo).status_code == 422
    corpo["papeis"]["video"] = [{"provedor": "groq", "modelo": ""}, {"provedor": "groq", "modelo": ""}]
    assert cliente.put("/api/configuracoes", json=corpo).status_code == 422


def test_o_roteador_segue_a_fila_e_o_modelo_salvos(cliente, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GEMINI_MODELO", "gemini-padrao")
    monkeypatch.setenv("GROQ_MODELO", "groq-padrao")
    antes = roteador_para(PapelLLM.VIDEO)
    assert [(p.nome, p.modelo) for p in antes.provedores] == [("groq", "groq-padrao"), ("gemini", "gemini-padrao")]
    corpo = _corpo(cliente)
    corpo["papeis"]["video"] = [
        {"provedor": "gemini", "modelo": "gemini-do-video"},
        {"provedor": "groq", "modelo": ""},
    ]
    cliente.put("/api/configuracoes", json=corpo)
    depois = roteador_para(PapelLLM.VIDEO)
    assert [(p.nome, p.modelo) for p in depois.provedores] == [("gemini", "gemini-do-video"), ("groq", "groq-padrao")]


def test_o_provedor_tardio_troca_sem_reiniciar(cliente, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GROQ_MODELO", "groq-padrao")
    tardio = ProvedorTardio(PapelLLM.VIDEO)
    assert tardio._atual().provedores[0].modelo == "groq-padrao"
    corpo = _corpo(cliente)
    corpo["modelo_padrao"]["groq"] = "groq-novo"
    cliente.put("/api/configuracoes", json=corpo)
    assert tardio._atual().provedores[0].modelo == "groq-novo"


def test_jev_e_checador_obedecem_o_que_foi_salvo(cliente, monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "x")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GROQ_MODELO", "m")
    assert AvaliadorDeQualidade.de_ambiente() is None  # o conftest desliga com SUNO_JEV=0
    assert VerificadorDeFidelidade.de_ambiente("ata") is None
    corpo = _corpo(cliente)
    corpo.update(jev_ligado=True, fidelidade_ligada=True, jev_limiar=0.7)
    cliente.put("/api/configuracoes", json=corpo)
    jev = AvaliadorDeQualidade.de_ambiente()
    assert jev is not None and jev.limiar == 0.7
    assert VerificadorDeFidelidade.de_ambiente("ata") is not None
    corpo.update(jev_ligado=False, fidelidade_ligada=False)
    cliente.put("/api/configuracoes", json=corpo)
    assert AvaliadorDeQualidade.de_ambiente() is None
    assert VerificadorDeFidelidade.de_ambiente("ata") is None


def test_o_limitador_usa_o_teto_salvo(cliente):
    corpo = _corpo(cliente)
    corpo["requisicoes_por_minuto"] = 8
    cliente.put("/api/configuracoes", json=corpo)
    assert limitador._maximo_do_ambiente() == 8


def test_entrada_de_provedor_limpa_o_modelo():
    assert EntradaDeProvedor(provedor="groq", modelo="  openai/gpt-oss-120b ").modelo == "openai/gpt-oss-120b"


def test_o_ciclo_usa_o_teto_de_rodadas_salvo(cliente):
    from suno.gerador import ciclo

    assert configuracoes.carregar().rodadas_de_correcao == 2  # SUNO_RODADAS=2 no conftest
    corpo = _corpo(cliente)
    corpo["rodadas_de_correcao"] = 5
    cliente.put("/api/configuracoes", json=corpo)
    assert ciclo.carregar_configuracoes().rodadas_de_correcao == 5


def test_uma_celula_aceita_a_rodada_do_teto_maximo():
    from suno.dominio import RODADAS_MAXIMAS, Celula, Tentativa

    assert Celula.model_fields["rodada"].metadata and Tentativa.model_fields["rodada"].metadata
    assert any(getattr(m, "le", None) == RODADAS_MAXIMAS for m in Celula.model_fields["rodada"].metadata)
