"""O Pacote de publicação: render determinístico do Carrossel, legenda e conferência visual.

Tudo aqui roda sem rede e sem LLM — matplotlib e Pillow bastam (ADR 0009). A Execução é
construída à mão e gravada em ``tmp_path``: os testes do Pacote não dependem do Gerador, só do
``execucao.json`` que ele grava.

O que estes testes protegem:

- 1080x1350 em todo slide, porque proporção variando estraga o carrossel inteiro (ADR 0009);
- render determinístico, que é o que torna a imagem testável em CI como o Avaliador;
- todo número desenhado saindo de ``AncoraNumerica.citacao()``, nunca de ``str(valor)`` (ADR 0011);
- a conferência visual medindo defeito de render sem reprovar a Célula e sem tocar no
  ``execucao.json`` (ADR 0014).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from suno.dominio import (
    ALTURA_SLIDE,
    LARGURA_SLIDE,
    AncoraNumerica,
    Ancoras,
    Audiencia,
    BlocoFala,
    Celula,
    Conteudo,
    Correcao,
    DefeitoRender,
    Destino,
    Execucao,
    Formato,
    HistoricoCelula,
    ImagemSlide,
    Laudo,
    Medida,
    Metrica,
    MotivoReprovacao,
    PapelLLM,
    ParecerVisao,
    PedidoLLM,
    Slide,
    Tentativa,
    Unidade,
)
from suno.ingestao.numeros import extrair_numeros
from suno.pacote import montar_pacote
from suno.pacote.carrossel import (
    COLUNAS_DA_FOLHA,
    LARGURA_DA_MINIATURA,
    folha_de_contato,
    renderizar_carrossel,
)
from suno.pacote.legenda import AVISO_DE_NAO_RECOMENDACAO, MAXIMO_DE_HASHTAGS, montar_legenda
from suno.pacote.visual import conferir_imagens, julgar_folha_de_contato, razao_de_contraste

IDENTIFICADOR = "copom-280-2026-08-05-0001"
ANO_DA_ATA = 2026

# As Âncoras ficam no módulo (são frozen) para que a forma citada saia sempre de ``citacao()``.
# Nenhum teste escreve a citação à mão: a forma canônica é do domínio, e quando ela muda —
# como mudou de ``14,00 % a.a.`` para ``14,00% a.a.`` — os testes acompanham sozinhos.
ANCORA_DA_SELIC = AncoraNumerica(
    chave="selic_decidida",
    rotulo="Selic decidida",
    valor_literal="14,00",
    valor=14.0,
    unidade=Unidade.PERCENTUAL_AO_ANO,
    trecho="O Copom decidiu reduzir a taxa Selic para 14,00% a.a.",
)
ANCORA_DA_SELIC_ANTERIOR = AncoraNumerica(
    chave="selic_anterior",
    rotulo="Selic anterior",
    valor_literal="14,25",
    valor=14.25,
    unidade=Unidade.PERCENTUAL_AO_ANO,
    trecho="A taxa vinha de 14,25% a.a. desde a reunião anterior.",
)
ANCORA_DO_PLACAR = AncoraNumerica(
    chave="placar_votacao",
    rotulo="Placar da votação",
    valor_literal="7 a 0",
    valor=7.0,
    unidade=Unidade.VOTOS,
    trecho="A decisão foi tomada por 7 votos a 0.",
)

CITACAO_DA_SELIC = ANCORA_DA_SELIC.citacao()
"""A forma canônica, vinda do domínio. Nunca digitada aqui."""

SELIC_DE_OUTRA_REUNIAO = ANCORA_DA_SELIC.model_copy(
    update={"valor_literal": "15,00", "valor": 15.0}
)
"""Um valor que não é o da Âncora, para adulterar o manifesto sem inventar formato de citação."""


# ---------------------------------------------------------------------------
# A Execução mínima, montada à mão
# ---------------------------------------------------------------------------


@pytest.fixture
def ancoras() -> Ancoras:
    return Ancoras(
        ata="copom-280-2026-08-05",
        numericas=[ANCORA_DA_SELIC, ANCORA_DA_SELIC_ANTERIOR, ANCORA_DO_PLACAR],
    )


@pytest.fixture
def celula_carrossel() -> Celula:
    corpo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[
            Slide(
                titulo="O Copom baixou os juros",
                corpo="A taxa básica da economia caiu nesta reunião. Veja o que isso muda.",
            ),
            Slide(
                titulo="De quanto foi a queda",
                corpo="A taxa anterior e a nova taxa, lado a lado.",
                dado="selic_decidida",
            ),
            Slide(
                titulo="Como foi a votação",
                corpo="A decisão saiu por unanimidade entre os membros do comitê.",
                dado="placar_votacao",
            ),
        ],
        ancoras_citadas=["selic_decidida", "selic_anterior", "placar_votacao"],
    )
    return Celula(audiencia=Audiencia.INICIANTE, formato=Formato.CARROSSEL, conteudo=corpo)


@pytest.fixture
def celula_texto_analitico() -> Celula:
    corpo = Conteudo(
        formato=Formato.TEXTO_ANALITICO,
        texto=(
            f"O Copom levou a Selic a {CITACAO_DA_SELIC}. A decisão foi unânime entre os"
            " membros do comitê.\n\nO comunicado manteve a leitura de que a inflação segue"
            " acima do centro da faixa perseguida."
        ),
        ancoras_citadas=["selic_decidida"],
    )
    return Celula(
        audiencia=Audiencia.INTERMEDIARIO, formato=Formato.TEXTO_ANALITICO, conteudo=corpo
    )


@pytest.fixture
def celula_roteiro() -> Celula:
    corpo = Conteudo(
        formato=Formato.ROTEIRO,
        blocos=[
            BlocoFala(inicio_s=0, fim_s=6, fala="Os juros caíram e isso mexe com o seu bolso."),
            BlocoFala(inicio_s=6, fim_s=20, fala="O comitê reduziu a taxa básica da economia."),
        ],
    )
    return Celula(audiencia=Audiencia.AVANCADO, formato=Formato.ROTEIRO, conteudo=corpo)


def _laudo(celula: Celula, destino: Destino) -> Laudo:
    medidas = [
        Medida(metrica=Metrica.ADERENCIA, valor=1.0, atingiu=destino is Destino.APROVADO),
    ]
    if destino is Destino.APROVADO:
        return Laudo(
            audiencia=celula.audiencia, formato=celula.formato, medidas=medidas, destino=destino
        )
    return Laudo(
        audiencia=celula.audiencia,
        formato=celula.formato,
        medidas=medidas,
        destino=destino,
        motivos=[MotivoReprovacao.FLESCH_BR],
        correcoes=[
            Correcao(
                metrica=Metrica.FLESCH_BR,
                valor_medido=18.0,
                faixa=None,
                distancia=7.0,
                instrucao="Flesch-BR medido 18,0; o Limiar da Audiência Avançado é outro.",
            )
        ],
    )


def _historico(celula: Celula, destino: Destino) -> HistoricoCelula:
    return HistoricoCelula(
        audiencia=celula.audiencia,
        formato=celula.formato,
        tentativas=[Tentativa(rodada=0, celula=celula, laudo=_laudo(celula, destino))],
        destino_final=destino,
        provedores_usados=["falso"],
    )


@pytest.fixture
def execucao_em_disco(
    pasta_execucoes: Path,
    ancoras: Ancoras,
    celula_carrossel: Celula,
    celula_texto_analitico: Celula,
    celula_roteiro: Celula,
) -> Path:
    """Grava o ``execucao.json`` à mão e devolve a pasta das execuções.

    Duas Células aprovadas e uma reprovada: é o cenário que separa "quem ganha Pacote" de
    "quem não ganha".
    """
    execucao = Execucao(
        identificador=IDENTIFICADOR,
        ata="copom-280-2026-08-05",
        provedor_gerador="falso",
        iniciada_em=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        concluida_em=datetime(2026, 8, 6, 12, 4, tzinfo=timezone.utc),
        ancoras=ancoras,
        celulas=[
            _historico(celula_carrossel, Destino.APROVADO),
            _historico(celula_texto_analitico, Destino.APROVADO),
            _historico(celula_roteiro, Destino.REPROVADO_CORRIGIVEL),
        ],
    )
    pasta = pasta_execucoes / IDENTIFICADOR
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "execucao.json").write_text(execucao.model_dump_json(indent=2), encoding="utf-8")
    return pasta_execucoes


def _manifesto(imagem: ImagemSlide) -> dict:
    return json.loads(Path(imagem.caminho).with_suffix(".json").read_text(encoding="utf-8"))


def _regravar_manifesto(imagem: ImagemSlide, manifesto: dict) -> None:
    Path(imagem.caminho).with_suffix(".json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _defeitos(conferencia) -> list[DefeitoRender]:
    return [medicao.defeito for medicao in conferencia.defeitos]


# ---------------------------------------------------------------------------
# 1 e 2 — dimensão exata e determinismo
# ---------------------------------------------------------------------------


def test_todo_slide_sai_em_1080x1350(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    imagens = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "render")

    assert len(imagens) == 3
    for imagem in imagens:
        with Image.open(imagem.caminho) as aberta:
            assert aberta.size == (LARGURA_SLIDE, ALTURA_SLIDE)
        assert (imagem.largura, imagem.altura) == (1080, 1350)


def test_duas_renderizacoes_dao_os_mesmos_pixels(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    """Sem data e sem aleatório: é o que deixa a imagem testável em CI (ADR 0009)."""
    primeira = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "um")
    segunda = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "dois")

    for antes, depois in zip(primeira, segunda):
        with Image.open(antes.caminho) as uma, Image.open(depois.caminho) as outra:
            assert ImageChops.difference(uma.convert("RGB"), outra.convert("RGB")).getbbox() is None


# ---------------------------------------------------------------------------
# 3 — número desenhado contra as Âncoras
# ---------------------------------------------------------------------------


def test_o_numero_do_grafico_sai_da_citacao_da_ancora(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    imagens = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "render")
    manifesto = _manifesto(imagens[1])
    desenhados = {numero["chave"]: numero["texto"] for numero in manifesto["numeros"]}

    assert desenhados["selic_decidida"] == ANCORA_DA_SELIC.citacao()
    assert desenhados["selic_anterior"] == ANCORA_DA_SELIC_ANTERIOR.citacao()
    # E nunca a forma que sairia de ``str(valor)``: o número é copiado, não reescrito (ADR 0011).
    assert str(ANCORA_DA_SELIC.valor) not in desenhados["selic_decidida"]
    assert DefeitoRender.NUMERO_DIVERGENTE not in _defeitos(conferir_imagens(imagens, ancoras))


def test_numero_adulterado_no_manifesto_vira_numero_divergente(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    imagens = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "render")
    manifesto = _manifesto(imagens[1])
    for numero in manifesto["numeros"]:
        if numero["chave"] == "selic_decidida":
            numero["texto"] = SELIC_DE_OUTRA_REUNIAO.citacao()
    _regravar_manifesto(imagens[1], manifesto)

    conferencia = conferir_imagens(imagens, ancoras)

    assert DefeitoRender.NUMERO_DIVERGENTE in _defeitos(conferencia)
    assert conferencia.precisa_refazer_render


# ---------------------------------------------------------------------------
# 4 e 5 — estouro de caixa e contraste
# ---------------------------------------------------------------------------


def test_titulo_de_300_caracteres_estoura_a_caixa(tmp_path: Path, ancoras: Ancoras) -> None:
    """A quebra controla a largura; a altura reservada é o que denuncia o texto longo demais."""
    titulo_longo = ("decisão do comitê de política monetária " * 10)[:300]
    corpo = Conteudo(
        formato=Formato.CARROSSEL,
        slides=[Slide(titulo=titulo_longo, corpo="Um corpo curto.")],
    )
    celula = Celula(audiencia=Audiencia.INICIANTE, formato=Formato.CARROSSEL, conteudo=corpo)

    imagens = renderizar_carrossel(celula, ancoras, tmp_path / "render")
    conferencia = conferir_imagens(imagens, ancoras)

    estouros = [m for m in conferencia.defeitos if m.defeito is DefeitoRender.ESTOURO_DE_CAIXA]
    assert estouros, "um título de 300 caracteres tem de estourar a caixa reservada"
    assert any("titulo" in medicao.detalhe for medicao in estouros)
    assert conferencia.precisa_refazer_render


def test_a_paleta_padrao_passa_no_contraste_e_a_cor_apagada_nao(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    imagens = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "render")

    assert DefeitoRender.CONTRASTE_BAIXO not in _defeitos(conferir_imagens(imagens, ancoras))

    manifesto = _manifesto(imagens[0])
    for caixa in manifesto["caixas"]:
        if caixa["nome"] == "corpo":
            caixa["cor"] = "#141B28"  # quase o fundo: razão perto de 1
    _regravar_manifesto(imagens[0], manifesto)

    conferencia = conferir_imagens(imagens, ancoras)

    assert DefeitoRender.CONTRASTE_BAIXO in _defeitos(conferencia)
    assert razao_de_contraste("#141B28", "#0E1420") < 4.5


# ---------------------------------------------------------------------------
# 6 — folha de contato
# ---------------------------------------------------------------------------


def test_folha_de_contato_reune_os_tres_slides(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    """Uma imagem só por Célula: três chamadas de visão por Ata em vez de dezoito (ADR 0014)."""
    imagens = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "render")

    caminho = folha_de_contato(imagens, tmp_path / "folha-de-contato.png")

    assert caminho.exists()
    with Image.open(caminho) as folha:
        assert folha.width >= COLUNAS_DA_FOLHA * LARGURA_DA_MINIATURA
        assert folha.height >= round(LARGURA_DA_MINIATURA * ALTURA_SLIDE / LARGURA_SLIDE)


# ---------------------------------------------------------------------------
# 7 — legenda e hashtags
# ---------------------------------------------------------------------------


def test_legenda_cita_a_selic_avisa_que_nao_recomenda_e_nao_inventa_numero(
    celula_texto_analitico: Celula, ancoras: Ancoras
) -> None:
    legenda, hashtags = montar_legenda(celula_texto_analitico, ancoras)

    assert CITACAO_DA_SELIC in legenda
    assert "Não é recomendação" in legenda
    assert legenda.rstrip().endswith(AVISO_DE_NAO_RECOMENDACAO)

    das_ancoras = {(a.valor_literal, a.unidade) for a in ancoras.numericas}
    achados = extrair_numeros(legenda, ano_padrao=ANO_DA_ATA)
    assert achados, "a legenda abre com a decisão, então tem pelo menos um número"
    for achado in achados:
        assert (achado.literal, achado.unidade) in das_ancoras

    assert 0 < len(hashtags) <= MAXIMO_DE_HASHTAGS
    assert len(set(hashtags)) == len(hashtags)
    assert all(etiqueta.startswith("#") for etiqueta in hashtags)


def test_hashtags_mudam_com_a_audiencia(
    celula_carrossel: Celula, celula_texto_analitico: Celula, ancoras: Ancoras
) -> None:
    _, do_iniciante = montar_legenda(celula_carrossel, ancoras)
    _, do_intermediario = montar_legenda(celula_texto_analitico, ancoras)

    assert "#educacaofinanceira" in do_iniciante
    assert do_iniciante != do_intermediario


# ---------------------------------------------------------------------------
# 8 e 9 — montar_pacote
# ---------------------------------------------------------------------------


def test_montar_pacote_so_atende_celula_aprovada_e_nao_toca_na_execucao(
    execucao_em_disco: Path,
) -> None:
    caminho_da_execucao = execucao_em_disco / IDENTIFICADOR / "execucao.json"
    antes = caminho_da_execucao.read_bytes()

    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco)

    assert len(pacotes) == 2, "as três Células viraram dois Pacotes: a reprovada não ganha um"
    formatos = {pacote.formato for pacote in pacotes}
    assert formatos == {Formato.CARROSSEL, Formato.TEXTO_ANALITICO}
    assert Formato.ROTEIRO not in formatos

    raiz = execucao_em_disco / IDENTIFICADOR / "pacote"
    assert (raiz / "iniciante-carrossel" / "pacote.json").exists()
    assert (raiz / "intermediario-texto_analitico" / "pacote.json").exists()
    assert (raiz / "intermediario-texto_analitico" / "texto.md").exists()
    assert not (raiz / "avancado-roteiro").exists()

    assert caminho_da_execucao.read_bytes() == antes, "montar o Pacote é leitura, nunca escrita"


def test_pacote_do_carrossel_traz_imagens_folha_e_conferencia_limpa(
    execucao_em_disco: Path,
) -> None:
    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco)
    do_carrossel = next(p for p in pacotes if p.formato is Formato.CARROSSEL)

    assert len(do_carrossel.imagens) == 3
    assert do_carrossel.folha_de_contato is not None
    assert Path(do_carrossel.folha_de_contato).exists()
    assert do_carrossel.video is None
    assert do_carrossel.conferencia.juiz_visao is None
    assert do_carrossel.conferencia.defeitos == []
    assert not do_carrossel.conferencia.precisa_refazer_render
    assert not do_carrossel.aprovado_por_humano


def test_pacote_do_texto_analitico_grava_o_markdown_e_a_legenda(
    execucao_em_disco: Path,
) -> None:
    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco)
    do_texto = next(p for p in pacotes if p.formato is Formato.TEXTO_ANALITICO)
    pasta = execucao_em_disco / IDENTIFICADOR / "pacote" / "intermediario-texto_analitico"

    assert CITACAO_DA_SELIC in (pasta / "texto.md").read_text(encoding="utf-8")
    assert AVISO_DE_NAO_RECOMENDACAO in (pasta / "legenda.txt").read_text(encoding="utf-8")
    assert do_texto.imagens == []
    assert do_texto.folha_de_contato is None


def test_pacote_json_gravado_volta_a_virar_pacote_publicacao(execucao_em_disco: Path) -> None:
    """O disco é a fonte da interface e do pytest: o que foi gravado tem de reabrir."""
    from suno.dominio import PacotePublicacao

    montar_pacote(IDENTIFICADOR, execucao_em_disco)
    caminho = (
        execucao_em_disco / IDENTIFICADOR / "pacote" / "iniciante-carrossel" / "pacote.json"
    )

    relido = PacotePublicacao.model_validate_json(caminho.read_text(encoding="utf-8"))

    assert relido.execucao == IDENTIFICADOR
    assert relido.audiencia is Audiencia.INICIANTE
    assert len(relido.imagens) == 3
    assert relido.hashtags


def test_renderizar_carrossel_recusa_outro_formato(
    tmp_path: Path, celula_roteiro: Celula, ancoras: Ancoras
) -> None:
    with pytest.raises(ValueError, match="Carrossel"):
        renderizar_carrossel(celula_roteiro, ancoras, tmp_path / "render")


# ---------------------------------------------------------------------------
# O juiz de visão: montado, desligado (ADR 0014, abaixo da linha)
# ---------------------------------------------------------------------------


class ProvedorDeMentira:
    """Guarda o pedido em vez de falar com alguém: o teste roda sem rede e sem chave."""

    nome = "mentira"

    def __init__(self) -> None:
        self.pedidos: list[PedidoLLM] = []

    def completar(self, pedido: PedidoLLM):  # pragma: no cover - o juiz usa o estruturado
        raise AssertionError("o juiz de visão pede saída estruturada")

    def completar_estruturado(self, pedido: PedidoLLM, modelo):
        self.pedidos.append(pedido)
        return modelo(parece_quebrado=False, observacoes=[], provedor=self.nome)


def test_o_juiz_de_visao_monta_o_pedido_com_a_imagem_e_nao_julga_recomendacao(
    tmp_path: Path, celula_carrossel: Celula, ancoras: Ancoras
) -> None:
    imagens = renderizar_carrossel(celula_carrossel, ancoras, tmp_path / "render")
    caminho = folha_de_contato(imagens, tmp_path / "folha-de-contato.png")
    provedor = ProvedorDeMentira()

    parecer = julgar_folha_de_contato(caminho, provedor)

    assert isinstance(parecer, ParecerVisao)
    pedido = provedor.pedidos[0]
    assert pedido.papel is PapelLLM.JUIZ_VISAO
    assert pedido.mensagens[-1].imagem_png == caminho.read_bytes()
    assert "NUNCA julga" in pedido.mensagens[0].texto
