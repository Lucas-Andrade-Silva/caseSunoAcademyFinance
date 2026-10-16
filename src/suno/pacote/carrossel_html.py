"""Renderização do Carrossel por templates HTML/CSS e Puppeteer (ADR 0020).

O Gemini escreve a estrutura (``tipo``, ``titulo``, ``corpo``, ``destaque``, ``dado``); aqui o
pipeline só preenche o template do tipo e o Puppeteer captura o PNG 1080x1350. Nenhuma
imagem é gerada por modelo: as letras são as DejaVu do matplotlib, lidas do disco.

O manifesto ``slide-<nn>.json`` sai com as caixas medidas no navegador (retângulo reservado e
espaço usado), que é o que ``visual.py`` confere.
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from suno.dominio import (
    ALTURA_SLIDE,
    LARGURA_SLIDE,
    AncoraNumerica,
    Ancoras,
    Audiencia,
    ChaveAncora,
    EscolhaDeLayout,
    PaletaVisual,
    ReferenciaVisual,
    Slide,
)
from suno.pacote import familias
from suno.pacote.carrossel import SELO_DA_AUDIENCIA
from suno.pacote.recolorir import recolorir
from suno.pacote.direcao_de_arte import (
    CATALOGO_DE_LAYOUTS,
    ComposicaoCarrossel,
    EscolhaDeLayout,
    planejar_direcao_de_arte,
)

PASTA_DOS_TEMPLATES = Path(__file__).parent / "templates"
PASTA_DAS_FONTES = Path(__file__).parent / "fontes"
FONTE_DO_TITULO = "anton-latin-400-normal.woff2"
FONTES_DO_TEXTO = {
    "FONTE_TEXTO": "poppins-latin-400-normal.woff2",
    "FONTE_TEXTO_MEDIO": "poppins-latin-600-normal.woff2",
    "FONTE_TEXTO_FORTE": "poppins-latin-700-normal.woff2",
}
PASTA_DO_RENDER = Path(__file__).resolve().parents[3] / "render"
TAMANHO_MINIMO_DA_LETRA = 26
AJUSTE_DE_TAMANHO = (
    "<script>(function(){function f(){document.querySelectorAll('[data-ajustar]').forEach(function(e){"
    "var t=parseFloat(getComputedStyle(e).fontSize);"
    f"while((e.scrollHeight>e.clientHeight+1||e.scrollWidth>e.clientWidth+1)&&t-2>={TAMANHO_MINIMO_DA_LETRA})"
    "{t-=2;e.style.fontSize=t+'px';}});}"
    "f();if(document.fonts&&document.fonts.ready){document.fonts.ready.then(f);}})();</script>"
)
"""Encolhe o título e o corpo de 2 em 2 px até caberem na caixa reservada, sem passar do mínimo
legível. O que ainda estourar é defeito de render, medido por ``visual.py``."""
ALTURA_DO_CORPO_COM_GRAFICO = 220
ALTURA_DO_CORPO_SEM_GRAFICO = 700


def disponivel() -> bool:
    """Node e o Puppeteer instalado (``npm install`` em ``render/``)."""
    return (
        shutil.which("node") is not None
        and (PASTA_DO_RENDER / "node_modules" / "puppeteer").is_dir()
    )


def _pontos(indice: int, total: int) -> str:
    """A fileira de pontos do pager: o slide atual vira uma pílula vermelha."""
    return "".join('<i class="ativo"></i>' if i == indice else "<i></i>" for i in range(total))


def _texto(valor: str) -> str:
    return html.escape(valor, quote=False)


def _titulo_com_destaque(slide: Slide) -> str:
    titulo = _texto(slide.titulo)
    if slide.destaque and slide.destaque in slide.titulo:
        marcado = f'<span class="destaque">{_texto(slide.destaque)}</span>'
        return titulo.replace(_texto(slide.destaque), marcado, 1)
    return titulo


def _barra(ancora: AncoraNumerica, rotulo: str, cor: str, teto: float) -> str:
    altura = round(260 * float(ancora.valor or 0) / teto)
    return (
        f'<div class="barra"><div class="valor" data-caixa="numero">{_texto(ancora.citacao())}</div>'
        f'<div class="bloco" style="height:{altura}px;background:{cor}"></div>'
        f'<div class="rotulo">{rotulo}</div></div>'
    )


def _numero_estatistico(ancora: AncoraNumerica) -> tuple[str, list[dict[str, str]]]:
    corpo = (
        '<div class="numero-grande">'
        f'<div class="valor" data-caixa="numero" data-ajustar>{_texto(ancora.citacao())}</div>'
        f'<div class="rotulo" data-caixa="numero-rotulo">{_texto(ancora.rotulo)}</div></div>'
    )
    return corpo, [{"chave": ancora.chave, "texto": ancora.citacao()}]


def _grafico(
    chave: str, ancoras: Ancoras, composicao: ComposicaoCarrossel
) -> tuple[str, list[dict[str, str]]]:
    """Barras Antes/Depois para as duas Selic; senão o número grande. Vazio se a chave não existe."""
    ancora = ancoras.numerica(chave)
    if ancora is None:
        return "", []
    if composicao is ComposicaoCarrossel.ESTATISTICO:
        corpo, numeros = _numero_estatistico(ancora)
        return f'<div class="grafico" data-fundo>{corpo}</div>', numeros
    anterior = ancoras.numerica(ChaveAncora.SELIC_ANTERIOR.value)
    decidida = ancoras.numerica(ChaveAncora.SELIC_DECIDIDA.value)
    comparaveis = (
        chave in (ChaveAncora.SELIC_ANTERIOR.value, ChaveAncora.SELIC_DECIDIDA.value)
        and anterior is not None
        and decidida is not None
        and anterior.valor is not None
        and decidida.valor is not None
    )
    if comparaveis:
        assert anterior is not None and decidida is not None
        teto = max(float(anterior.valor or 0), float(decidida.valor or 0)) or 1.0
        corpo = (
            '<div class="barras">'
            + _barra(anterior, "Antes", "#8A8A92", teto)
            + _barra(decidida, "Depois", "#FF0000", teto)
            + "</div>"
        )
        numeros = [
            {"chave": anterior.chave, "texto": anterior.citacao()},
            {"chave": decidida.chave, "texto": decidida.citacao()},
        ]
    else:
        corpo, numeros = _numero_estatistico(ancora)
    return f'<div class="grafico" data-fundo>{corpo}</div>', numeros


def _partes_da_comparacao(texto: str) -> tuple[str, str]:
    """Divide o corpo em dois painéis sem inventar texto novo."""
    for separador, conector in (
        (", conquanto ", "conquanto "),
        (", embora ", "embora "),
    ):
        partes = texto.split(separador, 1)
        if len(partes) == 2 and all(parte.strip() for parte in partes):
            return partes[0].strip(), conector.capitalize() + partes[1].strip()
    for separador in (";", " enquanto ", " mas ", ". "):
        partes = texto.split(separador, 1)
        if len(partes) == 2 and all(parte.strip() for parte in partes):
            return partes[0].strip(), partes[1].strip()
    palavras = texto.split()
    meio = max(1, len(palavras) // 2)
    esquerda = " ".join(palavras[:meio])
    direita = " ".join(palavras[meio:]) or esquerda
    return esquerda, direita


def _preencher(
    slide: Slide,
    audiencia: Audiencia,
    indice: int,
    total: int,
    ancoras: Ancoras,
    css: str,
    escolha: EscolhaDeLayout,
    imagem_uri: str | None = None,
) -> tuple[str, list[dict[str, str]]]:
    layout_da_familia = familias.carregar_layouts().get(escolha.composicao)
    if layout_da_familia is not None:
        return familias.preencher_layout(
            layout_da_familia,
            slide,
            ancoras=ancoras,
            indice=indice,
            total=total,
            imagem_uri=imagem_uri,
        )
    layout = CATALOGO_DE_LAYOUTS[escolha.composicao]
    modelo = (PASTA_DOS_TEMPLATES / layout.arquivo).read_text(encoding="utf-8")
    grafico, numeros = "", []
    if slide.dado:
        grafico, numeros = _grafico(slide.dado, ancoras, escolha.composicao)
    altura_corpo = ALTURA_DO_CORPO_COM_GRAFICO if grafico else ALTURA_DO_CORPO_SEM_GRAFICO
    esquerda, direita = _partes_da_comparacao(slide.corpo)
    trocas = {
        "CSS": css,
        "SELO": _texto(SELO_DA_AUDIENCIA[audiencia]),
        "NUMERO": f"{indice + 1}/{total}",
        "TITULO": _titulo_com_destaque(slide),
        "CORPO": _texto(slide.corpo),
        "CORPO_ESQUERDA": _texto(esquerda),
        "CORPO_DIREITA": _texto(direita),
        "GRAFICO": grafico,
        "ALTURA_CORPO": str(altura_corpo),
        "PONTOS": _pontos(indice, total),
        "ORDEM": str(indice + 1),
        "TOTAL": str(total),
        "AJUSTE": AJUSTE_DE_TAMANHO,
    }
    for nome, valor in trocas.items():
        modelo = modelo.replace("{{" + nome + "}}", valor)
    return modelo, numeros


def renderizar(
    slides: list[Slide],
    audiencia: Audiencia,
    ancoras: Ancoras,
    pasta: Path,
    historico_layouts: tuple[ComposicaoCarrossel | str, ...] = (),
    referencias_aprovadas: tuple[ReferenciaVisual, ...] = (),
    plano_direcao: tuple[EscolhaDeLayout, ...] | None = None,
    imagens: dict[int, Path] | None = None,
    paleta: PaletaVisual | None = None,
) -> list[Path]:
    """Grava ``slide-<nn>.png``, ``.json`` e ``.html`` em ``pasta`` e devolve os PNGs.

    ``imagens`` leva a foto já resolvida de cada slide (índice → arquivo). Sem foto, o layout da
    família degrada sozinho (classe ``sem-imagem``). ``paleta`` recolore os Layouts das famílias.
    O ``.html`` guarda o slide com as cores originais: é dele que a prévia do editor recolore com
    outra paleta sem montar o Pacote de novo.
    """
    css = (PASTA_DOS_TEMPLATES / "base.css").read_text(encoding="utf-8")
    css = css.replace("{{FONTE_TITULO}}", (PASTA_DAS_FONTES / FONTE_DO_TITULO).as_uri())
    for marcador, arquivo in FONTES_DO_TEXTO.items():
        css = css.replace("{{" + marcador + "}}", (PASTA_DAS_FONTES / arquivo).as_uri())
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos: list[Path] = []
    numeros_por_slide: list[list[dict[str, str]]] = []
    plano = (
        list(plano_direcao)
        if plano_direcao is not None
        else planejar_direcao_de_arte(slides, historico_layouts, referencias_aprovadas)
    )
    if len(plano) != len(slides):
        raise ValueError("o plano de direção precisa ter exatamente uma escolha por slide")
    with tempfile.TemporaryDirectory(prefix="suno-render-") as temporaria:
        trabalho: list[dict[str, str]] = []
        for indice, (slide, escolha) in enumerate(zip(slides, plano)):
            foto = (imagens or {}).get(indice)
            conteudo, numeros = _preencher(
                slide,
                audiencia,
                indice,
                len(slides),
                ancoras,
                css,
                escolha,
                imagem_uri=foto.resolve().as_uri() if foto is not None else None,
            )
            numeros_por_slide.append(numeros)
            nome = f"slide-{indice + 1:02d}"
            (pasta / f"{nome}.html").write_text(conteudo, encoding="utf-8")
            arquivo_html = Path(temporaria) / f"{nome}.html"
            arquivo_html.write_text(recolorir(conteudo, paleta), encoding="utf-8")
            png = pasta / f"{nome}.png"
            caminhos.append(png)
            trabalho.append(
                {
                    "html": str(arquivo_html),
                    "png": str(png),
                    "json": str(Path(temporaria) / f"{nome}.medido.json"),
                }
            )
        arquivo = Path(temporaria) / "trabalho.json"
        arquivo.write_text(
            json.dumps({"largura": LARGURA_SLIDE, "altura": ALTURA_SLIDE, "slides": trabalho}),
            encoding="utf-8",
        )
        subprocess.run(
            ["node", str(PASTA_DO_RENDER / "render.mjs"), str(arquivo)],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        for indice, (png, item) in enumerate(zip(caminhos, trabalho)):
            medido: dict[str, Any] = json.loads(Path(item["json"]).read_text(encoding="utf-8"))
            manifesto = {
                "slide": indice + 1,
                "total": len(slides),
                "audiencia": audiencia.value,
                "tipo": slides[indice].tipo.value,
                "layout": plano[indice].composicao.value,
                "direcao_de_arte": {
                    "pontuacao": plano[indice].pontuacao,
                    "motivos": list(plano[indice].motivos),
                    "referencia_visual": plano[indice].referencia_visual,
                    "intensidade_visual": plano[indice].intensidade_visual.value,
                },
                "largura": LARGURA_SLIDE,
                "altura": ALTURA_SLIDE,
                "caixas": medido["caixas"],
                "numeros": numeros_por_slide[indice],
            }
            png.with_suffix(".json").write_text(
                json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    return caminhos
