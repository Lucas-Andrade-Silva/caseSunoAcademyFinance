"""Os moldes de prompt por Audiência e Formato. O número entra por preenchimento de
`{{chave}}` a partir das Âncoras, nunca por escrita livre. O alvo interno de Flesch-BR é
mais folgado que o Limiar (overshoot calibrado, ADR 0002).

ADR 0011.
"""

from __future__ import annotations

from suno.dominio import Ancoras, Audiencia, Correcao, Formato, PedidoLLM


def montar_pedido(
    ata_texto: str,
    ancoras: Ancoras,
    audiencia: Audiencia,
    formato: Formato,
    rodada: int = 0,
    correcoes: list[Correcao] | None = None,
) -> PedidoLLM:
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0011")


def preencher(texto_com_moldes: str, ancoras: Ancoras) -> tuple[str, list[str]]:
    """Substitui `{{chave}}` pela citação da Âncora. Devolve o texto e as chaves usadas."""
    raise NotImplementedError("Etapa 2, agente 8 — ADR 0011")
