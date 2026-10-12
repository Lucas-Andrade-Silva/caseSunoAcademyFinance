"""A categoria da Ata: o Copom tem Âncoras essenciais calibradas; as outras Origens usam um conjunto
genérico (uma data e um número) e a Saída leva o selo "não calibrado".

Os Limiares e o Léxico foram medidos só com Atas do Copom. O conjunto genérico existe para um
Fato Relevante ou um documento importado não reprovar tudo por `falha de extração` só por não ter
`selic_decidida`, e não para dizer que o resto da calibração vale fora do Copom.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from suno.avaliador import avaliar
from suno.avaliador.integridade import medir_integridade
from suno.dominio import (
    CHAVES_ESSENCIAIS,
    CHAVES_ESSENCIAIS_GENERICAS,
    AncoraNumerica,
    Ata,
    Audiencia,
    CategoriaDaAta,
    Conteudo,
    Formato,
    MotivoReprovacao,
    Unidade,
    chaves_essenciais_da,
)
from suno.gerador.extracao import extrair_ancoras, montar_pedido_de_extracao
from suno.gerador.moldes import montar_pedido
from suno.ingestao.numeros import extrair_numeros
from suno.ingestao.pdf import carregar_ata
from suno.dominio import Ancoras
from suno.provedores.falso import ProvedorFalso

TEXTO_DO_COMUNICADO = (
    "FATO RELEVANTE\n"
    "A Empresa Exemplo S.A. informa que, em 8 de outubro de 2026, aprovou a aquisição de 100% "
    "das ações da Outra S.A. pelo valor de R$ 1,5 bilhão."
)


def _comunicado_relevante(texto: str = TEXTO_DO_COMUNICADO) -> Ata:
    return Ata(
        identificador="fato-relevante-exemplo",
        titulo="Empresa Exemplo S.A. · aquisição",
        data_referencia=date(2026, 10, 8),
        texto=texto,
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
        origem="cvm_fatos_relevantes",
    )


def _ancora(chave: str, unidade: Unidade, literal: str) -> AncoraNumerica:
    return AncoraNumerica(
        chave=chave, rotulo=chave, valor_literal=literal, unidade=unidade, trecho=f"... {literal} ..."
    )


# ---------------------------------------------------------------------------
# O domínio
# ---------------------------------------------------------------------------


def test_ata_sem_categoria_vale_copom():
    ata = Ata(identificador="x", titulo="x", data_referencia=date(2026, 8, 5), texto="t")

    assert ata.categoria is CategoriaDaAta.COPOM
    assert ata.origem == "copom"


def test_cada_categoria_tem_o_seu_conjunto_essencial():
    assert chaves_essenciais_da(CategoriaDaAta.COPOM) == CHAVES_ESSENCIAIS
    for categoria in (
        CategoriaDaAta.COMUNICADO_RELEVANTE,
        CategoriaDaAta.RELEASE,
        CategoriaDaAta.IMPORTADA,
    ):
        assert chaves_essenciais_da(categoria) == CHAVES_ESSENCIAIS_GENERICAS
    assert CHAVES_ESSENCIAIS_GENERICAS == {"data_do_comunicado", "numero_principal"}


def test_carregar_ata_le_categoria_e_origem_do_json(tmp_path: Path):
    (tmp_path / "comunicado-1.txt").write_text(TEXTO_DO_COMUNICADO, encoding="utf-8")
    (tmp_path / "comunicado-1.json").write_text(
        json.dumps(
            {
                "titulo": "Fato 1",
                "data_referencia": "2026-10-08",
                "categoria": "comunicado_relevante",
                "origem": "cvm_fatos_relevantes",
            }
        ),
        encoding="utf-8",
    )

    ata = carregar_ata(tmp_path / "comunicado-1.txt")

    assert ata.categoria is CategoriaDaAta.COMUNICADO_RELEVANTE
    assert ata.origem == "cvm_fatos_relevantes"


def test_carregar_ata_do_copom_sem_categoria_no_json_continua_copom():
    ata = carregar_ata(Path(__file__).resolve().parent.parent / "data" / "atas" / "copom-280-2026-08-05.pdf")

    assert ata.categoria is CategoriaDaAta.COPOM


# ---------------------------------------------------------------------------
# A integridade
# ---------------------------------------------------------------------------


def test_integridade_generica_aprova_com_data_e_numero():
    ancoras = [
        _ancora("data_do_comunicado", Unidade.DATA, "8 de outubro de 2026"),
        _ancora("numero_principal", Unidade.REAIS, "1,5 bilhão"),
    ]

    resultado = medir_integridade(ancoras, CHAVES_ESSENCIAIS_GENERICAS)

    assert resultado.completa
    assert resultado.faltantes == []


def test_integridade_generica_reprova_sem_numero():
    ancoras = [_ancora("data_do_comunicado", Unidade.DATA, "8 de outubro de 2026")]

    resultado = medir_integridade(ancoras, CHAVES_ESSENCIAIS_GENERICAS)

    assert not resultado.completa
    assert resultado.faltantes == ["numero_principal"]


def test_o_conjunto_do_copom_continua_sendo_o_padrao():
    ancoras = [
        _ancora("data_do_comunicado", Unidade.DATA, "8 de outubro de 2026"),
        _ancora("numero_principal", Unidade.REAIS, "1,5 bilhão"),
    ]

    resultado = medir_integridade(ancoras)

    assert not resultado.completa
    assert "selic_decidida" in resultado.faltantes


def test_avaliar_so_reprova_por_extracao_com_o_conjunto_da_categoria():
    ancoras = [
        _ancora("data_do_comunicado", Unidade.DATA, "8 de outubro de 2026"),
        _ancora("numero_principal", Unidade.REAIS, "1,5 bilhão"),
    ]
    conteudo = Conteudo(
        formato=Formato.TEXTO_ANALITICO,
        texto="A empresa comunicou uma compra. O mercado acompanha os próximos passos.",
        ancoras_citadas=[],
    )

    no_copom = avaliar(conteudo, ancoras, Audiencia.INICIANTE)
    no_generico = avaliar(
        conteudo, ancoras, Audiencia.INICIANTE, chaves_essenciais=CHAVES_ESSENCIAIS_GENERICAS
    )

    assert MotivoReprovacao.FALHA_DE_EXTRACAO in no_copom.motivos
    assert MotivoReprovacao.FALHA_DE_EXTRACAO not in no_generico.motivos


# ---------------------------------------------------------------------------
# A extração
# ---------------------------------------------------------------------------


def test_extracao_generica_acha_data_e_numero_por_regra_fixa():
    provedor = ProvedorFalso({"extracao": [{"chaves": [], "afirmacoes": []}]})

    ancoras = extrair_ancoras(_comunicado_relevante(), provedor)

    data = ancoras.numerica("data_do_comunicado")
    numero = ancoras.numerica("numero_principal")
    assert data is not None and data.unidade is Unidade.DATA and data.data_iso == date(2026, 10, 8)
    assert numero is not None
    assert numero.unidade is Unidade.REAIS  # prefere o valor em reais ao primeiro número
    assert numero.valor_literal == "1,5 bilhão"
    assert numero.trecho in TEXTO_DO_COMUNICADO.replace("\n", " ")


def test_extracao_generica_nao_pede_chave_do_copom_ao_llm():
    provedor = ProvedorFalso({"extracao": [{"chaves": [], "afirmacoes": []}]})

    extrair_ancoras(_comunicado_relevante(), provedor)

    pedido = provedor.pedidos[0]
    sistema = pedido.mensagens[0].texto
    usuario = pedido.mensagens[1].texto
    assert "Copom" not in sistema
    assert "selic" not in usuario.lower().split("texto da ata")[0]


def test_extracao_generica_aceita_chave_livre_do_llm():
    candidatos = extrair_numeros(TEXTO_DO_COMUNICADO, ano_padrao=2026)
    indice_das_acoes = next(i for i, c in enumerate(candidatos) if c.unidade is Unidade.PERCENTUAL)
    provedor = ProvedorFalso(
        {
            "extracao": [
                {
                    "chaves": [{"chave": "participacao_adquirida", "indice": indice_das_acoes}],
                    "afirmacoes": [],
                }
            ]
        }
    )

    ancoras = extrair_ancoras(_comunicado_relevante(), provedor)

    participacao = ancoras.numerica("participacao_adquirida")
    assert participacao is not None and participacao.valor_literal == "100"


def test_comunicado_sem_numero_nao_tem_numero_principal():
    ata = _comunicado_relevante("FATO RELEVANTE\nA Empresa informa que, em 8 de outubro de 2026, reuniu o conselho.")
    provedor = ProvedorFalso({"extracao": [{"chaves": [], "afirmacoes": []}]})

    ancoras = extrair_ancoras(ata, provedor)

    assert ancoras.numerica("data_do_comunicado") is not None
    assert ancoras.numerica("numero_principal") is None


def test_o_pedido_de_extracao_do_copom_nao_mudou():
    ata = Ata(
        identificador="copom", titulo="Copom", data_referencia=date(2026, 8, 5), texto="Texto."
    )

    pedido = montar_pedido_de_extracao(ata, [], ["selic_anterior"])

    assert "Ata do Copom" in pedido.mensagens[0].texto
    assert "- selic_anterior:" in pedido.mensagens[1].texto


# ---------------------------------------------------------------------------
# O molde da Célula
# ---------------------------------------------------------------------------


def test_o_molde_fala_do_comunicado_certo():
    ancoras = Ancoras(ata="x")

    do_copom = montar_pedido("texto", ancoras, Audiencia.INICIANTE, Formato.CARROSSEL)
    de_cvm = montar_pedido(
        "texto",
        ancoras,
        Audiencia.INICIANTE,
        Formato.CARROSSEL,
        comunicado="um Fato Relevante da CVM",
    )

    assert "Você adapta uma Ata do Copom" in do_copom.mensagens[0].texto
    assert "Você adapta um Fato Relevante da CVM" in de_cvm.mensagens[0].texto
    assert "Copom" not in de_cvm.mensagens[0].texto
