"""A ligação das famílias visuais ao Pacote: foto resolvida, crédito na legenda, escolha de família."""

from __future__ import annotations

from pathlib import Path

import pytest

from suno.dominio import (
    Audiencia,
    ComposicaoCarrossel,
    Conteudo,
    Celula,
    FamiliaVisual,
    Formato,
    Slide,
    TipoSlide,
)
from suno.imagens import BibliotecaDeImagens
from suno.pacote import carrossel, familias
from suno.pacote.direcao_de_arte import (
    FAMILIAS_AUTOMATICAS,
    escolher_familia,
    planejar_direcao_de_arte,
)
from suno.pacote.fotos import resolver_fotos
from suno.pacote.legenda import montar_legenda
from tests.test_pacote import ancoras  # noqa: F401 - fixture

RAIZ = Path(__file__).resolve().parent.parent
BIBLIOTECA = BibliotecaDeImagens(RAIZ / "data" / "imagens")


def _slides() -> list[Slide]:
    return [
        Slide(tipo=TipoSlide.HOOK, titulo="O que mudou nos juros?", corpo="Veja a decisão do Copom."),
        Slide(
            tipo=TipoSlide.PONTO,
            titulo="A decisão da reunião",
            corpo="O Copom definiu a Selic. Isso guia os outros juros do país.",
            imagem="banco central",
        ),
        Slide(tipo=TipoSlide.CITACAO, titulo="O tom da Ata", corpo="O Comitê vê incerteza. Pede cautela."),
        Slide(tipo=TipoSlide.CTA, titulo="Leia a Ata completa", corpo="Veja o documento no site do BC."),
    ]


# ---------------------------------------------------------------------------
# Fotos: biblioteca local, sem rede
# ---------------------------------------------------------------------------


def test_resolve_a_foto_do_assunto_pela_biblioteca_sem_rede() -> None:
    fotos = resolver_fotos(_slides(), BIBLIOTECA)

    assert set(fotos) == {1}, "só o slide que pediu foto ganha foto"
    foto = fotos[1]
    assert foto.imagem.autor and foto.imagem.licenca
    assert foto.caminho.is_file() and foto.caminho.is_absolute()


def test_assunto_sem_foto_na_biblioteca_nao_quebra_nem_inventa() -> None:
    slide = Slide(tipo=TipoSlide.PONTO, titulo="T", corpo="C", imagem="unicórnio dançando")

    assert resolver_fotos([slide], BIBLIOTECA) == {}


# ---------------------------------------------------------------------------
# Crédito na legenda (CC BY exige)
# ---------------------------------------------------------------------------


def _celula() -> Celula:
    conteudo = Conteudo(formato=Formato.CARROSSEL, slides=_slides(), ancoras_citadas=[])
    return Celula(audiencia=Audiencia.INICIANTE, formato=Formato.CARROSSEL, conteudo=conteudo)


def test_legenda_sem_creditos_fica_como_antes(ancoras) -> None:  # noqa: F811
    legenda, _ = montar_legenda(_celula(), ancoras)
    assert "Foto:" not in legenda
    assert legenda.rstrip().endswith("Não é recomendação de investimento.")


def test_legenda_com_creditos_acrescenta_o_bloco_depois_do_aviso(ancoras) -> None:  # noqa: F811
    legenda, _ = montar_legenda(_celula(), ancoras, creditos="Foto: Fulano / CC BY 2.0 / https://x")
    assert legenda.rstrip().endswith("Foto: Fulano / CC BY 2.0 / https://x")
    assert legenda.index("Não é recomendação") < legenda.index("Foto: Fulano")


# ---------------------------------------------------------------------------
# Escolha de família
# ---------------------------------------------------------------------------


def test_familia_automatica_nunca_inclui_a_asset() -> None:
    assert FamiliaVisual.ASSET not in FAMILIAS_AUTOMATICAS
    assert FamiliaVisual.SUNO_ESCURO not in FAMILIAS_AUTOMATICAS


def test_escolha_de_familia_e_deterministica_e_cobre_todos_os_slides() -> None:
    slides = _slides()
    primeira = escolher_familia(slides, [])
    assert escolher_familia(slides, []) is primeira
    assert primeira in FAMILIAS_AUTOMATICAS or primeira is FamiliaVisual.SUNO_ESCURO


def test_escolha_de_familia_evita_a_mais_usada_no_historico() -> None:
    slides = _slides()
    primeira = escolher_familia(slides, [])
    historico = [layout.composicao.value for layout in familias.layouts_da_familia(primeira)] * 3
    if len({f for f in FAMILIAS_AUTOMATICAS if familias.layouts_da_familia(f)}) < 2:
        pytest.skip("só uma família carregada ainda")

    assert escolher_familia(slides, historico) is not primeira


def test_referencia_escolhida_na_curadoria_define_a_familia() -> None:
    from suno.pacote.referencias_visuais import REFERENCIAS_INICIAIS

    referencia = next(r for r in REFERENCIAS_INICIAIS if r.composicao is ComposicaoCarrossel.EXPLICATIVO_CAPA)

    assert escolher_familia(_slides(), [], referencia_preferida=referencia) is FamiliaVisual.EXPLICATIVO


def test_plano_dentro_de_uma_familia_so_usa_layouts_dela_e_cobre_os_quatro_papeis() -> None:
    plano = planejar_direcao_de_arte(_slides(), familia=FamiliaVisual.EXPLICATIVO)

    assert {familias.familia_da_composicao(e.composicao) for e in plano} == {FamiliaVisual.EXPLICATIVO}
    assert plano[0].composicao is ComposicaoCarrossel.EXPLICATIVO_CAPA
    assert plano[-1].composicao is ComposicaoCarrossel.EXPLICATIVO_TEXTO_ILUSTRACAO


def test_slide_com_foto_prefere_o_layout_de_foto_e_sem_foto_o_de_texto() -> None:
    com_foto = Slide(tipo=TipoSlide.PONTO, titulo="T", corpo="C. D.", imagem="banco central")
    sem_foto = Slide(tipo=TipoSlide.PONTO, titulo="T", corpo="C. D.")

    [a] = planejar_direcao_de_arte([com_foto], familia=FamiliaVisual.EXPLICATIVO)
    [b] = planejar_direcao_de_arte([sem_foto], familia=FamiliaVisual.EXPLICATIVO)

    assert a.composicao is ComposicaoCarrossel.EXPLICATIVO_TEXTO_IMAGEM
    assert b.composicao is ComposicaoCarrossel.EXPLICATIVO_TEXTO


# ---------------------------------------------------------------------------
# O render escolhe o motor: sem Node a reserva Pillow ignora as famílias
# ---------------------------------------------------------------------------


def test_com_a_reserva_pillow_a_familia_e_a_antiga(monkeypatch) -> None:
    monkeypatch.setenv("SUNO_RENDER", "pillow")
    assert carrossel.motor_de_render() == "pillow"


# ---------------------------------------------------------------------------
# De ponta a ponta com o navegador: montar_pacote usa a família, a foto e o crédito
# ---------------------------------------------------------------------------

from suno.dominio import Execucao  # noqa: E402
from suno.pacote import carrossel_html, montar_pacote  # noqa: E402
from tests.test_pacote import IDENTIFICADOR, execucao_em_disco  # noqa: E402,F401
from tests.test_pacote import celula_carrossel, celula_roteiro, celula_texto_analitico  # noqa: E402,F401


def _execucao_com_foto_no_slide_dois(pasta_execucoes: Path) -> None:
    _execucao_com_assunto_no_slide(pasta_execucoes, 1, "banco central")


def _execucao_com_assunto_no_slide(pasta_execucoes: Path, posicao: int, assunto: str) -> None:
    arquivo = pasta_execucoes / IDENTIFICADOR / "execucao.json"
    execucao = Execucao.model_validate_json(arquivo.read_text(encoding="utf-8"))
    historico = next(h for h in execucao.celulas if h.formato is Formato.CARROSSEL)
    tentativa = historico.tentativas[-1]
    slides = [
        slide.model_copy(update={"imagem": assunto}) if indice == posicao else slide
        for indice, slide in enumerate(tentativa.celula.conteudo.slides or [])
    ]
    celula = tentativa.celula.model_copy(
        update={"conteudo": tentativa.celula.conteudo.model_copy(update={"slides": slides})}
    )
    novo = historico.model_copy(
        update={"tentativas": [*historico.tentativas[:-1], tentativa.model_copy(update={"celula": celula})]}
    )
    execucao = execucao.model_copy(
        update={"celulas": [novo if h is historico else h for h in execucao.celulas]}
    )
    arquivo.write_text(execucao.model_dump_json(indent=2), encoding="utf-8")


@pytest.mark.skipif(not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado")
def test_pacote_do_carrossel_usa_familia_foto_e_credito(
    execucao_em_disco: Path, monkeypatch  # noqa: F811
) -> None:
    monkeypatch.setenv("SUNO_RENDER", "puppeteer")
    _execucao_com_foto_no_slide_dois(execucao_em_disco)

    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco, familia_visual=FamiliaVisual.EXPLICATIVO)

    pacote = next(p for p in pacotes if p.formato is Formato.CARROSSEL)
    assert pacote.direcao_de_arte is not None
    assert pacote.direcao_de_arte.familia is FamiliaVisual.EXPLICATIVO
    assert {
        familias.familia_da_composicao(e.composicao) for e in pacote.direcao_de_arte.escolhas
    } == {FamiliaVisual.EXPLICATIVO}
    assert [f.indice for f in pacote.fotos] == [1]
    assert pacote.fotos[0].licenca and pacote.fotos[0].credito.startswith("Foto: ")
    assert pacote.legenda.rstrip().endswith(pacote.fotos[0].credito)
    assert pacote.conferencia.defeitos == []
    # O slide da foto usa o layout de foto; os sem foto não.
    assert pacote.direcao_de_arte.escolhas[1].composicao is ComposicaoCarrossel.EXPLICATIVO_TEXTO_IMAGEM


@pytest.mark.skipif(not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado")
def test_foto_pedida_por_slide_de_grafico_e_realocada_para_um_slide_que_comporta_foto(
    execucao_em_disco: Path, monkeypatch  # noqa: F811
) -> None:
    monkeypatch.setenv("SUNO_RENDER", "puppeteer")
    # Na família Dados, o slide 2 plota uma Âncora: só aceita layout de gráfico, então a foto vai para o slide 1.
    _execucao_com_assunto_no_slide(execucao_em_disco, 1, "banco central")

    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco, familia_visual=FamiliaVisual.DADOS)

    pacote = next(p for p in pacotes if p.formato is Formato.CARROSSEL)
    assert [f.indice for f in pacote.fotos] == [0]
    escolhas = pacote.direcao_de_arte.escolhas
    com_foto = {i for i, e in enumerate(escolhas) if "foto" in e.composicao.value}
    assert pacote.fotos[0].indice in com_foto, "a foto foi parar num slide cujo layout a desenha"
    assert pacote.fotos[0].assunto == "banco central"
    assert pacote.legenda.rstrip().endswith(pacote.fotos[0].credito)
    assert pacote.conferencia.defeitos == []


@pytest.mark.skipif(not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado")
def test_assunto_sem_foto_gera_o_slide_sem_foto_e_sem_credito(
    execucao_em_disco: Path, monkeypatch  # noqa: F811
) -> None:
    monkeypatch.setenv("SUNO_RENDER", "puppeteer")
    _execucao_com_assunto_no_slide(execucao_em_disco, 1, "unicórnio dançando")

    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco, familia_visual=FamiliaVisual.EXPLICATIVO)

    pacote = next(p for p in pacotes if p.formato is Formato.CARROSSEL)
    assert pacote.fotos == [] and "Foto:" not in pacote.legenda
    assert all(
        not e.composicao.value.endswith("imagem") for e in pacote.direcao_de_arte.escolhas
    ), "nenhum slide usa o layout que precisa de foto"
    assert pacote.conferencia.defeitos == []


@pytest.mark.skipif(not carrossel_html.disponivel(), reason="Node/Puppeteer não instalado")
def test_familia_que_nao_cobre_os_papeis_do_carrossel_e_recusada_com_mensagem_clara(
    execucao_em_disco: Path, monkeypatch  # noqa: F811
) -> None:
    monkeypatch.setenv("SUNO_RENDER", "puppeteer")

    with pytest.raises(ValueError, match="asset não tem layout para os papéis: .*ponto"):
        montar_pacote(IDENTIFICADOR, execucao_em_disco, familia_visual=FamiliaVisual.ASSET)


def test_com_a_reserva_pillow_o_pacote_sai_sem_foto_e_sem_familia(execucao_em_disco: Path) -> None:  # noqa: F811
    _execucao_com_foto_no_slide_dois(execucao_em_disco)

    pacotes = montar_pacote(IDENTIFICADOR, execucao_em_disco)

    pacote = next(p for p in pacotes if p.formato is Formato.CARROSSEL)
    assert pacote.fotos == []
    assert "Foto:" not in pacote.legenda
