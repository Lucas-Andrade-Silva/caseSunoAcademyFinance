"""O planejador e a pontuação da busca de imagens: o catálogo de assuntos visuais (ADR 0033).

Tudo offline e sem LLM: ``planejar`` monta consultas, ``pontuar`` julga um resultado pelo texto.
"""

from __future__ import annotations

import json

import pytest

from suno.imagens.consulta import CAMINHO_DO_CATALOGO, PONTOS_PARA_APROVAR, planejar, pontuar
from suno.imagens.texto import termos
from suno.imagens.web import SEM_LICENCA, CandidatoDeImagem


def resultado(titulo: str, *, imagem: str = "https://site.com/x.jpg", pagina: str = "https://site.com/materia") -> CandidatoDeImagem:
    return CandidatoDeImagem(
        titulo=titulo, autor="site.com", licenca=SEM_LICENCA, url_pagina=pagina, url_imagem=imagem, consulta="q"
    )


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------


def test_o_catalogo_e_json_valido_com_ids_unicos_e_campos_obrigatorios():
    catalogo = json.loads(CAMINHO_DO_CATALOGO.read_text(encoding="utf-8"))
    assuntos = catalogo["assuntos"]
    ids = [a["id"] for a in assuntos]
    assert len(ids) == len(set(ids)) and len(assuntos) >= 70
    for a in assuntos:
        assert a["tipo"] in {"empresa", "instituicao", "conceito", "setor"}, a["id"]
        assert a["nome"] and a["chaves"] and a["exigir"], a["id"]
        if a["tipo"] in {"conceito", "setor"}:
            assert a.get("consultas"), f"{a['id']}: conceito e setor precisam de consultas"
        for modelo in a.get("consultas", []):
            assert modelo.format(nome="x", contexto="y")  # só {nome} e {contexto}


# ---------------------------------------------------------------------------
# Planejador
# ---------------------------------------------------------------------------


def test_b3_vira_bolsa_de_valores_e_nunca_vitamina():
    plano = planejar("B3")
    assert plano.id == "b3"
    assert plano.consultas[0].startswith("B3 bolsa de valores sede")
    assert plano.consultas[1].startswith("B3 bolsa de valores logo")
    assert "-vitamina" in plano.consultas[0] and "-niacina" in plano.consultas[0]


@pytest.mark.parametrize(
    ("assunto", "esperado"),
    [
        ("sede da B3", "b3"),
        ("pregão da B3", "ibovespa"),
        ("Banco Central do Brasil", "bc"),
        ("sede do Banco Central", "bc"),
        ("Banco do Brasil", "bb"),
        ("reunião do Copom", "copom"),
        ("taxa Selic", "selic"),
        ("inflação IPCA", "inflacao"),
        ("Itaú Unibanco", "itau"),
        ("logo Nubank", "nubank"),
        ("conta de luz", "energia"),
        ("posto de gasolina", "combustiveis"),
        ("criptomoedas", "cripto"),
        ("Tesouro Direto", "tesouro"),
        ("Magazine Luiza", "magalu"),
    ],
)
def test_o_assunto_do_slide_acha_a_entrada_certa_do_catalogo(assunto, esperado):
    assert planejar(assunto).id == esperado


def test_a_chave_mais_longa_vence_e_banco_central_nao_vira_banco_do_brasil():
    assert planejar("Banco Central do Brasil").id == "bc"
    assert planejar("sede do Banco do Brasil").id == "bb"


def test_pedido_de_logo_poe_a_consulta_de_logo_primeiro_e_o_resto_vem_depois():
    assert planejar("logo Nubank").consultas[0].startswith("Nubank banco digital logo")
    assert "sede fachada" in planejar("logo Nubank").consultas[1]
    assert "sede fachada" in planejar("Nubank").consultas[0]  # sem pedido, foto primeiro


def test_assunto_fora_do_catalogo_cai_numa_busca_de_mercado_financeiro():
    plano = planejar("Faria Lima")
    assert plano.id == "generico"
    assert plano.consultas[0].startswith("Faria Lima mercado financeiro Brasil")
    assert plano.exigir == (("faria", "lima"),)


def test_homonimos_conhecidos_viram_operador_de_exclusao():
    assert "-valentine" in planejar("Vale").consultas[0]
    assert "vale refeicao" in planejar("Vale").proibidas
    assert "-maca" in planejar("Apple").consultas[0]


def test_no_maximo_quatro_exclusoes_na_consulta():
    for assunto in ("B3", "Vale", "Apple", "dólar", "Amazon"):
        for consulta in planejar(assunto).consultas:
            assert sum(1 for t in consulta.split() if t.startswith("-")) <= 4, consulta


# ---------------------------------------------------------------------------
# Pontuação
# ---------------------------------------------------------------------------


def test_resultado_que_cita_o_assunto_no_arquivo_e_no_titulo_e_aprovado_direto():
    triagem = pontuar(
        resultado("A Bolsa de Valores, a B3, vai funcionar no feriado?", imagem="https://x.com/uploads/b3-notas.jpg"),
        planejar("B3"),
    )
    assert triagem.decisao == "aprovar" and triagem.pontos >= PONTOS_PARA_APROVAR
    assert "arquivo" in triagem.motivo and "título" in triagem.motivo


def test_logo_citando_o_assunto_e_aprovado():
    triagem = pontuar(
        resultado("Logo B3 Brasil Bolsa Balcão", imagem="https://logospng.org/download/b3/logo-b3-icone-4096.png"),
        planejar("logo da B3"),
    )
    assert triagem.decisao == "aprovar"


def test_vitamina_b3_e_descartada_mesmo_citando_b3():
    triagem = pontuar(
        resultado("Vitamina B3: para que serve", imagem="https://nutries.com.br/vitamina-b3-2.jpeg"), planejar("B3")
    )
    assert triagem.decisao == "descartar" and "vitamina" in triagem.motivo


def test_titulo_fala_do_assunto_mas_o_arquivo_nao_fica_em_duvida():
    triagem = pontuar(
        resultado("Selic: entenda como funciona a taxa de juros", imagem="https://x.com/uploads/IMG-1234.png"),
        planejar("taxa Selic"),
    )
    assert triagem.decisao == "duvida" and 1 <= triagem.pontos < PONTOS_PARA_APROVAR


def test_resultado_sem_relacao_nenhuma_tem_zero_pontos():
    triagem = pontuar(resultado("Tintas esmalte 18 litros", imagem="https://x.com/tinta.jpg"), planejar("Petrobras"))
    assert (triagem.decisao, triagem.pontos) == ("duvida", 0)


def test_dominio_oficial_soma_ponto():
    sem = pontuar(resultado("Sede em Brasília", pagina="https://blog.com/x", imagem="https://blog.com/bcb.jpg"), planejar("Banco Central"))
    com = pontuar(
        resultado("Sede em Brasília", pagina="https://www.bcb.gov.br/x", imagem="https://www.bcb.gov.br/bcb.jpg"),
        planejar("Banco Central"),
    )
    assert com.pontos == sem.pontos + 1 + 1  # domínio vale um ponto e a página do bcb.gov.br cita o assunto


def test_plural_e_acento_nao_atrapalham():
    triagem = pontuar(
        resultado("Fundos imobiliários: guia", imagem="https://x.com/fundos-imobiliarios.jpg"), planejar("FIIs")
    )
    assert triagem.pontos >= 5 and triagem.decisao == "aprovar"


def test_termos_do_exigir_usam_a_mesma_normalizacao_do_resto_do_pacote():
    assert planejar("Selic").exigir[0] == tuple(termos("selic"))


@pytest.mark.parametrize(
    ("assunto", "titulo", "arquivo"),
    [
        ("XP Investimentos", "Descargar Windows XP Update", "https://x.com/windows-xp.png"),
        ("ações", "Bolsa Neverfull, bolsa tote feminina | Louis Vuitton", "https://x.com/bolsa.png"),
        ("Banco Inter", "Inter vence o Grêmio e lidera", "https://x.com/inter.png"),
        ("porto exportação", "Porto: guia da cidade, Portugal", "https://x.com/porto.png"),
    ],
)
def test_homonimos_da_vida_real_nao_sao_aprovados(assunto, titulo, arquivo):
    avaliacao = pontuar(resultado(titulo, imagem=arquivo), planejar(assunto))
    assert avaliacao.decisao != "aprovar", avaliacao


def test_cita_assunto_olha_tags_e_titulo_com_a_mesma_normalizacao():
    from suno.imagens.consulta import cita_assunto

    assert cita_assunto("banco central bcb Sede do Banco Central", planejar("Banco Central"))
    assert not cita_assunto("caixa economica federal", planejar("Federal Reserve"))
    assert cita_assunto("qualquer coisa", planejar("Faria Lima")) is False  # genérico também confere o nome


def test_conceito_citado_so_no_titulo_vai_ao_juiz_mas_empresa_nao():
    titulo = "Apesar de queda com alívio nas tensões entre EUA e China, bolsa sobe"
    china = pontuar(resultado(titulo, pagina="https://www.infomoney.com.br/china-eua", imagem="https://x.com/uploads/ouro.jpg"), planejar("China"))
    assert china.pontos >= PONTOS_PARA_APROVAR and china.decisao == "duvida" and "juiz" in china.motivo
    itau = pontuar(
        resultado("Itaú (ITUB4): banco revê projeções", pagina="https://www.infomoney.com.br/itau-resultado", imagem="https://x.com/IMG-1.jpg"),
        planejar("Itaú"),
    )
    assert itau.decisao == "aprovar"


def test_conceito_com_o_nome_no_arquivo_e_aprovado_direto():
    avaliacao = pontuar(
        resultado("Taxa Selic: entenda", imagem="https://x.com/uploads/taxa-selic-grafico.png"), planejar("taxa Selic")
    )
    assert avaliacao.decisao == "aprovar"
