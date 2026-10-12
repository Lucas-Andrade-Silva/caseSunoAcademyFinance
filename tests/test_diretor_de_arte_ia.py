"""O Diretor IA escolhe dentro das cercas; qualquer desvio cai nas regras locais."""

import json

from suno.dominio import PapelLLM, Slide, TipoSlide
from suno.pacote.diretor_de_arte_ia import planejar_com_diretor_de_arte
from suno.pacote.referencias_visuais import REFERENCIAS_INICIAIS
from suno.provedores.falso import ProvedorFalso


def _slides() -> list[Slide]:
    return [
        Slide(
            tipo=TipoSlide.HOOK,
            titulo="O que mudou nos juros?",
            corpo="Veja o cenário antes de rever sua carteira.",
        ),
        Slide(
            tipo=TipoSlide.CTA,
            titulo="Continue acompanhando",
            corpo="Compare as alternativas com calma.",
        ),
    ]


def test_diretor_ia_planeja_o_carrossel_inteiro_em_uma_chamada() -> None:
    provedor = ProvedorFalso(
        {
            "direcao_de_arte": [
                {
                    "escolhas": [
                        {
                            "indice": 0,
                            "composicao": "editorial",
                            "referencia_visual": "suno-editorial-cenario-de-juros",
                            "intensidade_visual": "alta",
                            "justificativa": "abre o cenário com hierarquia forte",
                        },
                        {
                            "indice": 1,
                            "composicao": "minimalista",
                            "referencia_visual": "suno-minimalista-reserva-de-emergencia",
                            "intensidade_visual": "baixa",
                            "justificativa": "encerra com foco e respiro",
                        },
                    ]
                }
            ]
        }
    )

    preferida = REFERENCIAS_INICIAIS[0]
    resultado = planejar_com_diretor_de_arte(
        _slides(),
        REFERENCIAS_INICIAIS,
        provedor=provedor,
        referencia_preferida=preferida,
    )

    assert resultado.origem == "ia"
    assert resultado.provedor == "falso"
    assert [item.composicao.value for item in resultado.escolhas] == [
        "editorial",
        "minimalista",
    ]
    assert provedor.rotulos_pedidos() == ["direcao_de_arte"]
    assert provedor.pedidos[0].papel is PapelLLM.DIRETOR_ARTE
    entrada = json.loads(provedor.pedidos[0].mensagens[-1].texto)
    assert entrada["referencia_preferida"]["identificador"] == preferida.identificador


def test_plano_ia_invalido_cai_no_seletor_deterministico() -> None:
    provedor = ProvedorFalso(
        {
            "direcao_de_arte": [
                {
                    "escolhas": [
                        {
                            "indice": 0,
                            "composicao": "editorial",
                            "referencia_visual": "suno-editorial-cenario-de-juros",
                            "intensidade_visual": "alta",
                            "justificativa": "abre o cenário",
                        },
                        {
                            "indice": 1,
                            "composicao": "editorial",
                            "referencia_visual": "suno-editorial-cenario-de-juros",
                            "intensidade_visual": "alta",
                            "justificativa": "repete sem necessidade",
                        },
                    ]
                }
            ]
        }
    )

    resultado = planejar_com_diretor_de_arte(
        _slides(), REFERENCIAS_INICIAIS, provedor=provedor
    )

    assert resultado.origem == "deterministico"
    assert "repetiu" in (resultado.motivo_fallback or "")
    assert resultado.escolhas[0].referencia_visual


def test_provedor_indisponivel_nao_impede_a_renderizacao() -> None:
    resultado = planejar_com_diretor_de_arte(
        _slides(), REFERENCIAS_INICIAIS, provedor=ProvedorFalso()
    )

    assert resultado.origem == "deterministico"
    assert resultado.motivo_fallback
    assert len(resultado.escolhas) == 2


def test_aprovacoes_humanas_entram_no_pedido_como_sinal_fraco() -> None:
    provedor = ProvedorFalso(
        {
            "direcao_de_arte": [
                {
                    "escolhas": [
                        {
                            "indice": 0,
                            "composicao": "editorial",
                            "referencia_visual": "suno-editorial-cenario-de-juros",
                            "intensidade_visual": "alta",
                            "justificativa": "abre o cenário",
                        },
                        {
                            "indice": 1,
                            "composicao": "minimalista",
                            "referencia_visual": "suno-minimalista-reserva-de-emergencia",
                            "intensidade_visual": "baixa",
                            "justificativa": "encerra com foco",
                        },
                    ]
                }
            ]
        }
    )
    sinais = {
        "composicoes_aprovadas": [{"composicao": "editorial", "aprovacoes": 3}],
        "referencias_aprovadas": [],
    }

    planejar_com_diretor_de_arte(
        _slides(), REFERENCIAS_INICIAIS, provedor=provedor, sinais_humanos=sinais
    )

    entrada = json.loads(provedor.pedidos[0].mensagens[-1].texto)
    assert entrada["sinais_humanos"] == sinais
    assert "preferência fraca" in provedor.pedidos[0].mensagens[0].texto
