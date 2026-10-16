"""A Qualidade do Jev: nota por dimensão, Limiar, Correção e o que acontece quando o Jev falha.

ADR 0035. Nenhum teste toca a rede: o transporte HTTP é simulado (a trava de rede da suíte
continuaria bloqueando qualquer saída de verdade).
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from suno.avaliador import avaliar
from suno.avaliador.qualidade import (
    DIMENSOES,
    AvaliadorDeQualidade,
    ClienteJev,
)
from suno.dominio import (
    LIMIAR_DE_QUALIDADE,
    AncoraNumerica,
    Ancoras,
    AncoraTextual,
    Ata,
    Audiencia,
    ChaveAncora,
    Conteudo,
    Destino,
    ErroProvedor,
    Formato,
    Metrica,
    MotivoReprovacao,
    Unidade,
)
from suno.gerador.ciclo import rodar_ciclo
from suno.provedores.falso import ProvedorFalso

URL = "https://jev.exemplo.test/v1/systemone"

TEXTO_FACIL = (
    "A Selic (a taxa básica de juros do país) não mudou. "
    "Ela agora é de 14,00% a.a.\n\n"
    "O Banco Central: é a casa que cuida do valor do dinheiro. "
    "A mudança chega devagar até a conta da sua casa."
)
TEXTO_QUE_REPROVA_NO_DETERMINISTICO = (
    "O hiato do produto segue positivo neste trimestre. A decisão saiu sem novidade."
)


def _ancoras() -> list[AncoraNumerica | AncoraTextual]:
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


def _conteudo(texto: str = TEXTO_FACIL) -> Conteudo:
    return Conteudo(formato=Formato.TEXTO_ANALITICO, texto=texto)


def _resposta(notas: dict[str, float]) -> dict:
    """O corpo que o Jev devolve: ``score`` de 0 a 3 por pergunta (quatro níveis)."""
    return {
        "model": "jev-1.13.0",
        "answers": {
            chave: {"type": "score", "score": nota, "confidence": 0.9} for chave, nota in notas.items()
        },
        "usage": {"input_tokens": 300, "output_tokens": 19},
    }


NOTAS_BOAS = {d.chave: 3.0 for d in DIMENSOES}
NOTAS_COM_DESENVOLVIMENTO_FRACO = {**NOTAS_BOAS, "desenvolvimento": 1.0}


class Jev:
    """Um Jev simulado: devolve as respostas em fila e guarda o que recebeu."""

    def __init__(self, *respostas: httpx.Response | dict) -> None:
        self.respostas = list(respostas)
        self.pedidos: list[httpx.Request] = []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        proxima = self.respostas.pop(0) if len(self.respostas) > 1 else self.respostas[0]
        return proxima if isinstance(proxima, httpx.Response) else httpx.Response(200, json=proxima)


def _avaliador(jev: Jev, limiar: float = LIMIAR_DE_QUALIDADE) -> AvaliadorDeQualidade:
    http = httpx.Client(transport=httpx.MockTransport(jev))
    return AvaliadorDeQualidade(
        ClienteJev(URL, "chave-de-teste", cliente=http, dormir=lambda _s: None), limiar=limiar
    )


# ---------------------------------------------------------------------------
# O pedido ao Jev
# ---------------------------------------------------------------------------


def test_o_pedido_leva_uma_pergunta_score_por_dimensao_e_a_chave_no_cabecalho() -> None:
    jev = Jev(_resposta(NOTAS_BOAS))
    _avaliador(jev).medir(_conteudo(), Audiencia.INICIANTE)

    (pedido,) = jev.pedidos
    corpo = json.loads(pedido.content)
    assert str(pedido.url) == URL
    assert pedido.headers["Authorization"] == "Bearer chave-de-teste"
    assert corpo["model"] == "jev-latest"
    assert set(corpo["questions"]) == {"desenvolvimento", "completude", "clareza", "tom"}
    for pergunta in corpo["questions"].values():
        assert pergunta["type"] == "score"
        assert len(pergunta["criteria"]) == 4  # do pior ao melhor


def test_o_pedido_diz_a_audiencia_e_o_formato_mas_nunca_quem_gerou() -> None:
    jev = Jev(_resposta(NOTAS_BOAS))
    _avaliador(jev).medir(_conteudo(), Audiencia.AVANCADO)

    estado = json.loads(jev.pedidos[0].content)["state"]
    assert "Avançado" in estado["audiencia"]
    assert estado["formato"] == "texto analítico"
    assert estado["conteudo"] == TEXTO_FACIL
    texto = json.dumps(estado).lower()
    for nome in ("gemini", "groq", "sambanova"):
        assert nome not in texto


def test_a_nota_vai_de_0_a_1_pela_escala_de_quatro_niveis() -> None:
    jev = Jev(_resposta({"desenvolvimento": 1.5, "completude": 3.0, "clareza": 0.0, "tom": 2.0}))
    resultado = _avaliador(jev).medir(_conteudo(), Audiencia.INICIANTE)

    notas = {d.chave: d.nota for d in resultado.dimensoes}
    assert notas == {"desenvolvimento": 0.5, "completude": 1.0, "clareza": 0.0, "tom": pytest.approx(2 / 3)}
    assert resultado.menor.chave == "clareza"


# ---------------------------------------------------------------------------
# No Laudo
# ---------------------------------------------------------------------------


def test_com_todas_as_dimensoes_acima_do_limiar_o_laudo_aprova_e_traz_a_qualidade() -> None:
    laudo = avaliar(
        _conteudo(), _ancoras(), Audiencia.INICIANTE, qualidade=_avaliador(Jev(_resposta(NOTAS_BOAS)))
    )

    assert laudo.destino is Destino.APROVADO
    medida = laudo.medida(Metrica.QUALIDADE)
    assert medida is not None and medida.atingiu is True and medida.valor == 1.0
    assert medida.faixa is not None and medida.faixa.minimo == LIMIAR_DE_QUALIDADE


def test_dimensao_abaixo_do_limiar_reprova_com_correcao_que_nomeia_a_dimensao() -> None:
    laudo = avaliar(
        _conteudo(),
        _ancoras(),
        Audiencia.INICIANTE,
        qualidade=_avaliador(Jev(_resposta(NOTAS_COM_DESENVOLVIMENTO_FRACO))),
    )

    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert laudo.motivos == [MotivoReprovacao.QUALIDADE]
    (correcao,) = laudo.correcoes
    assert correcao.metrica is Metrica.QUALIDADE
    assert correcao.valor_medido == pytest.approx(1 / 3)
    assert "desenvolvimento 33%" in correcao.instrucao
    assert "60%" in correcao.instrucao
    assert "clareza" not in correcao.instrucao  # só o que está abaixo


def test_o_limiar_pode_ser_trocado() -> None:
    jev = Jev(_resposta(NOTAS_COM_DESENVOLVIMENTO_FRACO))
    laudo = avaliar(
        _conteudo(), _ancoras(), Audiencia.INICIANTE, qualidade=_avaliador(jev, limiar=0.3)
    )

    assert laudo.destino is Destino.APROVADO  # 33% passa de 30%


def test_o_jev_nao_e_chamado_quando_o_determinístico_ja_reprovou() -> None:
    jev = Jev(_resposta(NOTAS_BOAS))
    laudo = avaliar(
        _conteudo(TEXTO_QUE_REPROVA_NO_DETERMINISTICO),
        _ancoras(),
        Audiencia.INICIANTE,
        qualidade=_avaliador(jev),
    )

    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert MotivoReprovacao.QUALIDADE not in laudo.motivos
    assert jev.pedidos == []
    assert laudo.medida(Metrica.QUALIDADE) is None


def test_sem_o_avaliador_o_laudo_continua_com_as_cinco_medidas() -> None:
    laudo = avaliar(_conteudo(), _ancoras(), Audiencia.INICIANTE)

    assert len(laudo.medidas) == 5
    assert laudo.medida(Metrica.QUALIDADE) is None


@pytest.mark.parametrize(
    "falha",
    [
        httpx.Response(500, text="erro interno"),
        httpx.Response(401, text="chave inválida"),
        httpx.Response(200, text="não é json"),
        httpx.Response(200, json={"answers": {"tom": {"type": "score", "score": 3}}}),  # faltam três
    ],
)
def test_falha_do_jev_nunca_reprova_o_laudo_sai_sem_qualidade(falha: httpx.Response) -> None:
    laudo = avaliar(_conteudo(), _ancoras(), Audiencia.INICIANTE, qualidade=_avaliador(Jev(falha)))

    assert laudo.destino is Destino.APROVADO
    assert laudo.medida(Metrica.QUALIDADE) is None


def test_429_espera_e_tenta_de_novo() -> None:
    esperas: list[float] = []
    jev = Jev(httpx.Response(429), httpx.Response(529), _resposta(NOTAS_BOAS))
    http = httpx.Client(transport=httpx.MockTransport(jev))
    cliente = ClienteJev(URL, "k", cliente=http, dormir=esperas.append)

    laudo = avaliar(
        _conteudo(), _ancoras(), Audiencia.INICIANTE, qualidade=AvaliadorDeQualidade(cliente)
    )

    assert laudo.destino is Destino.APROVADO
    assert len(jev.pedidos) == 3
    assert esperas == [1.0, 2.0]


def test_erro_de_rede_vira_erro_de_provedor_sem_vazar_a_chave() -> None:
    def cai(_pedido: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede")

    cliente = ClienteJev(
        URL, "chave-secreta", cliente=httpx.Client(transport=httpx.MockTransport(cai)), dormir=lambda _s: None
    )
    with pytest.raises(ErroProvedor) as erro:
        cliente.pontuar({"conteudo": "x"}, {})
    assert "chave-secreta" not in str(erro.value)


# ---------------------------------------------------------------------------
# Montagem pelo ambiente
# ---------------------------------------------------------------------------


@pytest.fixture
def sem_jev_no_ambiente(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for variavel in ("SUNO_JEV", "JEV_URL", "JEV_API_KEY", "TYPESAFE_API_KEY", "SUNO_JEV_LIMIAR"):
        monkeypatch.delenv(variavel, raising=False)
    return monkeypatch


def test_sem_chave_nao_monta_mesmo_ligado_por_padrao(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    assert AvaliadorDeQualidade.de_ambiente() is None


def test_o_jev_esta_sempre_ligado_basta_a_chave(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    sem_jev_no_ambiente.setenv("JEV_API_KEY", "k")  # sem SUNO_JEV no ambiente

    assert AvaliadorDeQualidade.de_ambiente() is not None


def test_so_suno_jev_0_ou_ligado_false_desligam_o_jev(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    sem_jev_no_ambiente.setenv("JEV_API_KEY", "k")

    sem_jev_no_ambiente.setenv("SUNO_JEV", "0")
    assert AvaliadorDeQualidade.de_ambiente() is None

    sem_jev_no_ambiente.setenv("SUNO_JEV", "qualquer coisa")
    assert AvaliadorDeQualidade.de_ambiente() is not None
    assert AvaliadorDeQualidade.de_ambiente(ligado=False) is None


def test_ligado_sem_chave_nao_monta_e_nao_quebra(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    assert AvaliadorDeQualidade.de_ambiente(ligado=True) is None


def test_a_variavel_liga_e_o_argumento_sobrepoe(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    sem_jev_no_ambiente.setenv("JEV_API_KEY", "k")
    sem_jev_no_ambiente.setenv("SUNO_JEV", "1")
    assert AvaliadorDeQualidade.de_ambiente() is not None
    assert AvaliadorDeQualidade.de_ambiente(ligado=False) is None


def test_a_url_e_o_limiar_vem_do_ambiente(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    sem_jev_no_ambiente.setenv("TYPESAFE_API_KEY", "k")
    sem_jev_no_ambiente.setenv("JEV_URL", "https://ponte.netlify.test/jev")
    sem_jev_no_ambiente.setenv("SUNO_JEV_LIMIAR", "0,75")

    avaliador = AvaliadorDeQualidade.de_ambiente(ligado=True)

    assert avaliador is not None
    assert avaliador.limiar == 0.75
    assert avaliador.cliente._url == "https://ponte.netlify.test/jev"


def test_limiar_invalido_cai_no_padrao(sem_jev_no_ambiente: pytest.MonkeyPatch) -> None:
    sem_jev_no_ambiente.setenv("JEV_API_KEY", "k")
    sem_jev_no_ambiente.setenv("SUNO_JEV_LIMIAR", "7")
    avaliador = AvaliadorDeQualidade.de_ambiente(ligado=True)
    assert avaliador is not None and avaliador.limiar == LIMIAR_DE_QUALIDADE


# ---------------------------------------------------------------------------
# No Ciclo de correção: abaixo do Limiar, gera de novo
# ---------------------------------------------------------------------------

TEXTO_DA_ATA = """Data: 4 e 5 de agosto de 2026

280ª Reunião do Copom

O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.
"""

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


def test_o_ciclo_gera_de_novo_quando_a_qualidade_fica_abaixo_e_aprova_na_segunda() -> None:
    ata = Ata(
        identificador="copom-teste",
        titulo="280ª Reunião",
        reuniao=280,
        data_referencia=date(2026, 8, 5),
        texto=TEXTO_DA_ATA,
    )
    ancoras = Ancoras(ata="copom-teste", numericas=[a for a in _ancoras() if isinstance(a, AncoraNumerica)])
    jev = Jev(_resposta(NOTAS_COM_DESENVOLVIMENTO_FRACO), _resposta(NOTAS_BOAS))
    rotulo = "celula:iniciante:texto_analitico:{rodada}"
    provedor = ProvedorFalso({rotulo.format(rodada=0): [FACIL], rotulo.format(rodada=1): [FACIL]})

    historico = rodar_ciclo(
        ata,
        ancoras,
        Audiencia.INICIANTE,
        Formato.TEXTO_ANALITICO,
        provedor,
        qualidade=_avaliador(jev),
    )

    assert historico.destino_final is Destino.APROVADO
    assert [t.laudo.destino for t in historico.tentativas] == [
        Destino.REPROVADO_CORRIGIVEL,
        Destino.APROVADO,
    ]
    assert historico.tentativas[0].laudo.motivos == [MotivoReprovacao.QUALIDADE]
    assert len(jev.pedidos) == 2


def test_erro_inesperado_do_jev_nunca_derruba_a_celula_o_laudo_sai_sem_qualidade() -> None:
    class Quebrado:
        limiar = LIMIAR_DE_QUALIDADE

        def medir(self, conteudo, audiencia):
            raise RuntimeError("algo que ninguém previu")

    laudo = avaliar(_conteudo(), _ancoras(), Audiencia.INICIANTE, qualidade=Quebrado())

    assert laudo.destino is Destino.APROVADO
    assert laudo.medida(Metrica.QUALIDADE) is None
