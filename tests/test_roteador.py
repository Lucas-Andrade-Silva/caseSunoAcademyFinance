"""O roteador: esperar quando a cota volta sozinha, trocar quando não volta (ADR 0007).

Tudo aqui roda com ``ProvedorFalso`` e um ``dormir`` que só anota o tempo. Nenhuma linha
toca na rede nem no relógio de verdade.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from suno.dominio import (
    CotaEsgotada,
    ErroProvedor,
    EsgotamentoDeCota,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    RespostaMalformada,
)
from suno.provedores import ProvedorFalso
from suno.provedores.roteador import Roteador, provedor_por_nome, roteador_para


class Saida(BaseModel):
    titulo: str
    valor: int


class EsperaAnotada:
    """Substitui ``time.sleep``: guarda quanto teria dormido, e não dorme."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    def anotar(self, segundos: float) -> None:
        self.esperas.append(segundos)


def _nao_dormir(segundos: float) -> None:
    """Nenhum teste dorme de verdade: a espera é injetada (regra comum dos agentes)."""


def _falso(nome: str, respostas: list) -> ProvedorFalso:
    provedor = ProvedorFalso(respostas)
    provedor.nome = nome  # o roteador identifica o provedor pelo nome, não pela classe
    return provedor


def _pedido(rotulo: str = "celula:iniciante:carrossel:0") -> PedidoLLM:
    return PedidoLLM(
        papel=PapelLLM.GERADOR,
        rotulo=rotulo,
        mensagens=[Mensagem(autor="usuario", texto="resuma a Ata")],
    )


# -- 1. cota por minuto: espera e insiste no mesmo provedor -------------------


def test_429_por_minuto_espera_o_tempo_sugerido_e_repete_o_mesmo_provedor():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_MINUTO, 12.0), "veio do gemini"])
    groq = _falso("groq", ["veio do groq"])
    espera = EsperaAnotada()
    roteador = Roteador([gemini, groq], dormir=espera.anotar)

    resposta = roteador.completar(_pedido())

    assert resposta.texto == "veio do gemini"
    assert resposta.provedor == "gemini"
    assert espera.esperas == [12.0]
    assert groq.pedidos == [], "cota por minuto não pode gastar a cota do próximo"
    assert "esperando 12 s" in roteador.historico[0]


def test_espera_sem_tempo_sugerido_usa_o_padrao_e_respeita_o_teto():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_MINUTO), "ok"])
    espera = EsperaAnotada()
    Roteador([gemini], dormir=espera.anotar, espera_maxima_s=5.0).completar(_pedido())
    assert espera.esperas == [5.0], "o teto de espera vale mesmo quando o provedor pede mais"


def test_por_minuto_insistente_troca_de_provedor_depois_do_teto_de_tentativas():
    teimoso = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_MINUTO, 1.0)] * 5)
    groq = _falso("groq", ["veio do groq"])
    espera = EsperaAnotada()
    roteador = Roteador([teimoso, groq], dormir=espera.anotar, tentativas_por_minuto=2)

    resposta = roteador.completar(_pedido())

    assert resposta.provedor == "groq"
    assert espera.esperas == [1.0, 1.0]
    assert "gemini" not in roteador.esgotados, "cota por minuto não mata o provedor no dia"


# -- 2 e 3. cota diária (e desconhecida): troca e não volta -------------------


def test_429_diario_troca_na_hora_e_a_chamada_seguinte_ja_vai_ao_segundo():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_DIA)])
    groq = _falso("groq", ["primeira", "segunda"])
    espera = EsperaAnotada()
    roteador = Roteador([gemini, groq], dormir=espera.anotar)

    assert roteador.completar(_pedido()).texto == "primeira"
    assert roteador.completar(_pedido()).texto == "segunda"

    assert espera.esperas == [], "erro diário não se resolve esperando"
    assert len(gemini.pedidos) == 1, "o provedor esgotado no dia não é procurado de novo"
    assert gemini.restantes() == 0
    assert "esgotado no dia" in roteador.historico[0]


def test_esgotamento_desconhecido_se_comporta_como_diario():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.DESCONHECIDO)])
    groq = _falso("groq", ["primeira", "segunda"])
    espera = EsperaAnotada()
    roteador = Roteador([gemini, groq], dormir=espera.anotar)

    assert roteador.completar(_pedido()).provedor == "groq"
    assert roteador.completar(_pedido()).provedor == "groq"

    assert espera.esperas == []
    assert roteador.esgotados == {"gemini"}
    assert "sem pista" in roteador.historico[0]


# -- 4. a troca não perde a saída estruturada --------------------------------


def test_troca_de_provedor_preserva_o_schema_no_pedido():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_DIA)])
    groq = _falso("groq", [{"titulo": "Selic", "valor": 15}])
    roteador = Roteador([gemini, groq], dormir=_nao_dormir)

    saida = roteador.completar_estruturado(_pedido(), Saida)

    assert saida == Saida(titulo="Selic", valor=15)
    assert groq.pedidos[-1].schema_saida is not None, "o schema viaja no pedido (ADR 0007)"
    assert groq.pedidos[-1].schema_saida == Saida.model_json_schema()
    assert gemini.pedidos[-1].schema_saida == groq.pedidos[-1].schema_saida


def test_resposta_fora_do_schema_troca_de_provedor():
    gemini = _falso("gemini", ['{"titulo": "sem o valor"}'])
    groq = _falso("groq", [{"titulo": "Selic", "valor": 15}])
    roteador = Roteador([gemini, groq], dormir=_nao_dormir)

    assert roteador.completar_estruturado(_pedido(), Saida) == Saida(titulo="Selic", valor=15)
    assert "fora do schema" in roteador.historico[0]


def test_resposta_malformada_do_provedor_passa_ao_proximo():
    gemini = _falso("gemini", [RespostaMalformada("gemini", "sem 'candidates'")])
    groq = _falso("groq", ["veio do groq"])
    roteador = Roteador([gemini, groq], dormir=_nao_dormir)
    assert roteador.completar(_pedido()).provedor == "groq"


def test_erro_generico_ganha_uma_segunda_chance_no_mesmo_provedor():
    gemini = _falso("gemini", [ErroProvedor("gemini", "HTTP 503"), "na segunda foi"])
    roteador = Roteador([gemini], dormir=_nao_dormir)

    assert roteador.completar(_pedido()).texto == "na segunda foi"

    gemini2 = _falso("gemini", [ErroProvedor("gemini", "HTTP 503"), ErroProvedor("gemini", "HTTP 503")])
    groq = _falso("groq", ["veio do groq"])
    assert Roteador([gemini2, groq], dormir=_nao_dormir).completar(_pedido()).provedor == "groq"


# -- 5. excluir ---------------------------------------------------------------


def test_excluir_nunca_chama_o_provedor_excluido():
    gemini = _falso("gemini", ["não deveria sair daqui"])
    groq = _falso("groq", ["veio do groq"])
    roteador = Roteador([gemini, groq], excluir=("gemini",), dormir=_nao_dormir)

    assert roteador.completar(_pedido()).provedor == "groq"
    assert gemini.pedidos == [], "o juiz não pode cair no provedor do Gerador (ADR 0008)"
    assert [p.nome for p in roteador.provedores] == ["groq"]


def test_excluir_todo_mundo_e_erro_de_configuracao():
    with pytest.raises(ErroProvedor):
        Roteador([_falso("gemini", ["x"])], excluir=("gemini",))


# -- 6. ninguém respondeu -----------------------------------------------------


def test_todos_esgotados_levanta_cota_do_roteador_com_o_historico():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_DIA)])
    groq = _falso("groq", [CotaEsgotada("groq", EsgotamentoDeCota.POR_DIA)])
    sambanova = _falso("sambanova", [CotaEsgotada("sambanova", EsgotamentoDeCota.DESCONHECIDO)])
    roteador = Roteador([gemini, groq, sambanova], dormir=_nao_dormir)

    with pytest.raises(CotaEsgotada) as achado:
        roteador.completar(_pedido())

    assert achado.value.provedor == "roteador"
    assert achado.value.esgotamento is EsgotamentoDeCota.POR_DIA
    assert len(roteador.historico) == 3
    for nome in ("gemini", "groq", "sambanova"):
        assert nome in str(achado.value)


# -- 7. quem respondeu fica registrado ---------------------------------------


def test_a_resposta_diz_o_provedor_concreto_nao_o_roteador():
    gemini = _falso("gemini", [CotaEsgotada("gemini", EsgotamentoDeCota.POR_DIA)])
    groq = _falso("groq", ["veio do groq"])
    resposta = Roteador([gemini, groq], dormir=_nao_dormir).completar(_pedido())

    assert resposta.provedor == "groq", "a Célula grava quem gerou, para o juiz excluir (ADR 0008)"


# -- 8. montagem a partir do ambiente ----------------------------------------


def test_provedor_por_nome_falso_nao_precisa_de_chave():
    assert isinstance(provedor_por_nome("falso"), ProvedorFalso)


def test_provedor_por_nome_carrega_respostas_prontas(tmp_path):
    arquivo = tmp_path / "respostas.json"
    arquivo.write_text('{"extracao": ["{}"]}', encoding="utf-8")
    provedor = provedor_por_nome("falso", respostas_prontas=arquivo)
    assert isinstance(provedor, ProvedorFalso)
    assert provedor.restantes("extracao") == 1


def test_provedor_por_nome_sem_chave_no_ambiente_explica_o_env():
    with pytest.raises(ErroProvedor) as achado:
        provedor_por_nome("gemini")
    assert "GEMINI_API_KEY" in str(achado.value)


def test_provedor_por_nome_desconhecido_e_erro():
    with pytest.raises(ErroProvedor):
        provedor_por_nome("openai")


def test_provedor_concreto_exige_nome_de_modelo_no_ambiente(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "chave-de-mentira")
    monkeypatch.delenv("GROQ_MODELO", raising=False)
    with pytest.raises(ErroProvedor) as achado:
        provedor_por_nome("groq")
    assert "GROQ_MODELO" in str(achado.value)


def test_roteador_para_sem_chave_nenhuma_manda_copiar_o_env():
    with pytest.raises(ErroProvedor) as achado:
        roteador_para(PapelLLM.GERADOR)
    assert ".env" in str(achado.value)


def test_roteador_para_monta_so_com_quem_tem_chave_e_na_ordem_do_papel(monkeypatch):
    for provedor in ("GEMINI", "GROQ", "SAMBANOVA"):
        monkeypatch.setenv(f"{provedor}_API_KEY", "chave-de-mentira")
        monkeypatch.setenv(f"{provedor}_MODELO", "modelo-de-mentira")

    gerador = roteador_para(PapelLLM.GERADOR)
    juiz = roteador_para(PapelLLM.JUIZ, excluir=("gemini",))

    assert [p.nome for p in gerador.provedores] == ["gemini", "groq", "sambanova"]
    assert [p.nome for p in juiz.provedores] == ["groq", "sambanova"]


def test_roteador_para_ignora_provedor_sem_chave(monkeypatch):
    monkeypatch.setenv("SAMBANOVA_API_KEY", "chave-de-mentira")
    monkeypatch.setenv("SAMBANOVA_MODELO", "modelo-de-mentira")
    assert [p.nome for p in roteador_para(PapelLLM.GERADOR).provedores] == ["sambanova"]
