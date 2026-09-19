"""O Laudo: as cinco medidas determinísticas juntas, três destinos, e a Correção que carrega
o valor medido (ADR 0001, 0013).

Sem mock nenhum das métricas: estes testes rodam o Flesch-BR, a Densidade, a Aderência, a
Recomendação e a integridade de verdade. É o que prova a promessa do ADR 0001 — o Avaliador
inteiro roda sem LLM e sem rede.
"""

from __future__ import annotations

from datetime import date

import pytest

from suno.avaliador import avaliar
from suno.comite import Comite
from suno.dominio import (
    AncoraNumerica,
    AncoraTextual,
    Audiencia,
    BlocoFala,
    ChaveAncora,
    Conteudo,
    Correcao,
    Destino,
    EstadoMedida,
    ExigenciaDeExplicacao,
    Faixa,
    Formato,
    Limiares,
    Metrica,
    MotivoReprovacao,
    Slide,
    Unidade,
)
from suno.provedores.falso import ProvedorFalso

# ---------------------------------------------------------------------------
# Âncoras de exemplo: a Ata 280, de 4 e 5 de agosto de 2026
# ---------------------------------------------------------------------------


def _ancoras(*, com_placar: bool = True) -> list[AncoraNumerica | AncoraTextual]:
    tabuada: list[AncoraNumerica | AncoraTextual] = [
        AncoraNumerica(
            chave=ChaveAncora.SELIC_DECIDIDA,
            rotulo="Selic decidida",
            valor_literal="14,00",
            valor=14.0,
            unidade=Unidade.PERCENTUAL_AO_ANO,
            trecho="O Copom decidiu manter a taxa Selic em 14,00% a.a.",
        ),
        AncoraNumerica(
            chave=ChaveAncora.DATA_REUNIAO,
            rotulo="Data da reunião",
            valor_literal="4 e 5 de agosto de 2026",
            valor=None,
            unidade=Unidade.DATA,
            trecho="Reunião de 4 e 5 de agosto de 2026.",
            data_iso=date(2026, 8, 5),
        ),
        AncoraTextual(
            identificador="decisao",
            afirmacao="O Copom manteve a taxa básica de juros inalterada.",
            trecho="O Copom decidiu manter a taxa Selic em 14,00% a.a.",
        ),
    ]
    if com_placar:
        tabuada.insert(
            1,
            AncoraNumerica(
                chave=ChaveAncora.PLACAR_VOTACAO,
                rotulo="Placar da votação",
                valor_literal="7 a 0",
                valor=None,
                unidade=Unidade.VOTOS,
                trecho="A decisão foi tomada por 7 votos a 0.",
            ),
        )
    return tabuada


# ---------------------------------------------------------------------------
# Textos de exemplo. Os termos do Léxico vêm explicados na primeira ocorrência,
# que é o que a Audiência Iniciante exige.
# ---------------------------------------------------------------------------

TEXTO_FACIL = (
    "A Selic (a taxa básica de juros do país) não mudou. "
    "Ela agora é de 14,00% a.a.\n\n"
    "O Banco Central: é a casa que cuida do valor do dinheiro. "
    "A mudança chega devagar até a conta da sua casa."
)

TEXTO_SEM_NUMERO = (
    "A Selic (a taxa básica de juros do país) não mudou hoje.\n\n"
    "O Banco Central: é a casa que cuida do valor do dinheiro."
)

TEXTO_COM_TERMO_CRU = "O hiato do produto segue positivo neste trimestre. A decisão saiu sem novidade."

TEXTO_COM_NUMERO_SOLTO = (
    "A Selic (a taxa básica de juros do país) é de 14,00% a.a. O preço subiu 15%."
)

TEXTO_QUE_RECOMENDA = (
    "A Selic (a taxa básica de juros do país) não mudou. Você deve comprar prefixados agora."
)


def _analitico(texto: str) -> Conteudo:
    return Conteudo(formato=Formato.TEXTO_ANALITICO, texto=texto)


def _numerica(chave: str) -> AncoraNumerica:
    """A Âncora numérica de exemplo daquela chave, para citar por `citacao()`."""
    return next(
        ancora
        for ancora in _ancoras()
        if isinstance(ancora, AncoraNumerica) and ancora.chave == chave
    )


def _correcao(laudo, metrica: Metrica) -> Correcao | None:
    return next((c for c in laudo.correcoes if c.metrica is metrica), None)


# ---------------------------------------------------------------------------
# 1. O caminho feliz
# ---------------------------------------------------------------------------


def test_texto_facil_para_iniciante_sai_aprovado_com_as_cinco_medidas() -> None:
    laudo = avaliar(_analitico(TEXTO_FACIL), _ancoras(), Audiencia.INICIANTE)

    assert laudo.destino is Destino.APROVADO
    assert laudo.motivos == []
    assert laudo.correcoes == []
    assert [m.metrica for m in laudo.medidas] == [
        Metrica.INTEGRIDADE,
        Metrica.FLESCH_BR,
        Metrica.DENSIDADE,
        Metrica.ADERENCIA,
        Metrica.RECOMENDACAO,
    ]
    assert all(m.atingiu for m in laudo.medidas)
    assert laudo.comite is None
    assert laudo.audiencia is Audiencia.INICIANTE
    assert laudo.formato is Formato.TEXTO_ANALITICO


# ---------------------------------------------------------------------------
# 2. O mesmo texto na Audiência errada
# ---------------------------------------------------------------------------


def test_texto_facil_demais_reprova_no_avancado_com_a_distancia_na_correcao() -> None:
    laudo = avaliar(_analitico(TEXTO_FACIL), _ancoras(), Audiencia.AVANCADO)

    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert laudo.motivos == [MotivoReprovacao.FLESCH_BR]

    medida = laudo.medida(Metrica.FLESCH_BR)
    assert medida is not None and medida.atingiu is False
    assert medida.faixa == Faixa(maximo=25.0)

    correcao = _correcao(laudo, Metrica.FLESCH_BR)
    assert correcao is not None
    assert correcao.valor_medido == medida.valor
    assert medida.valor is not None
    assert correcao.distancia == pytest.approx(medida.valor - 25.0)
    assert "Flesch-BR medido" in correcao.instrucao
    assert f"{correcao.distancia:.1f}".replace(".", ",") in correcao.instrucao
    assert "< 25" in correcao.instrucao
    assert "Avançado" in correcao.instrucao


def test_texto_dificil_demais_no_iniciante_pede_para_ficar_mais_facil() -> None:
    laudo = avaliar(_analitico(TEXTO_COM_TERMO_CRU), _ancoras(), Audiencia.INICIANTE)

    correcao = _correcao(laudo, Metrica.FLESCH_BR)
    assert correcao is not None
    assert "≥ 50" in correcao.instrucao
    assert "faltam" in correcao.instrucao
    assert "para ficar mais fácil" in correcao.instrucao


# ---------------------------------------------------------------------------
# 3. Densidade
# ---------------------------------------------------------------------------


def test_termo_do_lexico_sem_explicacao_reprova_por_densidade() -> None:
    laudo = avaliar(_analitico(TEXTO_COM_TERMO_CRU), _ancoras(), Audiencia.INICIANTE)

    assert MotivoReprovacao.DENSIDADE in laudo.motivos
    medida = laudo.medida(Metrica.DENSIDADE)
    assert medida is not None
    assert any("hiato do produto" in observacao for observacao in medida.observacoes)

    correcao = _correcao(laudo, Metrica.DENSIDADE)
    assert correcao is not None
    assert "hiato do produto" in correcao.instrucao
    assert "Iniciante" in correcao.instrucao


def test_o_mesmo_termo_cru_passa_no_avancado_que_nunca_exige_explicacao() -> None:
    laudo = avaliar(_analitico(TEXTO_COM_TERMO_CRU), _ancoras(), Audiencia.AVANCADO)

    assert MotivoReprovacao.DENSIDADE not in laudo.motivos


# ---------------------------------------------------------------------------
# 4. Aderência
# ---------------------------------------------------------------------------


def test_numero_fora_das_ancoras_reprova_por_aderencia() -> None:
    laudo = avaliar(_analitico(TEXTO_COM_NUMERO_SOLTO), _ancoras(), Audiencia.INICIANTE)

    assert MotivoReprovacao.ADERENCIA in laudo.motivos
    medida = laudo.medida(Metrica.ADERENCIA)
    assert medida is not None
    assert medida.estado is EstadoMedida.MEDIDA
    # Com a unidade: "15" sozinho não diz qual número está errado num texto que também tem
    # "15 p.p." — e `%` ≠ `p.p.` ≠ `pb`.
    assert any("15%" in observacao for observacao in medida.observacoes)

    correcao = _correcao(laudo, Metrica.ADERENCIA)
    assert correcao is not None
    assert "Números sem Âncora: 15%." in correcao.instrucao
    # A Correção lista as Âncoras disponíveis: elas são a única origem de número (ADR 0011).
    # A forma de citar é a de `AncoraNumerica.citacao()`, não um literal copiado: quem muda
    # a forma canônica muda o domínio, e este teste acompanha em vez de brigar.
    selic = _numerica(ChaveAncora.SELIC_DECIDIDA)
    placar = _numerica(ChaveAncora.PLACAR_VOTACAO)
    assert f"selic_decidida={selic.citacao()}" in correcao.instrucao
    assert f"placar_votacao={placar.citacao()}" in correcao.instrucao


def test_varios_numeros_fora_saem_com_a_unidade_de_cada_um() -> None:
    texto = (
        "A Selic (a taxa básica de juros do país) é de 14,00% a.a. "
        "O preço subiu 15% e o juro caiu 0,75 p.p."
    )
    laudo = avaliar(_analitico(texto), _ancoras(), Audiencia.INICIANTE)

    correcao = _correcao(laudo, Metrica.ADERENCIA)
    assert correcao is not None
    assert "Números sem Âncora: 15%, 0,75 p.p." in correcao.instrucao


def test_numero_inventado_na_rubrica_de_cena_tambem_reprova_por_aderencia() -> None:
    """Achado do revisor ADR-por-ADR (2026-09-19): a rubrica ``tela`` do Roteiro aparece
    escrita no vídeo e na interface, mas não é lida em voz alta nem medida pelo Flesch-BR — o
    que não quer dizer que um número inventado ali escape da conferência (ADR 0011). Antes da
    correção, este texto media Aderência 1,0."""
    conteudo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[
            BlocoFala(
                inicio_s=0,
                fim_s=5,
                fala="A Selic caiu.",
                tela="SELIC 19,75% a.a. — ALTA DE 375 pb",
            )
        ],
    )
    laudo = avaliar(conteudo, _ancoras(), Audiencia.INICIANTE)

    assert MotivoReprovacao.ADERENCIA in laudo.motivos
    medida = laudo.medida(Metrica.ADERENCIA)
    assert medida is not None
    assert any("19,75%" in observacao for observacao in medida.observacoes)
    # Flesch-BR continua sobre a fala só: a rubrica não entra na leitura, então uma rubrica
    # gritada em caixa alta não derruba o índice da fala curta e fácil.
    flesch = laudo.medida(Metrica.FLESCH_BR)
    assert flesch is not None and flesch.atingiu is True


# ---------------------------------------------------------------------------
# 5. Recomendação — a linha que não se cruza
# ---------------------------------------------------------------------------


def test_frase_que_recomenda_na_rubrica_de_cena_tambem_reprova() -> None:
    """A mesma lacuna vale para Recomendação: a rubrica é tão pública quanto a fala."""
    conteudo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[BlocoFala(inicio_s=0, fim_s=5, fala="A Selic caiu.", tela="COMPRE AGORA")],
    )
    laudo = avaliar(conteudo, _ancoras(), Audiencia.INICIANTE)

    assert MotivoReprovacao.RECOMENDACAO in laudo.motivos


def test_frase_que_recomenda_reprova_e_a_correcao_cita_a_frase() -> None:
    laudo = avaliar(_analitico(TEXTO_QUE_RECOMENDA), _ancoras(), Audiencia.INICIANTE)

    assert MotivoReprovacao.RECOMENDACAO in laudo.motivos
    medida = laudo.medida(Metrica.RECOMENDACAO)
    assert medida is not None
    assert medida.valor is not None and medida.valor >= 1
    assert medida.atingiu is False
    assert medida.faixa == Faixa(maximo=1)
    assert any("comprar prefixados" in observacao for observacao in medida.observacoes)

    correcao = _correcao(laudo, Metrica.RECOMENDACAO)
    assert correcao is not None
    assert "comprar prefixados" in correcao.instrucao
    assert "não aconselha" in correcao.instrucao


def test_texto_sem_recomendacao_mede_zero_ocorrencia() -> None:
    laudo = avaliar(_analitico(TEXTO_FACIL), _ancoras(), Audiencia.INICIANTE)

    medida = laudo.medida(Metrica.RECOMENDACAO)
    assert medida is not None
    assert medida.estado is EstadoMedida.MEDIDA
    assert medida.valor == 0.0
    assert medida.atingiu is True


# ---------------------------------------------------------------------------
# 6. Falha de extração: revisão humana, sem Ciclo de correção
# ---------------------------------------------------------------------------


def test_ancora_essencial_faltando_manda_para_a_revisao_humana_sem_correcao() -> None:
    laudo = avaliar(
        _analitico(TEXTO_FACIL), _ancoras(com_placar=False), Audiencia.INICIANTE
    )

    assert laudo.destino is Destino.REPROVADO_REVISAO_HUMANA
    assert MotivoReprovacao.FALHA_DE_EXTRACAO in laudo.motivos
    # Reescrever não conserta documento mal lido (ADR 0013).
    assert _correcao(laudo, Metrica.INTEGRIDADE) is None

    medida = laudo.medida(Metrica.INTEGRIDADE)
    assert medida is not None
    assert medida.atingiu is False
    assert medida.valor == pytest.approx(2 / 3)
    assert any("placar_votacao" in observacao for observacao in medida.observacoes)

    # As outras quatro medidas continuam no Laudo: o humano da fila H4 quer vê-las.
    assert len(laudo.medidas) == 5
    assert all(laudo.medida(metrica) is not None for metrica in Metrica)


def test_falha_de_extracao_nao_apaga_a_correcao_das_outras_metricas() -> None:
    laudo = avaliar(
        _analitico(TEXTO_QUE_RECOMENDA), _ancoras(com_placar=False), Audiencia.INICIANTE
    )

    assert laudo.destino is Destino.REPROVADO_REVISAO_HUMANA
    assert laudo.motivos[0] is MotivoReprovacao.FALHA_DE_EXTRACAO
    assert MotivoReprovacao.RECOMENDACAO in laudo.motivos
    assert _correcao(laudo, Metrica.RECOMENDACAO) is not None


# ---------------------------------------------------------------------------
# 7 e 8. Sem base para medir: ausente, nunca zero
# ---------------------------------------------------------------------------


def test_texto_sem_numero_deixa_a_aderencia_ausente_e_nao_reprova() -> None:
    laudo = avaliar(_analitico(TEXTO_SEM_NUMERO), _ancoras(), Audiencia.INICIANTE)

    medida = laudo.medida(Metrica.ADERENCIA)
    assert medida is not None
    assert medida.estado is EstadoMedida.AUSENTE
    assert medida.valor is None
    assert medida.atingiu is None
    assert MotivoReprovacao.ADERENCIA not in laudo.motivos
    assert laudo.destino is Destino.APROVADO


def test_texto_vazio_deixa_o_flesch_br_ausente_mas_reprova() -> None:
    """Achado do revisor de erros (2026-09-19): zero palavras nunca é "aprovado" — as três
    Formatos sempre têm um campo de texto obrigatório, então texto vazio só acontece quando o
    Gerador falhou (ex.: `{{chave}}` desconhecida apagada por `preencher`), nunca é uma
    Célula legítima sem base para medir. ``valor`` continua ``None``: a Medida não fabrica um
    zero, mas o Laudo não aprova o nada."""
    laudo = avaliar(_analitico(""), _ancoras(), Audiencia.INICIANTE)

    medida = laudo.medida(Metrica.FLESCH_BR)
    assert medida is not None
    assert medida.estado is EstadoMedida.AUSENTE
    assert medida.valor is None
    assert medida.valor != 0
    assert medida.atingiu is None
    assert MotivoReprovacao.FLESCH_BR in laudo.motivos
    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    correcao = _correcao(laudo, Metrica.FLESCH_BR)
    assert correcao is not None
    assert "sem nenhuma palavra legível" in correcao.instrucao


def test_carrossel_com_todos_os_slides_em_branco_tambem_reprova() -> None:
    """O outro caminho para o mesmo buraco: slides com titulo/corpo vazios juntam, via
    ``texto_avaliavel``, numa string só de quebras de linha — zero palavras, mesmo achado."""
    conteudo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[Slide(titulo="", corpo="") for _ in range(5)],
    )
    laudo = avaliar(conteudo, _ancoras(), Audiencia.INICIANTE)

    assert MotivoReprovacao.FLESCH_BR in laudo.motivos
    assert laudo.destino is not Destino.APROVADO


# ---------------------------------------------------------------------------
# 9. O comitê não toca no Roteiro
# ---------------------------------------------------------------------------


def _juiz(nome: str, notas: tuple[int, ...] = (4, 4, 4)) -> ProvedorFalso:
    provedor = ProvedorFalso(
        {"*": [{"nota": nota, "justificativa": "texto encadeado"} for nota in notas]}
    )
    provedor.nome = nome
    return provedor


def test_roteiro_nao_vai_ao_comite_mesmo_com_o_comite_ligado() -> None:
    primeiro, segundo = _juiz("juiz-a"), _juiz("juiz-b")
    conteudo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[
            BlocoFala(inicio_s=0, fim_s=6, fala="A Selic (a taxa básica de juros) não mudou."),
            BlocoFala(inicio_s=6, fim_s=12, fala="O Banco Central: é a casa do dinheiro."),
        ],
    )

    laudo = avaliar(
        conteudo,
        _ancoras(),
        Audiencia.INICIANTE,
        comite=Comite((primeiro, segundo), provedor_gerador="gemini"),
    )

    assert laudo.comite is None
    assert primeiro.pedidos == []
    assert segundo.pedidos == []
    assert len(laudo.medidas) == 5


def test_texto_analitico_com_comite_ligado_anexa_o_resultado_sem_mover_o_destino() -> None:
    primeiro, segundo = _juiz("juiz-a"), _juiz("juiz-b")

    laudo = avaliar(
        _analitico(TEXTO_FACIL),
        _ancoras(),
        Audiencia.INICIANTE,
        comite=Comite((primeiro, segundo), provedor_gerador="gemini"),
    )

    assert laudo.comite is not None
    assert laudo.comite.provedores == ["juiz-a", "juiz-b"]
    assert laudo.destino is Destino.APROVADO
    assert laudo.motivos == []
    assert len(primeiro.pedidos) == 3
    assert len(segundo.pedidos) == 3


def test_carrossel_com_comite_ligado_tambem_e_julgado() -> None:
    primeiro, segundo = _juiz("juiz-a"), _juiz("juiz-b")
    conteudo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[
            Slide(titulo="A Selic parada", corpo="A Selic (a taxa básica de juros) não mudou."),
            Slide(titulo="O que muda", corpo="O Banco Central: é a casa que cuida do dinheiro."),
        ],
    )

    laudo = avaliar(conteudo, _ancoras(), Audiencia.INICIANTE, comite=Comite((primeiro, segundo)))

    assert laudo.comite is not None
    assert len(laudo.comite.dimensoes) == 3


def test_comite_que_fica_sem_cota_deixa_o_laudo_sair_sem_comite() -> None:
    from suno.dominio import CotaEsgotada, EsgotamentoDeCota

    primeiro = ProvedorFalso({"*": [CotaEsgotada("juiz-a", EsgotamentoDeCota.POR_DIA)]})
    primeiro.nome = "juiz-a"
    segundo = _juiz("juiz-b")

    laudo = avaliar(
        _analitico(TEXTO_FACIL),
        _ancoras(),
        Audiencia.INICIANTE,
        comite=Comite((primeiro, segundo)),
    )

    # Comitê ausente, nunca nota zero (ADR 0008); o veredito determinístico não muda.
    assert laudo.comite is None
    assert laudo.destino is Destino.APROVADO


# ---------------------------------------------------------------------------
# 10. Limiares injetados
# ---------------------------------------------------------------------------


def test_limiares_customizados_mudam_o_veredito() -> None:
    conteudo = _analitico(TEXTO_COM_NUMERO_SOLTO)
    assert avaliar(conteudo, _ancoras(), Audiencia.INICIANTE).destino is (
        Destino.REPROVADO_CORRIGIVEL
    )

    frouxos = Limiares(
        audiencia=Audiencia.INICIANTE,
        flesch_br=Faixa(),
        explicacao=ExigenciaDeExplicacao.NUNCA,
        aderencia_minima=0.5,
        origem="Calibração de teste",
    )
    laudo = avaliar(conteudo, _ancoras(), Audiencia.INICIANTE, limiares=frouxos)

    assert laudo.destino is Destino.APROVADO
    medida = laudo.medida(Metrica.ADERENCIA)
    assert medida is not None
    assert medida.faixa == Faixa(minimo=0.5)
    assert medida.atingiu is True


def test_motivos_saem_na_ordem_das_medidas_e_sem_repeticao() -> None:
    texto = (
        "O hiato do produto segue positivo neste trimestre. "
        "O preço subiu 15%. "
        "Você deve comprar prefixados agora."
    )
    laudo = avaliar(_analitico(texto), _ancoras(com_placar=False), Audiencia.INICIANTE)

    assert laudo.motivos == sorted(laudo.motivos, key=_ordem_do_motivo)
    assert len(laudo.motivos) == len(set(laudo.motivos))
    assert laudo.destino is Destino.REPROVADO_REVISAO_HUMANA


def _ordem_do_motivo(motivo: MotivoReprovacao) -> int:
    ordem = [
        MotivoReprovacao.FALHA_DE_EXTRACAO,
        MotivoReprovacao.FLESCH_BR,
        MotivoReprovacao.DENSIDADE,
        MotivoReprovacao.ADERENCIA,
        MotivoReprovacao.RECOMENDACAO,
    ]
    return ordem.index(motivo)
