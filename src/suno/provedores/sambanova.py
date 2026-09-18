"""SambaNova Cloud via REST compatível com OpenAI (httpx). Reserva.

ADR 0007.

Conferido na documentação oficial em 18/09/2026:

- ``POST https://api.sambanova.ai/v1/chat/completions``, dialeto OpenAI, ``max_tokens``.
- ``response_format`` aceita ``json_object`` e ``json_schema``; ``strict: true`` "é aceito
  sem erro, mas não muda o comportamento", então vale o modo best-effort
  (https://docs.sambanova.ai/docs/en/features/function-calling). Mandamos ``json_schema``
  com ``strict: false``: quando o modelo escorregar, quem reprova é o
  ``RespostaMalformada`` do ``base.py`` e o roteador troca de provedor.
- ``reasoning_effort`` **não** aparece na documentação: a página de compatibilidade com a
  OpenAI lista o que é ignorado e o que muda, e não menciona o parâmetro
  (https://docs.sambanova.ai/docs/en/features/openai-compatibility). Só há anúncio na
  comunidade da própria SambaNova sobre "reasoning effort control" no gpt-oss-120b. Como a
  regra é seguir a doc oficial, ``esforco_raciocinio`` é ignorado aqui — virar
  ``envia_esforco_raciocinio = True`` é uma linha no dia em que a doc confirmar.
- Cota do tier gratuito: 20 RPM, 20 RPD, 200k TPD
  (https://docs.sambanova.ai/docs/en/models/rate-limits). A documentação **não** publica o
  texto do 429, então sem pista o esgotamento fica DESCONHECIDO — e o roteador trata
  DESCONHECIDO como diário, que é a leitura conservadora do ADR 0007.
"""

from __future__ import annotations

from typing import Any, Mapping

from suno.dominio import CotaEsgotada
from suno.provedores._openai_compat import (
    ProvedorNoDialetoOpenAI,
    interpretar_429_no_dialeto_openai,
)

BASE_PADRAO = "https://api.sambanova.ai/v1"


def interpretar_429(
    status: int,
    cabecalhos: Mapping[str, str],
    corpo: str | bytes | Mapping[str, Any] | None,
) -> CotaEsgotada:
    """Função pura: ``retry-after`` e o texto da mensagem; sem pista, DESCONHECIDO.

    Os cabeçalhos ``x-ratelimit-*`` da Groq não estão documentados aqui, então não valem
    como pista: ler cota de cabeçalho que a SambaNova não promete é adivinhação.
    """
    return interpretar_429_no_dialeto_openai(
        "sambanova", status, cabecalhos, corpo, ler_cabecalhos_de_cota=False
    )


class ProvedorSambaNova(ProvedorNoDialetoOpenAI):
    nome = "sambanova"
    base_padrao = BASE_PADRAO
    campo_do_teto = "max_tokens"
    schema_estrito = False
    envia_esforco_raciocinio = False

    def interpretar_429(
        self,
        status: int,
        cabecalhos: Mapping[str, str],
        corpo: str | bytes | Mapping[str, Any] | None,
    ) -> CotaEsgotada:
        return interpretar_429(status, cabecalhos, corpo)
