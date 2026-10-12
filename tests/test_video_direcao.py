"""A direção de cena do Roteiro: design system, duração escolhida, plano de edição e render.

O que estes testes protegem:

- as cores do design system são as do Carrossel (identidade única);
- cada duração (40s, 1m, 1m30, 2m, 3m) tem orçamento de palavras e de cenas, e uma duração que
  não existe é recusada com a lista das que existem;
- o pedido do Roteiro leva a duração e o catálogo; os outros Formatos não;
- ``cronometrar`` refaz o tempo pelas palavras e higieniza a direção;
- o plano JSON é completo, versionado e coerente com o Roteiro;
- todo ícone, cena, animação, efeito e transição compõe um quadro 9:16 sem quebrar;
- os sons são sintetizados e determinísticos.

Nenhum teste aqui usa rede, ffmpeg ou LLM; o único que codifica um mp4 pula sem o extra ``video``.
"""

from __future__ import annotations

import json
import wave
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import ImageChops

from suno.dominio import (
    AncoraNumerica,
    AnimacaoDoTexto,
    Ancoras,
    Audiencia,
    BlocoFala,
    Celula,
    Conteudo,
    Destino,
    DuracaoDoVideo,
    EfeitoDeCena,
    Execucao,
    Formato,
    HistoricoCelula,
    IconeDeCena,
    Laudo,
    Medida,
    Metrica,
    SomDeCena,
    Tentativa,
    TipoDeCena,
    TransicaoDeEntrada,
    Unidade,
)
from suno.gerador.moldes import (
    RespostaRoteiro,
    max_tokens_do_roteiro,
    montar_conteudo,
    montar_pedido,
)
from suno.pacote import carrossel
from suno.video import design, sons
from suno.video.icones import DESENHOS
from suno.video.plano import montar_plano, plano_do_roteiro, plano_em_markdown
from suno.video.render import ALTURA_VIDEO, LARGURA_VIDEO, compor_quadro, compor_transicao

IDENTIFICADOR = "copom-280-2026-08-05-direcao-0001"


@pytest.fixture
def ancoras_de_teste() -> Ancoras:
    return Ancoras(
        ata="copom-teste",
        numericas=[
            AncoraNumerica(
                chave="x",
                rotulo="Selic decidida",
                valor_literal="14,00",
                valor=14.0,
                unidade=Unidade.PERCENTUAL_AO_ANO,
                trecho="O Copom decidiu reduzir a taxa básica de juros para 14,00% a.a.",
            )
        ],
    )


def _bloco(**campos) -> BlocoFala:
    base = dict(inicio_s=0, fim_s=4, fala="Os juros caíram e isso mexe com o bolso de quem lê.", tela="JURO EM {{x}}")
    base.update(campos)
    return BlocoFala(**base)


def _roteiro(duracao: int | None = 60) -> Conteudo:
    blocos = [
        _bloco(
            fala="A Selic caiu e isso chega ao seu bolso, entenda em poucos segundos agora.",
            tela="O juro caiu?",
            cena=TipoDeCena.GANCHO,
            icone=IconeDeCena.PERGUNTA,
            texto_anima=AnimacaoDoTexto.DIGITAR,
        ),
        _bloco(
            fala="O comitê reduziu a taxa básica de juros por decisão unânime nesta reunião.",
            tela="14,50% a.a.",
            cena=TipoDeCena.DADO_GRANDE,
            icone=IconeDeCena.JUROS,
            entrada=TransicaoDeEntrada.DESLIZAR_CIMA,
            texto_anima=AnimacaoDoTexto.POP,
            texto_entra_em_s=0.5,
            efeito=EfeitoDeCena.CONTAGEM,
            som_de_entrada=SomDeCena.WHOOSH,
            som_de_efeito=SomDeCena.DING,
        ),
        _bloco(
            fala="Dois pontos pesam daqui para frente: a inflação e o ritmo da atividade.",
            tela="Inflação | Atividade",
            cena=TipoDeCena.LISTA,
            icone=IconeDeCena.BALANCA,
            entrada=TransicaoDeEntrada.FADE,
        ),
    ]
    return Conteudo(
        formato=Formato.ROTEIRO,
        blocos=design.cronometrar(blocos),
        duracao_alvo_s=duracao,
    )


# ---------------------------------------------------------------------------
# 1 — o design system
# ---------------------------------------------------------------------------


def test_as_cores_do_design_system_sao_as_do_carrossel() -> None:
    assert design.CORES["fundo"] == carrossel.COR_FUNDO
    assert design.CORES["texto"] == carrossel.COR_TEXTO
    assert design.CORES["apoio"] == carrossel.COR_APOIO
    assert design.CORES["destaque"] == carrossel.COR_DESTAQUE


def test_todo_valor_dos_catalogos_tem_descricao() -> None:
    assert set(design.CENAS) == set(TipoDeCena)
    assert set(design.ICONES) == set(IconeDeCena)
    assert set(design.TRANSICOES) == set(TransicaoDeEntrada)
    assert set(design.ANIMACOES_DO_TEXTO) == set(AnimacaoDoTexto)
    assert set(design.EFEITOS) == set(EfeitoDeCena)
    assert set(design.SONS) == set(SomDeCena)
    assert set(DESENHOS) == set(IconeDeCena), "todo ícone do catálogo tem desenho"


@pytest.mark.parametrize(
    ("duracao", "palavras", "cenas"),
    [(40, 100, (5, 8)), (60, 150, (8, 12)), (90, 225, (11, 18)), (120, 300, (15, 24)), (180, 450, (22, 36))],
)
def test_cada_duracao_tem_orcamento_de_palavras_e_de_cenas(duracao, palavras, cenas) -> None:
    orcamento = design.orcamento_de(DuracaoDoVideo(str(duracao)))

    assert orcamento.palavras_alvo == palavras
    assert (orcamento.cenas_minimas, orcamento.cenas_maximas) == cenas
    minimo, maximo = orcamento.faixa_de_duracao_s
    assert minimo == pytest.approx(duracao * 0.75)
    assert maximo == pytest.approx(duracao * 1.25)


def test_as_cinco_duracoes_sao_as_pedidas() -> None:
    assert design.duracoes_aceitas() == [40, 60, 90, 120, 180]


def test_duracao_que_nao_existe_e_recusada_com_a_lista() -> None:
    with pytest.raises(ValueError, match="40s, 60s, 90s, 120s, 180s"):
        design.duracao_valida(45)
    assert design.duracao_valida(90) is DuracaoDoVideo.S90


# ---------------------------------------------------------------------------
# 2 — o pedido e a montagem do Conteúdo
# ---------------------------------------------------------------------------


def test_o_pedido_do_roteiro_leva_a_duracao_e_o_catalogo(ancoras_de_teste: Ancoras) -> None:
    pedido = montar_pedido(
        "Ata", ancoras_de_teste, Audiencia.INICIANTE, Formato.ROTEIRO, duracao=DuracaoDoVideo.S90
    )
    sistema = pedido.mensagens[0].texto

    assert "Duração escolhida: 90 segundos" in sistema
    assert "cerca de 225" in sistema
    for nome in ("dado_grande", "grafico_alta", "deslizar_cima", "contagem", "whoosh"):
        assert nome in sistema
    assert pedido.max_tokens == max_tokens_do_roteiro(DuracaoDoVideo.S90)


def test_o_pedido_dos_outros_formatos_nao_leva_direcao_de_cena(ancoras_de_teste: Ancoras) -> None:
    for formato in (Formato.CARROSSEL, Formato.TEXTO_ANALITICO):
        sistema = montar_pedido(
            "Ata", ancoras_de_teste, Audiencia.INICIANTE, formato, duracao=DuracaoDoVideo.S180
        ).mensagens[0].texto
        assert "Duração escolhida" not in sistema
        assert "Direção de cena" not in sistema


def test_o_teto_de_tokens_do_roteiro_cresce_com_a_duracao() -> None:
    tetos = [max_tokens_do_roteiro(d) for d in DuracaoDoVideo]
    assert tetos == sorted(tetos)
    assert tetos[-1] <= 8192


def test_montar_conteudo_do_roteiro_cronometra_e_guarda_o_alvo(ancoras_de_teste: Ancoras) -> None:
    resposta = RespostaRoteiro(
        blocos=[
            _bloco(inicio_s=0, fim_s=1, fala="Um dois três quatro cinco seis sete oito nove dez."),
            _bloco(inicio_s=1, fim_s=2, fala="Curto.", efeito=EfeitoDeCena.CONTAGEM, cena=TipoDeCena.GANCHO),
        ]
    )

    conteudo = montar_conteudo(resposta, Formato.ROTEIRO, ancoras_de_teste, DuracaoDoVideo.S40)

    assert conteudo.duracao_alvo_s == 40
    primeiro, segundo = conteudo.blocos
    assert primeiro.inicio_s == 0
    assert primeiro.fim_s == pytest.approx(4.0), "10 palavras a 2,5 por segundo"
    assert segundo.inicio_s == primeiro.fim_s, "as cenas são consecutivas, sem buraco"
    assert segundo.fim_s - segundo.inicio_s == pytest.approx(design.TEMPOS["duracao_minima_da_cena_s"])
    assert segundo.efeito is EfeitoDeCena.NENHUM, "contagem só vale em dado_grande"


def test_cronometrar_higieniza_a_primeira_cena_e_o_atraso_do_texto() -> None:
    blocos = design.cronometrar(
        [
            _bloco(entrada=TransicaoDeEntrada.ZOOM, som_de_entrada=SomDeCena.WHOOSH, texto_entra_em_s=9.0),
            _bloco(),
        ]
    )

    assert blocos[0].entrada is TransicaoDeEntrada.CORTE
    assert blocos[0].som_de_entrada is None
    assert blocos[0].texto_entra_em_s <= blocos[0].fim_s - blocos[0].inicio_s - 1.0 + 1e-9


# ---------------------------------------------------------------------------
# 3 — o plano de edição
# ---------------------------------------------------------------------------


def test_o_plano_e_autocontido_e_versionado() -> None:
    plano = montar_plano(_roteiro(60), Audiencia.INICIANTE)

    assert plano["esquema"] == "suno.roteiro-de-video"
    assert plano["versao"] == "1"
    assert plano["design_system"]["cores"] == design.CORES
    assert plano["video"]["duracao_alvo_s"] == 60
    assert (plano["video"]["largura_px"], plano["video"]["altura_px"]) == (1080, 1920)
    assert plano["avatar"]["voz"]["idioma"] == "pt-BR"
    assert [c["ordem"] for c in plano["cenas"]] == [1, 2, 3]
    json.dumps(plano, ensure_ascii=False)  # serializável sem adaptador


def test_o_plano_traz_tempos_absolutos_sons_e_o_que_o_avatar_faz() -> None:
    plano = montar_plano(_roteiro(), Audiencia.AVANCADO)
    gancho, dado, lista = plano["cenas"]

    assert gancho["avatar"] == {"visivel": True, "posicao": "centro", "escala": 1.0}
    assert dado["avatar"]["posicao"] == "canto_inferior_direito"
    assert gancho["entrada"] == {"transicao": "corte", "duracao_s": 0.0}
    assert dado["entrada"]["duracao_s"] == design.TEMPOS["transicao_s"]
    assert dado["texto_na_tela"]["aparece_em_s"] == pytest.approx(dado["inicio_s"] + 0.5)
    assert [s["nome"] for s in dado["sons"]] == ["whoosh", "ding"]
    assert dado["sons"][0]["em_s"] == dado["inicio_s"]
    assert lista["texto_na_tela"]["partes"] == ["Inflação", "Atividade"]
    assert gancho["icone"]["nome"] == "pergunta"
    assert plano["video"]["duracao_estimada_s"] == lista["fim_s"]


def test_plano_de_conteudo_que_nao_e_roteiro_e_recusado() -> None:
    texto = Conteudo(formato=Formato.TEXTO_ANALITICO, texto="x")

    with pytest.raises(ValueError, match="Roteiro"):
        montar_plano(texto, Audiencia.INICIANTE)


def test_o_markdown_do_plano_tem_uma_linha_por_cena() -> None:
    markdown = plano_em_markdown(montar_plano(_roteiro(), Audiencia.INTERMEDIARIO))

    linhas = [linha for linha in markdown.splitlines() if linha.startswith("| ") and linha[2].isdigit()]
    assert len(linhas) == 3
    assert "dado_grande" in markdown and "whoosh em" in markdown


def test_roteiro_antigo_sem_direcao_continua_valido() -> None:
    """Uma Execução gravada antes da direção de cena abre, e vira plano com os padrões."""
    antigo = {"formato": "roteiro", "blocos": [{"inicio_s": 0, "fim_s": 2, "fala": "Oi.", "tela": "A"}]}

    conteudo = Conteudo.model_validate(antigo)
    plano = montar_plano(conteudo, Audiencia.INICIANTE)

    assert conteudo.duracao_alvo_s is None
    assert plano["cenas"][0]["tipo"] == "texto_destaque"
    assert plano["cenas"][0]["efeito"] == "nenhum"


# ---------------------------------------------------------------------------
# 4 — o quadro e a transição
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("icone", list(IconeDeCena))
def test_todo_icone_desenha_alguma_coisa(icone: IconeDeCena) -> None:
    vazio = compor_quadro(_bloco(tela="", fala="x"), Audiencia.INICIANTE, 0.0)
    com_icone = compor_quadro(_bloco(tela="", fala="x", icone=icone), Audiencia.INICIANTE, 0.0)

    assert ImageChops.difference(vazio, com_icone).getbbox() is not None


@pytest.mark.parametrize("cena", list(TipoDeCena))
@pytest.mark.parametrize("animacao", list(AnimacaoDoTexto))
def test_toda_cena_e_animacao_compoem_um_quadro_9_16(cena, animacao) -> None:
    bloco = _bloco(tela="Primeiro ponto | Segundo ponto", cena=cena, texto_anima=animacao, icone=IconeDeCena.LUPA)

    for tempo in (0.2, None):
        quadro = compor_quadro(bloco, Audiencia.AVANCADO, 0.3, tempo)
        assert quadro.size == (LARGURA_VIDEO, ALTURA_VIDEO)


@pytest.mark.parametrize("efeito", list(EfeitoDeCena))
def test_todo_efeito_compoe_um_quadro_9_16(efeito) -> None:
    bloco = _bloco(tela="Selic a 14,50%", cena=TipoDeCena.DADO_GRANDE, efeito=efeito)

    for tempo in (0.0, 0.6, 2.0):
        assert compor_quadro(bloco, Audiencia.INICIANTE, 0.5, tempo).size == (1080, 1920)


def test_o_texto_aparece_so_depois_do_atraso() -> None:
    bloco = _bloco(tela="Selic cai", texto_entra_em_s=1.0, texto_anima=AnimacaoDoTexto.APARECER)

    antes = compor_quadro(bloco, Audiencia.INICIANTE, 0.0, 0.5)
    sem_tela = compor_quadro(bloco.model_copy(update={"tela": ""}), Audiencia.INICIANTE, 0.0, 0.5)
    depois = compor_quadro(bloco, Audiencia.INICIANTE, 0.0, 1.6)

    assert ImageChops.difference(antes, sem_tela).getbbox() is None, "antes do atraso, nada da rubrica"
    assert ImageChops.difference(depois, sem_tela).getbbox() is not None


def test_a_contagem_chega_ao_valor_da_ancora() -> None:
    from suno.video.render import _contar_numero

    assert _contar_numero("14,50% a.a.", 0.0).startswith("0,00%")
    assert _contar_numero("14,50% a.a.", 1.0) == "14,50% a.a."
    assert _contar_numero("sem número", 0.3) == "sem número"
    meio = _contar_numero("14,50%", 0.5)
    assert 0 < float(meio.rstrip("%").replace(",", ".")) < 14.5


@pytest.mark.parametrize("transicao", list(TransicaoDeEntrada))
def test_toda_transicao_vai_da_cena_anterior_a_nova(transicao) -> None:
    anterior = compor_quadro(_bloco(tela="ANTES"), Audiencia.INICIANTE, 0.0)
    atual = compor_quadro(_bloco(tela="DEPOIS", cena=TipoDeCena.GANCHO), Audiencia.INICIANTE, 0.0)

    meio = compor_transicao(anterior, atual, transicao, 0.5)

    assert meio.size == (LARGURA_VIDEO, ALTURA_VIDEO)
    assert ImageChops.difference(compor_transicao(anterior, atual, transicao, 1.0), atual).getbbox() is None
    if transicao is not TransicaoDeEntrada.CORTE:
        assert ImageChops.difference(meio, atual).getbbox() is not None


# ---------------------------------------------------------------------------
# 5 — os sons
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("som", list(SomDeCena))
def test_todo_som_e_sintetizado_e_determinístico(som: SomDeCena) -> None:
    amostras = sons.amostras_do_som(som)

    assert len(amostras) == round(design.SONS[som].duracao_s * sons.TAXA)
    assert max(abs(a) for a in amostras) <= design.SONS[som].volume + 1e-9
    assert amostras == sons.amostras_do_som(som)


def test_a_trilha_de_efeitos_tem_a_duracao_do_video(tmp_path: Path) -> None:
    marcas = sons.marcas_dos_blocos(_roteiro().blocos)

    destino = sons.trilha_de_efeitos(marcas, 10.0, tmp_path / "efeitos.wav")

    assert destino is not None
    with wave.open(str(destino)) as arquivo:
        assert arquivo.getnframes() == 10 * sons.TAXA
    assert sons.trilha_de_efeitos([], 10.0, tmp_path / "nada.wav") is None


# ---------------------------------------------------------------------------
# 6 — do disco ao plano, e ao mp4
# ---------------------------------------------------------------------------


def _gravar(pasta: Path, conteudo: Conteudo, destino: Destino) -> None:
    celula = Celula(audiencia=Audiencia.INICIANTE, formato=Formato.ROTEIRO, conteudo=conteudo)
    laudo = Laudo(
        audiencia=celula.audiencia,
        formato=celula.formato,
        medidas=[Medida(metrica=Metrica.ADERENCIA, valor=1.0, atingiu=True)],
        destino=Destino.APROVADO,
    )
    historico = HistoricoCelula(
        audiencia=celula.audiencia,
        formato=celula.formato,
        tentativas=[Tentativa(rodada=0, celula=celula, laudo=laudo)],
        destino_final=destino,
        provedores_usados=["falso"],
    )
    execucao = Execucao(
        identificador=IDENTIFICADOR,
        ata="copom-280-2026-08-05",
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        ancoras=Ancoras(ata="copom-280-2026-08-05"),
        celulas=[historico],
    )
    raiz = pasta / IDENTIFICADOR
    raiz.mkdir(parents=True, exist_ok=True)
    (raiz / "execucao.json").write_text(execucao.model_dump_json(indent=2), encoding="utf-8")


def test_o_plano_do_roteiro_aprovado_vai_para_a_pasta_do_pacote(tmp_path: Path) -> None:
    _gravar(tmp_path, _roteiro(90), Destino.APROVADO)

    caminho = plano_do_roteiro(IDENTIFICADOR, Audiencia.INICIANTE, tmp_path)

    assert caminho == tmp_path / IDENTIFICADOR / "pacote" / "iniciante-roteiro" / "plano.json"
    assert json.loads(caminho.read_text(encoding="utf-8"))["video"]["duracao_alvo_s"] == 90
    assert caminho.with_suffix(".md").exists()


def test_roteiro_reprovado_nao_tem_plano(tmp_path: Path) -> None:
    _gravar(tmp_path, _roteiro(), Destino.REPROVADO_REVISAO_HUMANA)

    with pytest.raises(ValueError, match="Roteiro aprovado"):
        plano_do_roteiro(IDENTIFICADOR, Audiencia.INICIANTE, tmp_path)


def test_o_mp4_segue_a_direcao_e_cabe_na_faixa_da_duracao_escolhida(tmp_path: Path) -> None:
    pytest.importorskip("imageio_ffmpeg")
    from suno.video.render import medir_video, renderizar_video

    conteudo = _roteiro(40)
    _gravar(tmp_path, conteudo, Destino.APROVADO)

    caminho = renderizar_video(IDENTIFICADOR, Audiencia.INICIANTE, tmp_path)

    medicoes = medir_video(caminho, duracao_alvo_s=40)
    duracao = next(m for m in medicoes if "duração" in m.detalhe)
    assert duracao.valor == pytest.approx(conteudo.blocos[-1].fim_s, abs=0.6)
    assert next(m for m in medicoes if m.detalhe.startswith("1080x1920")).defeito is None
    # 40s de alvo, ~12s de vídeo: fora da faixa, e a medição acusa com o alvo certo.
    assert duracao.defeito is not None
    assert "30–50s" in duracao.detalhe


# ---------------------------------------------------------------------------
# 7 — a API: a duração escolhida e o plano de edição
# ---------------------------------------------------------------------------


def _cliente_da_api(pasta: Path, executor=None):
    from fastapi.testclient import TestClient

    from suno.api.app import criar_app
    from tests.test_geracao import PASTA_ATAS

    fontes = pasta.parent / f"{pasta.name}-fontes"
    return TestClient(criar_app(pasta, pasta_atas=PASTA_ATAS, pasta_fontes=fontes, executar_fn=executor))


@pytest.mark.parametrize("duracao", ["40", "60", "90", "120", "180"])
def test_a_duracao_escolhida_chega_ate_o_executor(tmp_path: Path, duracao: str) -> None:
    from tests.test_api_geracao import CORPO
    from tests.test_geracao import ExecutorFalso

    executor = ExecutorFalso()
    cliente = _cliente_da_api(tmp_path, executor)

    resposta = cliente.post("/api/execucoes", json={**CORPO, "duracao": duracao})

    assert resposta.status_code == 202
    assert cliente.app.state.gerenciador.aguardar_ocioso()
    assert executor.chamadas[0]["duracao"] is DuracaoDoVideo(duracao)


def test_sem_escolha_a_duracao_e_um_minuto(tmp_path: Path) -> None:
    from tests.test_api_geracao import CORPO
    from tests.test_geracao import ExecutorFalso

    executor = ExecutorFalso()
    cliente = _cliente_da_api(tmp_path, executor)

    cliente.post("/api/execucoes", json=CORPO)

    assert cliente.app.state.gerenciador.aguardar_ocioso()
    assert executor.chamadas[0]["duracao"] is DuracaoDoVideo.S60


def test_duracao_que_nao_existe_e_422(tmp_path: Path) -> None:
    from tests.test_api_geracao import CORPO

    resposta = _cliente_da_api(tmp_path).post("/api/execucoes", json={**CORPO, "duracao": "45"})

    assert resposta.status_code == 422


def test_a_rota_do_plano_devolve_json_e_markdown_do_roteiro_aprovado(tmp_path: Path) -> None:
    _gravar(tmp_path, _roteiro(60), Destino.APROVADO)

    resposta = _cliente_da_api(tmp_path).get(f"/api/execucoes/{IDENTIFICADOR}/celulas/iniciante/roteiro/plano")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["plano"]["esquema"] == "suno.roteiro-de-video"
    assert len(corpo["plano"]["cenas"]) == 3
    assert corpo["markdown"].startswith("# Plano de edição")


def test_a_rota_do_plano_recusa_roteiro_reprovado_e_audiencia_sem_roteiro(tmp_path: Path) -> None:
    _gravar(tmp_path, _roteiro(), Destino.REPROVADO_REVISAO_HUMANA)
    cliente = _cliente_da_api(tmp_path)

    assert cliente.get(f"/api/execucoes/{IDENTIFICADOR}/celulas/iniciante/roteiro/plano").status_code == 409
    assert cliente.get(f"/api/execucoes/{IDENTIFICADOR}/celulas/avancado/roteiro/plano").status_code == 404
