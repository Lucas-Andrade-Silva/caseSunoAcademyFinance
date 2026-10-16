"""A Fidelidade à Ata: um LLM aponta, o código confere a citação, e o que se confirma reprova.

ADR 0036. O provedor é o LLM falso: nenhum teste toca a rede.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from suno.avaliador import avaliar
from suno.avaliador.fidelidade import (
    LIMITE_DA_ATA_EM_CARACTERES,
    VerificadorDeFidelidade,
)
from suno.avaliador.qualidade import AvaliadorDeQualidade, ClienteJev
from suno.dominio import (
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
    PapelLLM,
    Unidade,
)
from suno.gerador.ciclo import rodar_ciclo
from suno.provedores.falso import ProvedorFalso

import httpx

TEXTO_DA_ATA = """Data: 4 e 5 de agosto de 2026

280ª Reunião do Copom

O Copom decidiu manter a taxa Selic em 14,00% a.a. A decisão foi tomada por 7 votos a 0.
O Comitê avalia que o balanço de riscos permanece assimétrico e acompanha a inflação de serviços.
"""

TEXTO_FACIL = (
    "A Selic (a taxa básica de juros do país) não mudou. "
    "Ela agora é de 14,00% a.a.\n\n"
    "O Banco Central: é a casa que cuida do valor do dinheiro. "
    "A mudança chega devagar até a conta da sua casa."
)
FRASE_INVENTADA = "O grupo prometeu baixar o preço das contas na próxima reunião."


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


def _achado(**campos: str) -> dict[str, str]:
    return {"trecho_da_celula": "", "problema": "sem_suporte", "trecho_da_ata": "", "explicacao": "x", **campos}


def _provedor(*problemas: dict[str, str] | BaseException) -> ProvedorFalso:
    rotulo = "fidelidade:iniciante:texto_analitico"
    if len(problemas) == 1 and isinstance(problemas[0], BaseException):
        return ProvedorFalso({rotulo: [problemas[0]]})
    return ProvedorFalso({rotulo: [json.dumps({"problemas": list(problemas)}, ensure_ascii=False)]})


def _verificador(provedor: ProvedorFalso, ata: str = TEXTO_DA_ATA) -> VerificadorDeFidelidade:
    return VerificadorDeFidelidade(provedor, ata)


def _laudo(verificador: VerificadorDeFidelidade | None, texto: str = TEXTO_FACIL):
    return avaliar(_conteudo(texto), _ancoras(), Audiencia.INICIANTE, fidelidade=verificador)


# ---------------------------------------------------------------------------
# O que vai ao LLM
# ---------------------------------------------------------------------------


def test_o_pedido_leva_a_ata_inteira_e_o_conteudo_e_nao_diz_quem_gerou() -> None:
    provedor = _provedor()
    _laudo(_verificador(provedor))

    (pedido,) = provedor.pedidos
    assert pedido.papel is PapelLLM.CHECADOR
    texto = " ".join(m.texto for m in pedido.mensagens)
    assert TEXTO_DA_ATA in texto
    assert TEXTO_FACIL in texto
    for nome in ("gemini", "groq", "sambanova", "jev"):
        assert nome not in texto.lower()
    assert pedido.temperatura == 0.0


def test_o_pedido_manda_ignorar_explicacao_de_termo_e_analogia() -> None:
    provedor = _provedor()
    _laudo(_verificador(provedor))

    sistema = provedor.pedidos[0].mensagens[0].texto
    assert "explicação de termo" in sistema and "analogia" in sistema
    assert "Na dúvida, não aponte" in sistema


# ---------------------------------------------------------------------------
# No Laudo
# ---------------------------------------------------------------------------


def test_sem_apontamentos_o_laudo_aprova_com_fidelidade_1() -> None:
    laudo = _laudo(_verificador(_provedor()))

    assert laudo.destino is Destino.APROVADO
    medida = laudo.medida(Metrica.FIDELIDADE)
    assert medida is not None and medida.valor == 1.0 and medida.atingiu is True


def test_sem_suporte_so_avisa_nao_reprova_porque_nao_ha_prova_a_conferir() -> None:
    texto = TEXTO_FACIL + " " + FRASE_INVENTADA
    verificador = _verificador(
        _provedor(_achado(trecho_da_celula=FRASE_INVENTADA, explicacao="A Ata não fala de cortes."))
    )

    laudo = _laudo(verificador, texto)

    assert laudo.destino is Destino.APROVADO
    assert laudo.correcoes == []
    medida = laudo.medida(Metrica.FIDELIDADE)
    assert medida is not None and medida.valor == 1.0 and medida.atingiu is True
    aviso = next(o for o in medida.observacoes if o.startswith("Aviso (não reprova)"))
    assert "«O grupo prometeu baixar o preço das contas na próxima reunião.»" in aviso


def test_contradiz_com_o_trecho_da_ata_reprova_e_a_correcao_cita_os_dois_trechos() -> None:
    texto = TEXTO_FACIL + " O grupo subiu o custo do dinheiro."
    verificador = _verificador(
        _provedor(
            _achado(
                trecho_da_celula="O grupo subiu o custo do dinheiro.",
                problema="contradiz",
                trecho_da_ata="O Copom decidiu manter a taxa Selic em 14,00% a.a.",
            )
        )
    )

    laudo = _laudo(verificador, texto)

    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert laudo.motivos == [MotivoReprovacao.FIDELIDADE]
    (correcao,) = laudo.correcoes
    assert correcao.metrica is Metrica.FIDELIDADE
    assert "«O grupo subiu o custo do dinheiro.»" in correcao.instrucao
    assert "a Ata diz o contrário" in correcao.instrucao
    assert "«O Copom decidiu manter a taxa Selic em 14,00% a.a.»" in correcao.instrucao
    medida = laudo.medida(Metrica.FIDELIDADE)
    assert medida is not None and medida.valor == 0.0 and medida.atingiu is False


def test_um_aviso_ao_lado_de_um_bloqueio_nao_entra_na_correcao() -> None:
    texto = TEXTO_FACIL + " O grupo subiu o custo do dinheiro. " + FRASE_INVENTADA
    verificador = _verificador(
        _provedor(
            _achado(trecho_da_celula=FRASE_INVENTADA),
            _achado(
                trecho_da_celula="O grupo subiu o custo do dinheiro.",
                problema="distorce",
                trecho_da_ata="O Copom decidiu manter a taxa Selic em 14,00% a.a.",
            ),
        )
    )

    laudo = _laudo(verificador, texto)

    (correcao,) = laudo.correcoes
    assert "subiu o custo" in correcao.instrucao
    assert "baixar o preço das contas" not in correcao.instrucao
    medida = laudo.medida(Metrica.FIDELIDADE)
    assert medida is not None and any("baixar o preço das contas" in o for o in medida.observacoes)


def test_trecho_que_nao_esta_na_celula_e_descartado_e_o_laudo_aprova() -> None:
    verificador = _verificador(_provedor(_achado(trecho_da_celula="uma frase que nunca foi escrita ali")))

    laudo = _laudo(verificador)

    assert laudo.destino is Destino.APROVADO
    medida = laudo.medida(Metrica.FIDELIDADE)
    assert medida is not None and medida.atingiu is True
    assert any("descartado" in o for o in medida.observacoes)


def test_trecho_curto_demais_e_vago_e_descartado() -> None:
    verificador = _verificador(_provedor(_achado(trecho_da_celula="A Selic")))

    assert _laudo(verificador).destino is Destino.APROVADO


def test_distorce_exige_que_o_trecho_da_ata_exista() -> None:
    texto = TEXTO_FACIL + " O grupo subiu o custo do dinheiro."
    inventado = _achado(
        trecho_da_celula="O grupo subiu o custo do dinheiro.",
        problema="distorce",
        trecho_da_ata="O Copom decidiu aumentar a taxa em 1 ponto percentual.",
    )
    verdadeiro = _achado(
        trecho_da_celula="O grupo subiu o custo do dinheiro.",
        problema="distorce",
        trecho_da_ata="O Copom decidiu manter a taxa Selic em 14,00% a.a.",
    )

    assert _laudo(_verificador(_provedor(inventado)), texto).destino is Destino.APROVADO

    laudo = _laudo(_verificador(_provedor(verdadeiro)), texto)
    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert "a Ata diz outra coisa" in laudo.correcoes[0].instrucao
    assert "«O Copom decidiu manter a taxa Selic em 14,00% a.a.»" in laudo.correcoes[0].instrucao


def test_a_conferencia_ignora_caixa_espacos_e_travessao() -> None:
    texto = TEXTO_FACIL + "\n\nO  grupo   SUBIU o custo   do dinheiro."
    verificador = _verificador(
        _provedor(
            _achado(
                trecho_da_celula="O grupo subiu o custo do dinheiro.",
                problema="contradiz",
                trecho_da_ata="o COPOM decidiu  manter a taxa Selic\nem 14,00% a.a.",
            )
        )
    )

    assert _laudo(verificador, texto).destino is Destino.REPROVADO_CORRIGIVEL


def test_as_ancoras_vao_ao_pedido_como_fatos_ja_conferidos() -> None:
    provedor = _provedor()
    _laudo(_verificador(provedor))

    texto = " ".join(m.texto for m in provedor.pedidos[0].mensagens)
    assert "FATOS JÁ CONFERIDOS PELO SISTEMA" in texto
    assert "Placar da votação: 7 a 0" in texto
    assert "Selic decidida: 14,00" in texto
    assert "conclusão direta dos FATOS JÁ CONFERIDOS" in texto


# ---------------------------------------------------------------------------
# Falha nunca reprova; ordem das camadas
# ---------------------------------------------------------------------------


def test_falha_do_provedor_nao_reprova_o_laudo_sai_sem_fidelidade() -> None:
    laudo = _laudo(_verificador(_provedor(ErroProvedor("sambanova", "503"))))

    assert laudo.destino is Destino.APROVADO
    assert laudo.medida(Metrica.FIDELIDADE) is None


def test_resposta_fora_do_schema_nao_reprova() -> None:
    provedor = ProvedorFalso({"fidelidade:iniciante:texto_analitico": ['{"problemas": "isto não é lista"}']})

    laudo = _laudo(_verificador(provedor))

    assert laudo.destino is Destino.APROVADO
    assert laudo.medida(Metrica.FIDELIDADE) is None


def test_ata_grande_demais_nao_vai_ao_provedor_e_nao_reprova() -> None:
    provedor = _provedor()
    laudo = _laudo(_verificador(provedor, ata="x" * (LIMITE_DA_ATA_EM_CARACTERES + 1)))

    assert provedor.pedidos == []
    assert laudo.destino is Destino.APROVADO
    assert laudo.medida(Metrica.FIDELIDADE) is None


def test_o_checador_nao_roda_quando_o_determinístico_ja_reprovou() -> None:
    provedor = _provedor()
    laudo = _laudo(_verificador(provedor), "O hiato do produto segue positivo neste trimestre.")

    assert laudo.destino is Destino.REPROVADO_CORRIGIVEL
    assert MotivoReprovacao.FIDELIDADE not in laudo.motivos
    assert provedor.pedidos == []


def test_o_checador_nao_roda_quando_a_qualidade_reprovou() -> None:
    notas = {d: 3.0 for d in ("desenvolvimento", "completude", "clareza", "tom")}
    notas["desenvolvimento"] = 0.0
    resposta = {"answers": {k: {"type": "score", "score": v} for k, v in notas.items()}}
    jev = httpx.Client(transport=httpx.MockTransport(lambda _r: httpx.Response(200, json=resposta)))
    qualidade = AvaliadorDeQualidade(ClienteJev("https://jev.test/v1/systemone", "k", cliente=jev))
    provedor = _provedor()

    laudo = avaliar(
        _conteudo(),
        _ancoras(),
        Audiencia.INICIANTE,
        qualidade=qualidade,
        fidelidade=_verificador(provedor),
    )

    assert laudo.motivos == [MotivoReprovacao.QUALIDADE]
    assert provedor.pedidos == []


def test_sem_o_checador_o_laudo_nao_tem_a_medida() -> None:
    assert _laudo(None).medida(Metrica.FIDELIDADE) is None


# ---------------------------------------------------------------------------
# Montagem pelo ambiente
# ---------------------------------------------------------------------------


@pytest.fixture
def sem_ambiente(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for variavel in (
        "SUNO_FIDELIDADE",
        "GROQ_API_KEY",
        "GROQ_MODELO",
        "GEMINI_API_KEY",
        "GEMINI_MODELO",
        "SAMBANOVA_API_KEY",
        "SAMBANOVA_MODELO",
    ):
        monkeypatch.delenv(variavel, raising=False)
    return monkeypatch


def test_desligado_por_padrao(sem_ambiente: pytest.MonkeyPatch) -> None:
    assert VerificadorDeFidelidade.de_ambiente(TEXTO_DA_ATA) is None


def test_ligado_sem_groq_nem_gemini_nao_monta_e_nao_quebra(sem_ambiente: pytest.MonkeyPatch) -> None:
    assert VerificadorDeFidelidade.de_ambiente(TEXTO_DA_ATA, ligado=True) is None


def test_so_com_o_sambanova_o_checador_nao_monta(sem_ambiente: pytest.MonkeyPatch) -> None:
    sem_ambiente.setenv("SAMBANOVA_API_KEY", "k")
    sem_ambiente.setenv("SAMBANOVA_MODELO", "modelo-de-teste")
    assert VerificadorDeFidelidade.de_ambiente(TEXTO_DA_ATA, ligado=True) is None


def test_ligado_com_as_duas_chaves_o_groq_vem_primeiro_e_o_gemini_depois(
    sem_ambiente: pytest.MonkeyPatch,
) -> None:
    for nome in ("GROQ", "GEMINI", "SAMBANOVA"):
        sem_ambiente.setenv(f"{nome}_API_KEY", "k")
        sem_ambiente.setenv(f"{nome}_MODELO", "modelo-de-teste")
    sem_ambiente.setenv("SUNO_FIDELIDADE", "1")

    verificador = VerificadorDeFidelidade.de_ambiente(TEXTO_DA_ATA)

    assert verificador is not None
    assert [p.nome for p in verificador.provedor.provedores] == ["groq", "gemini"]  # nunca o SambaNova
    assert VerificadorDeFidelidade.de_ambiente(TEXTO_DA_ATA, ligado=False) is None


def test_so_com_o_gemini_o_checador_monta_so_com_ele(sem_ambiente: pytest.MonkeyPatch) -> None:
    sem_ambiente.setenv("GEMINI_API_KEY", "k")
    sem_ambiente.setenv("GEMINI_MODELO", "modelo-de-teste")

    verificador = VerificadorDeFidelidade.de_ambiente(TEXTO_DA_ATA, ligado=True)

    assert verificador is not None
    assert [p.nome for p in verificador.provedor.provedores] == ["gemini"]


# ---------------------------------------------------------------------------
# No Ciclo de correção: bloqueia e regenera
# ---------------------------------------------------------------------------

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
APONTADA = "O grupo não disse qual será o próximo passo."


def test_o_ciclo_regenera_quando_o_checador_aponta_e_aprova_quando_ele_deixa_passar() -> None:
    ata = Ata(
        identificador="copom-teste",
        titulo="280ª Reunião",
        reuniao=280,
        data_referencia=date(2026, 8, 5),
        texto=TEXTO_DA_ATA,
    )
    ancoras = Ancoras(ata="copom-teste", numericas=[a for a in _ancoras() if isinstance(a, AncoraNumerica)])
    rotulo = "celula:iniciante:texto_analitico:{rodada}"
    gerador = ProvedorFalso({rotulo.format(rodada=0): [FACIL], rotulo.format(rodada=1): [FACIL]})
    apontou = json.dumps(
        {
            "problemas": [
                _achado(
                    trecho_da_celula=APONTADA,
                    problema="distorce",
                    trecho_da_ata="O Comitê avalia que o balanço de riscos permanece assimétrico",
                )
            ]
        },
        ensure_ascii=False,
    )
    checador = ProvedorFalso({"fidelidade:iniciante:texto_analitico": [apontou, json.dumps({"problemas": []})]})

    historico = rodar_ciclo(
        ata,
        ancoras,
        Audiencia.INICIANTE,
        Formato.TEXTO_ANALITICO,
        gerador,
        fidelidade=_verificador(checador, ata.texto),
    )

    assert [t.laudo.destino for t in historico.tentativas] == [Destino.REPROVADO_CORRIGIVEL, Destino.APROVADO]
    assert historico.tentativas[0].laudo.motivos == [MotivoReprovacao.FIDELIDADE]
    assert len(checador.pedidos) == 2


def test_erro_inesperado_do_checador_nunca_derruba_a_celula_o_laudo_sai_sem_fidelidade() -> None:
    class Quebrado:
        def verificar(self, conteudo, audiencia, ancoras=()):
            raise RuntimeError("algo que ninguém previu")

    laudo = _laudo(Quebrado())

    assert laudo.destino is Destino.APROVADO
    assert laudo.medida(Metrica.FIDELIDADE) is None
