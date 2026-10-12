"""A Visão unida: um só conteúdo que junta de 2 a 5 Atas, com cada número citando a sua origem.

É a peça mais difícil do painel (spec do front, risco 5). Aqui se prova o que a sustenta: o
dossiê composto, as chaves de Âncora prefixadas por parte (nada colide), o conjunto essencial por
parte, a instrução do molde e a execução ponta a ponta com o provedor falso.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from suno.dominio import (
    CHAVES_ESSENCIAIS_GENERICAS,
    Ancoras,
    Ata,
    Audiencia,
    CategoriaDaAta,
    Formato,
    ModoSelecao,
    chaves_essenciais_da_ata,
)
from suno.avaliador.integridade import medir_integridade
from suno.gerador import execucao as modulo_execucao
from suno.gerador.ciclo import gerar_celula
from suno.gerador.curador import AgenteCurador, compor_uniao
from suno.gerador.execucao import carregar_execucao, executar
from suno.gerador.extracao import extrair_ancoras_da_uniao
from suno.gerador.moldes import INSTRUCAO_DA_VISAO_UNIDA, montar_pedido
from suno.ingestao.pdf import carregar_ata
from suno.provedores.falso import ProvedorFalso

RAIZ = Path(__file__).resolve().parent.parent
COPOM = RAIZ / "data" / "atas" / "copom-280-2026-08-05.pdf"
TRECHO_DO_COPOM = "O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a."

TEXTO_DA_AQUISICAO = (
    "Em 8 de outubro de 2026 a Empresa Exemplo S.A. aprovou a aquisição de 100% das ações da "
    "Outra S.A. pelo valor de R$ 1,5 bilhão."
)
TEXTO_DA_EMISSAO = (
    "Em 9 de outubro de 2026 a Companhia Modelo S.A. aprovou a emissão de debêntures no valor "
    "de R$ 800 milhões, com vencimento em 5 anos."
)


def _ata(
    identificador: str,
    titulo: str,
    texto: str,
    data: date = date(2026, 10, 8),
    categoria: CategoriaDaAta = CategoriaDaAta.COMUNICADO_RELEVANTE,
) -> Ata:
    return Ata(
        identificador=identificador,
        titulo=titulo,
        data_referencia=data,
        texto=texto,
        categoria=categoria,
        origem="cvm_fatos_relevantes",
    )


@pytest.fixture
def copom() -> Ata:
    return carregar_ata(COPOM)


@pytest.fixture
def aquisicao() -> Ata:
    return _ata("cvm-aquisicao", "Empresa Exemplo · aquisição", TEXTO_DA_AQUISICAO)


@pytest.fixture
def emissao() -> Ata:
    return _ata(
        "cvm-emissao",
        "Companhia Modelo · emissão",
        TEXTO_DA_EMISSAO,
        data=date(2026, 10, 9),
    )


def _resposta_vazia() -> dict:
    return {"chaves": [], "afirmacoes": []}


# ---------------------------------------------------------------------------
# Compor
# ---------------------------------------------------------------------------


def test_a_uniao_junta_os_textos_sob_cabecalhos_numerados(copom: Ata, aquisicao: Ata):
    uniao = compor_uniao([copom, aquisicao])

    assert uniao.categoria is CategoriaDaAta.UNIDA
    assert uniao.partes == [copom.identificador, aquisicao.identificador]
    assert uniao.titulo.startswith("Visão unida: ")
    assert copom.titulo in uniao.titulo and aquisicao.titulo in uniao.titulo
    assert "[a1]" in uniao.texto and "[a2]" in uniao.texto
    assert uniao.texto.index("[a1]") < uniao.texto.index(TRECHO_DO_COPOM)
    assert uniao.texto.index("[a2]") < uniao.texto.index(TEXTO_DA_AQUISICAO)
    assert uniao.data_referencia == max(copom.data_referencia, aquisicao.data_referencia)


def test_o_identificador_da_uniao_e_estavel_curto_e_serve_de_pasta(copom: Ata, aquisicao: Ata):
    primeira = compor_uniao([copom, aquisicao])
    segunda = compor_uniao([copom, aquisicao])

    assert primeira.identificador == segunda.identificador
    assert primeira.identificador.startswith("uniao-")
    assert len(primeira.identificador) <= 20
    assert modulo_execucao.NOME_DE_PASTA.match(primeira.identificador)
    assert compor_uniao([aquisicao, copom]).identificador != primeira.identificador


@pytest.mark.parametrize("quantidade", [0, 1, 6])
def test_a_uniao_exige_de_duas_a_cinco_atas(quantidade: int, aquisicao: Ata):
    atas = [
        _ata(f"cvm-{n}", f"Comunicado {n}", TEXTO_DA_AQUISICAO) for n in range(quantidade)
    ]

    with pytest.raises(ValueError, match="de 2 a 5"):
        compor_uniao(atas)


def test_a_uniao_recusa_ata_repetida(aquisicao: Ata):
    with pytest.raises(ValueError, match="repetida"):
        compor_uniao([aquisicao, aquisicao])


# ---------------------------------------------------------------------------
# Extrair: uma chamada por parte, chaves prefixadas
# ---------------------------------------------------------------------------


def test_as_chaves_ganham_o_prefixo_da_parte_e_nada_colide(
    copom: Ata, aquisicao: Ata, emissao: Ata
):
    uniao = compor_uniao([copom, aquisicao, emissao])
    provedor = ProvedorFalso(
        {
            "extracao": [
                {
                    "chaves": [],
                    "afirmacoes": [
                        {
                            "identificador": "decisao",
                            "afirmacao": "O Copom reduziu a Selic.",
                            "trecho": TRECHO_DO_COPOM,
                        }
                    ],
                },
                _resposta_vazia(),
                _resposta_vazia(),
            ]
        }
    )

    ancoras = extrair_ancoras_da_uniao([copom, aquisicao, emissao], uniao, provedor)

    chaves = [a.chave for a in ancoras.numericas]
    assert len(chaves) == len(set(chaves))
    for prefixo in ("a1", "a2", "a3"):
        assert f"{prefixo}_data_do_comunicado" in chaves
        assert f"{prefixo}_numero_principal" in chaves
    assert "a1_selic_decidida" in chaves  # a parte do Copom ainda tem as chaves do Copom
    assert not any(c in chaves for c in ("data_do_comunicado", "numero_principal", "selic_decidida"))
    assert provedor.rotulos_pedidos() == ["extracao", "extracao", "extracao"]


def test_o_rotulo_diz_de_que_comunicado_vem_o_numero(copom: Ata, aquisicao: Ata):
    uniao = compor_uniao([copom, aquisicao])
    provedor = ProvedorFalso({"extracao": [_resposta_vazia(), _resposta_vazia()]})

    ancoras = extrair_ancoras_da_uniao([copom, aquisicao], uniao, provedor)

    do_segundo = ancoras.numerica("a2_numero_principal")
    assert do_segundo is not None
    assert do_segundo.rotulo.startswith("[a2] ")
    assert "Empresa Exemplo" in do_segundo.rotulo
    assert do_segundo.valor_literal == "1,5 bilhão"


def test_a_ancora_textual_tambem_ganha_o_prefixo(copom: Ata, aquisicao: Ata):
    uniao = compor_uniao([copom, aquisicao])
    provedor = ProvedorFalso(
        {
            "extracao": [
                {
                    "chaves": [],
                    "afirmacoes": [
                        {
                            "identificador": "decisao",
                            "afirmacao": "O Copom reduziu a Selic.",
                            "trecho": TRECHO_DO_COPOM,
                        }
                    ],
                },
                _resposta_vazia(),
            ]
        }
    )

    ancoras = extrair_ancoras_da_uniao([copom, aquisicao], uniao, provedor)

    assert [t.identificador for t in ancoras.textuais] == ["a1_decisao"]
    assert ancoras.textuais[0].afirmacao.startswith("[a1] ")


def test_chave_livre_do_llm_tambem_e_prefixada(copom: Ata, aquisicao: Ata):
    uniao = compor_uniao([copom, aquisicao])
    from suno.ingestao.numeros import extrair_numeros

    candidatos = extrair_numeros(aquisicao.texto, ano_padrao=2026)
    indice = next(i for i, c in enumerate(candidatos) if c.literal == "100")
    provedor = ProvedorFalso(
        {
            "extracao": [
                _resposta_vazia(),
                {"chaves": [{"chave": "participacao", "indice": indice}], "afirmacoes": []},
            ]
        }
    )

    ancoras = extrair_ancoras_da_uniao([copom, aquisicao], uniao, provedor)

    assert ancoras.numerica("a2_participacao") is not None


# ---------------------------------------------------------------------------
# O conjunto essencial é por parte
# ---------------------------------------------------------------------------


def test_o_essencial_da_uniao_e_o_generico_de_cada_parte(copom: Ata, aquisicao: Ata):
    uniao = compor_uniao([copom, aquisicao])

    essenciais = chaves_essenciais_da_ata(uniao)

    assert essenciais == {f"a{n}_{chave}" for n in (1, 2) for chave in CHAVES_ESSENCIAIS_GENERICAS}


def test_o_essencial_de_uma_ata_comum_continua_o_da_categoria(copom: Ata, aquisicao: Ata):
    assert chaves_essenciais_da_ata(aquisicao) == CHAVES_ESSENCIAIS_GENERICAS
    assert "selic_decidida" in chaves_essenciais_da_ata(copom)


def test_uma_parte_sem_numero_reprova_a_extracao_da_matriz_inteira(copom: Ata):
    sem_numero = _ata(
        "cvm-sem-numero",
        "Pedido de cancelamento",
        "São Paulo, 2 de outubro de 2026. A companhia pediu o cancelamento do registro.",
    )
    uniao = compor_uniao([copom, sem_numero])
    provedor = ProvedorFalso({"extracao": [_resposta_vazia(), _resposta_vazia()]})

    ancoras = extrair_ancoras_da_uniao([copom, sem_numero], uniao, provedor)
    resultado = medir_integridade(ancoras.todas(), chaves_essenciais_da_ata(uniao))

    assert not resultado.completa
    assert resultado.faltantes == ["a2_numero_principal"]


# ---------------------------------------------------------------------------
# O molde
# ---------------------------------------------------------------------------


def test_o_molde_da_uniao_manda_citar_a_origem_de_cada_numero():
    ancoras = Ancoras(ata="x")

    pedido = montar_pedido(
        "texto",
        ancoras,
        Audiencia.INICIANTE,
        Formato.CARROSSEL,
        comunicado="um conjunto de comunicados financeiros",
        instrucoes_do_conjunto=INSTRUCAO_DA_VISAO_UNIDA,
    )

    sistema = pedido.mensagens[0].texto
    assert "Você adapta um conjunto de comunicados financeiros" in sistema
    assert INSTRUCAO_DA_VISAO_UNIDA in sistema
    assert "de qual comunicado" in INSTRUCAO_DA_VISAO_UNIDA


def test_gerar_celula_da_uniao_usa_a_instrucao_e_a_descricao_da_categoria(
    copom: Ata, aquisicao: Ata
):
    uniao = compor_uniao([copom, aquisicao])
    resposta = {
        "titulo": "Visão unida",
        "o_que_foi_decidido": "A empresa aprovou a compra por {{a2_numero_principal}}.",
        "por_que": "A decisão amplia a atuação da companhia.",
        "o_que_observar_adiante": "Os próximos passos dependem dos órgãos competentes.",
    }
    provedor = ProvedorFalso({"extracao": [_resposta_vazia(), _resposta_vazia()]})
    ancoras = extrair_ancoras_da_uniao([copom, aquisicao], uniao, provedor)
    provedor.enfileirar("celula:iniciante:texto_analitico:0", resposta)

    celula = gerar_celula(uniao, ancoras, Audiencia.INICIANTE, Formato.TEXTO_ANALITICO, provedor)

    pedido = next(p for p in provedor.pedidos if p.rotulo.startswith("celula:"))
    assert "um conjunto de comunicados" in pedido.mensagens[0].texto
    assert INSTRUCAO_DA_VISAO_UNIDA in pedido.mensagens[0].texto
    assert "a2_numero_principal" in celula.conteudo.ancoras_citadas


# ---------------------------------------------------------------------------
# Ponta a ponta
# ---------------------------------------------------------------------------


def test_a_execucao_da_uniao_grava_o_modo_os_itens_e_as_ancoras_prefixadas(
    tmp_path: Path, monkeypatch, aquisicao: Ata
):
    atas = tmp_path / "atas"
    atas.mkdir()
    (atas / "cvm-aquisicao.txt").write_text(aquisicao.texto, encoding="utf-8")
    (atas / "cvm-aquisicao.json").write_text(
        json.dumps(
            {
                "titulo": aquisicao.titulo,
                "data_referencia": "2026-10-08",
                "categoria": "comunicado_relevante",
                "origem": "cvm_fatos_relevantes",
            }
        ),
        encoding="utf-8",
    )
    copom = carregar_ata(COPOM)
    uniao = compor_uniao([copom, carregar_ata(atas / "cvm-aquisicao.txt")])
    resposta = {
        "titulo": "Visão unida",
        "o_que_foi_decidido": "A empresa aprovou a compra por {{a2_numero_principal}}.",
        "por_que": "A decisão amplia a atuação da companhia.",
        "o_que_observar_adiante": "Os próximos passos dependem dos órgãos competentes.",
    }
    prontas = tmp_path / "prontas"
    prontas.mkdir()
    (prontas / f"{uniao.identificador}.json").write_text(
        json.dumps(
            {
                "extracao": [_resposta_vazia(), _resposta_vazia()],
                "celula:iniciante:texto_analitico:0": [resposta],
                "celula:iniciante:texto_analitico:1": [resposta],
                "celula:iniciante:texto_analitico:2": [resposta],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(modulo_execucao, "PASTA_RESPOSTAS_PRONTAS", prontas)

    execucao = executar(
        [COPOM, atas / "cvm-aquisicao.txt"],
        "falso",
        tmp_path / "execucoes",
        pedido=[(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)],
        identificador="saida-unida",
    )

    assert execucao.ata == uniao.identificador
    assert execucao.categoria is CategoriaDaAta.UNIDA
    assert execucao.selecao is not None
    assert execucao.selecao.modo is ModoSelecao.UNIDA
    assert execucao.selecao.itens == [copom.identificador, "cvm-aquisicao"]
    chaves = {a.chave for a in execucao.ancoras.numericas}
    assert {"a1_selic_decidida", "a2_numero_principal"} <= chaves
    assert len(execucao.celulas) == 1
    celula = execucao.celulas[0].celula_final
    assert celula is not None and "a2_numero_principal" in celula.conteudo.ancoras_citadas
    # volta do disco igual
    assert carregar_execucao("saida-unida", tmp_path / "execucoes").selecao == execucao.selecao


def test_executar_com_uma_lista_de_uma_ata_so_e_a_execucao_de_sempre(tmp_path: Path):
    execucao = executar(
        [COPOM],
        "falso",
        tmp_path,
        pedido=[(Audiencia.INICIANTE, Formato.CARROSSEL)],
    )

    assert execucao.categoria is CategoriaDaAta.COPOM
    assert execucao.selecao is not None and execucao.selecao.modo is ModoSelecao.SEPARADA
    assert execucao.ata == "copom-280-2026-08-05"
