"""A correção que raciocina e edita o mínimo: a frase exata de cada termo, o campo `raciocinio` primeiro
e a instrução de mudança mínima. Medido em Células reais: o Ciclo cego deixava 15 de 19 no mesmo problema
nas três rodadas (ADR 0013).
"""

from __future__ import annotations

import json
from datetime import date

from suno.avaliador import avaliar
from suno.avaliador.densidade import frase_em
from suno.dominio import (
    AncoraNumerica,
    Ancoras,
    Ata,
    Audiencia,
    BlocoFala,
    ChaveAncora,
    Conteudo,
    Correcao,
    Destino,
    Formato,
    Metrica,
    Slide,
    Unidade,
)
from suno.gerador.ciclo import rodar_ciclo
from suno.gerador.moldes import (
    RespostaCarrossel,
    RespostaRoteiro,
    RespostaTextoAnalitico,
    _bloco_de_correcoes,
)
from suno.provedores.falso import ProvedorFalso


def _ancoras() -> list[AncoraNumerica]:
    return [
        AncoraNumerica(
            chave=ChaveAncora.SELIC_DECIDIDA,
            rotulo="Selic decidida",
            valor_literal="14,00",
            valor=14.0,
            unidade=Unidade.PERCENTUAL_AO_ANO,
            trecho="O Copom decidiu manter a taxa Selic em 14,00% a.a.",
        ),
        AncoraNumerica(
            chave=ChaveAncora.PLACAR_VOTACAO,
            rotulo="Placar da votação",
            valor_literal="7 a 0",
            valor=None,
            unidade=Unidade.VOTOS,
            trecho="A decisão foi tomada por 7 votos a 0.",
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
    ]


def _instrucao_de_densidade(conteudo: Conteudo, audiencia: Audiencia) -> str:
    laudo = avaliar(conteudo, _ancoras(), audiencia)
    return next(c.instrucao for c in laudo.correcoes if c.metrica is Metrica.DENSIDADE)


# --- 1. a frase exata de cada termo --------------------------------------------------------


def test_frase_em_devolve_so_a_frase_do_termo_sem_quebrar_em_abreviacao() -> None:
    texto = "Primeira frase aqui. A Selic ficou em 14,00% a.a. e o hiato do produto segue positivo. Última frase."
    posicao = texto.index("hiato")

    assert frase_em(texto, posicao) == "A Selic ficou em 14,00% a.a. e o hiato do produto segue positivo."


def test_frase_em_tira_o_marcador_de_titulo_e_corta_a_frase_longa() -> None:
    assert frase_em("# O hiato do produto\n\nTexto.", 4) == "O hiato do produto"
    longa = "hiato " + "palavra " * 60
    assert frase_em(longa, 0).endswith("…") and len(frase_em(longa, 0)) <= 220


def test_texto_analitico_traz_a_frase_do_termo_na_correcao() -> None:
    conteudo = Conteudo(
        formato=Formato.TEXTO_ANALITICO,
        texto="A Selic (a taxa básica de juros) não mudou.\n\nO hiato do produto segue positivo neste trimestre.",
    )

    instrucao = _instrucao_de_densidade(conteudo, Audiencia.INTERMEDIARIO)

    assert "Onde cada um está:" in instrucao
    assert "- hiato do produto — «O hiato do produto segue positivo neste trimestre.»" in instrucao


def test_carrossel_diz_em_que_slide_esta_o_termo() -> None:
    conteudo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[
            Slide(tipo="hook", titulo="A Selic parou", corpo="Ela ficou em 14,00% a.a. e o mercado reagiu."),
            Slide(tipo="ponto", titulo="O que mudou", corpo="O hiato do produto segue positivo neste trimestre."),
            Slide(tipo="ponto", titulo="E agora", corpo="O Comitê acompanha a inflação de perto."),
            Slide(tipo="ponto", titulo="Por quê", corpo="Os preços sobem menos do que antes."),
            Slide(tipo="cta", titulo="Leia a Ata", corpo="O texto completo está no site do Banco Central."),
        ],
    )

    instrucao = _instrucao_de_densidade(conteudo, Audiencia.INTERMEDIARIO)

    assert "- hiato do produto — slide 2: «" in instrucao


def test_roteiro_diz_em_que_bloco_esta_o_termo() -> None:
    conteudo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[
            BlocoFala(inicio_s=0, fim_s=10, fala="A Selic ficou em 14,00% a.a. hoje.", tela="Selic"),
            BlocoFala(inicio_s=10, fim_s=30, fala="O hiato do produto segue positivo neste trimestre.", tela="Hiato"),
        ],
    )

    instrucao = _instrucao_de_densidade(conteudo, Audiencia.INTERMEDIARIO)

    assert "- hiato do produto — bloco 2: «" in instrucao


# --- 2 e 3. raciocinar primeiro, mudar o mínimo --------------------------------------------


def test_o_campo_raciocinio_vem_primeiro_em_cada_resposta_e_e_opcional() -> None:
    for modelo in (RespostaTextoAnalitico, RespostaCarrossel, RespostaRoteiro):
        esquema = modelo.model_json_schema()
        assert list(esquema["properties"])[0] == "raciocinio"
        assert "raciocinio" not in esquema.get("required", [])

    sem_o_campo = RespostaTextoAnalitico(
        titulo="t", o_que_foi_decidido="a", por_que="b", o_que_observar_adiante="c"
    )
    assert sem_o_campo.raciocinio == ""


def test_a_correcao_manda_raciocinar_e_mudar_so_as_frases_listadas() -> None:
    correcao = Correcao(
        metrica=Metrica.DENSIDADE,
        valor_medido=0.05,
        faixa=None,
        instrucao="Termos do Léxico sem explicação na primeira ocorrência: hiato do produto.",
    )

    bloco = _bloco_de_correcoes([correcao], "O texto da rodada anterior.")

    assert "preencha `raciocinio`" in bloco
    assert "mudança MÍNIMA" in bloco
    assert "copie todas as outras idênticas, palavra por palavra" in bloco
    assert "O texto da rodada anterior." in bloco  # o rascunho continua indo


# --- 4. o Ciclo aceita a resposta com raciocinio e não gasta chamada a mais ------------------

TEXTO_DA_ATA = """Data: 4 e 5 de agosto de 2026

280ª Reunião do Copom

O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.
"""

DIFICIL = {
    "titulo": "Decisão de política monetária e balanço de riscos",
    "o_que_foi_decidido": (
        "Na reunião referida, o colegiado deliberou pela redução da taxa básica de juros para "
        "{{selic_decidida}}, entendendo a decisão compatível com a estratégia de convergência da "
        "inflação para o redor da meta ao longo do horizonte relevante de política monetária."
    ),
    "por_que": (
        "O diagnóstico combina acumulação gradual das evidências de transmissão da política "
        "monetária contracionista à atividade econômica com persistência da pressão de demanda "
        "sobre a inflação corrente, configuração que sustenta a manutenção de caráter restritivo "
        "enquanto o hiato do produto permanecer em terreno desfavorável e o balanço de riscos "
        "seguir assimétrico."
    ),
    "o_que_observar_adiante": (
        "A magnitude do ciclo de calibração permanece condicionada à evolução observada da "
        "desinflação, dos efeitos de segunda ordem dos choques de oferta e da reancoragem das "
        "expectativas apuradas pela pesquisa Focus, elementos que o colegiado declara acompanhar."
    ),
}
FACIL = {
    "raciocinio": "Flesch alto demais para o Avançado? Não: o texto da rodada 0 estava difícil demais. Troquei.",
    "titulo": "O custo do dinheiro caiu",
    "o_que_foi_decidido": (
        "O grupo se reuniu em {{data_reuniao}}. A taxa caiu para {{selic_decidida}} ao ano. "
        "O placar foi de {{placar_votacao}}."
    ),
    "por_que": (
        "Os preços já sobem menos do que subiam. E o comércio está mais fraco. "
        "Foi por isso que a taxa pôde cair."
    ),
    "o_que_observar_adiante": (
        "O grupo não disse qual será o próximo passo. Quem tem dívida paga um pouco menos. "
        "Quem guarda dinheiro ganha um pouco menos."
    ),
}


def test_o_ciclo_aceita_a_resposta_com_raciocinio_e_corrige_na_rodada_um() -> None:
    ata = Ata(
        identificador="copom-teste",
        titulo="280ª Reunião",
        reuniao=280,
        data_referencia=date(2026, 8, 5),
        texto=TEXTO_DA_ATA,
    )
    ancoras = Ancoras(ata="copom-teste", numericas=_ancoras())
    rotulo = "celula:iniciante:texto_analitico:{rodada}"
    provedor = ProvedorFalso(
        {
            rotulo.format(rodada=0): [json.dumps(DIFICIL, ensure_ascii=False)],
            rotulo.format(rodada=1): [json.dumps(FACIL, ensure_ascii=False)],
        }
    )

    historico = rodar_ciclo(ata, ancoras, Audiencia.INICIANTE, Formato.TEXTO_ANALITICO, provedor)

    assert [t.laudo.destino for t in historico.tentativas] == [Destino.REPROVADO_CORRIGIVEL, Destino.APROVADO]
    assert len(provedor.pedidos) == 2  # o mesmo número de chamadas de antes: uma por rodada
    correcao = provedor.pedidos[1].mensagens[-1].texto
    assert "preencha `raciocinio`" in correcao
    assert "Onde cada um está:" in correcao  # a frase exata de cada termo chega ao Gerador
