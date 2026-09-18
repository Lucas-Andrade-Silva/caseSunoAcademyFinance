"""Gemini Flash via REST (httpx). Gera. O nome do modelo vem de GEMINI_MODELO.

ADR 0007.

Conferido na documentação oficial em 18/09/2026:

- ``POST {base}/v1beta/models/{modelo}:generateContent`` com o cabeçalho ``x-goog-api-key``;
  ``systemInstruction`` fora de ``contents``; ``generationConfig`` com ``temperature``,
  ``maxOutputTokens``, ``responseMimeType`` e ``responseSchema``; tokens em
  ``usageMetadata`` (https://ai.google.dev/api/generate-content).
- ``responseSchema`` é um **subconjunto do OpenAPI 3.0 Schema**, não JSON Schema inteiro
  (https://ai.google.dev/gemini-api/docs/structured-output). Ele não conhece ``$defs`` nem
  ``$ref`` na grafia com cifrão — o Schema do protocolo usa ``defs``/``ref`` — e ignora
  palavras de validação que o pydantic emite. Por isso ``adaptar_schema`` existe: é função
  pura, testada, que resolve as referências e joga fora o que a API não aceita.
- Gemini 2.0 exige ``propertyOrdering`` explícito para a ordem das propriedades; nas
  versões novas é inofensivo. Emitimos sempre.
- O controle do "pensar" fica em ``generationConfig.thinkingConfig``, e **qual campo usar
  depende da família do modelo**: a série 2.5 só aceita ``thinkingBudget`` (0 desliga, -1
  dinâmico) e "don't support thinkingLevel"; de Gemini 3 em diante vale ``thinkingLevel``
  (low/medium/high). Tokens de raciocínio saem em ``usageMetadata.thoughtsTokenCount``
  (https://ai.google.dev/gemini-api/docs/generate-content/thinking).
"""

from __future__ import annotations

import base64
import re
import time
from typing import Any, Mapping

import httpx

from suno.dominio import (
    CotaEsgotada,
    ErroProvedor,
    EsgotamentoDeCota,
    PedidoLLM,
    RespostaLLM,
    RespostaMalformada,
)
from suno.provedores._openai_compat import (
    TEMPO_LIMITE_S,
    corpo_em_json,
    espera_do_cabecalho,
    esgotamento_do_texto,
    resumir,
    segundos_da_duracao,
    texto_do_erro,
)
from suno.provedores.base import ProvedorBase

BASE_PADRAO = "https://generativelanguage.googleapis.com"

# O que o Schema do Gemini aceita (subconjunto do OpenAPI 3.0). Qualquer outra palavra do
# JSON Schema do pydantic é descartada em vez de arriscar um 400 no meio da Matriz.
CAMPOS_DO_SCHEMA = frozenset(
    {
        "type",
        "format",
        "title",
        "description",
        "nullable",
        "enum",
        "items",
        "properties",
        "required",
        "propertyOrdering",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "pattern",
        "minLength",
        "maxLength",
        "anyOf",
    }
)


# ``PedidoLLM.esforco_raciocinio`` -> ``thinkingLevel`` (Gemini 3 em diante).
ESFORCO_NO_GEMINI = {"baixo": "low", "medio": "medium", "alto": "high"}

# Na série 2.5 o controle é numérico e o teto é por modelo; a única tradução que não
# depende de constante específica de modelo é desligar o pensar.
SEM_RACIOCINIO = 0

_NUMERO_DA_FAMILIA = re.compile(r"(\d+)\.(\d+)")


def configuracao_de_raciocinio(modelo: str, esforco: str | None) -> dict[str, Any] | None:
    """Traduz o esforço declarado para o campo certo da família do modelo. Pura.

    Gemini 2.5 não conhece ``thinkingLevel``; Gemini 3 desaconselha ``thinkingBudget``.
    Como o nome do modelo é configuração (ADR 0007), a família sai do próprio nome, não de
    uma constante. Sem esforço declarado — ou sem família reconhecível — não manda nada, e
    o provedor usa o padrão dele (pensar dinâmico).
    """
    if not esforco:
        return None
    achado = _NUMERO_DA_FAMILIA.search(modelo or "")
    if achado is None:
        return None
    if int(achado.group(1)) >= 3:
        return {"thinkingLevel": ESFORCO_NO_GEMINI[esforco]}
    # Série 2.x: só "baixo" tem tradução honesta (desliga); médio e alto ficam no dinâmico.
    return {"thinkingBudget": SEM_RACIOCINIO} if esforco == "baixo" else None


def adaptar_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Traduz o JSON Schema do pydantic para o dialeto do ``responseSchema``.

    Pura e sem estado: resolve ``$ref``/``$defs`` inline, transforma ``const`` em ``enum``,
    dobra ``anyOf`` com ``null`` em ``nullable`` e descarta o resto.
    """
    definicoes: dict[str, Any] = {}
    for chave in ("$defs", "definitions"):
        achadas = schema.get(chave)
        if isinstance(achadas, Mapping):
            definicoes.update(achadas)
    return _converter(schema, definicoes, ())


def _converter(no: Any, definicoes: Mapping[str, Any], em_curso: tuple[str, ...]) -> Any:
    if isinstance(no, list):
        return [_converter(parte, definicoes, em_curso) for parte in no]
    if not isinstance(no, Mapping):
        return no

    referencia = no.get("$ref")
    if isinstance(referencia, str):
        nome = referencia.rsplit("/", 1)[-1]
        if nome in em_curso or nome not in definicoes:
            # Schema recursivo: o Gemini não tem como representá-lo, então vira objeto livre.
            return {"type": "object"}
        return _converter(definicoes[nome], definicoes, em_curso + (nome,))

    escolhas = no.get("anyOf") or no.get("oneOf")
    if isinstance(escolhas, list):
        return _converter_escolhas(no, escolhas, definicoes, em_curso)

    convertido: dict[str, Any] = {}
    for chave, valor in no.items():
        if chave == "const":
            convertido["enum"] = [valor]
            convertido.setdefault("type", _nome_do_valor(valor))
        elif chave == "properties" and isinstance(valor, Mapping):
            convertido["properties"] = {
                nome: _converter(sub, definicoes, em_curso) for nome, sub in valor.items()
            }
            convertido["propertyOrdering"] = list(valor)
        elif chave == "items":
            convertido["items"] = _converter(valor, definicoes, em_curso)
        elif chave in CAMPOS_DO_SCHEMA:
            convertido[chave] = valor
    if convertido.get("properties") is not None:
        convertido.setdefault("type", "object")
    if convertido.get("items") is not None:
        convertido.setdefault("type", "array")
    if isinstance(convertido.get("required"), list) and isinstance(convertido.get("properties"), Mapping):
        convertido["required"] = [n for n in convertido["required"] if n in convertido["properties"]]
    return convertido


def _converter_escolhas(
    no: Mapping[str, Any],
    escolhas: list[Any],
    definicoes: Mapping[str, Any],
    em_curso: tuple[str, ...],
) -> dict[str, Any]:
    """``X | None`` do pydantic vira ``nullable`` — o Gemini não tem união com null."""
    aceita_nulo = any(isinstance(e, Mapping) and e.get("type") == "null" for e in escolhas)
    reais = [e for e in escolhas if not (isinstance(e, Mapping) and e.get("type") == "null")]
    convertidas = [_converter(e, definicoes, em_curso) for e in reais]
    extras = {c: v for c, v in no.items() if c in CAMPOS_DO_SCHEMA and c != "anyOf"}
    if len(convertidas) == 1:
        resultado = {**convertidas[0], **extras}
    elif convertidas:
        resultado = {**extras, "anyOf": convertidas}
    else:
        resultado = {**extras, "type": "string"}
    if aceita_nulo:
        resultado["nullable"] = True
    return resultado


def _nome_do_valor(valor: Any) -> str:
    if isinstance(valor, bool):
        return "boolean"
    if isinstance(valor, int):
        return "integer"
    if isinstance(valor, float):
        return "number"
    if isinstance(valor, list):
        return "array"
    if isinstance(valor, Mapping):
        return "object"
    return "string"


def interpretar_429(
    status: int,
    cabecalhos: Mapping[str, str],
    corpo: str | bytes | Mapping[str, Any] | None,
) -> CotaEsgotada:
    """Função pura: 429 ``RESOURCE_EXHAUSTED`` -> ``CotaEsgotada``.

    O corpo do Google carrega ``error.details`` no padrão google.rpc: ``QuotaFailure``
    traz ``quotaId``/``quotaMetric`` (ex.: ``GenerateRequestsPerDayPerProjectPerModel-FreeTier``,
    onde ``PerDay`` vs ``PerMinute`` é a pista) e ``RetryInfo`` traz ``retryDelay`` ("12s").
    """
    dados = corpo_em_json(corpo)
    erro = dados.get("error") if isinstance(dados.get("error"), Mapping) else {}
    pistas: list[str] = []
    espera: float | None = None
    for detalhe in erro.get("details") or []:
        if not isinstance(detalhe, Mapping):
            continue
        marca = str(detalhe.get("@type", ""))
        if marca.endswith("QuotaFailure"):
            for violacao in detalhe.get("violations") or []:
                if isinstance(violacao, Mapping):
                    pistas.append(str(violacao.get("quotaId", "")))
                    pistas.append(str(violacao.get("quotaMetric", "")))
        elif marca.endswith("RetryInfo"):
            espera = segundos_da_duracao(str(detalhe.get("retryDelay") or ""))
    texto = texto_do_erro(dados, corpo)
    esgotamento = esgotamento_do_texto(" ".join(pistas))
    if esgotamento is EsgotamentoDeCota.DESCONHECIDO:
        # quotaId vem grudado ("PerDayPerProject"); o texto da mensagem usa "per day".
        esgotamento = esgotamento_do_texto(texto)
    if espera is None:
        espera = espera_do_cabecalho(cabecalhos)
    return CotaEsgotada(
        "gemini",
        esgotamento,
        espera,
        mensagem=f"HTTP {status} ({esgotamento}): {resumir(texto)}",
    )


class ProvedorGemini(ProvedorBase):
    nome = "gemini"

    def __init__(
        self,
        chave: str,
        modelo: str,
        *,
        cliente: httpx.Client | None = None,
        base_url: str | None = None,
    ) -> None:
        if not chave:
            raise ErroProvedor(self.nome, "chave de API ausente")
        if not modelo:
            raise ErroProvedor(self.nome, "nome de modelo ausente (vem do .env, nunca do código)")
        self.modelo = modelo
        self._chave = chave
        self._base = (base_url or BASE_PADRAO).rstrip("/")
        self._cliente = cliente or httpx.Client(timeout=httpx.Timeout(TEMPO_LIMITE_S))

    # -- tradução -----------------------------------------------------------

    def caminho(self) -> str:
        nome_do_modelo = self.modelo.split("/")[-1] if self.modelo.startswith("models/") else self.modelo
        return f"{self._base}/v1beta/models/{nome_do_modelo}:generateContent"

    def corpo_do_pedido(self, pedido: PedidoLLM) -> dict[str, Any]:
        conteudos: list[dict[str, Any]] = []
        partes_de_sistema: list[dict[str, Any]] = []
        for mensagem in pedido.mensagens:
            partes: list[dict[str, Any]] = []
            if mensagem.texto:
                partes.append({"text": mensagem.texto})
            if mensagem.imagem_png is not None:
                partes.append(
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64.b64encode(mensagem.imagem_png).decode("ascii"),
                        }
                    }
                )
            if mensagem.autor == "sistema":
                partes_de_sistema.extend(partes)
            else:
                conteudos.append({"role": "user", "parts": partes})
        geracao: dict[str, Any] = {
            "temperature": pedido.temperatura,
            "maxOutputTokens": pedido.max_tokens,
        }
        raciocinio = configuracao_de_raciocinio(self.modelo, pedido.esforco_raciocinio)
        if raciocinio is not None:
            geracao["thinkingConfig"] = raciocinio
        if pedido.schema_saida:
            geracao["responseMimeType"] = "application/json"
            geracao["responseSchema"] = adaptar_schema(pedido.schema_saida)
        corpo: dict[str, Any] = {"contents": conteudos, "generationConfig": geracao}
        if partes_de_sistema:
            corpo["systemInstruction"] = {"parts": partes_de_sistema}
        return corpo

    def resposta_do_corpo(self, dados: Mapping[str, Any], latencia_s: float) -> RespostaLLM:
        candidatos = dados.get("candidates") or []
        if not candidatos:
            bloqueio = (dados.get("promptFeedback") or {}).get("blockReason")
            if bloqueio:
                raise ErroProvedor(self.nome, f"pedido bloqueado pelo filtro: {bloqueio}")
            raise RespostaMalformada(self.nome, "resposta sem 'candidates'")
        primeiro = candidatos[0] if isinstance(candidatos[0], dict) else {}
        partes = (primeiro.get("content") or {}).get("parts") or []
        # Partes marcadas com "thought" são raciocínio, não resposta: não entram no texto.
        texto = "".join(
            str(parte.get("text", ""))
            for parte in partes
            if isinstance(parte, Mapping) and not parte.get("thought")
        )
        if not texto:
            motivo = primeiro.get("finishReason")
            if motivo == "MAX_TOKENS":
                raise RespostaMalformada(
                    self.nome,
                    "o teto de tokens acabou antes do texto: o 'pensar' gasta o mesmo "
                    "maxOutputTokens (pesquisa §4)",
                )
            raise RespostaMalformada(self.nome, f"resposta sem texto (finishReason={motivo})")
        uso = dados.get("usageMetadata") or {}
        # No Gemini o "pensar" é contado à parte de candidatesTokenCount, não dentro dele:
        # sem este campo, o consumo que mais estoura cota some da contabilidade.
        return RespostaLLM(
            texto=texto,
            provedor=self.nome,
            modelo=str(dados.get("modelVersion") or self.modelo),
            tokens_entrada=int(uso.get("promptTokenCount") or 0),
            tokens_saida=int(uso.get("candidatesTokenCount") or 0),
            tokens_raciocinio=int(uso.get("thoughtsTokenCount") or 0),
            latencia_s=latencia_s,
        )

    # -- contrato -----------------------------------------------------------

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        comeco = time.perf_counter()
        try:
            resposta_http = self._cliente.post(
                self.caminho(),
                headers={"x-goog-api-key": self._chave, "Content-Type": "application/json"},
                json=self.corpo_do_pedido(pedido),
            )
        except httpx.HTTPError as erro:
            raise ErroProvedor(self.nome, f"falha de transporte: {self.ocultar(str(erro))}") from None
        latencia_s = time.perf_counter() - comeco
        if resposta_http.status_code == 429:
            # O servidor pode ecoar a requisição no corpo: a mensagem passa pelo filtro.
            cota = interpretar_429(resposta_http.status_code, resposta_http.headers, resposta_http.text)
            raise CotaEsgotada(self.nome, cota.esgotamento, cota.espera_s, self.ocultar(cota.mensagem))
        if resposta_http.status_code >= 400:
            raise ErroProvedor(
                self.nome,
                f"HTTP {resposta_http.status_code}: {resumir(self.ocultar(resposta_http.text))}",
            )
        try:
            dados = resposta_http.json()
        except ValueError as erro:
            raise RespostaMalformada(self.nome, f"corpo não é JSON: {resumir(self.ocultar(str(erro)))}") from None
        if not isinstance(dados, dict):
            raise RespostaMalformada(self.nome, "corpo JSON não é um objeto")
        return self.resposta_do_corpo(dados, latencia_s)

    def ocultar(self, texto: str) -> str:
        """A chave vai em cabeçalho e nunca em URL; ainda assim, nunca sai em exceção."""
        return texto.replace(self._chave, "***") if self._chave else texto

    def fechar(self) -> None:
        self._cliente.close()
