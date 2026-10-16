"""O catálogo de Origens: o que existe, o que está ligado e o que ainda não chegou.

``data/fontes/catalogo.json`` é versionado e traz as Origens com o estado padrão. O que a pessoa
liga e desliga na interface vai para ``data/fontes/preferencias.json``, que fica fora do git:
ligar a CVM não deixa o repositório sujo.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, ValidationError

from suno.dominio import CategoriaDaAta

_registro = logging.getLogger(__name__)

PASTA_FONTES = Path("data/fontes")
NOME_DO_CATALOGO = "catalogo.json"
NOME_DAS_PREFERENCIAS = "preferencias.json"

PESO_DA_CATEGORIA: dict[CategoriaDaAta, int] = {
    CategoriaDaAta.COPOM: 3,
    CategoriaDaAta.COMUNICADO_RELEVANTE: 2,
    CategoriaDaAta.RELEASE: 2,
    CategoriaDaAta.IMPORTADA: 1,
    CategoriaDaAta.UNIDA: 1,
}
"""Desempate da sugestão: o Copom é a Origem calibrada, depois as institucionais, depois o resto."""


class Origem(BaseModel):
    id: str
    nome: str
    categoria: CategoriaDaAta
    ativa: bool = False
    disponivel: bool = True
    aviso: str | None = None


class OrigemDesconhecida(LookupError):
    """Não há Origem com esse identificador no catálogo."""


class OrigemIndisponivel(ValueError):
    """A Origem existe mas ainda não pode ser ligada (ex.: Releases da B3, "em breve")."""


CATALOGO_PADRAO: tuple[Origem, ...] = (
    Origem(id="copom", nome="Atas do Copom", categoria=CategoriaDaAta.COPOM, ativa=True),
    Origem(
        id="cvm_fatos_relevantes",
        nome="Fatos Relevantes da CVM",
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
    ),
    Origem(
        id="cvm_demonstracoes",
        nome="DFP, ITR e Formulários da CVM",
        categoria=CategoriaDaAta.RELEASE,
        ativa=True,
    ),
    Origem(
        id="bcb_relatorios",
        nome="Relatórios de Inflação e de Estabilidade",
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
        ativa=True,
    ),
    Origem(
        id="bcb_resolucoes",
        nome="Resoluções do CMN e do BCB",
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
        ativa=True,
    ),
    Origem(
        id="b3_oficios",
        nome="Ofícios e comunicados da B3",
        categoria=CategoriaDaAta.COMUNICADO_RELEVANTE,
        ativa=True,
    ),
    Origem(
        id="importados",
        nome="Documentos importados",
        categoria=CategoriaDaAta.IMPORTADA,
        ativa=True,
    ),
)


def _ler_json(caminho: Path) -> dict | None:
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as erro:
        _registro.warning("%s ilegível, usando o padrão: %s", caminho, erro)
        return None
    return bruto if isinstance(bruto, dict) else None


def _base(pasta_fontes: Path) -> list[Origem]:
    bruto = _ler_json(Path(pasta_fontes) / NOME_DO_CATALOGO)
    if bruto is None:
        return [o.model_copy() for o in CATALOGO_PADRAO]
    try:
        return [Origem.model_validate(o) for o in bruto.get("origens", [])]
    except ValidationError as erro:
        _registro.warning("catalogo.json inválido, usando o padrão: %s", erro)
        return [o.model_copy() for o in CATALOGO_PADRAO]


def _preferencias(pasta_fontes: Path) -> dict[str, bool]:
    bruto = _ler_json(Path(pasta_fontes) / NOME_DAS_PREFERENCIAS) or {}
    ativas = bruto.get("ativas", {})
    if not isinstance(ativas, dict):
        return {}
    return {str(id_): bool(valor) for id_, valor in ativas.items()}


def carregar_catalogo(pasta_fontes: Path) -> list[Origem]:
    """O catálogo com as preferências por cima. Origem indisponível nunca fica ligada."""
    preferencias = _preferencias(pasta_fontes)
    origens = _base(pasta_fontes)
    for origem in origens:
        if origem.id in preferencias:
            origem.ativa = preferencias[origem.id]
        if not origem.disponivel:
            origem.ativa = False
    return origens


def alternar(pasta_fontes: Path, identificador: str, ativa: bool) -> Origem:
    """Liga ou desliga uma Origem e grava a preferência. Devolve a Origem já atualizada."""
    origens = {o.id: o for o in carregar_catalogo(pasta_fontes)}
    origem = origens.get(identificador)
    if origem is None:
        raise OrigemDesconhecida(f"Origem {identificador!r} não existe no catálogo")
    if not origem.disponivel:
        raise OrigemIndisponivel(f"{origem.nome} está indisponível: {origem.aviso or 'em breve'}")
    preferencias = _preferencias(pasta_fontes)
    preferencias[identificador] = ativa
    pasta = Path(pasta_fontes)
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / NOME_DAS_PREFERENCIAS).write_text(
        json.dumps({"ativas": preferencias}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    origem.ativa = ativa
    return origem
