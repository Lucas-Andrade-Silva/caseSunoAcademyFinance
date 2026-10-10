"""A execução ponta a ponta com a Ata do repositório e o LLM falso: o cenário da demo,
gravado em disco, e as respostas prontas conferidas contra o Avaliador real.

Este arquivo é o que impede a demo de quebrar quando alguém mexe no Léxico, no canary ou
nos Limiares: se uma Célula que devia passar parar de passar, o teste diz qual e por quê.

ADR 0001, 0006, 0013.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from suno.avaliador import avaliar
from suno.dominio import (
    MATRIZ,
    Audiencia,
    Destino,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    Mensagem,
    MotivoReprovacao,
    PapelLLM,
    PedidoLLM,
)
from suno.gerador.execucao import (
    PASTA_RESPOSTAS_PRONTAS,
    ProvedorContado,
    carregar_execucao,
    executar,
    listar_execucoes,
    motivo_da_pendencia,
)
from suno.gerador.extracao import ROTULO_DO_PEDIDO, extrair_ancoras
from suno.gerador.moldes import MODELO_POR_FORMATO, montar_conteudo
from suno.ingestao.pdf import carregar_ata
from suno.provedores.falso import ProvedorFalso

IDENTIFICADOR_DA_ATA = "copom-280-2026-08-05"

CENARIO_APROVADO_NA_RODADA_ZERO = (
    (Audiencia.INICIANTE, Formato.CARROSSEL),
    (Audiencia.INICIANTE, Formato.ROTEIRO),
    (Audiencia.INTERMEDIARIO, Formato.TEXTO_ANALITICO),
    (Audiencia.INTERMEDIARIO, Formato.CARROSSEL),
    (Audiencia.AVANCADO, Formato.TEXTO_ANALITICO),
    (Audiencia.AVANCADO, Formato.CARROSSEL),
    (Audiencia.AVANCADO, Formato.ROTEIRO),
)
"""Sete das nove. As outras duas são a reprovação consertada e a que cai no H4."""

REPROVACAO_CONSERTADA = (Audiencia.INICIANTE, Formato.TEXTO_ANALITICO)
FILA_HUMANA = (Audiencia.INTERMEDIARIO, Formato.ROTEIRO)


@pytest.fixture(scope="module")
def caminho_das_prontas() -> Path:
    return PASTA_RESPOSTAS_PRONTAS / f"{IDENTIFICADOR_DA_ATA}.json"


@pytest.fixture(scope="module")
def respostas_prontas(caminho_das_prontas: Path) -> dict:
    return json.loads(caminho_das_prontas.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pasta_da_execucao(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Uma execução só para o arquivo inteiro: gerar a Matriz nove vezes não prova mais nada."""
    return tmp_path_factory.mktemp("execucoes")


@pytest.fixture(scope="module")
def execucao(caminho_ata: Path, pasta_da_execucao: Path) -> Execucao:
    return executar(caminho_ata, "falso", pasta_da_execucao)


# ---------------------------------------------------------------------------
# A execução ponta a ponta
# ---------------------------------------------------------------------------


def test_a_matriz_sai_inteira_e_na_ordem(execucao: Execucao):
    assert [(h.audiencia, h.formato) for h in execucao.celulas] == list(MATRIZ)
    assert execucao.ata == IDENTIFICADOR_DA_ATA
    assert execucao.provedor_gerador == "falso"
    assert execucao.comite_ligado is False
    assert execucao.selecao is not None
    assert execucao.selecao.itens == [IDENTIFICADOR_DA_ATA]
    assert execucao.avaliacao_transversal is not None
    assert execucao.avaliacao_transversal.total_recebido == len(MATRIZ)
    assert execucao.ciclo_transversal is not None
    assert execucao.ciclo_transversal.estado.value == "revisao_humana"
    assert execucao.ciclo_transversal.julgamentos == []


def test_as_sete_celulas_do_cenario_aprovam_na_primeira_rodada(execucao: Execucao):
    for audiencia, formato in CENARIO_APROVADO_NA_RODADA_ZERO:
        historico = execucao.historico(audiencia, formato)
        assert historico is not None
        assert historico.destino_final is Destino.APROVADO, f"{audiencia}:{formato}"
        assert len(historico.tentativas) == 1, f"{audiencia}:{formato}"


def test_a_reprovacao_que_o_ciclo_consertou(execucao: Execucao):
    """Entregável 3: reprovada de verdade na rodada 0, aprovada na rodada 1."""
    historico = execucao.historico(*REPROVACAO_CONSERTADA)
    assert historico is not None
    assert len(historico.tentativas) == 2
    assert historico.destino_final is Destino.APROVADO
    primeiro = historico.tentativas[0].laudo
    assert primeiro.destino is Destino.REPROVADO_CORRIGIVEL
    assert MotivoReprovacao.FLESCH_BR in primeiro.motivos
    assert MotivoReprovacao.DENSIDADE in primeiro.motivos
    assert primeiro.correcoes, "reprovação corrigível sem Correção não ensina nada"


def test_a_celula_teimosa_cai_na_fila_humana_depois_de_duas_correcoes(execucao: Execucao):
    historico = execucao.historico(*FILA_HUMANA)
    assert historico is not None
    assert [t.rodada for t in historico.tentativas] == [0, 1, 2]
    assert historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    assert all(
        MotivoReprovacao.FLESCH_BR in t.laudo.motivos for t in historico.tentativas
    )


def test_a_fila_humana_tem_exatamente_uma_pendencia(execucao: Execucao):
    assert len(execucao.pendencias) == 1
    pendencia = execucao.pendencias[0]
    assert pendencia.fila is FilaHumana.H4_REVISAO
    assert (pendencia.audiencia, pendencia.formato) == FILA_HUMANA
    assert MotivoReprovacao.FLESCH_BR.value in pendencia.motivo
    assert pendencia.resolvida is False


def test_o_custo_conta_as_treze_chamadas(execucao: Execucao):
    """Nove Células na rodada 0, três correções e uma extração."""
    assert execucao.custo.chamadas >= 12
    assert execucao.custo.tokens_entrada > 0
    assert execucao.custo.tokens_saida > 0
    assert execucao.custo.segundos > 0
    assert execucao.custo.por_provedor == {"falso": execucao.custo.chamadas}


def test_grava_e_le_de_volta_igual(execucao: Execucao, pasta_da_execucao: Path):
    arquivo = pasta_da_execucao / execucao.identificador / "execucao.json"
    assert arquivo.exists()
    assert listar_execucoes(pasta_da_execucao) == [execucao.identificador]
    de_volta = carregar_execucao(execucao.identificador, pasta_da_execucao)
    assert de_volta == execucao


def test_o_identificador_carrega_ata_provedor_e_horario(execucao: Execucao):
    assert execucao.identificador.startswith(f"{IDENTIFICADOR_DA_ATA}-falso-")
    carimbo = execucao.identificador.rsplit("-", 2)[-2:]
    assert len(carimbo[0]) == 8 and carimbo[0].isdigit()
    assert len(carimbo[1]) == 6 and carimbo[1].isdigit()


def test_os_markdown_de_leitura_acompanham_o_json(execucao: Execucao, pasta_da_execucao: Path):
    pasta = pasta_da_execucao / execucao.identificador / "celulas"
    nomes = sorted(caminho.name for caminho in pasta.iterdir())
    assert nomes == sorted(f"{a.value}-{f.value}.md" for a, f in MATRIZ)
    texto = (pasta / "iniciante-texto_analitico.md").read_text(encoding="utf-8")
    assert "14,00% a.a." in texto
    assert "{{" not in texto


def test_toda_ancora_citada_existe_nas_ancoras(execucao: Execucao):
    chaves = {ancora.chave for ancora in execucao.ancoras.numericas}
    for historico in execucao.celulas:
        for tentativa in historico.tentativas:
            assert set(tentativa.celula.conteudo.ancoras_citadas) <= chaves


def test_nenhuma_celula_da_execucao_contem_recomendacao(execucao: Execucao):
    for historico in execucao.celulas:
        for tentativa in historico.tentativas:
            assert MotivoReprovacao.RECOMENDACAO not in tentativa.laudo.motivos


# ---------------------------------------------------------------------------
# As respostas prontas conferidas contra o Avaliador real
# ---------------------------------------------------------------------------


def _rotulos_do_cenario() -> list[str]:
    rotulos = [ROTULO_DO_PEDIDO]
    rotulos += [f"celula:{a}:{f}:0" for a, f in MATRIZ]
    rotulos.append(f"celula:{REPROVACAO_CONSERTADA[0]}:{REPROVACAO_CONSERTADA[1]}:1")
    rotulos += [f"celula:{FILA_HUMANA[0]}:{FILA_HUMANA[1]}:{r}" for r in (1, 2)]
    return rotulos


def test_o_arquivo_de_respostas_prontas_tem_todos_os_rotulos_do_cenario(respostas_prontas: dict):
    faltando = [rotulo for rotulo in _rotulos_do_cenario() if rotulo not in respostas_prontas]
    assert faltando == []
    assert set(respostas_prontas) == set(_rotulos_do_cenario())


def test_cada_resposta_pronta_valida_no_modelo_do_seu_formato(respostas_prontas: dict):
    for rotulo, fila in respostas_prontas.items():
        if rotulo == ROTULO_DO_PEDIDO:
            continue
        _, _, formato_bruto, _ = rotulo.split(":")
        modelo = MODELO_POR_FORMATO[Formato(formato_bruto)]
        for pronta in fila:
            modelo.model_validate(pronta)


def test_toda_celula_aprovada_da_demo_passa_no_avaliador_real(
    caminho_ata: Path, caminho_das_prontas: Path, respostas_prontas: dict
):
    """O teste que garante que a demo não quebra quando o Léxico ou o canary mudam."""
    ata = carregar_ata(caminho_ata)
    ancoras = extrair_ancoras(ata, ProvedorFalso.de_arquivo(caminho_das_prontas))
    assert ancoras.chaves_faltantes() == frozenset()

    esperadas = {
        f"celula:{a}:{f}:0": (a, f) for a, f in CENARIO_APROVADO_NA_RODADA_ZERO
    }
    esperadas[f"celula:{REPROVACAO_CONSERTADA[0]}:{REPROVACAO_CONSERTADA[1]}:1"] = (
        REPROVACAO_CONSERTADA
    )

    for rotulo, (audiencia, formato) in esperadas.items():
        modelo = MODELO_POR_FORMATO[formato]
        resposta = modelo.model_validate(respostas_prontas[rotulo][0])
        conteudo = montar_conteudo(resposta, formato, ancoras)
        laudo = avaliar(conteudo, ancoras.todas(), audiencia)
        assert laudo.destino is Destino.APROVADO, (
            f"{rotulo} reprovou por {[m.value for m in laudo.motivos]}: "
            f"{[o for medida in laudo.medidas for o in medida.observacoes]}"
        )
        assert conteudo.ancoras_citadas, f"{rotulo} não citou Âncora nenhuma"


def test_as_ancoras_da_demo_saem_da_ata_de_verdade(caminho_ata: Path, caminho_das_prontas: Path):
    ata = carregar_ata(caminho_ata)
    ancoras = extrair_ancoras(ata, ProvedorFalso.de_arquivo(caminho_das_prontas))
    por_chave = {a.chave: a for a in ancoras.numericas}
    assert por_chave["selic_decidida"].citacao() == "14,00% a.a."
    assert por_chave["placar_votacao"].citacao() == "7 a 0"
    assert por_chave["ipca_projecao_ano_corrente"].citacao() == "5,1%"
    assert por_chave["ipca_projecao_ano_seguinte"].citacao() == "3,8%"
    assert por_chave["ipca_projecao_horizonte"].citacao() == "3,2%"
    for ancora in ancoras.numericas:
        assert ancora.trecho, f"{ancora.chave} sem trecho da Ata não é conferível"
    # A afirmação sem lastro do arquivo é descartada de propósito: o conferidor funciona.
    assert "afirmacao_sem_lastro" not in {t.identificador for t in ancoras.textuais}
    assert ancoras.textuais, "a demo precisa de Âncora textual para a Aderência textual"


# ---------------------------------------------------------------------------
# As bordas da execução
# ---------------------------------------------------------------------------


def test_ata_sem_respostas_prontas_cai_inteira_na_fila_humana(
    texto_ata: str, tmp_path: Path
):
    """Sem fila para o LLM falso não há Célula — e isso vira fila humana, não exceção."""
    ata_solta = tmp_path / "copom-999-2026-08-05.txt"
    ata_solta.write_text(texto_ata, encoding="utf-8")

    execucao = executar(ata_solta, "falso", tmp_path / "execucoes")
    assert execucao.custo.chamadas == 0
    assert all(historico.tentativas == [] for historico in execucao.celulas)
    assert len(execucao.pendencias) == len(MATRIZ)
    motivo = execucao.pendencias[0].motivo
    assert motivo.startswith("o provedor falso falhou na rodada 0:")
    assert "sem resposta pronta" in motivo
    # A regra fixa leu a Ata mesmo sem LLM: o problema foi de geração, não de extração.
    assert execucao.ancoras.chaves_faltantes() == frozenset()


def test_comite_pedido_sem_chave_no_ambiente_nao_derruba_a_execucao(
    caminho_ata: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """``--comite`` sobrepõe ``SUNO_COMITE``, mas sem chave não há dois juízes (ADR 0008).

    Comitê ausente é um Laudo sem comitê, nunca um Laudo pior — e o log diz o que falta.
    """
    with caplog.at_level("WARNING"):
        execucao = executar(caminho_ata, "falso", tmp_path / "execucoes", comite=True)

    assert execucao.comite_ligado is False
    assert all(t.laudo.comite is None for h in execucao.celulas for t in h.tentativas)
    explicacao = [linha for linha in caplog.messages if "comitê" in linha.lower()]
    assert explicacao, "comitê pedido e não montado tem que explicar por quê no log"
    assert any("env" in linha.lower() or "chave" in linha.lower() for linha in explicacao)
    # A demo não muda por causa do comitê: as nove Células saem iguais.
    assert len(execucao.celulas) == len(MATRIZ)
    assert sum(1 for h in execucao.celulas if h.destino_final is Destino.APROVADO) == 8


def test_comite_nao_pedido_nem_consulta_o_ambiente(caminho_ata: Path, tmp_path: Path):
    execucao = executar(caminho_ata, "falso", tmp_path / "execucoes", comite=False)
    assert execucao.comite_ligado is False


def test_o_contador_enxerga_as_chamadas_que_o_roteador_faz():
    """O roteador chama o ``completar`` da fila dele; sem isso o Custo sairia zerado."""
    from suno.provedores.roteador import Roteador

    interno = ProvedorFalso({"celula:x": ['{"titulo": "t"}']})
    contado = ProvedorContado(Roteador([interno]))

    class Saida(BaseModel):
        titulo: str

    pedido = PedidoLLM(
        papel=PapelLLM.GERADOR,
        rotulo="celula:x",
        mensagens=[Mensagem(autor="usuario", texto="oi")],
    )
    assert contado.completar_estruturado(pedido, Saida).titulo == "t"
    custo = contado.custo(1.0)
    assert custo.chamadas == 1
    assert custo.por_provedor == {"falso": 1}


def test_motivo_da_pendencia_e_a_falha_quando_o_provedor_derrubou_o_ciclo():
    interrompido = HistoricoCelula(
        audiencia=Audiencia.INICIANTE,
        formato=Formato.ROTEIRO,
        destino_final=Destino.REPROVADO_REVISAO_HUMANA,
        falha="o provedor gemini falhou na rodada 1: cota esgotada (por_dia)",
    )
    assert motivo_da_pendencia(interrompido) == interrompido.falha


def test_motivo_da_pendencia_sem_falha_cai_nos_motivos_do_ultimo_laudo(execucao: Execucao):
    """Quem esgotou o teto reprovou por mérito: ``falha`` fica ``None``."""
    teimosa = execucao.historico(*FILA_HUMANA)
    assert teimosa is not None
    assert teimosa.falha is None
    assert motivo_da_pendencia(teimosa) == MotivoReprovacao.FLESCH_BR.value


# ---------------------------------------------------------------------------
# Nome estável da pasta
# ---------------------------------------------------------------------------


def test_identificador_dado_vira_o_nome_da_pasta(caminho_ata: Path, tmp_path: Path):
    """A demo versionada precisa de caminho fixo: interface, pytest e relatório leem o mesmo."""
    pasta = tmp_path / "execucoes"
    execucao = executar(caminho_ata, "falso", pasta, identificador="demo")

    assert execucao.identificador == "demo"
    assert (pasta / "demo" / "execucao.json").exists()
    assert (pasta / "demo" / "celulas" / "iniciante-texto_analitico.md").exists()
    assert listar_execucoes(pasta) == ["demo"]
    assert carregar_execucao("demo", pasta) == execucao


def test_sem_identificador_o_nome_leva_o_carimbo_de_hora(caminho_ata: Path, tmp_path: Path):
    pasta = tmp_path / "execucoes"
    execucao = executar(caminho_ata, "falso", pasta)

    assert execucao.identificador.startswith(f"{IDENTIFICADOR_DA_ATA}-falso-")
    data, hora = execucao.identificador.rsplit("-", 2)[-2:]
    assert len(data) == 8 and data.isdigit()
    assert len(hora) == 6 and hora.isdigit()
    assert listar_execucoes(pasta) == [execucao.identificador]


def test_regerar_a_demo_sobrescreve_a_pasta_em_vez_de_criar_outra(
    caminho_ata: Path, tmp_path: Path
):
    pasta = tmp_path / "execucoes"
    primeira = executar(caminho_ata, "falso", pasta, identificador="demo")
    arquivo = pasta / "demo" / "execucao.json"
    arquivo.write_text('{"lixo": "de uma execução anterior"}', encoding="utf-8")

    segunda = executar(caminho_ata, "falso", pasta, identificador="demo")

    assert listar_execucoes(pasta) == ["demo"]
    assert segunda.identificador == "demo"
    assert carregar_execucao("demo", pasta) == segunda
    assert segunda.iniciada_em >= primeira.iniciada_em


@pytest.mark.parametrize("bruto", ["", "   ", "../fuga", "com/barra", "com\barra", ".oculto"])
def test_identificador_que_nao_serve_de_pasta_e_recusado_na_hora(
    caminho_ata: Path, tmp_path: Path, bruto: str
):
    """Falhar cedo: um nome com barra criaria pasta aninhada que ``listar_execucoes`` não vê."""
    with pytest.raises(ValueError, match="nome de pasta"):
        executar(caminho_ata, "falso", tmp_path / "execucoes", identificador=bruto)


# ---------------------------------------------------------------------------
# A citação já traz a unidade
# ---------------------------------------------------------------------------

UNIDADE_REPETIDA = re.compile(r"\{\{\s*\w+\s*\}\}[\s,]*(?:ao\s+ano|a\.a\.|por\s+cento|%)")
"""``{{selic_decidida}} ao ano`` renderiza ``14,00% a.a. ao ano``: a chave já traz a unidade."""


def test_nenhuma_chave_da_demo_e_seguida_da_unidade_que_ela_ja_traz(caminho_das_prontas: Path):
    bruto = caminho_das_prontas.read_text(encoding="utf-8")
    repetidas = UNIDADE_REPETIDA.findall(bruto)
    assert repetidas == [], f"unidade repetida depois de chave: {repetidas}"


def test_nenhuma_celula_da_demo_renderiza_unidade_dobrada(execucao: Execucao):
    """O sintoma, não a causa: o texto final não pode dizer a unidade duas vezes."""
    dobradas = ("a.a. ao ano", "% por cento", "a.a. %", "% a.a. ao ano")
    for historico in execucao.celulas:
        for tentativa in historico.tentativas:
            texto = tentativa.celula.conteudo.texto_avaliavel()
            for dobrada in dobradas:
                assert dobrada not in texto, f"{historico.audiencia}:{historico.formato}"
