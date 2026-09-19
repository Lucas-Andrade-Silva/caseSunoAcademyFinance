"""O Ciclo de correção: duas rodadas no teto, feedback com o valor medido, e falha de
extração indo direto para a fila humana.

ADR 0013.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from suno.dominio import (
    AncoraNumerica,
    Ancoras,
    Ata,
    Audiencia,
    CotaEsgotada,
    Destino,
    ErroProvedor,
    EsgotamentoDeCota,
    Formato,
    MotivoReprovacao,
    Unidade,
)
from suno.gerador.ciclo import (
    CREDENCIAL_OCULTA,
    TETO_DE_RODADAS,
    interrompido_por_provedor,
    rodar_ciclo,
    sem_credencial,
)
from suno.provedores.falso import ProvedorFalso

TEXTO_DA_ATA = """Data: 4 e 5 de agosto de 2026

280ª Reunião do Copom

O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.
"""


@pytest.fixture
def ata() -> Ata:
    return Ata(
        identificador="copom-teste",
        titulo="280ª Reunião de teste",
        reuniao=280,
        data_referencia=date(2026, 8, 5),
        texto=TEXTO_DA_ATA,
    )


def _ancora_selic() -> AncoraNumerica:
    return AncoraNumerica(
        chave="selic_decidida",
        rotulo="Selic decidida",
        valor_literal="14,00",
        valor=14.0,
        unidade=Unidade.PERCENTUAL_AO_ANO,
        trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
    )


@pytest.fixture
def ancoras_completas() -> Ancoras:
    return Ancoras(
        ata="copom-teste",
        numericas=[
            _ancora_selic(),
            AncoraNumerica(
                chave="placar_votacao",
                rotulo="Placar da votação",
                valor_literal="7 a 0",
                valor=7.0,
                unidade=Unidade.VOTOS,
                trecho="Votaram por essa decisão os seguintes membros",
            ),
            AncoraNumerica(
                chave="data_reuniao",
                rotulo="Data da reunião",
                valor_literal="4 e 5 de agosto de 2026",
                unidade=Unidade.DATA,
                trecho="Data: 4 e 5 de agosto de 2026",
                data_iso=date(2026, 8, 5),
            ),
        ],
    )


@pytest.fixture
def ancoras_degradadas() -> Ancoras:
    """Falta ``placar_votacao`` e ``data_reuniao``: a Ata foi mal lida (ADR 0013)."""
    return Ancoras(ata="copom-teste", numericas=[_ancora_selic()])


DIFICIL = json.dumps(
    {
        "titulo": "Decisão de política monetária e balanço de riscos",
        "o_que_foi_decidido": (
            "Na reunião referida, o colegiado deliberou pela redução da taxa básica de "
            "juros para {{selic_decidida}}, entendendo a decisão compatível com a "
            "estratégia de convergência da inflação para o redor da meta ao longo do "
            "horizonte relevante de política monetária."
        ),
        "por_que": (
            "O diagnóstico combina acumulação gradual das evidências de transmissão da "
            "política monetária contracionista à atividade econômica com persistência da "
            "pressão de demanda sobre a inflação corrente, configuração que sustenta a "
            "manutenção de caráter restritivo enquanto o hiato do produto permanecer em "
            "terreno desfavorável e o balanço de riscos seguir assimétrico."
        ),
        "o_que_observar_adiante": (
            "A magnitude do ciclo de calibração permanece condicionada à evolução "
            "observada da desinflação, dos efeitos de segunda ordem dos choques de oferta "
            "e da reancoragem das expectativas apuradas pela pesquisa Focus, elementos "
            "que o colegiado declara acompanhar detidamente."
        ),
    },
    ensure_ascii=False,
)

FACIL = json.dumps(
    {
        "titulo": "O custo do dinheiro caiu",
        "o_que_foi_decidido": (
            "O grupo se reuniu em {{data_reuniao}}. "
            "A taxa caiu para {{selic_decidida}} ao ano. "
            "O placar foi de {{placar_votacao}}."
        ),
        "por_que": (
            "Os preços já sobem menos do que subiam. "
            "E o comércio está mais fraco. "
            "Foi por isso que a taxa pôde cair."
        ),
        "o_que_observar_adiante": (
            "O grupo não disse qual será o próximo passo. "
            "Quem tem dívida paga um pouco menos. "
            "Quem guarda dinheiro ganha um pouco menos."
        ),
    },
    ensure_ascii=False,
)

ROTULO = "celula:iniciante:texto_analitico:{rodada}"


def _provedor(*por_rodada: str | BaseException) -> ProvedorFalso:
    return ProvedorFalso(
        {ROTULO.format(rodada=rodada): [pronta] for rodada, pronta in enumerate(por_rodada)}
    )


def _rodar(ata: Ata, ancoras: Ancoras, provedor: ProvedorFalso):
    return rodar_ciclo(ata, ancoras, Audiencia.INICIANTE, Formato.TEXTO_ANALITICO, provedor)


# ---------------------------------------------------------------------------


def test_a_celula_facil_aprova_na_rodada_zero(ata: Ata, ancoras_completas: Ancoras):
    historico = _rodar(ata, ancoras_completas, _provedor(FACIL))
    assert historico.destino_final is Destino.APROVADO
    assert [t.rodada for t in historico.tentativas] == [0]
    assert historico.provedores_usados == ["falso"]


def test_correcao_que_resolve_aprova_na_rodada_um(ata: Ata, ancoras_completas: Ancoras):
    historico = _rodar(ata, ancoras_completas, _provedor(DIFICIL, FACIL))
    assert [t.rodada for t in historico.tentativas] == [0, 1]
    assert historico.tentativas[0].laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert historico.destino_final is Destino.APROVADO


def test_o_ciclo_para_na_segunda_correcao_e_vai_para_a_fila_humana(
    ata: Ata, ancoras_completas: Ancoras
):
    provedor = _provedor(DIFICIL, DIFICIL, DIFICIL)
    historico = _rodar(ata, ancoras_completas, provedor)
    assert [t.rodada for t in historico.tentativas] == [0, 1, 2]
    assert len(historico.tentativas) == TETO_DE_RODADAS + 1
    assert historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    # Nunca uma quarta geração: só três pedidos saíram.
    assert provedor.rotulos_pedidos() == [ROTULO.format(rodada=r) for r in (0, 1, 2)]
    assert not interrompido_por_provedor(historico)


def test_falha_de_extracao_gera_uma_vez_e_nao_tenta_corrigir(
    ata: Ata, ancoras_degradadas: Ancoras
):
    """Reescrever não conserta documento mal lido (ADR 0013)."""
    provedor = _provedor(FACIL, FACIL, FACIL)
    historico = _rodar(ata, ancoras_degradadas, provedor)
    assert len(historico.tentativas) == 1
    assert historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    laudo = historico.laudo_final
    assert laudo is not None
    assert MotivoReprovacao.FALHA_DE_EXTRACAO in laudo.motivos
    assert provedor.rotulos_pedidos() == [ROTULO.format(rodada=0)]


def test_erro_de_provedor_na_rodada_um_preserva_a_rodada_zero(
    ata: Ata, ancoras_completas: Ancoras
):
    provedor = _provedor(DIFICIL, CotaEsgotada("falso", EsgotamentoDeCota.POR_DIA))
    historico = _rodar(ata, ancoras_completas, provedor)
    assert len(historico.tentativas) == 1
    assert historico.tentativas[0].rodada == 0
    assert historico.tentativas[0].celula.conteudo.texto is not None
    assert historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    assert interrompido_por_provedor(historico)


def test_erro_de_provedor_na_rodada_zero_deixa_o_historico_vazio(
    ata: Ata, ancoras_completas: Ancoras
):
    provedor = _provedor(CotaEsgotada("falso", EsgotamentoDeCota.POR_DIA))
    historico = _rodar(ata, ancoras_completas, provedor)
    assert historico.tentativas == []
    assert historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    assert interrompido_por_provedor(historico)


def test_erro_que_nao_e_do_provedor_tambem_para_o_ciclo_sem_subir(
    ata: Ata, ancoras_completas: Ancoras
):
    """Achado do revisor de erros (2026-09-19): `ProvedorFalso` documenta e aceita
    `BaseException` arbitrária na fila (ex.: um `TimeoutError` roteirizado); antes desta
    correção, qualquer exceção que não fosse `ErroProvedor` subia por `rodar_ciclo` e
    derrubava a Matriz inteira — nove Células perdidas e nenhum `execucao.json` gravado."""
    provedor = _provedor(RuntimeError("boom"))
    historico = _rodar(ata, ancoras_completas, provedor)
    assert historico.tentativas == []
    assert historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    assert historico.falha is not None
    assert "boom" in historico.falha
    assert "erro inesperado" in historico.falha


def test_o_pedido_da_rodada_um_carrega_a_instrucao_da_correcao(
    ata: Ata, ancoras_completas: Ancoras
):
    provedor = _provedor(DIFICIL, FACIL)
    historico = _rodar(ata, ancoras_completas, provedor)
    correcoes = historico.tentativas[0].laudo.correcoes
    assert correcoes, "a rodada 0 tinha que reprovar com correção"

    pedido_da_correcao = provedor.pedidos[1]
    assert pedido_da_correcao.rotulo == ROTULO.format(rodada=1)
    usuario = next(m.texto for m in pedido_da_correcao.mensagens if m.autor == "usuario")
    assert "O que precisa mudar" in usuario
    for correcao in correcoes:
        assert correcao.instrucao in usuario


def test_a_rodada_fica_gravada_na_celula(ata: Ata, ancoras_completas: Ancoras):
    historico = _rodar(ata, ancoras_completas, _provedor(DIFICIL, DIFICIL, DIFICIL))
    assert [t.celula.rodada for t in historico.tentativas] == [0, 1, 2]
    assert all(t.celula.provedor == "falso" for t in historico.tentativas)


# ---------------------------------------------------------------------------
# A falha de provedor vira estado, não só linha de log
# ---------------------------------------------------------------------------


def test_a_falha_nomeia_o_provedor_a_rodada_e_o_erro(ata: Ata, ancoras_completas: Ancoras):
    provedor = _provedor(DIFICIL, CotaEsgotada("falso", EsgotamentoDeCota.POR_DIA))
    historico = _rodar(ata, ancoras_completas, provedor)
    assert historico.falha is not None
    assert historico.falha.startswith("o provedor falso falhou na rodada 1:")
    assert "cota esgotada" in historico.falha


def test_quem_esgotou_o_teto_nao_tem_falha(ata: Ata, ancoras_completas: Ancoras):
    """Reprovar por mérito é diferente de parar no meio: só o segundo preenche ``falha``."""
    historico = _rodar(ata, ancoras_completas, _provedor(DIFICIL, DIFICIL, DIFICIL))
    assert historico.falha is None
    assert not interrompido_por_provedor(historico)


def test_a_celula_aprovada_nao_tem_falha(ata: Ata, ancoras_completas: Ancoras):
    historico = _rodar(ata, ancoras_completas, _provedor(FACIL))
    assert historico.falha is None


def test_a_falha_nao_leva_chave_de_api_para_o_disco(ata: Ata, ancoras_completas: Ancoras):
    """``falha`` vai para ``execucao.json`` e para a interface: credencial não viaja junto."""
    chave = "AIzaSyD" + "x9K2" * 8
    erro = ErroProvedor("gemini", f"401 em https://api/v1?key={chave} (api_key={chave})")
    historico = _rodar(ata, ancoras_completas, _provedor(erro))
    assert historico.falha is not None
    assert chave not in historico.falha
    assert CREDENCIAL_OCULTA in historico.falha
    assert "401" in historico.falha  # o que interessa para o humano do H4 continua lá


@pytest.mark.parametrize(
    "mensagem",
    [
        "cota esgotada (por_dia)",
        "resposta fora do schema RespostaCarrossel: 1 validation error",
        "GEMINI_API_KEY ausente: preencha o .env (veja .env.example)",
        "tempo esgotado depois de 30 s",
    ],
)
def test_mensagem_sem_segredo_atravessa_intacta(mensagem: str):
    """O limpador não pode mutilar o erro comum, que é o caso de sempre."""
    assert sem_credencial(mensagem) == mensagem
