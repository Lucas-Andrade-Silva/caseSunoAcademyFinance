"""Renderiza TODOS os layouts de uma família com o motor real e o texto no tamanho do Gerador.

Uso (da raiz do projeto, com o venv):
  .venv\\Scripts\\python.exe templates\\recriados\\_ferramentas\\galeria_familia.py <familia> [--saida arquivo.jpg]

Para cada layout renderiza: o caso normal (com foto, se o layout usa), o caso SEM foto (a degradação
``sem-imagem``) e um caso de texto LONGO (o encolhimento até caber). Layouts que exigem dado usam uma
Âncora real da Selic. Também imprime os defeitos da conferência visual (estouro, contraste, dimensão).
O resultado é a folha de contato: é por ela que se julga o layout, não pelo texto de exemplo do HTML.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "src"))

from suno.dominio import (  # noqa: E402
    Ancoras,
    AncoraNumerica,
    Audiencia,
    EscolhaDeLayout,
    FamiliaVisual,
    ImagemSlide,
    Slide,
    TipoSlide,
    Unidade,
)
from suno.pacote import carrossel_html, familias  # noqa: E402
from suno.pacote.visual import conferir_imagens  # noqa: E402

FOTOS = ["bcb-sede", "mercado-imobiliario", "bolsa-sp", "pregao", "analise", "dinheiro"]

SELIC = AncoraNumerica(
    chave="selic_decidida", rotulo="Selic decidida", valor_literal="13,75", valor=13.75,
    unidade=Unidade.PERCENTUAL_AO_ANO, trecho="O Copom decidiu reduzir a taxa básica para 13,75% a.a.",
)
ANCORAS = Ancoras(ata="copom-281-2026-09-16", numericas=[SELIC])

# Textos no tamanho que o Gerador produz (título mediano de 35 caracteres, corpo de ~150).
NORMAL = {
    TipoSlide.HOOK: dict(
        titulo="Juros em 13,75% a.a.: qual o próximo passo?",
        corpo="A 281ª reunião do Copom trouxe ajustes na Selic. O mercado observa a inflação.",
        destaque="próximo passo", imagem="banco central"),
    TipoSlide.PONTO: dict(
        titulo="A decisão da 281ª reunião",
        corpo=("O Copom (o grupo que decide os juros) definiu a Selic (o juro básico da economia) em "
               "13,75% a.a. Isso guia todos os outros juros do país."),
        destaque="decisão", imagem="mercado"),
    TipoSlide.CITACAO: dict(
        titulo="O cenário atual exige cautela",
        corpo=("O Comitê destaca que a incerteza (a falta de clareza sobre o futuro) segue alta. "
               "Por isso, a política monetária precisa ser firme."),
        imagem="banco central"),
    TipoSlide.CTA: dict(
        titulo="Leia a Ata completa",
        corpo="Veja o documento no site do Banco Central. Ele explica a decisão em detalhes."),
}
LONGO = dict(
    titulo="Por que a decisão de juros do Banco Central muda o custo do crédito para as famílias",
    corpo=("O Copom (o grupo que decide os juros, ou seja, o custo de pegar dinheiro emprestado) definiu a "
           "Selic (o juro básico da economia) em 13,75% a.a. Essa taxa guia todos os outros juros do país e "
           "muda o preço do crédito, dos financiamentos e dos investimentos de renda fixa para as famílias."),
)


def _slide(layout: familias.LayoutDeFamilia, longo: bool) -> Slide:
    papel = sorted(layout.papeis, key=lambda p: list(TipoSlide).index(p))[0]
    base = dict(NORMAL[papel])
    if longo:
        base.update(LONGO)
    if layout.exige_dado or layout.orientado_a_dados:
        base["dado"] = "selic_decidida"
    return Slide(tipo=papel, **base)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("familia")
    ap.add_argument("--saida")
    ap.add_argument(
        "--miniaturas", action="store_true",
        help="grava a miniatura 4:5 de cada layout (caso normal) em templates/familias/<familia>/miniaturas/",
    )
    a = ap.parse_args()
    familia = FamiliaVisual(a.familia)
    layouts = familias.layouts_da_familia(familia)
    if not layouts:
        sys.exit(f"nenhum layout carregado para {familia.value}")
    casos: list[tuple[str, familias.LayoutDeFamilia, Slide, Path | None]] = []
    for i, layout in enumerate(layouts):
        foto = RAIZ / "data" / "imagens" / f"{FOTOS[i % len(FOTOS)]}.jpg"
        casos.append((f"{layout.composicao.value}", layout, _slide(layout, False), foto if layout.usa_imagem else None))
        if layout.usa_imagem:
            casos.append((f"{layout.composicao.value} SEM foto", layout, _slide(layout, False), None))
        casos.append((f"{layout.composicao.value} LONGO", layout, _slide(layout, True), foto if layout.usa_imagem else None))
    imagens_finais: list[Image.Image] = []
    rotulos: list[str] = []
    defeitos_total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for n, (rotulo, layout, slide, foto) in enumerate(casos):
            pasta = Path(tmp) / f"c{n}"
            plano = (EscolhaDeLayout(indice=0, composicao=layout.composicao, pontuacao=0),)
            [png] = carrossel_html.renderizar(
                [slide], Audiencia.INICIANTE, ANCORAS, pasta, plano_direcao=plano,
                imagens={0: foto} if foto else None,
            )
            medidas = conferir_imagens(
                [ImagemSlide(indice=0, caminho=png, largura=1080, altura=1350)], ANCORAS
            ).medicoes
            ruins = [m for m in medidas if m.defeito is not None]
            defeitos_total += len(ruins)
            for m in ruins:
                print(f"DEFEITO [{rotulo}] {m.defeito.value}: {m.detalhe}")
            imagens_finais.append(Image.open(png).convert("RGB").resize((540, 675)))
            if a.miniaturas and rotulo == layout.composicao.value:
                destino = familias.PASTA_DAS_FAMILIAS / familia.value / "miniaturas"
                destino.mkdir(parents=True, exist_ok=True)
                Image.open(png).convert("RGB").resize((480, 600), Image.LANCZOS).save(
                    destino / f"{layout.composicao.value}.png", optimize=True
                )
            rotulos.append(rotulo + ("  ⚠ defeito" if ruins else ""))
    colunas = min(4, len(imagens_finais))
    linhas = (len(imagens_finais) + colunas - 1) // colunas
    folha = Image.new("RGB", (colunas * 550 + 10, linhas * 715 + 10), (24, 24, 24))
    d = ImageDraw.Draw(folha)
    for i, (im, r) in enumerate(zip(imagens_finais, rotulos)):
        x, y = 10 + (i % colunas) * 550, 10 + (i // colunas) * 715
        folha.paste(im, (x, y))
        d.text((x, y + 680), r, fill=(255, 255, 255))
    saida = Path(a.saida) if a.saida else RAIZ / "templates" / "recriados" / f"_galeria" / f"{familia.value}-real.jpg"
    saida.parent.mkdir(parents=True, exist_ok=True)
    folha.save(saida, quality=88)
    print(f"{len(casos)} casos, {defeitos_total} defeitos medidos. Folha de contato: {saida}")


if __name__ == "__main__":
    main()
