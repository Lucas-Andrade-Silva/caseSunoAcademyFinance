"""O LLM de mentira: fila de respostas por rótulo, sem rede, com exceções roteirizadas."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from pydantic import BaseModel

from suno.dominio import CotaEsgotada, EsgotamentoDeCota, Mensagem, PapelLLM, PedidoLLM, RespostaMalformada
from suno.provedores import Provedor, ProvedorFalso
from suno.provedores.base import extrair_json
from suno.provedores.falso import FilaVazia


def _pedido(rotulo: str = "qualquer") -> PedidoLLM:
    return PedidoLLM(papel=PapelLLM.GERADOR, rotulo=rotulo, mensagens=[Mensagem(autor="usuario", texto="oi")])


class Saida(BaseModel):
    titulo: str
    valor: int


def test_falso_cumpre_o_contrato_de_provedor():
    assert isinstance(ProvedorFalso(), Provedor)


def test_devolve_da_fila_do_rotulo_antes_da_fila_padrao():
    provedor = ProvedorFalso({"extracao": ["A"], "*": ["B", "C"]})
    assert provedor.completar(_pedido("extracao")).texto == "A"
    assert provedor.completar(_pedido("extracao")).texto == "B"
    assert provedor.completar(_pedido("outro")).texto == "C"


def test_fila_vazia_levanta_erro_em_vez_de_inventar():
    provedor = ProvedorFalso()
    with pytest.raises(FilaVazia):
        provedor.completar(_pedido())


def test_excecao_na_fila_e_levantada_para_simular_429():
    provedor = ProvedorFalso([CotaEsgotada("falso", EsgotamentoDeCota.POR_DIA), "depois"])
    with pytest.raises(CotaEsgotada) as info:
        provedor.completar(_pedido())
    assert info.value.esgotamento is EsgotamentoDeCota.POR_DIA
    assert provedor.completar(_pedido()).texto == "depois"


def test_objeto_na_fila_vira_json_e_saida_estruturada_valida():
    provedor = ProvedorFalso([{"titulo": "x", "valor": 3}])
    saida = provedor.completar_estruturado(_pedido(), Saida)
    assert saida == Saida(titulo="x", valor=3)
    assert provedor.pedidos[0].schema_saida is not None, "o schema viaja no pedido (ADR 0007)"


def test_saida_fora_do_schema_levanta_resposta_malformada():
    provedor = ProvedorFalso(['{"titulo": "x"}'])
    with pytest.raises(RespostaMalformada):
        provedor.completar_estruturado(_pedido(), Saida)


def test_extrair_json_tolera_cerca_de_codigo():
    assert json.loads(extrair_json('```json\n{"a": 1}\n```')) == {"a": 1}
    assert json.loads(extrair_json('texto antes {"a": 1} texto depois')) == {"a": 1}


def test_carrega_respostas_de_arquivo(tmp_path: Path):
    arquivo = tmp_path / "respostas.json"
    arquivo.write_text(json.dumps({"celula:iniciante:carrossel:0": [{"slides": []}], "*": ["livre"]}), encoding="utf-8")
    provedor = ProvedorFalso.de_arquivo(arquivo)
    assert provedor.restantes("celula:iniciante:carrossel:0") == 1
    assert json.loads(provedor.completar(_pedido("celula:iniciante:carrossel:0")).texto) == {"slides": []}


def test_e_seguro_com_nove_chamadas_em_paralelo():
    rotulos = [f"celula:{i}" for i in range(9)]
    provedor = ProvedorFalso({r: [r.upper()] for r in rotulos})
    resultados: dict[str, str] = {}

    def chamar(r: str) -> None:
        resultados[r] = provedor.completar(_pedido(r)).texto

    fios = [threading.Thread(target=chamar, args=(r,)) for r in rotulos]
    for f in fios:
        f.start()
    for f in fios:
        f.join()
    assert resultados == {r: r.upper() for r in rotulos}
    assert sorted(provedor.rotulos_pedidos()) == sorted(rotulos)
