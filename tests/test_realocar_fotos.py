"""Foto achada vai para um slide que comporte foto; sem lugar, sai (e o crédito sai junto)."""

from __future__ import annotations

from pathlib import Path

from suno.dominio import FamiliaVisual, Slide, TipoSlide
from suno.imagens import ImagemResolvida
from suno.pacote.direcao_de_arte import CATALOGO_DE_LAYOUTS, planejar_direcao_de_arte
from suno.pacote.fotos import FotoDoSlide, acomodar_fotos

FAMILIA = FamiliaVisual.DADOS


class Plano:
    def __init__(self, escolhas) -> None:
        self.escolhas = escolhas


def planejar(lista: list[Slide]) -> Plano:
    return Plano(planejar_direcao_de_arte(lista, familia=FAMILIA))


def foto(assunto: str) -> FotoDoSlide:
    imagem = ImagemResolvida(
        arquivo=Path(f"{assunto}.jpg"), titulo=assunto, autor="site.com", licenca="x",
        url_origem="https://site.com", consulta=assunto, origem="web", validada_por="texto",
    )
    return FotoDoSlide(imagem=imagem, caminho=Path(f"{assunto}.jpg"))


def slide(tipo: TipoSlide, titulo: str, **campos) -> Slide:
    return Slide(tipo=tipo, titulo=titulo, corpo="Um texto de apoio com algumas palavras para o slide.", **campos)


def usa_foto(plano: Plano, indice: int) -> bool:
    return CATALOGO_DE_LAYOUTS[plano.escolhas[indice].composicao].usa_imagem


def test_foto_que_cabe_no_slide_que_a_pediu_fica_onde_esta():
    slides = [
        slide(TipoSlide.HOOK, "A pergunta"),
        slide(TipoSlide.PONTO, "A sede", imagem="sede B3"),
        slide(TipoSlide.CTA, "Leia a Ata"),
    ]
    resultado = acomodar_fotos(slides, {1: foto("sede B3")}, FAMILIA, planejar)
    assert set(resultado.fotos) == {1} and resultado.movidas == [] and resultado.descartadas == []
    assert usa_foto(resultado.plano, 1)


def test_slide_sem_foto_recebe_layout_que_nao_precisa_de_foto():
    slides = [
        slide(TipoSlide.HOOK, "A pergunta", imagem="algo sem foto"),
        slide(TipoSlide.PONTO, "O ponto", imagem="outro sem foto"),
        slide(TipoSlide.CTA, "Leia a Ata"),
    ]
    resultado = acomodar_fotos(slides, {}, FAMILIA, planejar)
    assert resultado.fotos == {}
    assert all(not usa_foto(resultado.plano, i) for i in range(3))
    assert all(s.imagem is None for s in resultado.slides)  # o plano não vê assunto sem foto


def test_foto_do_cta_que_nao_aceita_foto_vai_para_um_slide_que_aceita():
    slides = [
        slide(TipoSlide.HOOK, "A pergunta"),
        slide(TipoSlide.PONTO, "Primeiro ponto"),
        slide(TipoSlide.PONTO, "Segundo ponto"),
        slide(TipoSlide.CTA, "Leia a Ata", imagem="sede B3"),
    ]
    resultado = acomodar_fotos(slides, {3: foto("sede B3")}, FAMILIA, planejar)
    assert resultado.movidas == [(3, 2)], "vai para o slide mais próximo que aceita foto"
    assert set(resultado.fotos) == {2} and usa_foto(resultado.plano, 2)
    assert resultado.slides[3].imagem is None and resultado.slides[2].imagem == "sede B3"
    assert resultado.descartadas == []


def test_foto_do_slide_de_grafico_e_realocada():
    slides = [
        slide(TipoSlide.HOOK, "A pergunta"),
        slide(TipoSlide.PONTO, "O número", dado="selic_decidida", imagem="Banco Central"),
        slide(TipoSlide.PONTO, "O contexto"),
        slide(TipoSlide.CTA, "Leia a Ata"),
    ]
    resultado = acomodar_fotos(slides, {1: foto("Banco Central")}, FAMILIA, planejar)
    assert resultado.movidas == [(1, 2)]
    assert set(resultado.fotos) == {2} and usa_foto(resultado.plano, 2)
    assert not usa_foto(resultado.plano, 1)


def test_sem_nenhum_slide_que_aceite_foto_ela_e_descartada():
    slides = [
        slide(TipoSlide.HOOK, "A pergunta"),
        slide(TipoSlide.PONTO, "O número", dado="selic_decidida", imagem="Banco Central"),
        slide(TipoSlide.CTA, "Leia a Ata"),
    ]
    resultado = acomodar_fotos(slides, {1: foto("Banco Central")}, FAMILIA, planejar)
    assert resultado.fotos == {} and resultado.descartadas == [1]
    assert all(not usa_foto(resultado.plano, i) for i in range(3))
    assert all(s.imagem is None for s in resultado.slides)


def test_duas_fotos_nao_disputam_o_mesmo_slide():
    slides = [
        slide(TipoSlide.PONTO, "Um", imagem="a"),
        slide(TipoSlide.PONTO, "Dois", dado="selic_decidida", imagem="b"),
        slide(TipoSlide.PONTO, "Tres"),
        slide(TipoSlide.CTA, "Leia a Ata"),
    ]
    resultado = acomodar_fotos(slides, {0: foto("a"), 1: foto("b")}, FAMILIA, planejar)
    assert sorted(resultado.fotos) == [0, 2], "a de gráfico vai para o único outro slide que aceita foto"
    assert {f.imagem.consulta for f in resultado.fotos.values()} == {"a", "b"}
    assert all(usa_foto(resultado.plano, i) for i in resultado.fotos)


def test_o_laco_acaba_mesmo_se_o_plano_insistir_em_layout_sem_foto():
    class Teimoso:
        def __call__(self, lista):
            return Plano(planejar_direcao_de_arte(lista, familia=FamiliaVisual.SUNO_ESCURO))  # nenhum layout usa foto

    slides = [slide(TipoSlide.PONTO, "Um", imagem="a"), slide(TipoSlide.PONTO, "Dois"), slide(TipoSlide.CTA, "Fim")]
    resultado = acomodar_fotos(slides, {0: foto("a")}, FamiliaVisual.SUNO_ESCURO, Teimoso())
    assert resultado.fotos == {} and resultado.descartadas
