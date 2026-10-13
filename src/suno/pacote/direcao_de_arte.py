"""Direção de arte determinística para o Carrossel.

O Gerador continua responsável pelo papel narrativo de cada slide (gancho, ponto,
citação ou CTA). Este módulo escolhe somente a composição visual, a partir de um
catálogo fechado. Assim, diversidade não altera o texto aprovado nem depende de
uma nova chamada de LLM.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from suno.dominio import (
    ComposicaoCarrossel,
    DirecaoDeArteCarrossel,
    EscolhaDeLayout,
    FamiliaVisual,
    ReferenciaVisual,
    Slide,
    TipoSlide,
)
from suno.pacote import familias


@dataclass(frozen=True)
class LayoutCarrossel:
    composicao: ComposicaoCarrossel
    arquivo: str
    descricao: str
    tipos_compativeis: frozenset[TipoSlide]
    exige_dado: bool = False
    familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO
    usa_imagem: bool = False
    orientado_a_dados: bool = False
    pontos_por_papel: dict[TipoSlide, int] = field(default_factory=dict, compare=False)


TODOS_OS_TIPOS = frozenset(TipoSlide)
TIPOS_DE_CORPO = frozenset({TipoSlide.PONTO, TipoSlide.CITACAO})
TIPOS_ESTATISTICOS = frozenset({TipoSlide.PONTO, TipoSlide.CITACAO, TipoSlide.CTA})

CATALOGO_DE_LAYOUTS: dict[ComposicaoCarrossel, LayoutCarrossel] = {
    ComposicaoCarrossel.EDITORIAL: LayoutCarrossel(
        composicao=ComposicaoCarrossel.EDITORIAL,
        arquivo="editorial.html",
        descricao="Título dominante, texto de apoio e tensão assimétrica.",
        tipos_compativeis=TODOS_OS_TIPOS,
    ),
    ComposicaoCarrossel.MINIMALISTA: LayoutCarrossel(
        composicao=ComposicaoCarrossel.MINIMALISTA,
        arquivo="minimalista.html",
        descricao="Poucos elementos, baixa densidade e grande área de respiro.",
        tipos_compativeis=TODOS_OS_TIPOS,
    ),
    ComposicaoCarrossel.INFOGRAFICO: LayoutCarrossel(
        composicao=ComposicaoCarrossel.INFOGRAFICO,
        arquivo="infografico.html",
        descricao="Texto e visualização da Âncora numérica no mesmo campo visual.",
        tipos_compativeis=TIPOS_DE_CORPO,
        exige_dado=True,
        orientado_a_dados=True,
    ),
    ComposicaoCarrossel.COMPARATIVO: LayoutCarrossel(
        composicao=ComposicaoCarrossel.COMPARATIVO,
        arquivo="comparativo.html",
        descricao="Duas áreas contrastantes para relações de antes/depois ou oposição.",
        tipos_compativeis=TIPOS_DE_CORPO,
        orientado_a_dados=True,
    ),
    ComposicaoCarrossel.ESTATISTICO: LayoutCarrossel(
        composicao=ComposicaoCarrossel.ESTATISTICO,
        arquivo="estatistico.html",
        descricao="Uma Âncora numérica recebe a maior hierarquia do slide.",
        tipos_compativeis=TIPOS_ESTATISTICOS,
        exige_dado=True,
        orientado_a_dados=True,
    ),
    ComposicaoCarrossel.NARRATIVO: LayoutCarrossel(
        composicao=ComposicaoCarrossel.NARRATIVO,
        arquivo="narrativo.html",
        descricao="Etapa numerada para progressão sequencial do argumento.",
        tipos_compativeis=TODOS_OS_TIPOS,
    ),
}

def _layout_da_familia(layout: familias.LayoutDeFamilia) -> LayoutCarrossel:
    return LayoutCarrossel(
        composicao=layout.composicao,
        arquivo=layout.arquivo,
        descricao=layout.descricao,
        tipos_compativeis=layout.papeis,
        exige_dado=layout.exige_dado,
        familia=layout.familia,
        usa_imagem=layout.usa_imagem,
        orientado_a_dados=layout.orientado_a_dados,
        pontos_por_papel=dict(layout.pontos_por_papel),
    )


CATALOGO_DE_LAYOUTS.update(
    {composicao: _layout_da_familia(layout) for composicao, layout in familias.carregar_layouts().items()}
)

_TERMOS_DE_COMPARACAO = (
    "antes",
    "depois",
    "contra",
    "compar",
    "diferen",
    "enquanto",
    "lado a lado",
    "versus",
    " vs ",
)


def _quantidade_de_palavras(slide: Slide) -> int:
    return len(f"{slide.titulo} {slide.corpo}".split())


def _parece_comparacao(slide: Slide) -> bool:
    texto = f" {slide.titulo} {slide.corpo} ".casefold()
    return any(termo in texto for termo in _TERMOS_DE_COMPARACAO)


FAMILIAS_AUTOMATICAS: tuple[FamiliaVisual, ...] = (
    FamiliaVisual.NOTICIA,
    FamiliaVisual.EXPLICATIVO,
    FamiliaVisual.JORNAL,
    FamiliaVisual.DADOS,
)
"""As famílias que a escolha automática pode usar. ``asset`` fica de fora de propósito: carrega a
marca e o aviso legal da Suno Asset (fundos) e só entra quando alguém a pede."""


def escolher_familia(
    slides: Iterable[Slide],
    historico_recente: Iterable[ComposicaoCarrossel | str] = (),
    referencia_preferida: ReferenciaVisual | None = None,
) -> FamiliaVisual:
    """A família do carrossel inteiro: um carrossel usa uma só, como os posts reais da Suno.

    A referência escolhida na curadoria manda. Sem ela, vence a família menos usada no histórico
    recente que consegue cobrir todos os slides; o empate sai de um hash do conteúdo, então a
    mesma entrada repete a mesma escolha. Sem nenhuma elegível, volta ao layout escuro antigo.
    """
    if referencia_preferida is not None:
        return familias.familia_da_composicao(referencia_preferida.composicao)
    lista = list(slides)
    elegiveis = [
        familia
        for familia in FAMILIAS_AUTOMATICAS
        if lista and all(_candidatos(slide, familia) for slide in lista)
    ]
    if not elegiveis:
        return FamiliaVisual.SUNO_ESCURO
    recentes = [
        familias.familia_da_composicao(ComposicaoCarrossel(item))
        for item in list(historico_recente)[-12:]
    ]
    usos = Counter(recentes)
    material = "|".join(f"{slide.titulo}|{slide.corpo}" for slide in lista).encode()
    desempate = int.from_bytes(hashlib.blake2s(material, digest_size=2).digest(), "big")
    return min(
        elegiveis,
        key=lambda familia: (
            usos[familia],
            (FAMILIAS_AUTOMATICAS.index(familia) - desempate) % len(FAMILIAS_AUTOMATICAS),
        ),
    )


def _desempate(slide: Slide, composicao: ComposicaoCarrossel, indice: int) -> int:
    """Varia empates pelo conteúdo, mas repete a mesma decisão para a mesma entrada."""
    material = f"{indice}|{slide.titulo}|{slide.corpo}|{composicao.value}".encode()
    return int.from_bytes(hashlib.blake2s(material, digest_size=2).digest(), "big")


def _candidatos(
    slide: Slide, familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO
) -> list[LayoutCarrossel]:
    candidatos = [
        layout
        for layout in CATALOGO_DE_LAYOUTS.values()
        if layout.familia is familia
        and slide.tipo in layout.tipos_compativeis
        and (not layout.exige_dado or slide.dado)
    ]
    if slide.dado:
        orientados_a_dados = [layout for layout in candidatos if layout.orientado_a_dados]
        if orientados_a_dados:
            return orientados_a_dados
    return candidatos


def composicoes_compativeis(
    slide: Slide, familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO
) -> frozenset[ComposicaoCarrossel]:
    """Catálogo permitido para um slide; compartilhado com a validação do Diretor IA."""
    return frozenset(layout.composicao for layout in _candidatos(slide, familia))


def _pontuar(
    slide: Slide,
    composicao: ComposicaoCarrossel,
    usados: Counter[ComposicaoCarrossel],
    recentes: list[ComposicaoCarrossel],
) -> tuple[int, tuple[str, ...]]:
    pontos = 0
    motivos: list[str] = []
    palavras = _quantidade_de_palavras(slide)
    comparacao = _parece_comparacao(slide)
    layout = CATALOGO_DE_LAYOUTS[composicao]

    bonus_do_papel = layout.pontos_por_papel.get(slide.tipo, 0)
    if bonus_do_papel:
        pontos += bonus_do_papel
        motivos.append("papel do slide neste layout")
    if layout.usa_imagem:
        if slide.imagem:
            pontos += 5
            motivos.append("há foto para este slide")
        else:
            pontos -= 7
            motivos.append("layout de foto sem foto disponível")

    if slide.tipo is TipoSlide.HOOK:
        bonus = {
            ComposicaoCarrossel.EDITORIAL: 9,
            ComposicaoCarrossel.NARRATIVO: 5,
            ComposicaoCarrossel.MINIMALISTA: 3,
        }.get(composicao, 0)
        pontos += bonus
        if bonus:
            motivos.append("abre o argumento")
    elif slide.tipo is TipoSlide.CTA:
        bonus = {
            ComposicaoCarrossel.MINIMALISTA: 9,
            ComposicaoCarrossel.EDITORIAL: 4,
            ComposicaoCarrossel.NARRATIVO: 3,
        }.get(composicao, 0)
        pontos += bonus
        if bonus:
            motivos.append("encerra com uma ação clara")
    elif slide.tipo is TipoSlide.CITACAO:
        bonus = {
            ComposicaoCarrossel.EDITORIAL: 8,
            ComposicaoCarrossel.MINIMALISTA: 4,
            ComposicaoCarrossel.NARRATIVO: 2,
        }.get(composicao, 0)
        pontos += bonus
        if bonus:
            motivos.append("valoriza uma formulação textual")

    if slide.dado:
        bonus = {
            ComposicaoCarrossel.ESTATISTICO: 8,
            ComposicaoCarrossel.INFOGRAFICO: 7,
            ComposicaoCarrossel.COMPARATIVO: 3,
        }.get(composicao, 0)
        pontos += bonus
        if bonus:
            motivos.append("possui Âncora numérica")

    if comparacao and composicao is ComposicaoCarrossel.COMPARATIVO:
        pontos += 10
        motivos.append("expressa comparação")
    elif comparacao and composicao is ComposicaoCarrossel.INFOGRAFICO:
        pontos += 3

    if palavras <= 16 and composicao is ComposicaoCarrossel.MINIMALISTA:
        pontos += 5
        motivos.append("baixa densidade textual")
    elif palavras >= 28 and composicao is ComposicaoCarrossel.NARRATIVO:
        pontos += 5
        motivos.append("conteúdo pede progressão")
    elif (
        17 <= palavras <= 27
        and not slide.dado
        and composicao is ComposicaoCarrossel.EDITORIAL
    ):
        pontos += 3
        motivos.append("densidade editorial")

    repeticoes = usados[composicao]
    if repeticoes:
        pontos -= 5 * repeticoes
        motivos.append(f"penalidade por {repeticoes} uso(s) no carrossel")
    repeticoes_recentes = recentes.count(composicao)
    if repeticoes_recentes:
        pontos -= 2 * repeticoes_recentes
        motivos.append("penalidade pelo histórico recente")
    if recentes and recentes[-1] is composicao:
        pontos -= 8
        motivos.append("evita repetição consecutiva")

    return pontos, tuple(motivos or ["compatível com o conteúdo"])


def planejar_direcao_de_arte(
    slides: Iterable[Slide],
    historico_recente: Iterable[ComposicaoCarrossel | str] = (),
    referencias_aprovadas: Iterable[ReferenciaVisual] = (),
    referencia_preferida: ReferenciaVisual | None = None,
    familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO,
) -> list[EscolhaDeLayout]:
    """Escolhe uma composição por slide sem aleatoriedade ou chamada externa.

    ``historico_recente`` permite que o chamador penalize layouts vistos em outros
    carrosséis. Os usos do próprio carrossel são sempre considerados. ``familia`` restringe o
    catálogo aos layouts de uma família: um carrossel usa uma só, como os posts reais da Suno.
    O ``Slide.imagem`` deve vir preenchido só quando a foto foi de fato resolvida: o plano
    evita layout de foto quando não há foto.
    """
    lista = list(slides)
    recentes = [ComposicaoCarrossel(item) for item in historico_recente][-12:]
    referencias = {
        referencia.composicao: referencia
        for referencia in referencias_aprovadas
        if referencia.aprovada
    }
    if referencia_preferida is not None and not referencia_preferida.aprovada:
        raise ValueError("a referência escolhida na curadoria não está aprovada")
    usados: Counter[ComposicaoCarrossel] = Counter()
    escolhas: list[EscolhaDeLayout] = []

    for indice, slide in enumerate(lista):
        candidatos = _candidatos(slide, familia)
        if escolhas and len(candidatos) > 1:
            anterior = escolhas[-1].composicao
            candidatos_sem_repetir = [
                layout for layout in candidatos if layout.composicao is not anterior
            ]
            if candidatos_sem_repetir:
                candidatos = candidatos_sem_repetir
        avaliados: list[tuple[int, int, ComposicaoCarrossel, tuple[str, ...]]] = []
        for layout in candidatos:
            pontos, motivos = _pontuar(slide, layout.composicao, usados, recentes)
            if (
                referencia_preferida is not None
                and layout.composicao is referencia_preferida.composicao
            ):
                pontos += 8
                motivos = (
                    *motivos,
                    f"linguagem visual escolhida: {referencia_preferida.titulo}",
                )
            avaliados.append(
                (pontos, _desempate(slide, layout.composicao, indice), layout.composicao, motivos)
            )
        if not avaliados:  # proteção contra catálogo inválido; hoje todos os tipos têm opção.
            raise ValueError(f"nenhum layout compatível com o slide {indice + 1}")
        pontos, _, composicao, motivos = max(avaliados, key=lambda item: (item[0], item[1]))
        referencia = (
            referencia_preferida
            if referencia_preferida is not None
            and referencia_preferida.composicao is composicao
            else referencias.get(composicao)
        )
        if referencia is not None:
            motivos = (*motivos, f'referência aprovada: {referencia.titulo}')
        escolhas.append(
            EscolhaDeLayout(
                indice=indice,
                composicao=composicao,
                pontuacao=pontos,
                motivos=motivos,
                referencia_visual=(referencia.identificador if referencia is not None else None),
            )
        )
        usados[composicao] += 1
        recentes.append(composicao)
        recentes = recentes[-12:]
    return escolhas


def resumir_direcao_renderizada(
    manifestos: Iterable[Path],
    historico_considerado: Iterable[ComposicaoCarrossel | str] = (),
    *,
    origem_do_plano: str = "deterministico",
    provedor: str | None = None,
    motivo_fallback: str | None = None,
    familia: FamiliaVisual | None = None,
) -> DirecaoDeArteCarrossel | None:
    """Reconstrói o plano a partir dos manifestos que comprovam o que foi renderizado."""
    escolhas: list[EscolhaDeLayout] = []
    for caminho in manifestos:
        if not caminho.exists():
            continue
        manifesto = json.loads(caminho.read_text(encoding="utf-8"))
        composicao = manifesto.get("layout")
        direcao = manifesto.get("direcao_de_arte") or {}
        if not composicao:
            continue
        escolhas.append(
            EscolhaDeLayout(
                indice=max(0, int(manifesto.get("slide", len(escolhas) + 1)) - 1),
                composicao=ComposicaoCarrossel(composicao),
                pontuacao=int(direcao.get("pontuacao", 0)),
                motivos=tuple(str(item) for item in direcao.get("motivos", [])),
                referencia_visual=direcao.get("referencia_visual"),
                intensidade_visual=direcao.get("intensidade_visual", "media"),
            )
        )
    if not escolhas:
        return None
    distribuicao = Counter(escolha.composicao.value for escolha in escolhas)
    repeticoes = sum(
        atual.composicao is anterior.composicao
        for anterior, atual in zip(escolhas, escolhas[1:])
    )
    return DirecaoDeArteCarrossel(
        familia=familia,
        escolhas=escolhas,
        distribuicao=dict(sorted(distribuicao.items())),
        historico_considerado=[
            ComposicaoCarrossel(item) for item in historico_considerado
        ][-12:],
        repeticoes_consecutivas=repeticoes,
        origem_do_plano=origem_do_plano,
        provedor=provedor,
        motivo_fallback=motivo_fallback,
    )


__all__ = [
    "CATALOGO_DE_LAYOUTS",
    "ComposicaoCarrossel",
    "EscolhaDeLayout",
    "LayoutCarrossel",
    "composicoes_compativeis",
    "planejar_direcao_de_arte",
    "resumir_direcao_renderizada",
]
