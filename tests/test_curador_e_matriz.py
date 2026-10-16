"""Contrato da arquitetura: curador, três personas e conferência determinística da Matriz.

O LLM Judge transversal foi removido (ADR 0037); sobra a conferência sem LLM, que checa quantidade,
unicidade, aprovação e referências das Células pedidas.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from suno.avaliador import avaliar_matriz
from suno.dominio import (
    MATRIZ,
    AncoraNumerica,
    Ancoras,
    Ata,
    Audiencia,
    Celula,
    Conteudo,
    Destino,
    EstadoAvaliacaoTransversal,
    Formato,
    HistoricoCelula,
    Laudo,
    ModoSelecao,
    SelecaoCuradoria,
    Slide,
    Tentativa,
    Unidade,
)
from suno.gerador.curador import AgenteCurador, DossieCurado
from suno.gerador.extracao import ROTULO_DO_PEDIDO
from suno.gerador.personas import AGENTES_GERADORES
from suno.ingestao.pdf import carregar_ata
from suno.provedores.falso import ProvedorFalso


def test_selecao_unida_aceita_varios_itens_e_separada_exige_um():
    unida = SelecaoCuradoria(modo=ModoSelecao.UNIDA, itens=["bcb-1", "cvm-2"])
    separada = SelecaoCuradoria(modo=ModoSelecao.SEPARADA, itens=["bcb-1"])

    assert unida.itens == ["bcb-1", "cvm-2"]
    assert separada.itens == ["bcb-1"]
    with pytest.raises(ValidationError, match="exatamente um item"):
        SelecaoCuradoria(modo=ModoSelecao.SEPARADA, itens=["bcb-1", "cvm-2"])


def test_existem_exatamente_tres_geradores_um_por_persona():
    assert len(AGENTES_GERADORES) == 3
    assert [agente.audiencia for agente in AGENTES_GERADORES] == list(Audiencia)


def test_curador_prepara_um_dossie_unico(caminho_ata):
    provedor = ProvedorFalso({ROTULO_DO_PEDIDO: [{"chaves": [], "afirmacoes": []}]})
    ata = carregar_ata(caminho_ata)

    dossie = AgenteCurador(provedor).preparar(ata)

    assert dossie.ata is ata
    assert dossie.ancoras.ata == ata.identificador
    assert dossie.selecao.modo is ModoSelecao.SEPARADA
    assert dossie.selecao.itens == [ata.identificador]
    assert provedor.rotulos_pedidos() == [ROTULO_DO_PEDIDO]


def _ancoras() -> Ancoras:
    return Ancoras(
        ata="ata",
        numericas=[
            AncoraNumerica(
                chave="selic_decidida",
                rotulo="Selic",
                valor_literal="14,00",
                valor=14.0,
                unidade=Unidade.PERCENTUAL_AO_ANO,
                trecho="Selic em 14,00% a.a.",
            )
        ],
    )


def _conteudo(formato: Formato, *, chave: str = "selic_decidida") -> Conteudo:
    campos = {"formato": formato, "ancoras_citadas": [chave]}
    if formato is Formato.TEXTO_ANALITICO:
        return Conteudo(**campos, texto="Taxa em 14,00% a.a.")
    if formato is Formato.CARROSSEL:
        return Conteudo(**campos, slides=[Slide(titulo="Taxa", corpo="14,00% a.a.")])
    return Conteudo(**campos, blocos=[{"inicio_s": 0, "fim_s": 1, "fala": "14,00% a.a."}])


def _historico(audiencia: Audiencia, formato: Formato, *, chave: str = "selic_decidida"):
    celula = Celula(audiencia=audiencia, formato=formato, conteudo=_conteudo(formato, chave=chave))
    laudo = Laudo(audiencia=audiencia, formato=formato, medidas=[], destino=Destino.APROVADO)
    return HistoricoCelula(
        audiencia=audiencia,
        formato=formato,
        tentativas=[Tentativa(rodada=0, celula=celula, laudo=laudo)],
        destino_final=Destino.APROVADO,
    )


def test_avaliador_transversal_aprova_somente_a_matriz_inteira_e_coerente():
    celulas = [_historico(audiencia, formato) for audiencia, formato in MATRIZ]

    avaliacao = avaliar_matriz(celulas, _ancoras())

    assert avaliacao.estado is EstadoAvaliacaoTransversal.APROVADA
    assert avaliacao.total_recebido == 9
    assert avaliacao.total_com_conteudo == 9
    assert avaliacao.observacoes == []


def test_avaliador_transversal_manda_matriz_incompleta_ou_inconsistente_para_revisao():
    celulas = [_historico(audiencia, formato) for audiencia, formato in MATRIZ][:-1]
    celulas[0] = _historico(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO, chave="inventada")

    avaliacao = avaliar_matriz(celulas, _ancoras())

    assert avaliacao.estado is EstadoAvaliacaoTransversal.REVISAO_HUMANA
    assert avaliacao.posicoes_faltantes == ["avancado:roteiro"]
    assert avaliacao.referencias_invalidas == ["iniciante:texto_analitico:inventada"]


def _dossie() -> DossieCurado:
    return DossieCurado(
        ata=Ata(
            identificador="ata",
            titulo="Ata de teste",
            data_referencia=date(2026, 10, 9),
            texto="O Copom decidiu manter a Selic em 14,00% a.a.",
        ),
        ancoras=_ancoras(),
        selecao=SelecaoCuradoria(modo=ModoSelecao.SEPARADA, itens=["ata"]),
    )
