"""O dialeto OpenAI que Groq e SambaNova falam, num lugar só (ADR 0007).

Os dois expõem ``POST {base}/chat/completions`` com ``Authorization: Bearer``. As duas
diferenças reais, conferidas na documentação oficial em 18/09/2026:

- Groq depreciou ``max_tokens`` em favor de ``max_completion_tokens``
  (https://console.groq.com/docs/api-reference).
- ``strict: true`` só tem efeito na Groq, que faz decodificação restrita para
  ``openai/gpt-oss-120b`` (https://console.groq.com/docs/structured-outputs); na SambaNova
  ele é aceito e ignorado, e vale o modo best-effort
  (https://docs.sambanova.ai/docs/en/features/function-calling).

O schema de saída vem em ``pedido.schema_saida`` e é traduzido a cada chamada: nenhum
cliente guarda binding, e é isso que deixa o roteador trocar de provedor sem perder a
saída estruturada.
"""

from __future__ import annotations

import base64
import json
import re
import time
from typing import Any, Mapping

import httpx

from suno.dominio import (
    CotaEsgotada,
    ErroProvedor,
    EsgotamentoDeCota,
    Mensagem,
    PedidoLLM,
    RespostaLLM,
    RespostaMalformada,
)
from suno.provedores.base import ProvedorBase

# Timeout explícito: sem ele o httpx espera para sempre e a Matriz de nove Células trava.
TEMPO_LIMITE_S = 60.0

# ``Mensagem.autor`` é do domínio; "system"/"user" é do dialeto da API.
PAPEL_NA_API = {"sistema": "system", "usuario": "user"}

# ``PedidoLLM.esforco_raciocinio`` é do domínio; low/medium/high é do dialeto da API.
ESFORCO_NA_API = {"baixo": "low", "medio": "medium", "alto": "high"}

# "2m59.56s" gruda unidade e número, então a fronteira é "não vem outra letra", não \b.
_DURACAO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ms|s|m|h)(?![a-z])", re.IGNORECASE)
_TENTE_DE_NOVO = re.compile(r"try again in\s+([0-9][0-9.,\s]*(?:ms|s|m|h)[0-9.,smh\s]*)", re.IGNORECASE)
_FATOR = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}

# Pistas de texto do 429. Ordem importa: dia ganha de minuto, porque tratar um erro
# diário como "espera um pouco" é o erro que nunca passa (ADR 0007).
PISTAS_DE_DIA = ("per day", "per-day", "perday", "daily", "tpd", "rpd", "por dia")
PISTAS_DE_MINUTO = ("per minute", "per-minute", "perminute", "tpm", "rpm", "por minuto")


def segundos_da_duracao(texto: str) -> float | None:
    """Soma "2m59.56s", "12s", "500ms" em segundos. Devolve ``None`` se não achar nada."""
    total: float | None = None
    for valor, unidade in _DURACAO.findall(texto or ""):
        total = (total or 0.0) + float(valor.replace(",", ".")) * _FATOR[unidade.lower()]
    return total


def espera_da_mensagem(texto: str) -> float | None:
    """Lê o "Please try again in 2m59.56s" que a Groq manda no corpo do 429."""
    achado = _TENTE_DE_NOVO.search(texto or "")
    return segundos_da_duracao(achado.group(1)) if achado else None


def espera_do_cabecalho(cabecalhos: Mapping[str, str]) -> float | None:
    """``retry-after`` em segundos. Data HTTP é ignorada de propósito: é rara e ambígua."""
    bruto = _cabecalho(cabecalhos, "retry-after")
    if not bruto:
        return None
    try:
        return float(bruto.strip())
    except ValueError:
        return segundos_da_duracao(bruto)


def _cabecalho(cabecalhos: Mapping[str, str], chave: str) -> str | None:
    for nome, valor in dict(cabecalhos).items():
        if nome.lower() == chave:
            return str(valor)
    return None


def corpo_em_json(corpo: str | bytes | Mapping[str, Any] | None) -> dict[str, Any]:
    """Aceita corpo já decodificado, texto ou bytes. Corpo ilegível vira ``{}``."""
    if isinstance(corpo, Mapping):
        return dict(corpo)
    if corpo is None:
        return {}
    if isinstance(corpo, bytes):
        corpo = corpo.decode("utf-8", "replace")
    try:
        carga = json.loads(corpo)
    except (json.JSONDecodeError, TypeError):
        return {}
    return carga if isinstance(carga, dict) else {}


def texto_do_erro(dados: Mapping[str, Any], corpo: str | bytes | Mapping[str, Any] | None) -> str:
    """Junta mensagem estruturada e corpo cru: a pista do 429 pode estar em qualquer um."""
    erro = dados.get("error")
    pedacos: list[str] = []
    if isinstance(erro, Mapping):
        for campo in ("message", "code", "type"):
            valor = erro.get(campo)
            if isinstance(valor, str):
                pedacos.append(valor)
    elif isinstance(erro, str):
        pedacos.append(erro)
    if isinstance(corpo, (str, bytes)):
        pedacos.append(corpo.decode("utf-8", "replace") if isinstance(corpo, bytes) else corpo)
    return " ".join(pedacos)


def esgotamento_do_texto(texto: str) -> EsgotamentoDeCota:
    """Dia ganha de minuto; sem pista, DESCONHECIDO (o roteador trata como dia)."""
    baixo = (texto or "").lower()
    if any(p in baixo for p in PISTAS_DE_DIA):
        return EsgotamentoDeCota.POR_DIA
    if any(p in baixo for p in PISTAS_DE_MINUTO):
        return EsgotamentoDeCota.POR_MINUTO
    return EsgotamentoDeCota.DESCONHECIDO


def esgotamento_dos_cabecalhos(cabecalhos: Mapping[str, str]) -> EsgotamentoDeCota:
    """Pista secundária documentada pela Groq: o cap de *requests* é diário e o de *tokens*
    é por minuto (https://console.groq.com/docs/rate-limits, 18/09/2026). Quem zerou diz
    qual cota estourou quando a mensagem não diz.
    """
    restantes_requisicoes = _cabecalho(cabecalhos, "x-ratelimit-remaining-requests")
    restantes_tokens = _cabecalho(cabecalhos, "x-ratelimit-remaining-tokens")
    if restantes_requisicoes is not None and restantes_requisicoes.strip() in {"0", "0.0"}:
        return EsgotamentoDeCota.POR_DIA
    if restantes_tokens is not None and restantes_tokens.strip() in {"0", "0.0"}:
        return EsgotamentoDeCota.POR_MINUTO
    return EsgotamentoDeCota.DESCONHECIDO


def interpretar_429_no_dialeto_openai(
    provedor: str,
    status: int,
    cabecalhos: Mapping[str, str],
    corpo: str | bytes | Mapping[str, Any] | None,
    *,
    ler_cabecalhos_de_cota: bool = True,
) -> CotaEsgotada:
    """Função pura: do 429 cru para o ``CotaEsgotada`` que o roteador sabe ler."""
    dados = corpo_em_json(corpo)
    texto = texto_do_erro(dados, corpo)
    esgotamento = esgotamento_do_texto(texto)
    if esgotamento is EsgotamentoDeCota.DESCONHECIDO and ler_cabecalhos_de_cota:
        esgotamento = esgotamento_dos_cabecalhos(cabecalhos)
    espera = espera_do_cabecalho(cabecalhos)
    if espera is None:
        espera = espera_da_mensagem(texto)
    return CotaEsgotada(
        provedor,
        esgotamento,
        espera,
        mensagem=f"HTTP {status} ({esgotamento}): {resumir(texto)}",
    )


def resumir(texto: str, limite: int = 200) -> str:
    """Trecho curto para a mensagem de erro. Corpo inteiro em log não ajuda ninguém."""
    limpo = " ".join((texto or "").split())
    return limpo if len(limpo) <= limite else limpo[: limite - 1] + "…"


def endurecer_schema(schema: Any) -> Any:
    """Prepara o JSON Schema para o modo estrito do dialeto OpenAI.

    A decodificação restrita exige ``additionalProperties: false`` e todas as propriedades
    em ``required`` (https://console.groq.com/docs/structured-outputs, 18/09/2026). Campos
    opcionais do pydantic já viram ``anyOf`` com ``null``, então exigi-los não mente: o
    modelo responde ``null``. Função pura — não muda o schema recebido.
    """
    if isinstance(schema, list):
        return [endurecer_schema(parte) for parte in schema]
    if not isinstance(schema, dict):
        return schema
    novo = {chave: endurecer_schema(valor) for chave, valor in schema.items()}
    if novo.get("type") == "object" or "properties" in novo:
        propriedades = novo.get("properties")
        if isinstance(propriedades, dict):
            novo["required"] = list(propriedades)
        novo["additionalProperties"] = False
    return novo


def nome_de_schema(rotulo: str) -> str:
    """O campo ``json_schema.name`` só aceita [A-Za-z0-9_-]; o rótulo usa ':'."""
    limpo = re.sub(r"[^A-Za-z0-9_-]", "_", rotulo or "")
    return limpo[:60] or "saida"


def mensagens_no_dialeto_openai(mensagens: list[Mensagem]) -> list[dict[str, Any]]:
    """Imagem vira data URL, o caminho padrão do dialeto para entrada visual (ADR 0014)."""
    convertidas: list[dict[str, Any]] = []
    for mensagem in mensagens:
        papel = PAPEL_NA_API.get(mensagem.autor, "user")
        if mensagem.imagem_png is None:
            convertidas.append({"role": papel, "content": mensagem.texto})
            continue
        codificada = base64.b64encode(mensagem.imagem_png).decode("ascii")
        convertidas.append(
            {
                "role": papel,
                "content": [
                    {"type": "text", "text": mensagem.texto},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{codificada}"}},
                ],
            }
        )
    return convertidas


def texto_do_conteudo(conteudo: Any) -> str:
    """``content`` é string na maioria das respostas e lista de partes em algumas."""
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        return "".join(parte.get("text", "") for parte in conteudo if isinstance(parte, dict))
    return ""


class ProvedorNoDialetoOpenAI(ProvedorBase):
    """Base de Groq e SambaNova. Cada subclasse muda nome, base, teto e modo do schema."""

    nome = "openai-compat"
    base_padrao = ""
    campo_do_teto = "max_tokens"
    schema_estrito = False
    # Só manda ``reasoning_effort`` quem tem a documentação oficial dizendo que existe.
    envia_esforco_raciocinio = False

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
        self._base = (base_url or self.base_padrao).rstrip("/")
        self._cliente = cliente or httpx.Client(timeout=httpx.Timeout(TEMPO_LIMITE_S))

    # -- tradução -----------------------------------------------------------

    def corpo_do_pedido(self, pedido: PedidoLLM) -> dict[str, Any]:
        corpo: dict[str, Any] = {
            "model": self.modelo,
            "messages": mensagens_no_dialeto_openai(pedido.mensagens),
            "temperature": pedido.temperatura,
            self.campo_do_teto: pedido.max_tokens,
        }
        if pedido.esforco_raciocinio and self.envia_esforco_raciocinio:
            corpo["reasoning_effort"] = ESFORCO_NA_API[pedido.esforco_raciocinio]
        if pedido.schema_saida:
            schema = endurecer_schema(pedido.schema_saida) if self.schema_estrito else pedido.schema_saida
            corpo["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": nome_de_schema(pedido.rotulo),
                    "strict": self.schema_estrito,
                    "schema": schema,
                },
            }
        return corpo

    def resposta_do_corpo(self, dados: Mapping[str, Any], latencia_s: float) -> RespostaLLM:
        escolhas = dados.get("choices") or []
        if not escolhas:
            raise RespostaMalformada(self.nome, "resposta sem 'choices'")
        primeira = escolhas[0] if isinstance(escolhas[0], dict) else {}
        mensagem = primeira.get("message") or {}
        texto = texto_do_conteudo(mensagem.get("content"))
        if not texto:
            motivo = primeira.get("finish_reason")
            if motivo == "length":
                raise RespostaMalformada(
                    self.nome,
                    "o teto de tokens acabou antes do texto: em modelo de raciocínio o "
                    "'pensar' gasta o mesmo max_tokens (pesquisa §4)",
                )
            raise RespostaMalformada(self.nome, f"resposta sem texto (finish_reason={motivo})")
        uso = dados.get("usage") or {}
        # No dialeto OpenAI o raciocínio já está dentro de completion_tokens; o detalhe só
        # diz quanto dele foi "pensar". Vem quando o provedor manda, e 0 quando não manda.
        detalhe = uso.get("completion_tokens_details") or {}
        return RespostaLLM(
            texto=texto,
            provedor=self.nome,
            modelo=str(dados.get("model") or self.modelo),
            tokens_entrada=int(uso.get("prompt_tokens") or 0),
            tokens_saida=int(uso.get("completion_tokens") or 0),
            tokens_raciocinio=int(detalhe.get("reasoning_tokens") or 0),
            latencia_s=latencia_s,
        )

    # -- contrato -----------------------------------------------------------

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        comeco = time.perf_counter()
        try:
            resposta_http = self._cliente.post(
                f"{self._base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._chave}",
                    "Content-Type": "application/json",
                },
                json=self.corpo_do_pedido(pedido),
            )
        except httpx.HTTPError as erro:
            raise ErroProvedor(self.nome, f"falha de transporte: {self.ocultar(str(erro))}") from None
        latencia_s = time.perf_counter() - comeco
        if resposta_http.status_code == 429:
            # O servidor pode ecoar a requisição no corpo: a mensagem passa pelo filtro.
            cota = self.interpretar_429(resposta_http.status_code, resposta_http.headers, resposta_http.text)
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

    def interpretar_429(
        self,
        status: int,
        cabecalhos: Mapping[str, str],
        corpo: str | bytes | Mapping[str, Any] | None,
    ) -> CotaEsgotada:
        return interpretar_429_no_dialeto_openai(self.nome, status, cabecalhos, corpo)

    def ocultar(self, texto: str) -> str:
        """A chave nunca sai em exceção nem em log, nem por acidente de eco do servidor."""
        return texto.replace(self._chave, "***") if self._chave else texto

    def fechar(self) -> None:
        self._cliente.close()
