"""Extração das Âncoras: roda uma vez por Ata, antes da Matriz. As Âncoras numéricas saem do
extrator determinístico de ingestao/numeros.py; o LLM só localiza e rotula, nunca reescreve valor.

ADR 0011.

## A ordem: regra fixa primeiro, LLM depois

1. ``extrair_numeros`` varre a Ata e devolve os candidatos, cada um já com literal, valor,
   unidade e o trecho literal de onde veio.
2. Regras fixas resolvem as chaves que uma Ata do Copom sempre tem — ``selic_decidida``,
   ``placar_votacao``, ``data_reuniao``, ``numero_reuniao``. Onde a regra fixa acha, a
   Âncora nasce dela e o que o LLM disser sobre aquela chave é ignorado.
3. O LLM recebe a lista numerada dos candidatos e devolve só ``{chave → índice}`` para o
   que ainda falta, mais as Âncoras textuais. **O valor, a unidade e o trecho saem do
   candidato**, nunca do que o LLM escreveu: o campo ``valor_lido`` existe no schema
   justamente para o LLM ter onde escrever o número, e é descartado.

Se o provedor falha, a extração segue só com a regra fixa. Quem decide se isso é aceitável
é a integridade, no Avaliador (ADR 0013) — aqui nada levanta exceção por Ata incompleta.

## A fronteira do ADR 0011 (leia antes de supor cobertura)

Número por extenso sem unidade ("quinze por cento" entra; "nove Células" não) e número
relativo ("acima do projetado no trimestre anterior") **não entram na tabela de Âncoras**.
Eles continuam sujeitos só à Aderência textual, e o Gerador não tem ``{{chave}}`` para
citá-los — o que significa que uma Célula não consegue falar desses números sem cair em
"número fora das Âncoras". A fronteira completa do extrator está no docstring de
``suno.ingestao.numeros``; esta é a metade que importa para quem escreve molde.
"""

from __future__ import annotations

import logging
import re
from typing import Sequence

from pydantic import BaseModel, Field

from suno.dominio import (
    AncoraNumerica,
    Ancoras,
    AncoraTextual,
    Ata,
    ChaveAncora,
    ErroProvedor,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    Unidade,
)
from suno.ingestao.numeros import NumeroEncontrado, extrair_numeros
from suno.provedores.base import Provedor

_registro = logging.getLogger(__name__)

ROTULO_DO_PEDIDO = "extracao"
"""O rótulo que o LLM falso usa para achar a resposta pronta da extração."""

ROTULOS: dict[str, str] = {
    ChaveAncora.SELIC_DECIDIDA: "Selic decidida nesta reunião",
    ChaveAncora.SELIC_ANTERIOR: "Selic antes desta reunião",
    ChaveAncora.VARIACAO_PB: "Variação da Selic em pontos-base",
    ChaveAncora.PLACAR_VOTACAO: "Placar da votação",
    ChaveAncora.DATA_REUNIAO: "Data da reunião",
    ChaveAncora.DATA_PROXIMA_REUNIAO: "Data da próxima reunião",
    ChaveAncora.IPCA_PROJECAO_ANO_CORRENTE: "Projeção do IPCA para o ano corrente",
    ChaveAncora.IPCA_PROJECAO_ANO_SEGUINTE: "Projeção do IPCA para o ano seguinte",
    ChaveAncora.ALVO_INFLACAO: "Alvo de inflação perseguido pelo Copom",
    ChaveAncora.NUMERO_REUNIAO: "Número da reunião do Copom",
}
"""Como um humano chamaria cada chave. Chave livre cai no próprio nome."""

CHAVE_LIVRE = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
"""``AncoraNumerica.chave`` aceita chave fora do enum; só não aceita lixo do LLM."""

CARACTERES_DE_TRECHO = 220
"""Quanto de cada trecho vai no pedido. A Ata inteira vai junto, então nada se perde."""


# ---------------------------------------------------------------------------
# O que o LLM devolve
# ---------------------------------------------------------------------------


class ChaveRotulada(BaseModel):
    """Um candidato apontado por índice. ``valor_lido`` é descartado de propósito."""

    chave: str = Field(description="Chave canônica da Âncora, ex. 'ipca_projecao_ano_corrente'.")
    indice: int = Field(description="Índice do candidato na lista numerada do pedido.")
    valor_lido: str | None = Field(
        default=None,
        description=(
            "O número como você o leu. Campo de conferência: o sistema usa o valor do "
            "candidato apontado por 'indice', nunca este (ADR 0011)."
        ),
    )


class AfirmacaoRotulada(BaseModel):
    """Uma Âncora textual proposta pelo LLM, antes de conferir o trecho contra a Ata."""

    identificador: str
    afirmacao: str
    trecho: str = Field(description="Cópia literal de uma frase da Ata que sustenta a afirmação.")


class RotulagemDaAta(BaseModel):
    """A resposta estruturada do estágio de extração."""

    chaves: list[ChaveRotulada] = Field(default_factory=list)
    afirmacoes: list[AfirmacaoRotulada] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Regra fixa
# ---------------------------------------------------------------------------

_DECISAO_SELIC = re.compile(
    r"decidiu\s+(?:reduzir|elevar|manter|aumentar|diminuir)\s+a\s+taxa\s+b[áa]sica\s+de\s+juros"
    r"\s+(?:para|em)\s+(\d{1,2}(?:,\d+)?)\s*%\s*a\.?\s*a\.?",
    re.IGNORECASE,
)
_PLACAR_EXPLICITO = re.compile(r"por\s+(\d{1,2})\s+votos?\s+a\s+(\d{1,2})", re.IGNORECASE)
_VOTARAM = re.compile(
    r"Votaram\s+por\s+essa\s+decis[ãa]o\s+os\s+seguintes\s+membros[^:.]*:?(?P<nomes>[^.]*)\.",
    re.IGNORECASE | re.DOTALL,
)
_LINHA_DA_DATA = re.compile(r"^[ \t]*Data:[ \t]*(?P<linha>.+)$", re.MULTILINE)
_NUMERO_DA_REUNIAO = re.compile(r"(\d{1,4})\s*ª\s*Reuni[ãa]o", re.IGNORECASE)


def _candidato_em(candidatos: Sequence[NumeroEncontrado], posicao: int) -> NumeroEncontrado | None:
    """O candidato determinístico que cobre esta posição do texto, se houver."""
    for candidato in candidatos:
        if candidato.inicio <= posicao < candidato.fim:
            return candidato
    return None


def _ancora_do_candidato(chave: str, candidato: NumeroEncontrado) -> AncoraNumerica:
    """Tudo vem do candidato: nem a regra fixa nem o LLM mudam valor, unidade ou trecho."""
    return AncoraNumerica(
        chave=chave,
        rotulo=ROTULOS.get(chave, chave.replace("_", " ")),
        valor_literal=candidato.literal,
        valor=candidato.valor,
        unidade=candidato.unidade,
        trecho=re.sub(r"\s+", " ", candidato.trecho).strip(),
        data_iso=candidato.data_iso,
        qualificador=candidato.qualificador,
    )


def _selic_decidida(texto: str, candidatos: Sequence[NumeroEncontrado]) -> AncoraNumerica | None:
    casado = _DECISAO_SELIC.search(texto)
    if casado is None:
        return None
    candidato = _candidato_em(candidatos, casado.start(1))
    if candidato is None:
        return None
    return _ancora_do_candidato(ChaveAncora.SELIC_DECIDIDA, candidato)


def _contar_nomes(bruto: str) -> int:
    """Conta os membros listados depois de "Votaram por essa decisão…"."""
    nomes = [re.sub(r"\s+", " ", parte).strip(" \t\n") for parte in re.split(r",|\be\b", bruto)]
    return sum(1 for nome in nomes if len(nome) > 3 and re.search(r"[A-ZÁÂÃÉÊÍÓÔÕÚÇ]", nome))


def _placar_votacao(texto: str, candidatos: Sequence[NumeroEncontrado]) -> AncoraNumerica | None:
    explicito = _PLACAR_EXPLICITO.search(texto)
    if explicito is not None:
        candidato = _candidato_em(candidatos, explicito.start(1))
        if candidato is not None:
            return _ancora_do_candidato(ChaveAncora.PLACAR_VOTACAO, candidato)
    votaram = _VOTARAM.search(texto)
    if votaram is None:
        return None
    membros = _contar_nomes(votaram.group("nomes"))
    if membros == 0:
        return None
    # Unanimidade: quem votou, votou a favor. O placar nasce da contagem de nomes.
    return AncoraNumerica(
        chave=ChaveAncora.PLACAR_VOTACAO,
        rotulo=ROTULOS[ChaveAncora.PLACAR_VOTACAO],
        valor_literal=f"{membros} a 0",
        valor=float(membros),
        unidade=Unidade.VOTOS,
        trecho=re.sub(r"\s+", " ", votaram.group(0)).strip(),
    )


def _data_reuniao(ata: Ata, candidatos: Sequence[NumeroEncontrado]) -> AncoraNumerica | None:
    """A linha "Data: 4 e 5 de agosto de 2026"; senão, o candidato que bate com os metadados."""
    linha = _LINHA_DA_DATA.search(ata.texto)
    if linha is not None:
        for achado in extrair_numeros(linha.group("linha"), ano_padrao=ata.data_referencia.year):
            if achado.unidade is Unidade.DATA and achado.data_iso is not None:
                candidato = _candidato_em(candidatos, linha.start("linha") + achado.inicio)
                return _ancora_do_candidato(
                    ChaveAncora.DATA_REUNIAO, candidato if candidato is not None else achado
                )
    pelos_metadados = [
        candidato
        for candidato in candidatos
        if candidato.unidade is Unidade.DATA and candidato.data_iso == ata.data_referencia
    ]
    if not pelos_metadados:
        return None
    mais_completo = max(pelos_metadados, key=lambda candidato: len(candidato.literal))
    return _ancora_do_candidato(ChaveAncora.DATA_REUNIAO, mais_completo)


def _numero_reuniao(ata: Ata, candidatos: Sequence[NumeroEncontrado]) -> AncoraNumerica | None:
    casado = _NUMERO_DA_REUNIAO.search(ata.texto)
    if casado is None:
        return None
    candidato = _candidato_em(candidatos, casado.start(1))
    if candidato is None:
        return None
    return _ancora_do_candidato(ChaveAncora.NUMERO_REUNIAO, candidato)


def por_regra_fixa(ata: Ata, candidatos: Sequence[NumeroEncontrado]) -> list[AncoraNumerica]:
    """As chaves que uma Ata do Copom sempre tem, sem LLM nenhum no caminho."""
    achadas = (
        _selic_decidida(ata.texto, candidatos),
        _placar_votacao(ata.texto, candidatos),
        _data_reuniao(ata, candidatos),
        _numero_reuniao(ata, candidatos),
    )
    return [ancora for ancora in achadas if ancora is not None]


# ---------------------------------------------------------------------------
# O LLM rotula
# ---------------------------------------------------------------------------


def _listar_candidatos(candidatos: Sequence[NumeroEncontrado]) -> str:
    linhas = []
    for indice, candidato in enumerate(candidatos):
        trecho = re.sub(r"\s+", " ", candidato.trecho).strip()[:CARACTERES_DE_TRECHO]
        linhas.append(
            f"[{indice}] literal={candidato.literal!r} unidade={candidato.unidade.value!r} "
            f"trecho={trecho!r}"
        )
    return "\n".join(linhas)


def montar_pedido_de_extracao(
    ata: Ata, candidatos: Sequence[NumeroEncontrado], faltantes: Sequence[str]
) -> PedidoLLM:
    """O pedido de rotulagem. Só índice sai daqui; nenhum número volta em prosa."""
    pedidas = "\n".join(f"- {chave}: {ROTULOS.get(chave, chave)}" for chave in faltantes)
    sistema = (
        "Você rotula números que já foram extraídos de uma Ata do Copom. Você não escreve "
        "números: você aponta o índice do candidato certo.\n"
        "Para cada chave pedida, devolva o índice do candidato da lista que corresponde a "
        "ela. Se nenhum candidato corresponder, omita a chave — não invente.\n"
        "Devolva também as afirmações factuais centrais da Ata (Âncoras textuais). O campo "
        "'trecho' precisa ser cópia literal de uma frase da Ata: afirmação com trecho que "
        "não está na Ata é descartada pelo sistema."
    )
    usuario = (
        f"Ata {ata.identificador} — {ata.titulo}\n\n"
        f"Chaves que ainda faltam:\n{pedidas or '- (nenhuma)'}\n\n"
        f"Candidatos numéricos:\n{_listar_candidatos(candidatos)}\n\n"
        f"Texto da Ata:\n{ata.texto}"
    )
    return PedidoLLM(
        papel=PapelLLM.GERADOR,
        rotulo=ROTULO_DO_PEDIDO,
        mensagens=[
            Mensagem(autor="sistema", texto=sistema),
            Mensagem(autor="usuario", texto=usuario),
        ],
        max_tokens=2048,
        temperatura=0.0,
        esforco_raciocinio="baixo",
    )


def _numericas_rotuladas(
    rotulagem: RotulagemDaAta,
    candidatos: Sequence[NumeroEncontrado],
    ja_presentes: set[str],
) -> list[AncoraNumerica]:
    novas: list[AncoraNumerica] = []
    vistas = set(ja_presentes)
    for rotulada in rotulagem.chaves:
        chave = rotulada.chave.strip().lower()
        if chave in vistas:
            continue  # a regra fixa ganha do LLM, e chave repetida entra uma vez só
        if not CHAVE_LIVRE.match(chave):
            _registro.warning("chave fora de padrão na rotulagem: %r", rotulada.chave)
            continue
        if not 0 <= rotulada.indice < len(candidatos):
            _registro.warning("índice inválido para a chave %r: %d", chave, rotulada.indice)
            continue
        novas.append(_ancora_do_candidato(chave, candidatos[rotulada.indice]))
        vistas.add(chave)
    return novas


def _textuais_conferidas(rotulagem: RotulagemDaAta, texto: str) -> list[AncoraTextual]:
    """Âncora textual cujo trecho não aparece literalmente na Ata é descartada."""
    achatado = re.sub(r"\s+", " ", texto)
    conferidas: list[AncoraTextual] = []
    vistos: set[str] = set()
    for afirmacao in rotulagem.afirmacoes:
        trecho = re.sub(r"\s+", " ", afirmacao.trecho).strip()
        if not trecho or trecho not in achatado:
            _registro.warning("Âncora textual descartada: trecho fora da Ata: %r", trecho[:80])
            continue
        if afirmacao.identificador in vistos:
            continue
        vistos.add(afirmacao.identificador)
        conferidas.append(
            AncoraTextual(
                identificador=afirmacao.identificador,
                afirmacao=afirmacao.afirmacao.strip(),
                trecho=trecho,
            )
        )
    return conferidas


# ---------------------------------------------------------------------------
# A porta do módulo
# ---------------------------------------------------------------------------


def extrair_ancoras(ata: Ata, provedor: Provedor) -> Ancoras:
    """A tabela de Âncoras da Ata: regra fixa primeiro, LLM só para rotular (ADR 0011)."""
    candidatos = extrair_numeros(ata.texto, ano_padrao=ata.data_referencia.year)
    numericas = por_regra_fixa(ata, candidatos)
    presentes = {ancora.chave for ancora in numericas}
    faltantes = [chave.value for chave in ChaveAncora if chave.value not in presentes]

    textuais: list[AncoraTextual] = []
    pedido = montar_pedido_de_extracao(ata, candidatos, faltantes)
    try:
        rotulagem = provedor.completar_estruturado(pedido, RotulagemDaAta)
    except ErroProvedor as erro:
        # Extração degradada não é exceção: a integridade decide depois (ADR 0013).
        _registro.warning("extração seguiu só com a regra fixa: %s", erro)
    else:
        numericas.extend(_numericas_rotuladas(rotulagem, candidatos, presentes))
        textuais = _textuais_conferidas(rotulagem, ata.texto)

    return Ancoras(ata=ata.identificador, numericas=numericas, textuais=textuais)
