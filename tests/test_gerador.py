"""O Gerador: extração que copia o número, moldes que só deixam o número entrar por chave,
e as nove Células rodando ao mesmo tempo.

ADR 0010, 0011.
"""

from __future__ import annotations

import json
import time
from datetime import date

import pytest

from suno.avaliador import avaliar
from suno.dominio import (
    MATRIZ,
    AncoraNumerica,
    Ancoras,
    Ata,
    Audiencia,
    BlocoFala,
    Conteudo,
    Destino,
    ErroProvedor,
    Formato,
    Laudo,
    Medida,
    Metrica,
    PedidoLLM,
    RespostaLLM,
    Slide,
    Unidade,
)
from suno.gerador.extracao import (
    ROTULO_DO_PEDIDO,
    RotulagemDaAta,
    extrair_ancoras,
    por_regra_fixa,
)
from suno.gerador.matriz import gerar_matriz
from suno.gerador.moldes import (
    ALVO_FLESCH_BR,
    RespostaCarrossel,
    RespostaRoteiro,
    RespostaTextoAnalitico,
    montar_conteudo,
    montar_pedido,
    preencher,
)
from suno.ingestao.numeros import extrair_numeros
from suno.provedores.falso import ProvedorFalso

TEXTO_DA_ATA = """Data: 4 e 5 de agosto de 2026

280ª Reunião do Copom

17. O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a., e entende que essa
decisão é compatível com a estratégia de convergência da inflação.

19. Votaram por essa decisão os seguintes membros do Comitê: Gabriel Muricca Galípolo
(presidente), Ailton de Aquino Santos, Gilneu Francisco Astolfi Vivan, Izabela Moreira
Correa, Nilton José Schneider David, Paulo Picchetti, e Rodrigo Alves Teixeira.

20. As projeções do cenário de referência são de 5,1% para o ano corrente e 3,8% para o
ano seguinte.
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


def _indice_do_literal(texto: str, literal: str, unidade: Unidade) -> int:
    candidatos = extrair_numeros(texto, ano_padrao=2026)
    for indice, candidato in enumerate(candidatos):
        if candidato.literal == literal and candidato.unidade is unidade:
            return indice
    raise AssertionError(f"candidato {literal!r} ({unidade}) não existe no texto")


def _provedor_de_extracao(rotulagem: dict) -> ProvedorFalso:
    return ProvedorFalso({ROTULO_DO_PEDIDO: [json.dumps(rotulagem, ensure_ascii=False)]})


@pytest.fixture
def ancoras_de_teste() -> Ancoras:
    return Ancoras(
        ata="copom-teste",
        numericas=[
            AncoraNumerica(
                chave="selic_decidida",
                rotulo="Selic decidida",
                valor_literal="14,00",
                valor=14.0,
                unidade=Unidade.PERCENTUAL_AO_ANO,
                trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
            ),
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


# ---------------------------------------------------------------------------
# Extração: o valor vem do candidato, nunca do que o LLM escreveu
# ---------------------------------------------------------------------------


def test_regra_fixa_acha_as_quatro_chaves_que_uma_ata_do_copom_sempre_tem(ata: Ata):
    achadas = {a.chave: a for a in por_regra_fixa(ata, extrair_numeros(ata.texto, ano_padrao=2026))}
    assert set(achadas) == {"selic_decidida", "placar_votacao", "data_reuniao", "numero_reuniao"}
    assert achadas["selic_decidida"].valor_literal == "14,00"
    assert achadas["selic_decidida"].unidade is Unidade.PERCENTUAL_AO_ANO
    assert achadas["placar_votacao"].valor_literal == "7 a 0"  # sete nomes contados, zero contra
    assert achadas["data_reuniao"].data_iso == date(2026, 8, 5)
    assert achadas["numero_reuniao"].valor == 280


def test_valor_da_ancora_vem_do_candidato_mesmo_quando_o_llm_escreve_outro_numero(ata: Ata):
    """ADR 0011: o LLM aponta o índice; quem manda no número é o extrator."""
    indice = _indice_do_literal(ata.texto, "14,00", Unidade.PERCENTUAL_AO_ANO)
    provedor = _provedor_de_extracao(
        {
            "chaves": [{"chave": "selic_anterior", "indice": indice, "valor_lido": "99,99% a.a."}],
            "afirmacoes": [],
        }
    )
    ancoras = extrair_ancoras(ata, provedor)
    anterior = ancoras.numerica("selic_anterior")
    assert anterior is not None
    assert anterior.valor_literal == "14,00"
    assert anterior.valor == pytest.approx(14.0)
    assert "99,99" not in anterior.valor_literal
    assert "14,00% a.a." in anterior.trecho


def test_indice_invalido_e_ignorado_sem_derrubar_a_extracao(ata: Ata):
    provedor = _provedor_de_extracao(
        {
            "chaves": [
                {"chave": "selic_anterior", "indice": 9999},
                {"chave": "alvo_inflacao", "indice": -3},
            ],
            "afirmacoes": [],
        }
    )
    ancoras = extrair_ancoras(ata, provedor)
    assert ancoras.numerica("selic_anterior") is None
    assert ancoras.numerica("alvo_inflacao") is None
    assert ancoras.chaves_faltantes() == frozenset()  # a regra fixa deu conta das essenciais


def test_regra_fixa_ganha_do_llm_na_mesma_chave(ata: Ata):
    indice_de_5_1 = _indice_do_literal(ata.texto, "5,1", Unidade.PERCENTUAL)
    provedor = _provedor_de_extracao(
        {
            "chaves": [{"chave": "selic_decidida", "indice": indice_de_5_1}],
            "afirmacoes": [],
        }
    )
    selic = extrair_ancoras(ata, provedor).numerica("selic_decidida")
    assert selic is not None and selic.valor_literal == "14,00"


def test_ancora_textual_com_trecho_que_nao_esta_na_ata_e_descartada(ata: Ata):
    provedor = _provedor_de_extracao(
        {
            "chaves": [],
            "afirmacoes": [
                {
                    "identificador": "decisao",
                    "afirmacao": "O Copom reduziu a taxa básica de juros.",
                    "trecho": "O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
                },
                {
                    "identificador": "inventada",
                    "afirmacao": "O Copom prometeu novos cortes.",
                    "trecho": "O Copom prometeu novos cortes na próxima reunião.",
                },
            ],
        }
    )
    ancoras = extrair_ancoras(ata, provedor)
    assert [t.identificador for t in ancoras.textuais] == ["decisao"]


def test_trecho_com_quebra_de_linha_da_ata_ainda_casa(ata: Ata):
    """A Ata vem do PDF com a frase partida; o conferidor normaliza espaço antes de olhar."""
    provedor = _provedor_de_extracao(
        {
            "chaves": [],
            "afirmacoes": [
                {
                    "identificador": "decisao",
                    "afirmacao": "A decisão é compatível com a convergência.",
                    "trecho": "essa decisão é compatível com a estratégia de convergência",
                }
            ],
        }
    )
    assert len(extrair_ancoras(ata, provedor).textuais) == 1


def test_provedor_que_falha_deixa_a_extracao_so_com_a_regra_fixa(ata: Ata):
    provedor = ProvedorFalso({ROTULO_DO_PEDIDO: [ErroProvedor("falso", "sem cota")]})
    ancoras = extrair_ancoras(ata, provedor)
    assert {a.chave for a in ancoras.numericas} == {
        "selic_decidida",
        "placar_votacao",
        "data_reuniao",
        "numero_reuniao",
    }
    assert ancoras.textuais == []
    assert ancoras.chaves_faltantes() == frozenset()


def test_ata_sem_a_decisao_deixa_chave_essencial_faltando(ata: Ata):
    """Ata fora do padrão degrada em silêncio — e é a integridade que grita (ADR 0013)."""
    truncada = ata.model_copy(update={"texto": "Data: 4 e 5 de agosto de 2026\n\n280ª Reunião"})
    provedor = _provedor_de_extracao({"chaves": [], "afirmacoes": []})
    ancoras = extrair_ancoras(truncada, provedor)
    assert "selic_decidida" in ancoras.chaves_faltantes()
    assert "placar_votacao" in ancoras.chaves_faltantes()


def test_rotulagem_valida_no_modelo_pydantic_do_estagio():
    modelo = RotulagemDaAta.model_validate(
        {"chaves": [{"chave": "alvo_inflacao", "indice": 2}], "afirmacoes": []}
    )
    assert modelo.chaves[0].valor_lido is None


# ---------------------------------------------------------------------------
# Moldes: o número entra por preenchimento
# ---------------------------------------------------------------------------


def test_preencher_troca_a_chave_pela_citacao_e_reporta_a_chave(ancoras_de_teste: Ancoras):
    texto, chaves = preencher("A taxa foi a {{selic_decidida}} hoje.", ancoras_de_teste)
    assert texto == "A taxa foi a 14,00% a.a. hoje."
    assert chaves == ["selic_decidida"]


def test_preencher_conta_a_chave_uma_vez_so(ancoras_de_teste: Ancoras):
    texto, chaves = preencher("{{placar_votacao}} e de novo {{placar_votacao}}", ancoras_de_teste)
    assert texto == "7 a 0 e de novo 7 a 0"
    assert chaves == ["placar_votacao"]


def test_citacao_em_fim_de_frase_nao_dobra_o_ponto(ancoras_de_teste: Ancoras):
    """``a.a.`` já traz o ponto; o que sai é o ponto final do LLM, nunca um dígito."""
    texto, chaves = preencher("A taxa foi a {{selic_decidida}}.", ancoras_de_teste)
    assert texto == "A taxa foi a 14,00% a.a."
    assert chaves == ["selic_decidida"]


def test_o_ponto_some_mas_o_numero_fica_inteiro(ancoras_de_teste: Ancoras):
    texto, _ = preencher("Subiu para {{selic_decidida}}. E parou.", ancoras_de_teste)
    assert "14,00" in texto
    assert texto == "Subiu para 14,00% a.a. E parou."


def test_reticencias_e_ponto_comum_ficam_como_estao(ancoras_de_teste: Ancoras):
    texto, _ = preencher("O placar foi {{placar_votacao}}... e pronto.", ancoras_de_teste)
    assert texto == "O placar foi 7 a 0... e pronto."


def test_chave_desconhecida_perde_o_marcador_e_nao_vira_numero(ancoras_de_teste: Ancoras):
    texto, chaves = preencher("A Selic ficou em {{taxa_inventada}}.", ancoras_de_teste)
    assert texto == "A Selic ficou em ."
    assert chaves == []


def test_montar_conteudo_preenche_titulo_corpo_e_fala(ancoras_de_teste: Ancoras):
    carrossel = RespostaCarrossel(
        slides=[
            Slide(titulo=f"Slide {i}", corpo="A taxa foi a {{selic_decidida}}.", dado=None)
            for i in range(5)
        ]
    )
    conteudo = montar_conteudo(carrossel, Formato.CARROSSEL, ancoras_de_teste)
    assert conteudo.slides is not None
    assert all("14,00% a.a." in slide.corpo for slide in conteudo.slides)
    assert conteudo.ancoras_citadas == ["selic_decidida"]


def test_montar_conteudo_nao_preenche_a_rubrica_de_cena(ancoras_de_teste: Ancoras):
    """``tela`` não é falado e não é medido: o molde fica lá como rubrica."""
    roteiro = RespostaRoteiro(
        blocos=[
            BlocoFala(inicio_s=0, fim_s=5, fala="Foi a {{selic_decidida}}.", tela="{{selic_decidida}}"),
            BlocoFala(inicio_s=5, fim_s=10, fala="Fim.", tela=""),
        ]
    )
    conteudo = montar_conteudo(roteiro, Formato.ROTEIRO, ancoras_de_teste)
    assert conteudo.blocos is not None
    assert conteudo.blocos[0].fala == "Foi a 14,00% a.a."
    assert conteudo.blocos[0].tela == "{{selic_decidida}}"


def test_montar_conteudo_do_texto_analitico_monta_as_tres_partes(ancoras_de_teste: Ancoras):
    resposta = RespostaTextoAnalitico(
        titulo="Selic em {{selic_decidida}}",
        o_que_foi_decidido="Caiu para {{selic_decidida}}.",
        por_que="Porque sim.",
        o_que_observar_adiante="Placar de {{placar_votacao}}.",
    )
    conteudo = montar_conteudo(resposta, Formato.TEXTO_ANALITICO, ancoras_de_teste)
    assert conteudo.texto is not None
    assert "## O que foi decidido" in conteudo.texto
    assert "## Por quê" in conteudo.texto
    assert "## O que observar adiante" in conteudo.texto
    assert "{{" not in conteudo.texto
    assert conteudo.ancoras_citadas == ["selic_decidida", "placar_votacao"]


def test_a_instrucao_de_nunca_escrever_numero_esta_no_pedido(ancoras_de_teste: Ancoras):
    """O LLM recebe a Ata inteira, com todos os números dela: o que segura é a instrução."""
    pedido = montar_pedido("texto da Ata", ancoras_de_teste, Audiencia.INICIANTE, Formato.CARROSSEL)
    sistema = next(m.texto for m in pedido.mensagens if m.autor == "sistema")
    usuario = next(m.texto for m in pedido.mensagens if m.autor == "usuario")
    assert "escrevendo `{{chave}}`" in sistema
    assert "escrevendo `{{chave}}`" in usuario
    assert "{{selic_decidida}}: Selic decidida (% a.a.)" in usuario
    assert "{{placar_votacao}}: Placar da votação (votos)" in usuario


def test_rotulo_do_pedido_identifica_audiencia_formato_e_rodada(ancoras_de_teste: Ancoras):
    pedido = montar_pedido(
        "Ata", ancoras_de_teste, Audiencia.INTERMEDIARIO, Formato.ROTEIRO, rodada=2
    )
    assert pedido.rotulo == "celula:intermediario:roteiro:2"


def test_a_linha_que_nao_se_cruza_esta_em_toda_mensagem_de_sistema(ancoras_de_teste: Ancoras):
    for audiencia, formato in MATRIZ:
        pedido = montar_pedido("Ata", ancoras_de_teste, audiencia, formato)
        sistema = next(m.texto for m in pedido.mensagens if m.autor == "sistema")
        assert "Nunca sugira comprar, vender" in sistema


def test_rodada_de_correcao_carrega_o_valor_medido_e_nao_instrucao_generica(
    ancoras_de_teste: Ancoras,
):
    dificil = Conteudo(
        formato=Formato.TEXTO_ANALITICO,
        texto=(
            "O Comitê avalia que as evidências de transmissão da política monetária "
            "contracionista para a atividade econômica têm se acumulado gradualmente, ainda "
            "que a inflação permaneça pressionada pela demanda agregada, configuração que "
            "exige a preservação do caráter restritivo enquanto o hiato do produto seguir "
            "em terreno desfavorável e o balanço de riscos permanecer assimétrico."
        ),
    )
    laudo = avaliar(dificil, ancoras_de_teste.todas(), Audiencia.INICIANTE)
    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL

    pedido = montar_pedido(
        "Ata",
        ancoras_de_teste,
        Audiencia.INICIANTE,
        Formato.TEXTO_ANALITICO,
        rodada=1,
        correcoes=list(laudo.correcoes),
    )
    usuario = next(m.texto for m in pedido.mensagens if m.autor == "usuario")
    assert "O que precisa mudar" in usuario
    assert "Flesch-BR medido" in usuario


def test_rodada_zero_nao_carrega_bloco_de_correcao(ancoras_de_teste: Ancoras):
    pedido = montar_pedido("Ata", ancoras_de_teste, Audiencia.AVANCADO, Formato.CARROSSEL)
    usuario = next(m.texto for m in pedido.mensagens if m.autor == "usuario")
    assert "O que precisa mudar" not in usuario


def test_alvo_interno_e_mais_folgado_que_o_limiar_publicado():
    """Overshoot do ADR 0002: o Gerador pede mais do que o Laudo cobra."""
    from suno.dominio import LIMIARES_PROVISORIOS

    assert ALVO_FLESCH_BR[Audiencia.INICIANTE].minimo > LIMIARES_PROVISORIOS[
        Audiencia.INICIANTE
    ].flesch_br.minimo
    assert ALVO_FLESCH_BR[Audiencia.AVANCADO].maximo < LIMIARES_PROVISORIOS[
        Audiencia.AVANCADO
    ].flesch_br.maximo
    interno = ALVO_FLESCH_BR[Audiencia.INTERMEDIARIO]
    publicado = LIMIARES_PROVISORIOS[Audiencia.INTERMEDIARIO].flesch_br
    assert interno.minimo > publicado.minimo and interno.maximo < publicado.maximo


# ---------------------------------------------------------------------------
# A Matriz roda em paralelo
# ---------------------------------------------------------------------------

LATENCIA_SIMULADA_S = 0.2
"""Perto do que uma chamada real custa, pequeno o bastante para não travar a suíte."""


class ProvedorLento(ProvedorFalso):
    """Um LLM falso que demora. É o único jeito de ver paralelismo num teste."""

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        time.sleep(LATENCIA_SIMULADA_S)
        return super().completar(pedido)


def _laudo_aprovado(conteudo, ancoras, audiencia, *, limiares=None, comite=None) -> Laudo:
    return Laudo(
        audiencia=audiencia,
        formato=conteudo.formato,
        medidas=[Medida(metrica=Metrica.FLESCH_BR, valor=60.0, atingiu=True)],
        destino=Destino.APROVADO,
    )


def test_as_nove_celulas_rodam_ao_mesmo_tempo(ata: Ata, ancoras_de_teste: Ancoras, monkeypatch):
    """Em sequência seriam nove esperas; o teste só passa se elas se sobrepuserem."""
    monkeypatch.setattr("suno.gerador.ciclo.avaliar", _laudo_aprovado)
    resposta = json.dumps(
        {"slides": [{"titulo": "t", "corpo": "c"} for _ in range(5)]}, ensure_ascii=False
    )
    texto = json.dumps(
        {"titulo": "t", "o_que_foi_decidido": "a", "por_que": "b", "o_que_observar_adiante": "c"}
    )
    roteiro = json.dumps(
        {"blocos": [{"inicio_s": 0, "fim_s": 5, "fala": "a"}, {"inicio_s": 5, "fim_s": 9, "fala": "b"}]}
    )
    filas: dict[str, list[str]] = {}
    for audiencia, formato in MATRIZ:
        pronta = {Formato.CARROSSEL: resposta, Formato.TEXTO_ANALITICO: texto}.get(formato, roteiro)
        filas[f"celula:{audiencia}:{formato}:0"] = [pronta]
    provedor = ProvedorLento(filas)

    comeco = time.perf_counter()
    historicos = gerar_matriz(ata, ancoras_de_teste, provedor)
    decorrido = time.perf_counter() - comeco

    assert len(historicos) == len(MATRIZ)
    assert decorrido < 1.0, f"nove chamadas de {LATENCIA_SIMULADA_S}s levaram {decorrido:.2f}s"


def test_a_matriz_sai_na_ordem_de_matriz(ata: Ata, ancoras_de_teste: Ancoras, monkeypatch):
    monkeypatch.setattr("suno.gerador.ciclo.avaliar", _laudo_aprovado)
    texto = json.dumps(
        {"titulo": "t", "o_que_foi_decidido": "a", "por_que": "b", "o_que_observar_adiante": "c"}
    )
    carrossel = json.dumps({"slides": [{"titulo": "t", "corpo": "c"} for _ in range(5)]})
    roteiro = json.dumps(
        {"blocos": [{"inicio_s": 0, "fim_s": 5, "fala": "a"}, {"inicio_s": 5, "fim_s": 9, "fala": "b"}]}
    )
    filas = {
        f"celula:{audiencia}:{formato}:0": [
            {Formato.TEXTO_ANALITICO: texto, Formato.CARROSSEL: carrossel}.get(formato, roteiro)
        ]
        for audiencia, formato in MATRIZ
    }
    historicos = gerar_matriz(ata, ancoras_de_teste, ProvedorFalso(filas))
    assert [(h.audiencia, h.formato) for h in historicos] == list(MATRIZ)
