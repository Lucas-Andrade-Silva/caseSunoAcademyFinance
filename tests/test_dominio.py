"""Os modelos fechados do domínio: o contrato que todos os módulos assumem."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from suno.dominio import (
    CHAVES_ESSENCIAIS,
    LIMIARES_PROVISORIOS,
    MATRIZ,
    AncoraNumerica,
    AncoraTextual,
    Ancoras,
    Audiencia,
    BlocoFala,
    Celula,
    ChaveAncora,
    Conteudo,
    Destino,
    EstadoMedida,
    Execucao,
    Faixa,
    Formato,
    HistoricoCelula,
    Laudo,
    Medida,
    Metrica,
    MotivoReprovacao,
    Slide,
    Tentativa,
    Unidade,
)


def _ancora_selic() -> AncoraNumerica:
    return AncoraNumerica(
        chave=ChaveAncora.SELIC_DECIDIDA,
        rotulo="Selic decidida",
        valor_literal="14,00",
        valor=14.0,
        unidade=Unidade.PERCENTUAL_AO_ANO,
        trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
    )


def _laudo(destino: Destino, motivos: list[MotivoReprovacao]) -> Laudo:
    return Laudo(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.TEXTO_ANALITICO,
        medidas=[Medida(metrica=Metrica.FLESCH_BR, valor=55.0, faixa=Faixa(minimo=50), atingiu=True)],
        destino=destino,
        motivos=motivos,
    )


# -- Matriz -------------------------------------------------------------------


def test_matriz_tem_nove_celulas_em_ordem_estavel():
    assert len(MATRIZ) == 9
    assert MATRIZ[0] == (Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)
    assert MATRIZ[-1] == (Audiencia.AVANCADO, Formato.ROTEIRO)
    assert len(set(MATRIZ)) == 9


# -- Âncoras (ADR 0011) ---------------------------------------------------------


def test_ancora_numerica_cita_valor_literal_com_unidade():
    assert _ancora_selic().citacao() == "14,00 % a.a."
    votos = AncoraNumerica(chave="placar_votacao", rotulo="Placar", valor_literal="7 a 0", unidade=Unidade.VOTOS, trecho="...")
    assert votos.citacao() == "7 a 0"
    pct = AncoraNumerica(chave="ipca", rotulo="IPCA", valor_literal="5,1", unidade=Unidade.PERCENTUAL, trecho="...")
    assert pct.citacao() == "5,1%"


def test_ancora_numerica_e_imutavel():
    with pytest.raises(ValidationError):
        _ancora_selic().valor_literal = "15,00"  # type: ignore[misc]


def test_unidades_distinguem_pp_de_percentual_e_de_pb():
    assert Unidade.PONTO_PERCENTUAL != Unidade.PERCENTUAL
    assert Unidade.PONTOS_BASE != Unidade.PONTO_PERCENTUAL
    assert {u.value for u in Unidade} >= {"%", "p.p.", "pb", "% a.a."}


def test_ancoras_sabem_o_que_falta_para_integridade():
    ancoras = Ancoras(ata="copom-280", numericas=[_ancora_selic()])
    faltantes = ancoras.chaves_faltantes()
    assert ChaveAncora.SELIC_DECIDIDA not in faltantes
    assert faltantes == CHAVES_ESSENCIAIS - {ChaveAncora.SELIC_DECIDIDA}
    assert ancoras.numerica("selic_decidida") is not None
    assert ancoras.numerica("inexistente") is None


def test_ancoras_todas_mistura_numericas_e_textuais():
    ancoras = Ancoras(
        ata="copom-280",
        numericas=[_ancora_selic()],
        textuais=[AncoraTextual(identificador="decisao", afirmacao="Reduziu a Selic.", trecho="...")],
    )
    assert len(ancoras.todas()) == 2


# -- Conteúdo e Célula --------------------------------------------------------------


def test_conteudo_exige_corpo_do_formato():
    with pytest.raises(ValidationError):
        Conteudo(formato=Formato.CARROSSEL, texto="sem slides")


def test_texto_avaliavel_do_roteiro_ignora_rubrica_de_cena():
    conteudo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[
            BlocoFala(inicio_s=0, fim_s=5, fala="A Selic caiu.", tela="GRÁFICO DA SELIC"),
            BlocoFala(inicio_s=5, fim_s=10, fala="O que muda para você?", tela="CORTE PARA APRESENTADOR"),
        ],
    )
    avaliavel = conteudo.texto_avaliavel()
    assert "A Selic caiu." in avaliavel
    assert "GRÁFICO" not in avaliavel


def test_texto_avaliavel_do_carrossel_junta_titulo_e_corpo():
    conteudo = Conteudo(formato=Formato.CARROSSEL, slides=[Slide(titulo="Gancho", corpo="Corpo do slide", dado="selic_decidida")])
    assert conteudo.texto_avaliavel() == "Gancho\nCorpo do slide"


def test_bloco_de_fala_exige_fim_depois_do_inicio():
    with pytest.raises(ValidationError):
        BlocoFala(inicio_s=5, fim_s=5, fala="x")


def test_celula_nao_aceita_formato_divergente_do_conteudo():
    with pytest.raises(ValidationError):
        Celula(audiencia=Audiencia.INICIANTE, formato=Formato.ROTEIRO, conteudo=Conteudo(formato=Formato.TEXTO_ANALITICO, texto="x"))


def test_celula_tem_no_maximo_duas_rodadas_de_correcao():
    conteudo = Conteudo(formato=Formato.TEXTO_ANALITICO, texto="x")
    Celula(audiencia=Audiencia.INICIANTE, formato=Formato.TEXTO_ANALITICO, conteudo=conteudo, rodada=2)
    with pytest.raises(ValidationError):
        Celula(audiencia=Audiencia.INICIANTE, formato=Formato.TEXTO_ANALITICO, conteudo=conteudo, rodada=3)


# -- Limiares (ADR 0002) -------------------------------------------------------------


def test_faixa_e_fechada_no_minimo_e_aberta_no_maximo():
    faixa = Faixa(minimo=25, maximo=50)
    assert faixa.contem(25)
    assert faixa.contem(49.9)
    assert not faixa.contem(50)
    assert not faixa.contem(24.9)


def test_faixa_mede_distancia_ate_entrar():
    assert Faixa(minimo=50).distancia(47.2) == pytest.approx(2.8)
    assert Faixa(maximo=25).distancia(30) == pytest.approx(5)
    assert Faixa(minimo=25, maximo=50).distancia(30) == 0


def test_limiares_provisorios_seguem_as_faixas_do_nilc():
    assert LIMIARES_PROVISORIOS[Audiencia.INICIANTE].flesch_br == Faixa(minimo=50)
    assert LIMIARES_PROVISORIOS[Audiencia.INTERMEDIARIO].flesch_br == Faixa(minimo=25, maximo=50)
    assert LIMIARES_PROVISORIOS[Audiencia.AVANCADO].flesch_br == Faixa(maximo=25)
    for limiares in LIMIARES_PROVISORIOS.values():
        assert "aguardando Calibração" in limiares.origem


# -- Laudo (ADR 0008, 0013) ------------------------------------------------------------


def test_medida_ausente_nunca_carrega_valor():
    Medida(metrica=Metrica.FLESCH_BR, estado=EstadoMedida.AUSENTE)
    with pytest.raises(ValidationError):
        Medida(metrica=Metrica.FLESCH_BR, estado=EstadoMedida.AUSENTE, valor=0.0)


def test_laudo_tem_tres_destinos():
    assert {d.value for d in Destino} == {"aprovado", "reprovado_corrigivel", "reprovado_revisao_humana"}


def test_motivo_de_reprovacao_e_enumerado_com_os_cinco_valores():
    assert {m.value for m in MotivoReprovacao} == {"flesch_br", "densidade", "aderencia", "recomendacao", "falha_de_extracao"}


def test_laudo_aprovado_nao_carrega_motivo():
    with pytest.raises(ValidationError):
        _laudo(Destino.APROVADO, [MotivoReprovacao.FLESCH_BR])


def test_laudo_reprovado_exige_motivo():
    with pytest.raises(ValidationError):
        _laudo(Destino.REPROVADO_CORRIGIVEL, [])


def test_falha_de_extracao_vai_direto_a_revisao_humana():
    _laudo(Destino.REPROVADO_REVISAO_HUMANA, [MotivoReprovacao.FALHA_DE_EXTRACAO])
    with pytest.raises(ValidationError):
        _laudo(Destino.REPROVADO_CORRIGIVEL, [MotivoReprovacao.FALHA_DE_EXTRACAO])


def test_laudo_nasce_sem_comite():
    laudo = _laudo(Destino.APROVADO, [])
    assert laudo.comite is None
    assert laudo.medida(Metrica.FLESCH_BR) is not None
    assert laudo.medida(Metrica.DENSIDADE) is None


# -- Execução em disco ---------------------------------------------------------------


def test_execucao_serializa_e_volta_igual():
    conteudo = Conteudo(formato=Formato.TEXTO_ANALITICO, texto="A Selic foi para 14,00 % a.a.", ancoras_citadas=["selic_decidida"])
    celula = Celula(audiencia=Audiencia.INICIANTE, formato=Formato.TEXTO_ANALITICO, conteudo=conteudo)
    historico = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.TEXTO_ANALITICO,
        tentativas=[
            Tentativa(rodada=0, celula=celula, laudo=_laudo(Destino.REPROVADO_CORRIGIVEL, [MotivoReprovacao.FLESCH_BR])),
            Tentativa(rodada=1, celula=celula.model_copy(update={"rodada": 1}), laudo=_laudo(Destino.APROVADO, [])),
        ],
        destino_final=Destino.APROVADO,
    )
    execucao = Execucao(
        identificador="exec-1",
        ata="copom-280-2026-08-05",
        provedor_gerador="falso",
        iniciada_em=date(2026, 9, 18).isoformat() + "T10:00:00Z",  # type: ignore[arg-type]
        ancoras=Ancoras(ata="copom-280-2026-08-05", numericas=[_ancora_selic()]),
        celulas=[historico],
    )
    reconstruida = Execucao.model_validate_json(execucao.model_dump_json())
    assert reconstruida == execucao
    assert reconstruida.historico(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO).laudo_final.destino is Destino.APROVADO
    assert reconstruida.contagem_por_motivo()[MotivoReprovacao.FLESCH_BR] == 1
