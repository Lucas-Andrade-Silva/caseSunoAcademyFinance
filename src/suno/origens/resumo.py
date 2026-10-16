"""O resumo de uma Ata na lista de Fontes: determinístico, sem LLM, sem cota.

Título e data vêm dos metadados. O texto do resumo é a frase da decisão quando há uma (verbos
como "decidiu", "aprovou", "comunica"), senão a primeira frase com corpo, senão o início do texto.
A contagem é de números e datas distintos que a extração de regra fixa acha, sem chamar modelo.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel

from suno.avaliador.integridade import medir_integridade
from suno.dominio import Ata, CategoriaDaAta, Unidade, chaves_essenciais_da
from suno.gerador.extracao import por_regra_generica
from suno.ingestao.numeros import NumeroEncontrado, extrair_numeros

LIMITE_DO_RESUMO = 280

_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])")
_NUMERACAO_NO_FIM = re.compile(r"\s+\d{1,2}\.$")
_VERBOS_DE_DECISAO = re.compile(
    r"\b(decidiu|decide|aprovou|aprova|comunica|informa|anunciou|anuncia|divulga|divulgou)\b",
    re.IGNORECASE,
)


class ResumoDaAta(BaseModel):
    """O que a tela mostra de uma Ata sem abrir o texto inteiro."""

    identificador: str
    origem: str
    categoria: CategoriaDaAta
    titulo: str
    data_referencia: date
    resumo: str
    total_ancoras: int
    calibrada: bool
    demo_disponivel: bool
    extracao_completa: bool
    """Dá para gerar? Fora do Copom: a Ata traz um número, ou texto suficiente para o LLM extrair
    uma afirmação central. Sem nenhum dos dois, toda Célula reprovaria por falha de extração."""
    qualitativa: bool = False
    """Fora do Copom: nenhum número no texto. O conteúdo sai sem valor a conferir (ADR 0034)."""


def _cortar(texto: str) -> str:
    if len(texto) <= LIMITE_DO_RESUMO:
        return texto
    trecho = texto[: LIMITE_DO_RESUMO - 1]
    return trecho[: trecho.rfind(" ")].rstrip(" ,;:") + "…" if " " in trecho else trecho + "…"


def frase_de_resumo(texto: str) -> str:
    """A frase que melhor diz do que se trata o documento, em até 280 caracteres."""
    plano = re.sub(r"\s+", " ", texto).strip()
    frases = [_NUMERACAO_NO_FIM.sub("", f).strip() for f in _FIM_DE_FRASE.split(plano)]
    com_decisao = [f for f in frases if 40 <= len(f) <= 360 and _VERBOS_DE_DECISAO.search(f)]
    if com_decisao:
        return _cortar(com_decisao[0])
    com_corpo = [f for f in frases if 60 <= len(f) <= 360]
    if com_corpo:
        return _cortar(com_corpo[0])
    return _cortar(plano)


def contar_ancoras(achados: list[NumeroEncontrado]) -> int:
    """Números e datas distintos que a regra fixa acha no texto (sem LLM)."""
    return len({(achado.literal, achado.unidade) for achado in achados})


TEXTO_MINIMO_SEM_NUMERO = 200
"""Caracteres que uma Ata sem número precisa ter para o LLM achar uma afirmação central."""


def extracao_completa(ata: Ata, achados: list[NumeroEncontrado]) -> bool:
    """A extração vai ter o que o conjunto essencial da categoria exige?

    No Copom a regra fixa mais a rotulagem do LLM completam o conjunto, e não dá para prever o
    que o LLM acha: vale ``True``. Fora do Copom a data sai de regra fixa (do texto ou dos
    metadados) e o fato central é um número ou, sem número, uma afirmação que só o LLM extrai:
    com número a resposta é exata; sem número vale o texto ter corpo para uma afirmação.
    """
    if ata.categoria is CategoriaDaAta.COPOM:
        return True
    ancoras = por_regra_generica(ata, achados)
    if medir_integridade(ancoras, chaves_essenciais_da(ata.categoria)).completa:
        return True
    return len(ata.texto.strip()) >= TEXTO_MINIMO_SEM_NUMERO


def sem_numero(ata: Ata, achados: list[NumeroEncontrado]) -> bool:
    """Fora do Copom, nenhum número (só datas) no texto: o conteúdo será qualitativo."""
    return ata.categoria is not CategoriaDaAta.COPOM and not any(
        a.unidade is not Unidade.DATA for a in achados
    )


def resumir_ata(ata: Ata, *, demo_disponivel: bool) -> ResumoDaAta:
    achados = extrair_numeros(ata.texto, ano_padrao=ata.data_referencia.year)
    return ResumoDaAta(
        identificador=ata.identificador,
        origem=ata.origem,
        categoria=ata.categoria,
        titulo=ata.titulo,
        data_referencia=ata.data_referencia,
        resumo=frase_de_resumo(ata.texto),
        total_ancoras=contar_ancoras(achados),
        calibrada=ata.categoria is CategoriaDaAta.COPOM,
        demo_disponivel=demo_disponivel,
        extracao_completa=extracao_completa(ata, achados),
        qualitativa=sem_numero(ata, achados),
    )
