"""Ata sem número vira conteúdo qualitativo (ADR 0034): a afirmação central substitui o número."""

from __future__ import annotations

from datetime import date

from suno.avaliador import avaliar
from suno.avaliador.integridade import medir_integridade
from suno.dominio import (
    CHAVES_ESSENCIAIS,
    CHAVES_ESSENCIAIS_GENERICAS,
    Ancoras,
    AncoraNumerica,
    AncoraTextual,
    Ata,
    Audiencia,
    CategoriaDaAta,
    Conteudo,
    Formato,
    MotivoReprovacao,
    Unidade,
)
from suno.gerador.extracao import extrair_ancoras, montar_pedido_de_extracao, por_regra_generica
from suno.gerador.moldes import INSTRUCAO_SEM_NUMERO, montar_pedido, sem_numero_a_citar
from suno.ingestao.numeros import extrair_numeros
from suno.provedores.falso import ProvedorFalso

TEXTO = (
    "FATO RELEVANTE\n"
    "A Empresa Exemplo S.A. informa ao mercado que o conselho de administração aprovou a "
    "substituição do diretor-presidente, que deixa o cargo após a conclusão do plano de sucessão. "
    "O novo diretor-presidente é um executivo da própria companhia."
)
TRECHO = "o conselho de administração aprovou a substituição do diretor-presidente"
TITULO = "Empresa Exemplo S.A. · sucessão"


def _ata(texto: str = TEXTO, referencia: date = date(2026, 10, 8)) -> Ata:
    return Ata(
        identificador="fato-sem-numero",
        titulo=TITULO,
        data_referencia=referencia,
        texto=texto,
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
        origem="cvm_fatos_relevantes",
    )


def _afirmacao(trecho: str = TRECHO) -> AncoraTextual:
    return AncoraTextual(identificador="decisao", afirmacao="O conselho trocou o presidente.", trecho=trecho)


def _data() -> AncoraNumerica:
    return AncoraNumerica(
        chave="data_do_comunicado",
        rotulo="data",
        valor_literal="08/10/2026",
        unidade=Unidade.DATA,
        trecho=TITULO,
        data_iso=date(2026, 10, 8),
    )


def _provedor(afirmacoes: list[dict]) -> ProvedorFalso:
    return ProvedorFalso({"extracao": [{"chaves": [], "afirmacoes": afirmacoes}]})


# ---------------------------------------------------------------------------
# Integridade
# ---------------------------------------------------------------------------


def test_afirmacao_central_substitui_o_numero_principal():
    resultado = medir_integridade([_data(), _afirmacao()], CHAVES_ESSENCIAIS_GENERICAS)
    assert resultado.completa and resultado.faltantes == []


def test_sem_numero_e_sem_afirmacao_continua_falha_de_extracao():
    resultado = medir_integridade([_data()], CHAVES_ESSENCIAIS_GENERICAS)
    assert not resultado.completa and resultado.faltantes == ["numero_principal"]


def test_afirmacao_sem_trecho_nao_vale():
    resultado = medir_integridade([_data(), _afirmacao(trecho="  ")], CHAVES_ESSENCIAIS_GENERICAS)
    assert not resultado.completa


def test_no_copom_a_afirmacao_nao_substitui_a_decisao():
    resultado = medir_integridade([_afirmacao()], CHAVES_ESSENCIAIS)
    assert not resultado.completa and "selic_decidida" in resultado.faltantes


def test_na_visao_unida_a_afirmacao_vale_so_para_a_propria_parte():
    essenciais = frozenset(
        {"a1_data_do_comunicado", "a1_numero_principal", "a2_data_do_comunicado", "a2_numero_principal"}
    )
    datas = [
        _data().model_copy(update={"chave": "a1_data_do_comunicado"}),
        _data().model_copy(update={"chave": "a2_data_do_comunicado"}),
    ]
    so_da_parte_1 = [*datas, _afirmacao().model_copy(update={"identificador": "a1_decisao"})]
    assert medir_integridade(so_da_parte_1, essenciais).faltantes == ["a2_numero_principal"]
    nas_duas = [*so_da_parte_1, _afirmacao().model_copy(update={"identificador": "a2_decisao"})]
    assert medir_integridade(nas_duas, essenciais).completa


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------


def test_sem_data_no_texto_vale_a_data_dos_metadados():
    ata = _ata(referencia=date(2026, 10, 8))
    ancoras = por_regra_generica(ata, extrair_numeros(ata.texto, ano_padrao=2026))
    data = next(a for a in ancoras if a.chave == "data_do_comunicado")
    assert data.data_iso == date(2026, 10, 8) and data.valor_literal == "08/10/2026"
    assert data.trecho == TITULO, "o trecho é o título, nunca vazio"
    assert not any(a.chave == "numero_principal" for a in ancoras)


def test_a_data_do_texto_continua_ganhando_da_dos_metadados():
    ata = _ata("Em 7 de outubro de 2026 a companhia aprovou a operação. " + TEXTO)
    ancoras = por_regra_generica(ata, extrair_numeros(ata.texto, ano_padrao=2026))
    data = next(a for a in ancoras if a.chave == "data_do_comunicado")
    assert data.trecho != TITULO


def test_extracao_de_ata_sem_numero_guarda_a_afirmacao_conferida():
    ata = _ata()
    ancoras = extrair_ancoras(
        ata, _provedor([{"identificador": "decisao", "afirmacao": "Trocou o presidente.", "trecho": TRECHO}])
    )
    assert [t.identificador for t in ancoras.textuais] == ["decisao"]
    assert medir_integridade(ancoras.todas(), CHAVES_ESSENCIAIS_GENERICAS).completa


def test_afirmacao_inventada_pelo_llm_e_descartada_e_a_extracao_falha():
    ata = _ata()
    ancoras = extrair_ancoras(
        ata,
        _provedor([{"identificador": "x", "afirmacao": "A empresa fechou.", "trecho": "frase que não está na Ata"}]),
    )
    assert ancoras.textuais == []
    assert not medir_integridade(ancoras.todas(), CHAVES_ESSENCIAIS_GENERICAS).completa


def test_o_pedido_de_extracao_sem_numero_pede_de_uma_a_cinco_afirmacoes():
    ata = _ata()
    pedido = montar_pedido_de_extracao(ata, extrair_numeros(ata.texto, ano_padrao=2026), [])
    sistema = pedido.mensagens[0].texto
    assert "não traz número nenhum" in sistema and "1 a 5" in sistema
    com_numero = _ata(TEXTO + " O valor da operação foi de R$ 2 bilhões.")
    outro = montar_pedido_de_extracao(com_numero, extrair_numeros(com_numero.texto, ano_padrao=2026), [])
    assert "não traz número nenhum" not in outro.mensagens[0].texto


# ---------------------------------------------------------------------------
# Gerador e Avaliador
# ---------------------------------------------------------------------------


def _ancoras(*numericas: AncoraNumerica, textuais: list[AncoraTextual] | None = None) -> Ancoras:
    return Ancoras(ata="fato-sem-numero", numericas=list(numericas), textuais=textuais or [])


def test_o_prompt_do_gerador_manda_escrever_sem_inventar_numero_e_lista_as_afirmacoes():
    ancoras = _ancoras(_data(), textuais=[_afirmacao()])
    assert sem_numero_a_citar(ancoras)
    pedido = montar_pedido(TEXTO, ancoras, Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)
    assert INSTRUCAO_SEM_NUMERO in pedido.mensagens[0].texto
    assert "O conselho trocou o presidente." in pedido.mensagens[1].texto


def test_com_numero_o_prompt_nao_pede_conteudo_qualitativo_mas_lista_as_afirmacoes():
    # As afirmações fixam o sentido do fato: sem elas o gerador escreveu "o Copom mantém os
    # juros" sobre uma Ata que cortou a Selic (beta teste copom-281, 2026-10-17).
    valor = AncoraNumerica(
        chave="numero_principal",
        rotulo="valor",
        valor_literal="1,5 bilhão",
        unidade=Unidade.REAIS,
        trecho="R$ 1,5 bilhão",
    )
    ancoras = _ancoras(_data(), valor, textuais=[_afirmacao()])
    assert not sem_numero_a_citar(ancoras)
    pedido = montar_pedido(TEXTO, ancoras, Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)
    assert INSTRUCAO_SEM_NUMERO not in pedido.mensagens[0].texto
    assert "O conselho trocou o presidente." in pedido.mensagens[1].texto


def test_conteudo_sem_numero_nao_reprova_por_extracao_nem_por_aderencia():
    conteudo = Conteudo(
        formato=Formato.TEXTO_ANALITICO,
        texto=(
            "A empresa trocou o presidente. O conselho aprovou a mudança. "
            "O novo líder já trabalhava na casa. Isso mostra um plano de sucessão."
        ),
        ancoras_citadas=[],
    )

    laudo = avaliar(
        conteudo, [_data(), _afirmacao()], Audiencia.INICIANTE, chaves_essenciais=CHAVES_ESSENCIAIS_GENERICAS
    )

    assert MotivoReprovacao.FALHA_DE_EXTRACAO not in laudo.motivos
    assert MotivoReprovacao.ADERENCIA not in laudo.motivos


def test_sem_afirmacao_o_mesmo_conteudo_reprova_por_extracao():
    conteudo = Conteudo(formato=Formato.TEXTO_ANALITICO, texto="A empresa trocou o presidente.", ancoras_citadas=[])
    laudo = avaliar(conteudo, [_data()], Audiencia.INICIANTE, chaves_essenciais=CHAVES_ESSENCIAIS_GENERICAS)
    assert MotivoReprovacao.FALHA_DE_EXTRACAO in laudo.motivos
