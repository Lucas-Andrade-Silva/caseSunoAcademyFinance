"""Groq via REST compatível com OpenAI (httpx). Julga. Distingue 'per minute' de 'per day' no 429.

ADR 0007.

Conferido na documentação oficial em 18/09/2026:

- ``POST https://api.groq.com/openai/v1/chat/completions``; ``max_tokens`` está depreciado
  em favor de ``max_completion_tokens`` (https://console.groq.com/docs/api-reference).
- ``openai/gpt-oss-120b`` — o modelo do ``.env.example`` — está na lista de modelos com
  ``strict: true``, decodificação restrita que garante o schema
  (https://console.groq.com/docs/structured-outputs). Por isso aqui é ``json_schema``
  estrito, e não ``json_object`` com o schema no prompt.
- O 429 traz ``retry-after`` e os cabeçalhos ``x-ratelimit-*``, onde o cap de requisições é
  diário e o de tokens é por minuto (https://console.groq.com/docs/rate-limits). O texto
  exato da mensagem não está na documentação: ver o relatório do agente 6.
- ``reasoning_effort`` aceita ``low``/``medium``/``high`` nos modelos gpt-oss, incluindo o
  ``openai/gpt-oss-120b`` do ``.env.example`` (https://console.groq.com/docs/reasoning).
  É por onde ``PedidoLLM.esforco_raciocinio`` entra.
"""

from __future__ import annotations

from typing import Any, Mapping

from suno.dominio import CotaEsgotada
from suno.provedores._openai_compat import (
    ProvedorNoDialetoOpenAI,
    interpretar_429_no_dialeto_openai,
)

BASE_PADRAO = "https://api.groq.com/openai/v1"


def interpretar_429(
    status: int,
    cabecalhos: Mapping[str, str],
    corpo: str | bytes | Mapping[str, Any] | None,
) -> CotaEsgotada:
    """Função pura, testável sem transporte: 429 cru -> ``CotaEsgotada``.

    A Groq é a que mais entrega pista: "tokens per minute (TPM)" ou "requests per day
    (RPD)" no texto, "Please try again in 2m59.56s" para a espera, e os cabeçalhos de cota
    como segunda pista quando o texto não diz.
    """
    return interpretar_429_no_dialeto_openai("groq", status, cabecalhos, corpo)


class ProvedorGroq(ProvedorNoDialetoOpenAI):
    nome = "groq"
    base_padrao = BASE_PADRAO
    campo_do_teto = "max_completion_tokens"
    schema_estrito = True
    envia_esforco_raciocinio = True

    def interpretar_429(
        self,
        status: int,
        cabecalhos: Mapping[str, str],
        corpo: str | bytes | Mapping[str, Any] | None,
    ) -> CotaEsgotada:
        return interpretar_429(status, cabecalhos, corpo)
