"""Diretor de Arte IA restrito ao catálogo, com fallback determinístico.

Uma única chamada planeja o carrossel inteiro. O modelo escolhe; o código valida.
Texto, números, CSS, marca e renderização nunca ficam sob controle do provedor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from pydantic import BaseModel, Field

from suno.dominio import (
    ComposicaoCarrossel,
    ErroProvedor,
    EscolhaDeLayout,
    FamiliaVisual,
    IntensidadeVisual,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    ReferenciaVisual,
    Slide,
)
from suno.pacote.direcao_de_arte import composicoes_compativeis, planejar_direcao_de_arte
from suno.pacote.familias import familia_da_composicao
from suno.provedores.base import Provedor


class DecisaoDoDiretor(BaseModel):
    indice: int = Field(ge=0)
    composicao: ComposicaoCarrossel
    referencia_visual: str
    intensidade_visual: IntensidadeVisual
    justificativa: str = Field(min_length=3, max_length=220)


class PlanoDoDiretor(BaseModel):
    escolhas: list[DecisaoDoDiretor]


@dataclass(frozen=True)
class ResultadoDirecao:
    escolhas: list[EscolhaDeLayout]
    origem: str
    provedor: str | None = None
    motivo_fallback: str | None = None


def _pedido(
    slides: list[Slide],
    referencias: list[ReferenciaVisual],
    historico_recente: Iterable[ComposicaoCarrossel | str],
    sinais_humanos: dict[str, list[dict[str, int | str]]] | None = None,
    referencia_preferida: ReferenciaVisual | None = None,
    familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO,
) -> PedidoLLM:
    entrada = {
        "familia": familia.value,
        "slides": [
            {
                "indice": indice,
                "funcao": slide.tipo.value,
                "titulo": slide.titulo,
                "corpo": slide.corpo,
                "tem_dado": bool(slide.dado),
                "tem_foto": bool(slide.imagem),
            }
            for indice, slide in enumerate(slides)
        ],
        "referencias_aprovadas": [
            {
                "identificador": referencia.identificador,
                "composicao": referencia.composicao.value,
                "tema": referencia.tema,
                "instrucao": referencia.instrucao_de_design,
                "analise": referencia.analise.model_dump(mode="json"),
            }
            for referencia in referencias
        ],
        "historico_recente": [ComposicaoCarrossel(item).value for item in historico_recente],
        "sinais_humanos": sinais_humanos or {},
        "referencia_preferida": (
            {
                "identificador": referencia_preferida.identificador,
                "composicao": referencia_preferida.composicao.value,
                "instrucao": referencia_preferida.instrucao_de_design,
            }
            if referencia_preferida is not None
            else None
        ),
    }
    return PedidoLLM(
        papel=PapelLLM.DIRETOR_ARTE,
        rotulo="direcao_de_arte",
        mensagens=[
            Mensagem(
                autor="sistema",
                texto=(
                    "Você é o Diretor de Arte de um carrossel financeiro da Suno. Escolha uma "
                    "composição e uma referência aprovada por slide, sempre da família visual "
                    "indicada em 'familia' (as referências já são só dela): um carrossel usa uma "
                    "só família. Prefira layouts de foto nos slides com 'tem_foto' e layouts de "
                    "texto nos demais. Preserve clareza, coerência "
                    "do carrossel e diversidade; evite repetir composições consecutivas. Trate "
                    "aprovações humanas anteriores apenas como preferência fraca: elas nunca "
                    "substituem compatibilidade, clareza ou variedade. Não reescreva o texto, "
                    "Use a referência preferida como linguagem visual do conjunto, não como "
                    "ordem para repetir o mesmo layout em todos os slides. Nunca repita uma "
                    "composição em slides consecutivos quando houver alternativa compatível. "
                    "não invente números, não crie CSS e não escolha referência "
                    "de outra composição. Responda apenas no schema solicitado."
                ),
            ),
            Mensagem(autor="usuario", texto=json.dumps(entrada, ensure_ascii=False)),
        ],
        max_tokens=1800,
        temperatura=0.2,
        esforco_raciocinio="baixo",
    )


def _validar_e_converter(
    plano: PlanoDoDiretor,
    slides: list[Slide],
    referencias: list[ReferenciaVisual],
    familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO,
) -> list[EscolhaDeLayout]:
    if [item.indice for item in plano.escolhas] != list(range(len(slides))):
        raise ValueError("o Diretor de Arte não devolveu exatamente uma escolha por slide")
    por_id = {referencia.identificador: referencia for referencia in referencias}
    escolhas: list[EscolhaDeLayout] = []
    anterior: ComposicaoCarrossel | None = None
    for slide, decisao in zip(slides, plano.escolhas):
        compativeis = composicoes_compativeis(slide, familia)
        if decisao.composicao not in compativeis:
            raise ValueError(
                f"composição {decisao.composicao.value} incompatível com o slide {decisao.indice + 1}"
            )
        referencia = por_id.get(decisao.referencia_visual)
        if referencia is None or not referencia.aprovada:
            raise ValueError("o Diretor de Arte escolheu uma referência não aprovada")
        if referencia.composicao is not decisao.composicao:
            raise ValueError("a referência escolhida não pertence à composição indicada")
        if anterior is decisao.composicao and len(compativeis) > 1:
            raise ValueError("o Diretor de Arte repetiu uma composição consecutiva sem necessidade")
        escolhas.append(
            EscolhaDeLayout(
                indice=decisao.indice,
                composicao=decisao.composicao,
                pontuacao=100,
                motivos=(
                    f"Diretor de Arte IA: {decisao.justificativa}",
                    f"referência aprovada: {referencia.titulo}",
                ),
                referencia_visual=referencia.identificador,
                intensidade_visual=decisao.intensidade_visual,
            )
        )
        anterior = decisao.composicao
    return escolhas


def planejar_com_diretor_de_arte(
    slides: Iterable[Slide],
    referencias_aprovadas: Iterable[ReferenciaVisual],
    historico_recente: Iterable[ComposicaoCarrossel | str] = (),
    *,
    provedor: Provedor | None = None,
    sinais_humanos: dict[str, list[dict[str, int | str]]] | None = None,
    referencia_preferida: ReferenciaVisual | None = None,
    familia: FamiliaVisual = FamiliaVisual.SUNO_ESCURO,
) -> ResultadoDirecao:
    lista = list(slides)
    referencias = [
        item
        for item in referencias_aprovadas
        if item.aprovada and familia_da_composicao(item.composicao) is familia
    ]
    historico = tuple(historico_recente)
    if provedor is not None and referencias and lista:
        try:
            plano = provedor.completar_estruturado(
                _pedido(
                    lista,
                    referencias,
                    historico,
                    sinais_humanos,
                    referencia_preferida,
                    familia,
                ),
                PlanoDoDiretor,
            )
            return ResultadoDirecao(
                escolhas=_validar_e_converter(plano, lista, referencias, familia),
                origem="ia",
                provedor=provedor.nome,
            )
        except (ErroProvedor, ValueError) as erro:
            motivo = str(erro)
    else:
        motivo = "Diretor de Arte IA indisponível"
    return ResultadoDirecao(
        escolhas=planejar_direcao_de_arte(
            lista,
            historico,
            referencias,
            referencia_preferida=referencia_preferida,
            familia=familia,
        ),
        origem="deterministico",
        motivo_fallback=motivo,
    )


__all__ = [
    "DecisaoDoDiretor",
    "PlanoDoDiretor",
    "ResultadoDirecao",
    "planejar_com_diretor_de_arte",
]
