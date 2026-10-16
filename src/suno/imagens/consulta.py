"""Busca de imagens própria para o mercado financeiro (ADR 0033).

Digitar "B3" no buscador traz a vitamina B3. Aqui o assunto do slide vira um ``PlanoDeBusca``:
as consultas certas (``B3 bolsa de valores sede``, depois ``B3 bolsa de valores logo``), o que um
resultado precisa conter para valer (``exigir``) e o que o desclassifica (``proibidas``). Os
dados vêm do catálogo de assuntos visuais (``assuntos.json``), que a pessoa com conhecimento de
mercado mantém. Assunto fora do catálogo cai numa busca genérica de mercado financeiro.

``pontuar`` julga um resultado só pelo texto (nome do arquivo, título, página de origem), sem
LLM e sem baixar nada. Quem pontua alto é aprovado direto, quem cai em palavra proibida é
descartado, e só o resto vai ao juiz de visão.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from suno.imagens.texto import sem_acento, termos
from suno.imagens.web import CandidatoDeImagem

CAMINHO_DO_CATALOGO = Path(__file__).with_name("assuntos.json")

PONTOS_NO_ARQUIVO = 3  # o nome do arquivo da imagem cita o assunto
PONTOS_NO_TITULO = 2
PONTOS_NA_PAGINA = 1
PONTOS_DE_CONTEXTO = 1  # o título fala de mercado, bolsa, juros...
PONTOS_DE_DOMINIO = 1  # site de confiança ou o oficial do assunto
PONTOS_PARA_APROVAR = 5
# Empresa e instituição têm nome próprio: o nome no título da matéria é evidência boa de que a imagem
# é o logo ou a sede. Conceito e setor ("China", "inflação") aparecem em título de matéria com foto
# genérica: ali só o nome no arquivo da imagem basta para aprovar sem o juiz.
TIPOS_QUE_ACEITAM_O_TITULO = frozenset({"empresa", "instituicao"})
MAXIMO_DE_PROIBIDAS_NA_BUSCA = 4  # cada '-palavra' estreita a busca; passar disso esvazia o resultado

_PALAVRAS_DE_FORMA = frozenset(
    "sede fachada predio edificio foto fotos imagem imagens logo logotipo logomarca marca simbolo".split()
)
_PEDIDO_DE_LOGO = frozenset("logo logotipo logomarca marca simbolo".split())
_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")

Decisao = Literal["aprovar", "duvida", "descartar"]


@dataclass(frozen=True)
class PlanoDeBusca:
    """Como buscar e como julgar as imagens de um assunto."""

    assunto: str
    id: str  # id do catálogo, ou "generico" quando o assunto não está lá
    consultas: tuple[str, ...]
    tipo: str = "generico"  # empresa, instituicao, conceito, setor ou generico
    exigir: tuple[tuple[str, ...], ...] = ()  # cada item é uma frase em termos normalizados; vale qualquer uma
    proibidas: tuple[str, ...] = ()  # frases normalizadas
    dominios: tuple[str, ...] = ()
    contexto: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Triagem:
    decisao: Decisao
    pontos: int
    motivo: str


def _normalizar(texto: str) -> str:
    return _NAO_ALFANUMERICO.sub(" ", sem_acento(texto)).strip()


def _tokens_de_url(url: str) -> list[str]:
    return _normalizar(url).split()


@lru_cache(maxsize=1)
def _catalogo(caminho: Path = CAMINHO_DO_CATALOGO) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _entrada_para(assunto: str, catalogo: dict) -> dict | None:
    """A entrada cuja chave aparece, como frase inteira, no assunto; vence a chave mais longa."""
    texto = f" {_normalizar(assunto)} "
    melhor: tuple[int, dict] | None = None
    for entrada in catalogo["assuntos"]:
        for chave in entrada["chaves"]:
            frase = _normalizar(chave)
            if frase and re.search(rf" {re.escape(frase)}s? ", texto):
                if melhor is None or len(frase) > melhor[0]:
                    melhor = (len(frase), entrada)
    return melhor[1] if melhor else None


def _consultas(entrada: dict, quer_logo: bool) -> list[str]:
    contexto = entrada.get("contexto", "")
    modelos = entrada.get("consultas") or [
        "{nome} {contexto} sede fachada",
        "{nome} {contexto} logo",
    ]
    consultas = [" ".join(m.format(nome=entrada["nome"], contexto=contexto).split()) for m in modelos]
    if quer_logo and len(consultas) > 1:
        logos = [c for c in consultas if "logo" in c.split()]
        consultas = logos + [c for c in consultas if c not in logos]
    return consultas


def _com_proibidas(consulta: str, proibidas: tuple[str, ...]) -> str:
    """Acrescenta '-palavra' (só palavras soltas) para o buscador não trazer o homônimo."""
    palavras = [p for p in proibidas if " " not in p][:MAXIMO_DE_PROIBIDAS_NA_BUSCA]
    return " ".join([consulta, *(f"-{p}" for p in palavras)])


def planejar(assunto: str, caminho: Path = CAMINHO_DO_CATALOGO) -> PlanoDeBusca:
    """O plano de busca do assunto (o texto de ``Slide.imagem``), do catálogo ou genérico."""
    catalogo = _catalogo(caminho)
    quer_logo = bool(set(_normalizar(assunto).split()) & _PEDIDO_DE_LOGO)
    globais = tuple(_normalizar(p) for p in catalogo.get("proibidas_globais", []))
    contexto_global = frozenset(termos(" ".join(catalogo.get("contexto_financeiro", []))))
    entrada = _entrada_para(assunto, catalogo)
    if entrada is None:
        # O núcleo mantém maiúscula e acento do slide: o buscador acerta mais com o nome como é escrito.
        nucleo = " ".join(p for p in assunto.split() if _normalizar(p) not in _PALAVRAS_DE_FORMA) or assunto
        base = [f"{nucleo} mercado financeiro Brasil", f"{nucleo} economia Brasil"]
        return PlanoDeBusca(
            assunto=assunto,
            id="generico",
            tipo="generico",
            consultas=tuple(_com_proibidas(c, globais) for c in base),
            exigir=(tuple(termos(nucleo)),) if termos(nucleo) else (),
            proibidas=globais,
            dominios=tuple(catalogo.get("dominios_de_confianca", [])),
            contexto=contexto_global,
        )
    proibidas = tuple(dict.fromkeys([*(_normalizar(p) for p in entrada.get("proibidas", [])), *globais]))
    return PlanoDeBusca(
        assunto=assunto,
        id=entrada["id"],
        tipo=entrada["tipo"],
        consultas=tuple(_com_proibidas(c, proibidas) for c in _consultas(entrada, quer_logo)),
        exigir=tuple(tuple(termos(frase)) for frase in entrada.get("exigir", []) if termos(frase)),
        proibidas=proibidas,
        dominios=tuple([*entrada.get("dominios", []), *catalogo.get("dominios_de_confianca", [])]),
        contexto=contexto_global | frozenset(termos(entrada.get("contexto", ""))),
    )


def _singular(termo: str) -> str:
    """Mesma regra de ``termos()``: o plural simples some dos dois lados da comparação."""
    return termo[:-1] if len(termo) > 3 and termo.endswith("s") else termo


def _tem_frase(texto: str, frase: str) -> bool:
    return f" {frase} " in f" {texto} "


def _cita(tokens: list[str], frases: tuple[tuple[str, ...], ...]) -> bool:
    """Alguma das frases (todos os termos, na ordem do texto) aparece nos tokens?"""
    normalizados = {_singular(t) for t in tokens}
    return any(all(t in normalizados for t in frase) for frase in frases)


def _dominio_vale(url: str, dominios: tuple[str, ...]) -> bool:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in dominios)


def cita_assunto(texto: str, plano: PlanoDeBusca) -> bool:
    """O texto (tags e título de uma foto já guardada) cita o assunto do plano? Sem ``exigir``, vale tudo."""
    if not plano.exigir:
        return True
    return _cita(_normalizar(texto).split(), plano.exigir)


def pontuar(candidato: CandidatoDeImagem, plano: PlanoDeBusca) -> Triagem:
    """Julga o resultado só pelo texto: arquivo, título e página de origem."""
    arquivo = _tokens_de_url(urlparse(candidato.url_imagem).path)
    titulo = _tokens_de_url(candidato.titulo)
    pagina = _tokens_de_url(candidato.url_pagina)
    tudo = _normalizar(" ".join([candidato.titulo, candidato.url_pagina, candidato.url_imagem]))

    for frase in plano.proibidas:
        if frase and _tem_frase(tudo, frase):
            return Triagem("descartar", -PONTOS_PARA_APROVAR, f"palavra proibida: {frase}")

    pontos, motivos = 0, []
    no_arquivo = False
    if plano.exigir:
        for tokens, valor, nome in (
            (arquivo, PONTOS_NO_ARQUIVO, "arquivo"),
            (titulo, PONTOS_NO_TITULO, "título"),
            (pagina, PONTOS_NA_PAGINA, "página"),
        ):
            if _cita(tokens, plano.exigir):
                pontos += valor
                motivos.append(nome)
                no_arquivo = no_arquivo or nome == "arquivo"
    if plano.contexto & {_singular(t) for t in titulo + pagina}:
        pontos += PONTOS_DE_CONTEXTO
        motivos.append("contexto")
    if _dominio_vale(candidato.url_pagina, plano.dominios) or _dominio_vale(candidato.url_imagem, plano.dominios):
        pontos += PONTOS_DE_DOMINIO
        motivos.append("domínio")

    aceita = no_arquivo or plano.tipo in TIPOS_QUE_ACEITAM_O_TITULO
    decisao: Decisao = "aprovar" if pontos >= PONTOS_PARA_APROVAR and aceita else "duvida"
    if pontos >= PONTOS_PARA_APROVAR and not aceita:
        motivos.append("(conceito sem o nome no arquivo: vai ao juiz)")
    return Triagem(decisao, pontos, "+".join(motivos) or "sem indício no texto")
