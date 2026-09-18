"""A suíte `pydantic-evals` rodando dentro do pytest, offline (ADR 0003).

Um teste por arquivo de casos. `uv run pytest -s tests/test_evals.py` imprime o relatório
do `pydantic-evals` caso a caso; sem `-s` o pytest engole a saída e só o veredito aparece.

Os casos de ponta a ponta chamam `avaliar` de verdade; os testes dos avaliadores próprios
rodam contra uma tarefa de mentira, para que um defeito na suíte não se disfarce de defeito
do Avaliador (e vice-versa).

`Dataset.evaluate_sync` cria o próprio laço de eventos, que no Windows abre um
`socket.socketpair()` de loopback — liberado pela trava de rede do `tests/conftest.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_evals import Case, Dataset

from evals.avaliadores import (
    AVALIADORES_PROPRIOS,
    DestinoEsperado,
    MedidaAusente,
    MedidaNaFaixa,
    MotivosEsperados,
)
from evals.tarefas import Entrada, MedidaResumida, SaidaLaudo, julgar
from suno.dominio import (
    LIMIARES_PROVISORIOS,
    Audiencia,
    Destino,
    EstadoMedida,
    Formato,
    Metrica,
    MotivoReprovacao,
)

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DE_CASOS = RAIZ / "evals" / "casos"
ARQUIVOS = sorted(PASTA_DE_CASOS.glob("*.yaml"))
MINIMO_DE_CASOS = 6

Casos = Dataset[Entrada, SaidaLaudo, str]


def _carregar(arquivo: Path) -> Casos:
    return Casos.from_file(arquivo, custom_evaluator_types=AVALIADORES_PROPRIOS)


def test_ha_um_arquivo_de_casos_por_metrica_mais_a_matriz():
    esperados = {
        "flesch_br.yaml",
        "densidade.yaml",
        "aderencia.yaml",
        "recomendacao.yaml",
        "integridade.yaml",
        "matriz.yaml",
    }
    assert esperados <= {a.name for a in ARQUIVOS}


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.stem)
def test_casos_carregam_e_estao_documentados(arquivo: Path):
    """Carregar o YAML já valida `inputs` contra `Entrada` e os avaliadores contra as
    classes próprias: um nome de métrica errado no arquivo quebra aqui, não em produção.
    """
    casos = _carregar(arquivo)
    assert len(casos.cases) >= MINIMO_DE_CASOS, f"{arquivo.name} tem menos de {MINIMO_DE_CASOS}"
    nomes = [caso.name for caso in casos.cases]
    assert all(nomes), "todo caso precisa de nome: é o que aparece no relatório"
    assert len(set(nomes)) == len(nomes), "nome de caso duplicado"
    for caso in casos.cases:
        assert caso.metadata, f"{caso.name} não diz por que existe"


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.stem)
def test_nenhum_caso_chama_juiz_de_llm(arquivo: Path):
    """A suíte é determinística e offline: `LLMJudge` e `GEval` existem e ficam fora."""
    texto = arquivo.read_text(encoding="utf-8")
    assert "LLMJudge" not in texto
    assert "GEval" not in texto


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda a: a.stem)
def test_suite_roda_contra_o_avaliador(arquivo: Path):
    """Roda os casos do arquivo e exige que **toda** asserção tenha passado.

    `max_concurrency=1` de propósito: a tarefa é síncrona e o `pydantic-evals` a joga numa
    thread, e execução em ordem fixa é o que torna a saída comparável entre rodadas.

    O `print` do relatório sai com `pytest -s`; sem `-s` o pytest o captura e só mostra em
    caso de falha, que é quando ele importa.
    """
    casos = _carregar(arquivo)
    resultado = casos.evaluate_sync(julgar, max_concurrency=1, progress=False)
    print()
    resultado.print(include_reasons=True, width=160)

    assert not resultado.failures, [f.error_message for f in resultado.failures]

    quebrados: list[str] = []
    for caso in resultado.cases:
        for falha in caso.evaluator_failures:
            quebrados.append(f"{caso.name}: avaliador {falha.name} quebrou — {falha.error_message}")
        for nome, afirmacao in caso.assertions.items():
            if not afirmacao.value:
                quebrados.append(f"{caso.name}: {nome} — {afirmacao.reason}")
    assert not quebrados, "\n".join(quebrados)


def test_a_suite_inteira_afirma_algo_em_todo_caso():
    """Nenhum caso passa por falta de afirmação: todo caso afirma pelo menos uma coisa."""
    for arquivo in ARQUIVOS:
        casos = _carregar(arquivo)
        resultado = casos.evaluate_sync(julgar, max_concurrency=1, progress=False)
        for caso in resultado.cases:
            assert caso.assertions, f"{arquivo.stem}/{caso.name} não afirma nada"


# ---------------------------------------------------------------------------
# A fronteira exata do Limiar, sem depender do Avaliador
# ---------------------------------------------------------------------------


def test_fronteira_exata_do_limiar_da_audiencia_iniciante():
    """50,0 é aprovado para o Iniciante; 49,9 não.

    Os casos YAML chegam perto pelos dois lados (50,87 e 49,96) e não podem chegar em
    50,0 exato: com contagem inteira de palavras, frases e sílabas, o menor texto que
    resolve `248,835 − 1,015·(P/F) − 84,6·(S/P) = 50` tem P múltiplo de 1880 palavras. A
    fronteira exata, então, é afirmada direto sobre a `Faixa`.
    """
    faixa = LIMIARES_PROVISORIOS[Audiencia.INICIANTE].flesch_br
    assert faixa.contem(50.0) is True
    assert faixa.contem(49.9) is False
    assert faixa.distancia(49.9) == pytest.approx(0.1)


def test_fronteira_do_intermediario_e_fechada_embaixo_e_aberta_em_cima():
    faixa = LIMIARES_PROVISORIOS[Audiencia.INTERMEDIARIO].flesch_br
    assert faixa.contem(25.0) is True
    assert faixa.contem(49.999) is True
    assert faixa.contem(50.0) is False


# ---------------------------------------------------------------------------
# Os avaliadores próprios, exercitados sem o Avaliador
# ---------------------------------------------------------------------------


def _entrada() -> Entrada:
    return Entrada(audiencia=Audiencia.INICIANTE, formato=Formato.TEXTO_ANALITICO, texto="x")


def _rodar(esperado: SaidaLaudo | None, obtido: SaidaLaudo, evaluators: tuple) -> dict[str, bool]:
    casos = Casos(
        name="avaliadores",
        cases=[Case(name="unico", inputs=_entrada(), expected_output=esperado, metadata="teste")],
        evaluators=evaluators,
    )
    resultado = casos.evaluate_sync(lambda _: obtido, max_concurrency=1, progress=False)
    caso = resultado.cases[0]
    assert not caso.evaluator_failures, [f.error_message for f in caso.evaluator_failures]
    return {nome: a.value for nome, a in caso.assertions.items()}


def test_destino_e_motivos_esperados_comparam_o_que_o_caso_declara():
    obtido = SaidaLaudo(destino=Destino.REPROVADO_CORRIGIVEL, motivos=[MotivoReprovacao.DENSIDADE])

    igual = _rodar(
        SaidaLaudo(destino=Destino.REPROVADO_CORRIGIVEL, motivos=[MotivoReprovacao.DENSIDADE]),
        obtido,
        (DestinoEsperado(), MotivosEsperados()),
    )
    assert igual == {"destino": True, "motivos": True}

    diferente = _rodar(
        SaidaLaudo(destino=Destino.APROVADO, motivos=[]),
        obtido,
        (DestinoEsperado(), MotivosEsperados()),
    )
    assert diferente == {"destino": False, "motivos": False}


def test_motivos_esperados_nao_aceita_motivo_a_mais():
    """Reprovar pelo motivo certo mais um errado não é passar: a comparação é exata."""
    obtido = SaidaLaudo(
        destino=Destino.REPROVADO_CORRIGIVEL,
        motivos=[MotivoReprovacao.DENSIDADE, MotivoReprovacao.FLESCH_BR],
    )
    achados = _rodar(
        SaidaLaudo(motivos=[MotivoReprovacao.DENSIDADE]), obtido, (MotivosEsperados(),)
    )
    assert achados == {"motivos": False}


def test_caso_sem_expectativa_nao_afirma_nada_sobre_o_destino():
    """É assim que o caso de medida ausente pode se calar sobre o destino."""
    obtido = SaidaLaudo(destino=Destino.APROVADO, motivos=[])
    assert _rodar(None, obtido, (DestinoEsperado(), MotivosEsperados())) == {}
    assert _rodar(SaidaLaudo(), obtido, (DestinoEsperado(), MotivosEsperados())) == {}


def test_medida_na_faixa_usa_a_regra_de_faixa_do_dominio():
    def com_flesch(valor: float) -> SaidaLaudo:
        return SaidaLaudo(
            destino=Destino.APROVADO,
            medidas={Metrica.FLESCH_BR: MedidaResumida(estado=EstadoMedida.MEDIDA, valor=valor)},
        )

    faixa = (MedidaNaFaixa(metrica=Metrica.FLESCH_BR, minimo=50.0, maximo=75.0),)
    assert _rodar(None, com_flesch(50.0), faixa) == {"flesch_br_na_faixa": True}
    assert _rodar(None, com_flesch(49.9), faixa) == {"flesch_br_na_faixa": False}
    assert _rodar(None, com_flesch(75.0), faixa) == {"flesch_br_na_faixa": False}


def test_medida_na_faixa_reprova_medida_ausente():
    """Declarar faixa é afirmar que havia base para medir."""
    ausente = SaidaLaudo(
        destino=Destino.APROVADO,
        medidas={Metrica.FLESCH_BR: MedidaResumida(estado=EstadoMedida.AUSENTE)},
    )
    achados = _rodar(None, ausente, (MedidaNaFaixa(metrica=Metrica.FLESCH_BR, minimo=50.0),))
    assert achados == {"flesch_br_na_faixa": False}


def test_medida_ausente_exige_estado_ausente_e_valor_nulo():
    ausente = SaidaLaudo(medidas={Metrica.DENSIDADE: MedidaResumida(estado=EstadoMedida.AUSENTE)})
    zerada = SaidaLaudo(
        medidas={Metrica.DENSIDADE: MedidaResumida(estado=EstadoMedida.MEDIDA, valor=0.0)}
    )
    checagem = (MedidaAusente(metrica=Metrica.DENSIDADE),)
    assert _rodar(None, ausente, checagem) == {"densidade_ausente": True}
    assert _rodar(None, zerada, checagem) == {"densidade_ausente": False}


def test_metrica_escrita_como_texto_no_yaml_vira_enum():
    """O `pydantic-evals` chama o construtor cru, sem validar: a coerção é nossa."""
    assert MedidaAusente(metrica="densidade").metrica is Metrica.DENSIDADE
    assert MedidaNaFaixa(metrica="flesch_br", minimo=1.0).metrica is Metrica.FLESCH_BR


# ---------------------------------------------------------------------------
# A montagem de Conteúdo por Formato
# ---------------------------------------------------------------------------


def test_o_formato_nao_muda_o_texto_medido():
    """Carrossel e Roteiro recompõem o mesmo texto: o Formato não pode mexer na medida."""
    texto = "Primeira parte.\n\nSegunda parte."
    por_formato = {
        formato: Entrada(
            audiencia=Audiencia.INICIANTE, formato=formato, texto=texto
        ).conteudo()
        for formato in Formato
    }
    assert por_formato[Formato.CARROSSEL].texto_avaliavel().split() == texto.split()
    assert por_formato[Formato.ROTEIRO].texto_avaliavel().split() == texto.split()
    assert len(por_formato[Formato.CARROSSEL].slides or []) == 2
    assert len(por_formato[Formato.ROTEIRO].blocos or []) == 2


def test_texto_vazio_vira_corpo_vazio_e_nao_corpo_ausente():
    for formato in Formato:
        conteudo = Entrada(audiencia=Audiencia.INICIANTE, formato=formato, texto="").conteudo()
        assert conteudo.texto_avaliavel() == ""
