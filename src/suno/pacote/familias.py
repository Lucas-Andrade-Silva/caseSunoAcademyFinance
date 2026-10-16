"""Famílias visuais do Carrossel: manifesto declarativo e motor de preenchimento de slots.

Uma **família** é o conjunto de layouts de uma conta da Suno (Notícia, Explicativo, Jornal, Dados,
Asset). Cada uma vive em ``templates/familias/<familia>/`` com um ``familia.json`` e um HTML por
layout. O HTML marca o conteúdo variável com ``data-slot="nome"``; este módulo troca só esse
conteúdo e injeta fontes, fundo e o script de encolhimento. O resto do HTML não é tocado, então
cada template continua renderizável sozinho, com o texto de exemplo.

O Gerador escreve ``titulo`` e ``corpo`` (e o assunto da foto); o manifesto diz de onde cada slot
tira o valor (ver ``FONTES_DE_SLOT``). Nenhum campo de texto novo entra no ``Slide``: o Avaliador
julga ``titulo + corpo`` e tudo o que o layout mostra sai desses dois campos ou de uma Âncora.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from suno.dominio import (
    Ancoras,
    ComposicaoCarrossel,
    FamiliaVisual,
    Slide,
    TipoSlide,
)

PASTA_DOS_TEMPLATES = Path(__file__).parent / "templates"
PASTA_DAS_FAMILIAS = PASTA_DOS_TEMPLATES / "familias"
PASTA_DAS_FONTES = Path(__file__).parent / "fontes"

COMPOSICOES_LEGADAS = frozenset(
    {
        ComposicaoCarrossel.EDITORIAL,
        ComposicaoCarrossel.MINIMALISTA,
        ComposicaoCarrossel.INFOGRAFICO,
        ComposicaoCarrossel.COMPARATIVO,
        ComposicaoCarrossel.ESTATISTICO,
        ComposicaoCarrossel.NARRATIVO,
    }
)
TAMANHO_MINIMO_DA_LETRA = 26

# Faces que os templates podem usar; todas OFL, lidas do disco (nada é baixado no render).
FACES_DAS_FONTES: tuple[tuple[str, int, str], ...] = (
    ("Anton", 400, "anton-latin-400-normal"),
    ("Poppins", 300, "poppins-latin-300-normal"),
    ("Poppins", 400, "poppins-latin-400-normal"),
    ("Poppins", 600, "poppins-latin-600-normal"),
    ("Poppins", 700, "poppins-latin-700-normal"),
    ("Inter", 400, "inter-latin-400-normal"),
    ("Inter", 500, "inter-latin-500-normal"),
    ("Inter", 600, "inter-latin-600-normal"),
    ("Inter", 700, "inter-latin-700-normal"),
    ("Newsreader", 400, "newsreader-latin-400-normal"),
    ("Newsreader", 600, "newsreader-latin-600-normal"),
    ("Newsreader", 700, "newsreader-latin-700-normal"),
)

FONTES_DE_SLOT = frozenset(
    {
        "titulo",  # o título, texto puro
        "titulo_realcado",  # o título com o ``destaque`` envolto em <span class="realce">
        "titulo_antes_do_realce",  # o título sem o trecho final em destaque
        "realce",  # o trecho final do título que é o ``destaque`` (None se não for sufixo literal)
        "corpo",  # o corpo inteiro
        "corpo_sem_ultima_frase",  # o corpo sem a última frase (a frase em vermelho)
        "ultima_frase",  # a última frase do corpo, ou None se só há uma
        "paragrafo_1",
        "paragrafo_2",
        "paragrafo_3",
        "numero",  # a citação da Âncora de ``slide.dado``
        "rotulo",  # o rótulo da Âncora de ``slide.dado``
        "ordem",  # posição do slide, 1-based
        "ordem_sem_capa",  # posição sem contar a capa (o primeiro item depois dela é 1)
        "total",  # quantos slides tem o carrossel
        "imagem",  # a foto licenciada resolvida para o slide
        "manter",  # elemento decorativo fixo: o motor não toca nele
        "por_papel",  # texto fixo que muda conforme o papel do slide (ver ``por_papel`` do slot)
    }
)


class SlotObrigatorioAusente(ValueError):
    """O layout exige um slot que o slide não tem como preencher."""


class HtmlSeguro(str):
    """Texto já escapado, que pode conter marcação própria (o realce do título)."""


class _Manter:
    """Sentinela: o elemento decorativo fica como está no HTML."""


MANTER = _Manter()


@dataclass(frozen=True)
class SlotDoLayout:
    nome: str
    fonte: str
    tipo: str = "texto"  # "texto" | "imagem"
    obrigatorio: bool = True
    max_caracteres: int | None = None
    por_papel: dict[TipoSlide, str] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class LayoutDeFamilia:
    composicao: ComposicaoCarrossel
    familia: FamiliaVisual
    arquivo: str  # relativo a PASTA_DOS_TEMPLATES
    descricao: str
    papeis: frozenset[TipoSlide]
    slots: dict[str, SlotDoLayout]
    usa_imagem: bool = False
    exige_dado: bool = False
    orientado_a_dados: bool = False
    fundo: str = "#FFFFFF"
    pontos_por_papel: dict[TipoSlide, int] = field(default_factory=dict)
    referencia: dict | None = field(default=None, compare=False)  # semente do banco de referências


# ---------------------------------------------------------------------------
# Manifesto
# ---------------------------------------------------------------------------


def familia_da_composicao(composicao: ComposicaoCarrossel) -> FamiliaVisual:
    """A família de uma composição: as seis antigas são ``suno_escuro``; as novas levam o prefixo."""
    if composicao in COMPOSICOES_LEGADAS:
        return FamiliaVisual.SUNO_ESCURO
    return FamiliaVisual(composicao.value.split("_", 1)[0])


def _ler_layout(familia: FamiliaVisual, identificador: str, dados: dict) -> LayoutDeFamilia:
    composicao = ComposicaoCarrossel(identificador)
    slots = {
        nome: SlotDoLayout(
            nome=nome,
            fonte=spec["fonte"],
            tipo=spec.get("tipo", "imagem" if spec["fonte"] == "imagem" else "texto"),
            obrigatorio=spec.get("obrigatorio", True),
            max_caracteres=spec.get("max_caracteres"),
            por_papel={TipoSlide(p): str(v) for p, v in spec.get("por_papel", {}).items()},
        )
        for nome, spec in dados["slots"].items()
    }
    desconhecidas = {s.fonte for s in slots.values()} - FONTES_DE_SLOT
    desconhecidas = {f for f in desconhecidas if not f.startswith("fixo:")}
    if desconhecidas:
        raise ValueError(f"{identificador}: fonte de slot desconhecida {sorted(desconhecidas)}")
    return LayoutDeFamilia(
        composicao=composicao,
        familia=familia,
        arquivo=dados["arquivo"],
        descricao=dados["descricao"],
        papeis=frozenset(TipoSlide(p) for p in dados["papeis"]),
        slots=slots,
        usa_imagem=dados.get("usa_imagem", False),
        exige_dado=dados.get("exige_dado", False),
        orientado_a_dados=dados.get("orientado_a_dados", False),
        fundo=dados.get("fundo", "#FFFFFF"),
        pontos_por_papel={TipoSlide(p): int(v) for p, v in dados.get("pontos_por_papel", {}).items()},
        referencia=dados.get("referencia"),
    )


@lru_cache(maxsize=1)
def carregar_layouts() -> dict[ComposicaoCarrossel, LayoutDeFamilia]:
    """Todos os layouts das famílias novas, lidos dos ``familia.json`` em disco."""
    layouts: dict[ComposicaoCarrossel, LayoutDeFamilia] = {}
    for manifesto in sorted(PASTA_DAS_FAMILIAS.glob("*/familia.json")):
        dados = json.loads(manifesto.read_text(encoding="utf-8"))
        familia = FamiliaVisual(dados["familia"])
        for identificador, layout in dados["layouts"].items():
            lido = _ler_layout(familia, identificador, layout)
            if familia_da_composicao(lido.composicao) is not familia:
                raise ValueError(f"{identificador} não pertence à família {familia.value}")
            layouts[lido.composicao] = lido
    return layouts


def miniatura_do_layout(composicao: ComposicaoCarrossel) -> Path | None:
    """A imagem de exemplo do layout (``<familia>/miniaturas/<composicao>.png``), se existir.

    É o que a Curadoria mostra no lugar de um desenho: o layout renderizado com texto real.
    """
    familia = familia_da_composicao(composicao)
    if familia is FamiliaVisual.SUNO_ESCURO:
        return None
    caminho = PASTA_DAS_FAMILIAS / familia.value / "miniaturas" / f"{composicao.value}.png"
    return caminho if caminho.is_file() else None


def layouts_da_familia(familia: FamiliaVisual) -> list[LayoutDeFamilia]:
    return [layout for layout in carregar_layouts().values() if layout.familia is familia]


def papeis_cobertos(familia: FamiliaVisual) -> frozenset[TipoSlide]:
    """Os papéis que a família desenha sem depender de Âncora: um carrossel com outro papel não cabe nela."""
    return frozenset(
        papel
        for layout in layouts_da_familia(familia)
        if not layout.exige_dado
        for papel in layout.papeis
    )


# ---------------------------------------------------------------------------
# Texto do slide em pedaços
# ---------------------------------------------------------------------------

_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9\"“(])")


def separar_ultima_frase(corpo: str) -> tuple[str, str | None]:
    """Divide o corpo em ``(corpo, ultima_frase)``.

    O Gerador escreve o corpo num parágrafo só, então a frase de fecho (que as famílias mostram
    em vermelho) é a última frase. Se o texto traz parágrafos explícitos (linha em branco), o
    último parágrafo é o fecho.
    """
    texto = corpo.strip()
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    if len(paragrafos) >= 2:
        return "\n\n".join(paragrafos[:-1]), paragrafos[-1]
    frases = _FIM_DE_FRASE.split(texto)
    if len(frases) >= 2:
        return " ".join(frases[:-1]), frases[-1]
    return texto, None


def _paragrafos(corpo: str) -> list[str]:
    texto = corpo.strip()
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    if len(paragrafos) >= 2:
        return paragrafos
    return [f.strip() for f in _FIM_DE_FRASE.split(texto) if f.strip()]


def _realce(slide: Slide) -> tuple[str, str] | None:
    """``(antes, trecho)`` se o ``destaque`` é um final literal do título; senão ``None``."""
    trecho = (slide.destaque or "").strip()
    titulo = slide.titulo.strip()
    if not trecho or not titulo.rstrip(".?!:").endswith(trecho):
        return None
    ponta = titulo.rstrip(".?!:")
    return ponta[: len(ponta) - len(trecho)].rstrip(), trecho


def _titulo_realcado(slide: Slide) -> str | None:
    trecho = (slide.destaque or "").strip()
    if not trecho or trecho not in slide.titulo:
        return None
    antes, _, depois = slide.titulo.partition(trecho)
    return HtmlSeguro(
        f'{html.escape(antes, quote=False)}<span class="realce">'
        f"{html.escape(trecho, quote=False)}</span>{html.escape(depois, quote=False)}"
    )


def valores_do_slide(
    layout: LayoutDeFamilia,
    slide: Slide,
    *,
    ancoras: Ancoras,
    indice: int,
    total: int,
    imagem_uri: str | None,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    """O valor de cada slot do layout e as Âncoras numéricas desenhadas (para o ADR 0011)."""
    ancora = ancoras.numerica(slide.dado) if slide.dado else None
    corpo_sem_ultima, ultima = separar_ultima_frase(slide.corpo)
    realce = _realce(slide)
    paragrafos = _paragrafos(slide.corpo)
    por_fonte: dict[str, object] = {
        "titulo": slide.titulo,
        "titulo_realcado": _titulo_realcado(slide) or slide.titulo,
        "titulo_antes_do_realce": realce[0] if realce else slide.titulo,
        "realce": realce[1] if realce else None,
        "corpo": slide.corpo,
        "corpo_sem_ultima_frase": corpo_sem_ultima,
        "ultima_frase": ultima,
        "paragrafo_1": paragrafos[0] if len(paragrafos) >= 1 else None,
        "paragrafo_2": paragrafos[1] if len(paragrafos) >= 2 else None,
        "paragrafo_3": paragrafos[2] if len(paragrafos) >= 3 else None,
        "numero": ancora.citacao() if ancora is not None else None,
        "rotulo": ancora.rotulo if ancora is not None else None,
        "ordem": str(indice + 1),
        "ordem_sem_capa": str(max(1, indice)),
        "total": str(total),
        "imagem": imagem_uri,
        "manter": MANTER,
    }
    valores: dict[str, object] = {}
    desenhados: list[dict[str, str]] = []
    for nome, slot in layout.slots.items():
        if slot.fonte.startswith("fixo:"):
            valores[nome] = slot.fonte.removeprefix("fixo:")
            continue
        if slot.fonte == "por_papel":
            valores[nome] = slot.por_papel.get(slide.tipo)
            continue
        valores[nome] = por_fonte[slot.fonte]
        if slot.fonte == "numero" and ancora is not None and slide.dado:
            desenhados.append({"chave": slide.dado, "texto": ancora.citacao()})
    return valores, desenhados


# ---------------------------------------------------------------------------
# O motor de slots
# ---------------------------------------------------------------------------

_ABERTURA = re.compile(
    r"<(?P<tag>[a-zA-Z][\w-]*)(?P<antes>[^<>]*?)\sdata-slot=\"(?P<nome>[\w-]+)\"(?P<depois>[^<>]*)>"
)
_VAZIOS = frozenset({"img", "br", "hr", "input", "meta", "link"})


def _fim_do_elemento(texto: str, abertura: re.Match[str]) -> tuple[int, int]:
    """``(inicio_do_fechamento, fim_do_elemento)``; elementos vazios têm os dois no fim da abertura."""
    tag = abertura.group("tag")
    if tag.lower() in _VAZIOS or abertura.group(0).endswith("/>"):
        return abertura.end(), abertura.end()
    profundidade = 1
    for achado in re.finditer(rf"<(/?){re.escape(tag)}\b[^<>]*?(/?)>", texto[abertura.end():]):
        fechando, autofecha = achado.group(1) == "/", achado.group(2) == "/"
        if autofecha and not fechando:
            continue
        profundidade += -1 if fechando else 1
        if profundidade == 0:
            return abertura.end() + achado.start(), abertura.end() + achado.end()
    raise ValueError(f"<{tag} data-slot={abertura.group('nome')!r}> não é fechado")


def preencher_slots(
    modelo: str, slots: dict[str, SlotDoLayout], valores: dict[str, object]
) -> str:
    """Troca o conteúdo de cada ``data-slot``; o resto do HTML fica intacto.

    Texto é escapado (``HtmlSeguro`` passa como está). Slot opcional sem valor sai do HTML por
    inteiro; obrigatório sem valor é ``SlotObrigatorioAusente``. Imagem troca o ``src``.
    """
    # Com um contêiner medido (data-caixa="area"), o slot só entra na conferência de contraste.
    atributo_de_medida = "data-contraste" if 'data-caixa="area"' in modelo else "data-caixa"
    aberturas = list(_ABERTURA.finditer(modelo))
    nomes = [a.group("nome") for a in aberturas]
    if len(nomes) != len(set(nomes)):
        raise ValueError(f"data-slot repetido no template: {sorted(n for n in set(nomes) if nomes.count(n) > 1)}")
    saida = modelo
    for abertura in reversed(aberturas):
        nome = abertura.group("nome")
        slot = slots.get(nome)
        if slot is None:
            raise ValueError(f"o HTML tem data-slot={nome!r} que o manifesto não declara")
        valor = valores.get(nome)
        inicio_fecha, fim = _fim_do_elemento(saida, abertura)
        if isinstance(valor, _Manter):
            continue
        if valor is None or valor == "":
            if slot.obrigatorio:
                raise SlotObrigatorioAusente(f"slot obrigatório sem valor: {nome}")
            saida = saida[: abertura.start()] + saida[fim:]
            continue
        abre = abertura.group(0)
        if slot.tipo == "imagem":
            if re.search(r'\ssrc="[^"]*"', abre):
                nova = re.sub(r'(\ssrc=")[^"]*(")', lambda m: f"{m.group(1)}{valor}{m.group(2)}", abre, count=1)
            else:
                nova = abre[:-1] + f' src="{valor}">'
            saida = saida[: abertura.start()] + nova + saida[abertura.end():]
            continue
        conteudo = valor if isinstance(valor, HtmlSeguro) else html.escape(str(valor), quote=False)
        nova = abre[:-1] + f' {atributo_de_medida}="{nome}">'
        saida = saida[: abertura.start()] + nova + conteudo + saida[inicio_fecha:]
    return saida


# ---------------------------------------------------------------------------
# O documento final
# ---------------------------------------------------------------------------


def bloco_de_fontes() -> str:
    """``@font-face`` de todas as famílias permitidas, apontando para os arquivos do projeto."""
    faces = "".join(
        f'@font-face{{font-family:"{familia}";font-weight:{peso};'
        f'src:url("{(PASTA_DAS_FONTES / (arquivo + ".woff2")).as_uri()}")}}'
        for familia, peso, arquivo in FACES_DAS_FONTES
    )
    return f"<style>{faces}</style>"


def script_de_ajuste() -> str:
    """Encolhe, de 2 em 2 px, cada ``[data-ajustar]`` até o texto caber na caixa (mínimo legível).

    A tolerância é um quarto da letra: com leading apertado o contorno do glifo passa da linha
    (uns 5 px) e a regra de 1 px do render antigo encolheria todo texto até o mínimo.
    """
    return (
        "<script>(function(){function f(){document.querySelectorAll('[data-ajustar]').forEach(function(e){"
        "var t=parseFloat(getComputedStyle(e).fontSize);"
        f"while((e.scrollHeight>e.clientHeight+t*0.25||e.scrollWidth>e.clientWidth+1)&&t-2>={TAMANHO_MINIMO_DA_LETRA})"
        "{t-=2;e.style.fontSize=t+'px';}});}"
        "f();if(document.fonts&&document.fonts.ready){document.fonts.ready.then(f);}})();</script>"
    )


def preencher_layout(
    layout: LayoutDeFamilia,
    slide: Slide,
    *,
    ancoras: Ancoras,
    indice: int,
    total: int,
    imagem_uri: str | None,
) -> tuple[str, list[dict[str, str]]]:
    """O HTML completo do slide neste layout e as Âncoras numéricas que ele desenha."""
    modelo = (PASTA_DOS_TEMPLATES / layout.arquivo).read_text(encoding="utf-8")
    valores, numeros = valores_do_slide(
        layout, slide, ancoras=ancoras, indice=indice, total=total, imagem_uri=imagem_uri
    )
    corpo = preencher_slots(modelo, layout.slots, valores)
    return _documento(corpo, layout, sem_imagem=layout.usa_imagem and not imagem_uri), numeros


def documento_de_exemplo(layout: LayoutDeFamilia) -> str:
    """O template com o texto de exemplo dele, pronto para abrir; sem foto, degrada como no render."""
    modelo = (PASTA_DOS_TEMPLATES / layout.arquivo).read_text(encoding="utf-8")
    return _documento(modelo, layout, sem_imagem=layout.usa_imagem)


def _documento(corpo: str, layout: LayoutDeFamilia, *, sem_imagem: bool) -> str:
    classe = ' class="sem-imagem"' if sem_imagem else ""
    # O <body> é explícito para carregar o fundo medido (contraste) e a classe de degradação; o
    # ``data-fundo-cor`` também diz à recoloração se o Layout é claro ou escuro.
    corpo = corpo.replace(
        "</style>", f'</style><body{classe} data-fundo data-fundo-cor="{layout.fundo}">', 1
    )
    corpo = corpo.replace("{{FONTES}}", bloco_de_fontes())
    return corpo + script_de_ajuste()
