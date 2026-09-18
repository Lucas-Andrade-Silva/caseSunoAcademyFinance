"""Kappa de Cohen, matriz de confusão e o resumo que o Entregável 6 cita.

Roda offline e sem `.env`, como toda a suíte. Os rótulos usados aqui são fixtures
sintéticas escritas em `tmp_path` ou as duas linhas de `rotulos.exemplo.csv` marcadas com
`pessoa=exemplo`: **nada disto é Calibração**, que só existe quando duas pessoas rotularem
à mão (ADR 0002, FORMATO.md).
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from suno.avaliador.calibracao import (
    COLUNAS,
    KAPPA_ALVO,
    ORIGEM_AUTOMATICA,
    SEM_BASE,
    SEPARADOR,
    audiencia_pelo_indice,
    dentro_do_alvo,
    kappa_cohen,
    kappa_do_arquivo,
    ler_rotulos,
    matriz_de_confusao,
    matriz_de_confusao_da_execucao,
    resumo_da_execucao,
)
from suno.dominio import (
    Ancoras,
    Audiencia,
    BlocoFala,
    Celula,
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
)

RAIZ = Path(__file__).resolve().parent.parent
CSV_DE_EXEMPLO = RAIZ / "data" / "calibracao" / "rotulos.exemplo.csv"


# ---------------------------------------------------------------------------
# Kappa de Cohen
# ---------------------------------------------------------------------------


def test_concordancia_total_da_um():
    rotulos = ["iniciante", "intermediario", "avancado", "iniciante", "avancado"]
    assert kappa_cohen(rotulos, list(rotulos)) == pytest.approx(1.0)


def test_exemplo_classico_de_cohen_da_zero_virgula_quatro():
    """O exemplo canônico: 20 sim/sim, 5 sim/não, 10 não/sim, 15 não/não em 50 casos.

    po = 0,70 e pe = 0,50, então κ = 0,40. É o valor publicado, e é por isso que este
    teste existe: confere a fórmula contra um número que veio de fora do projeto.
    """
    a = ["sim"] * 20 + ["sim"] * 5 + ["nao"] * 10 + ["nao"] * 15
    b = ["sim"] * 20 + ["nao"] * 5 + ["sim"] * 10 + ["nao"] * 15
    assert kappa_cohen(a, b) == pytest.approx(0.40)


def test_independencia_da_zero():
    """Concordância igual à esperada pelo acaso: κ = 0, sem ser discordância."""
    a = ["sim", "sim", "nao", "nao"]
    b = ["sim", "nao", "sim", "nao"]
    assert kappa_cohen(a, b) == pytest.approx(0.0)


def test_discordancia_sistematica_fica_negativa():
    a = ["sim", "sim", "nao", "nao"]
    b = ["nao", "nao", "sim", "sim"]
    assert kappa_cohen(a, b) < 0


def test_sem_celula_rotulada_e_nan():
    assert math.isnan(kappa_cohen([], []))


def test_categoria_unica_e_nan_nunca_um():
    """As duas pessoas marcaram tudo igual porque só existia uma opção: não há base.

    Devolver 1,0 aqui seria dizer "concordância perfeita" onde não houve escolha nenhuma.
    """
    assert math.isnan(kappa_cohen(["sim"] * 8, ["sim"] * 8))


def test_tamanhos_diferentes_sao_erro():
    with pytest.raises(ValueError, match="mesmo tamanho"):
        kappa_cohen(["sim"], ["sim", "nao"])


@pytest.mark.parametrize(
    "kappa, esperado",
    [(0.59, False), (0.6, True), (0.7, True), (0.8, True), (0.81, False), (math.nan, False)],
)
def test_faixa_alvo_do_adr_0002(kappa: float, esperado: bool):
    assert dentro_do_alvo(kappa) is esperado
    assert KAPPA_ALVO == (0.6, 0.8)


# ---------------------------------------------------------------------------
# A matriz vinda do CSV
# ---------------------------------------------------------------------------


def test_matriz_do_csv_de_exemplo():
    matriz = matriz_de_confusao(CSV_DE_EXEMPLO)
    assert set(matriz) == {"iniciante", "intermediario", "avancado"}
    assert matriz["iniciante"]["intermediario"] == 1
    assert matriz["avancado"]["avancado"] == 1
    assert matriz["intermediario"] == {"iniciante": 0, "intermediario": 0, "avancado": 0}


def test_csv_de_exemplo_nao_e_calibracao():
    """As duas linhas estão marcadas como exemplo: ninguém as conta como rótulo."""
    linhas = ler_rotulos(CSV_DE_EXEMPLO)
    assert linhas, "o arquivo de exemplo precisa ter as duas linhas de formato"
    assert {linha["pessoa"] for linha in linhas} == {"exemplo"}


def test_matriz_filtrada_por_pessoa_ignora_quem_nao_rotulou():
    matriz = matriz_de_confusao(CSV_DE_EXEMPLO, pessoa="ninguem")
    assert all(n == 0 for linha in matriz.values() for n in linha.values())


def test_cabecalho_fora_do_formato_e_erro(tmp_path: Path):
    caminho = tmp_path / "rotulos.csv"
    caminho.write_text("execucao;audiencia\nx;iniciante\n", encoding="utf-8")
    with pytest.raises(ValueError, match="FORMATO.md"):
        ler_rotulos(caminho)


def _escrever_rotulos(caminho: Path, linhas: list[dict[str, str]]) -> None:
    conteudo = [SEPARADOR.join(COLUNAS)]
    for linha in linhas:
        conteudo.append(SEPARADOR.join(linha.get(coluna, "") for coluna in COLUNAS))
    caminho.write_text("\n".join(conteudo) + "\n", encoding="utf-8")


def test_kappa_do_arquivo_pareia_pela_celula_e_nao_pela_ordem(tmp_path: Path):
    """As duas pessoas preenchem em ordens diferentes; o par é a Célula, não a linha."""
    celulas = [
        ("iniciante", "carrossel", "iniciante", "iniciante"),
        ("iniciante", "roteiro", "intermediario", "intermediario"),
        ("intermediario", "carrossel", "intermediario", "avancado"),
        ("avancado", "roteiro", "avancado", "avancado"),
    ]
    de_ana = [
        {
            "execucao": "e1",
            "audiencia": audiencia,
            "formato": formato,
            "rodada": "0",
            "pessoa": "ana",
            "audiencia_percebida": percebida_ana,
            "aprovaria": "sim",
        }
        for audiencia, formato, percebida_ana, _ in celulas
    ]
    de_bruno = [
        {
            "execucao": "e1",
            "audiencia": audiencia,
            "formato": formato,
            "rodada": "0",
            "pessoa": "bruno",
            "audiencia_percebida": percebida_bruno,
            "aprovaria": "sim",
        }
        for audiencia, formato, _, percebida_bruno in reversed(celulas)
    ]
    caminho = tmp_path / "rotulos.csv"
    _escrever_rotulos(caminho, de_ana + de_bruno)

    esperado = kappa_cohen(
        [c[2] for c in celulas],
        [c[3] for c in celulas],
    )
    assert kappa_do_arquivo(caminho, "ana", "bruno") == pytest.approx(esperado)


def test_kappa_do_arquivo_sem_celula_em_comum_e_nan(tmp_path: Path):
    caminho = tmp_path / "rotulos.csv"
    _escrever_rotulos(
        caminho,
        [
            {
                "execucao": "e1",
                "audiencia": "iniciante",
                "formato": "carrossel",
                "rodada": "0",
                "pessoa": "ana",
                "audiencia_percebida": "iniciante",
            },
            {
                "execucao": "e1",
                "audiencia": "avancado",
                "formato": "roteiro",
                "rodada": "0",
                "pessoa": "bruno",
                "audiencia_percebida": "avancado",
            },
        ],
    )
    assert math.isnan(kappa_do_arquivo(caminho, "ana", "bruno"))


# ---------------------------------------------------------------------------
# A matriz automática, sem rótulo humano
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "indice, audiencia",
    [
        (90.0, Audiencia.INICIANTE),
        (50.0, Audiencia.INICIANTE),
        (49.9, Audiencia.INTERMEDIARIO),
        (25.0, Audiencia.INTERMEDIARIO),
        (24.9, Audiencia.AVANCADO),
        (-40.0, Audiencia.AVANCADO),
    ],
)
def test_audiencia_pelo_indice_respeita_a_fronteira(indice: float, audiencia: Audiencia):
    """As faixas do NILC são fechadas no mínimo: 50,0 é Iniciante e 49,9 já não é."""
    assert audiencia_pelo_indice(indice) is audiencia


def _laudo(
    audiencia: Audiencia,
    formato: Formato,
    indice: float | None,
    *,
    com_medida: bool = True,
) -> Laudo:
    medidas: list[Medida] = []
    if com_medida:
        if indice is None:
            medidas.append(Medida(metrica=Metrica.FLESCH_BR, estado=EstadoMedida.AUSENTE))
        else:
            medidas.append(
                Medida(
                    metrica=Metrica.FLESCH_BR,
                    valor=indice,
                    faixa=Faixa(minimo=50.0),
                    atingiu=indice >= 50.0,
                )
            )
    reprova = indice is not None and indice < 50.0
    return Laudo(
        audiencia=audiencia,
        formato=formato,
        medidas=medidas,
        destino=Destino.REPROVADO_CORRIGIVEL if reprova else Destino.APROVADO,
        motivos=[MotivoReprovacao.FLESCH_BR] if reprova else [],
    )


def _conteudo(formato: Formato, texto: str) -> Conteudo:
    """O corpo que cada Formato exige. Texto vazio vira lista vazia, não corpo ausente."""
    if formato is Formato.CARROSSEL:
        return Conteudo(
            formato=formato, slides=[Slide(titulo=texto, corpo="")] if texto else []
        )
    if formato is Formato.ROTEIRO:
        return Conteudo(
            formato=formato,
            blocos=[BlocoFala(inicio_s=0.0, fim_s=5.0, fala=texto)] if texto else [],
        )
    return Conteudo(formato=formato, texto=texto)


def _historico(
    audiencia: Audiencia,
    formato: Formato,
    texto: str,
    indice: float | None,
    *,
    rodadas: int = 1,
    com_medida: bool = True,
) -> HistoricoCelula:
    laudo = _laudo(audiencia, formato, indice, com_medida=com_medida)
    tentativas = [
        Tentativa(
            rodada=rodada,
            celula=Celula(
                audiencia=audiencia,
                formato=formato,
                rodada=rodada,
                conteudo=_conteudo(formato, texto),
            ),
            laudo=laudo,
        )
        for rodada in range(rodadas)
    ]
    return HistoricoCelula(
        audiencia=audiencia,
        formato=formato,
        tentativas=tentativas,
        destino_final=laudo.destino,
    )


def _execucao(*historicos: HistoricoCelula) -> Execucao:
    return Execucao(
        identificador="2026-09-18T00-00-teste",
        ata="copom-280-2026-08-05",
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 9, 18, tzinfo=timezone.utc),
        ancoras=Ancoras(ata="copom-280-2026-08-05"),
        celulas=list(historicos),
    )


def test_matriz_da_execucao_usa_o_flesch_do_laudo():
    execucao = _execucao(
        _historico(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO, "texto fácil.", 86.9),
        _historico(Audiencia.INICIANTE, Formato.CARROSSEL, "texto denso.", 10.0),
        _historico(Audiencia.AVANCADO, Formato.ROTEIRO, "texto médio.", 40.0),
    )
    matriz = matriz_de_confusao_da_execucao(execucao)
    assert matriz["iniciante"]["iniciante"] == 1
    assert matriz["iniciante"]["avancado"] == 1
    assert matriz["avancado"]["intermediario"] == 1
    assert matriz["intermediario"] == {"iniciante": 0, "intermediario": 0, "avancado": 0}


def test_medida_ausente_cai_na_coluna_ausente_e_nao_no_avancado():
    """Sem base para medir não é "percebido como Avançado": é ausente (ADR 0008)."""
    execucao = _execucao(_historico(Audiencia.INTERMEDIARIO, Formato.CARROSSEL, "", None))
    matriz = matriz_de_confusao_da_execucao(execucao)
    assert matriz["intermediario"][SEM_BASE] == 1
    assert matriz["intermediario"]["avancado"] == 0


def test_sem_medida_no_laudo_o_indice_e_recalculado_do_texto():
    """Laudo sem a Medida de Flesch-BR ainda entra na matriz: o texto está lá."""
    execucao = _execucao(
        _historico(
            Audiencia.AVANCADO,
            Formato.TEXTO_ANALITICO,
            "O dia está bom. O sol saiu. Tudo bem por aqui.",
            None,
            com_medida=False,
        )
    )
    matriz = matriz_de_confusao_da_execucao(execucao)
    assert matriz["avancado"]["iniciante"] == 1


def test_celula_sem_tentativa_fica_de_fora_da_matriz():
    vazia = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.ROTEIRO,
        tentativas=[],
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
    )
    matriz = matriz_de_confusao_da_execucao(_execucao(vazia))
    assert all(n == 0 for linha in matriz.values() for n in linha.values())


# ---------------------------------------------------------------------------
# O resumo do Entregável 6
# ---------------------------------------------------------------------------


def test_resumo_da_execucao_e_serializavel_em_json():
    execucao = _execucao(
        _historico(Audiencia.INICIANTE, Formato.TEXTO_ANALITICO, "texto fácil.", 86.9),
        _historico(Audiencia.INICIANTE, Formato.CARROSSEL, "texto denso.", 10.0, rodadas=3),
    )
    resumo = resumo_da_execucao(execucao)
    devolta = json.loads(json.dumps(resumo, ensure_ascii=False))

    assert devolta["execucao"] == "2026-09-18T00-00-teste"
    assert devolta["celulas"] == 2
    assert devolta["por_motivo"]["flesch_br"] == 3, "três tentativas reprovadas pelo mesmo motivo"
    assert devolta["rodadas_por_celula"][1]["rodadas"] == 3
    assert devolta["rodadas_por_celula"][0]["faixa_nilc"] == "muito fácil"
    assert devolta["matriz_de_confusao"]["iniciante"]["avancado"] == 1
    assert devolta["origem"] == ORIGEM_AUTOMATICA


def test_resumo_carimba_a_origem_automatica():
    """O relatório não pode citar esta matriz como concordância entre pessoas."""
    resumo = resumo_da_execucao(_execucao())
    assert "aguardando Calibração" in resumo["origem"]
    assert resumo["kappa_alvo"] == [0.6, 0.8]


def test_contagem_por_motivo_vem_do_dominio():
    execucao = _execucao(
        _historico(Audiencia.INICIANTE, Formato.CARROSSEL, "texto denso.", 10.0, rodadas=2)
    )
    resumo = resumo_da_execucao(execucao)
    esperado = {str(m): n for m, n in execucao.contagem_por_motivo().items()}
    assert resumo["por_motivo"] == esperado


def test_data_de_referencia_nao_entra_no_resumo():
    """O resumo é sobre a execução, não sobre a Ata: nada de `date` solto no JSON."""
    resumo = resumo_da_execucao(_execucao())
    assert not any(isinstance(valor, date) for valor in resumo.values())
