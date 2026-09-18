"""Os três provedores reais, com ``httpx.MockTransport``: nenhum byte sai da máquina.

O que está travado aqui é o contrato com cada API — onde o schema entra no corpo, de onde
saem os tokens, e como cada 429 é lido (ADR 0007). Os formatos vêm da documentação oficial
conferida em 18/09/2026; as URLs estão no relatório do agente 6.
"""

from __future__ import annotations

import json
from typing import Any, Literal

import httpx
import pytest
from pydantic import BaseModel

from suno.dominio import (
    CotaEsgotada,
    ErroProvedor,
    EsgotamentoDeCota,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    RespostaMalformada,
)
from suno.provedores import gemini as modulo_gemini
from suno.provedores import groq as modulo_groq
from suno.provedores import sambanova as modulo_sambanova
from suno.provedores.gemini import ProvedorGemini, adaptar_schema, configuracao_de_raciocinio
from suno.provedores.groq import ProvedorGroq
from suno.provedores.sambanova import ProvedorSambaNova

CHAVE = "chave-secreta-que-nunca-pode-vazar"


class Slide(BaseModel):
    frase: str
    numero_citado: str | None = None


class Carrossel(BaseModel):
    titulo: str
    audiencia: Literal["iniciante"]
    slides: list[Slide]


def _pedido(
    com_schema: bool = True,
    imagem: bytes | None = None,
    esforco: str | None = None,
) -> PedidoLLM:
    return PedidoLLM(
        papel=PapelLLM.GERADOR,
        rotulo="celula:iniciante:carrossel:0",
        mensagens=[
            Mensagem(autor="sistema", texto="Você adapta Atas do Copom."),
            Mensagem(autor="usuario", texto="Adapte esta Ata.", imagem_png=imagem),
        ],
        schema_saida=Carrossel.model_json_schema() if com_schema else None,
        max_tokens=700,
        temperatura=0.3,
        esforco_raciocinio=esforco,
    )


def _cliente(atender) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(atender))


def _corpo_enviado(requisicoes: list[httpx.Request]) -> dict[str, Any]:
    return json.loads(requisicoes[-1].content)


def _chaves_do_schema(no: Any) -> set[str]:
    achadas: set[str] = set()
    if isinstance(no, dict):
        for chave, valor in no.items():
            achadas.add(chave)
            achadas |= _chaves_do_schema(valor)
    elif isinstance(no, list):
        for parte in no:
            achadas |= _chaves_do_schema(parte)
    return achadas


RESPOSTA_PRONTA = '{"titulo": "Selic a 15%", "audiencia": "iniciante", "slides": []}'


# ---------------------------------------------------------------------------
# 9. uma resposta 200 vira RespostaLLM, e o corpo enviado está no formato certo
# ---------------------------------------------------------------------------


def test_gemini_manda_schema_sistema_e_modelo_e_le_os_tokens():
    requisicoes: list[httpx.Request] = []

    def atender(requisicao: httpx.Request) -> httpx.Response:
        requisicoes.append(requisicao)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {"parts": [{"text": "pensando", "thought": True}, {"text": RESPOSTA_PRONTA}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {"promptTokenCount": 1234, "candidatesTokenCount": 56},
                "modelVersion": "modelo-do-parametro",
            },
        )

    provedor = ProvedorGemini(CHAVE, "modelo-do-parametro", cliente=_cliente(atender), base_url="https://exemplo")
    resposta = provedor.completar_estruturado(_pedido(), Carrossel)

    assert resposta == Carrossel.model_validate_json(RESPOSTA_PRONTA)
    requisicao = requisicoes[-1]
    assert str(requisicao.url) == "https://exemplo/v1beta/models/modelo-do-parametro:generateContent"
    assert requisicao.headers["x-goog-api-key"] == CHAVE
    corpo = _corpo_enviado(requisicoes)
    assert corpo["systemInstruction"]["parts"][0]["text"].startswith("Você adapta")
    assert [c["role"] for c in corpo["contents"]] == ["user"]
    assert corpo["generationConfig"]["maxOutputTokens"] == 700
    assert corpo["generationConfig"]["temperature"] == 0.3
    assert corpo["generationConfig"]["responseMimeType"] == "application/json"
    assert corpo["generationConfig"]["responseSchema"]["properties"]["titulo"]["type"] == "string"


def test_gemini_conta_tokens_e_descarta_partes_de_raciocinio():
    def atender(_requisicao: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "resposta"}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
            },
        )

    resposta = ProvedorGemini(CHAVE, "m", cliente=_cliente(atender)).completar(_pedido(com_schema=False))
    assert (resposta.texto, resposta.tokens_entrada, resposta.tokens_saida) == ("resposta", 10, 3)
    assert resposta.provedor == "gemini"


def test_gemini_manda_imagem_como_inline_data():
    requisicoes: list[httpx.Request] = []

    def atender(requisicao: httpx.Request) -> httpx.Response:
        requisicoes.append(requisicao)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    provedor = ProvedorGemini(CHAVE, "m", cliente=_cliente(atender))
    provedor.completar(_pedido(com_schema=False, imagem=b"\x89PNG-de-mentira"))

    partes = _corpo_enviado(requisicoes)["contents"][0]["parts"]
    assert partes[1]["inlineData"]["mimeType"] == "image/png"
    assert partes[1]["inlineData"]["data"], "a imagem vai em base64"


def test_gemini_sem_texto_por_teto_de_tokens_e_resposta_malformada():
    def atender(_requisicao: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]})

    with pytest.raises(RespostaMalformada):
        ProvedorGemini(CHAVE, "m", cliente=_cliente(atender)).completar(_pedido(com_schema=False))


@pytest.mark.parametrize(
    "classe, modulo, campo_do_teto, estrito",
    [
        (ProvedorGroq, modulo_groq, "max_completion_tokens", True),
        (ProvedorSambaNova, modulo_sambanova, "max_tokens", False),
    ],
)
def test_dialeto_openai_manda_response_format_e_le_o_usage(classe, modulo, campo_do_teto, estrito):
    requisicoes: list[httpx.Request] = []

    def atender(requisicao: httpx.Request) -> httpx.Response:
        requisicoes.append(requisicao)
        return httpx.Response(
            200,
            json={
                "model": "modelo-do-parametro",
                "choices": [{"message": {"role": "assistant", "content": RESPOSTA_PRONTA}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 800, "completion_tokens": 42, "total_tokens": 842},
            },
        )

    provedor = classe(CHAVE, "modelo-do-parametro", cliente=_cliente(atender), base_url="https://exemplo/v1")
    saida = provedor.completar_estruturado(_pedido(), Carrossel)

    assert saida.titulo == "Selic a 15%"
    requisicao = requisicoes[-1]
    assert str(requisicao.url) == "https://exemplo/v1/chat/completions"
    assert requisicao.headers["authorization"] == f"Bearer {CHAVE}"
    corpo = _corpo_enviado(requisicoes)
    assert corpo["model"] == "modelo-do-parametro", "o modelo vem do parâmetro, não de constante"
    assert corpo[campo_do_teto] == 700
    assert [m["role"] for m in corpo["messages"]] == ["system", "user"]
    formato = corpo["response_format"]
    assert formato["type"] == "json_schema"
    assert formato["json_schema"]["strict"] is estrito
    assert formato["json_schema"]["name"] == "celula_iniciante_carrossel_0"
    assert formato["json_schema"]["schema"]["properties"]["titulo"]["type"] == "string"
    assert ("additionalProperties" in formato["json_schema"]["schema"]) is estrito


def test_groq_le_tokens_e_registra_o_proprio_nome():
    def atender(_requisicao: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "texto"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 9, "completion_tokens": 4},
            },
        )

    resposta = ProvedorGroq(CHAVE, "m", cliente=_cliente(atender)).completar(_pedido(com_schema=False))
    assert (resposta.provedor, resposta.tokens_entrada, resposta.tokens_saida) == ("groq", 9, 4)


def test_dialeto_openai_sem_texto_por_teto_de_tokens_e_resposta_malformada():
    def atender(_requisicao: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}, "finish_reason": "length"}]})

    with pytest.raises(RespostaMalformada):
        ProvedorSambaNova(CHAVE, "m", cliente=_cliente(atender)).completar(_pedido(com_schema=False))


# ---------------------------------------------------------------------------
# O schema do Gemini é um subconjunto do OpenAPI 3.0: a adaptação é pura e testada
# ---------------------------------------------------------------------------


def test_adaptar_schema_resolve_defs_e_descarta_o_que_o_gemini_nao_aceita():
    adaptado = adaptar_schema(Carrossel.model_json_schema())
    chaves = _chaves_do_schema(adaptado)

    assert not {c for c in chaves if c.startswith("$")}, "nada de $defs/$ref (ADR 0007)"
    assert "additionalProperties" not in chaves
    assert adaptado["propertyOrdering"] == ["titulo", "audiencia", "slides"]
    slide = adaptado["properties"]["slides"]["items"]
    assert slide["properties"]["frase"]["type"] == "string", "o $ref do Slide foi resolvido inline"
    assert slide["properties"]["numero_citado"]["nullable"] is True, "X | None vira nullable"
    assert adaptado["properties"]["audiencia"]["enum"] == ["iniciante"], "Literal vira enum"


def test_adaptar_schema_e_pura_e_aguenta_schema_recursivo():
    original = {
        "type": "object",
        "$defs": {"No": {"type": "object", "properties": {"filho": {"$ref": "#/$defs/No"}}}},
        "properties": {"raiz": {"$ref": "#/$defs/No"}},
        "additionalProperties": False,
    }
    copia = json.loads(json.dumps(original))
    adaptado = adaptar_schema(original)

    assert original == copia, "adaptar_schema não pode mexer no schema recebido"
    assert adaptado["properties"]["raiz"]["properties"]["filho"] == {"type": "object"}


# ---------------------------------------------------------------------------
# 10. interpretar_429: um por minuto, um diário, um sem pista, para cada provedor
# ---------------------------------------------------------------------------


def _corpo_do_gemini(quota: str) -> str:
    return json.dumps(
        {
            "error": {
                "code": 429,
                "message": "You exceeded your current quota, please check your plan and billing details.",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                                "quotaId": quota,
                            }
                        ],
                    },
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "12s"},
                ],
            }
        }
    )


def test_gemini_429_por_minuto_le_quota_id_e_a_espera_sugerida():
    cota = modulo_gemini.interpretar_429(
        429, {}, _corpo_do_gemini("GenerateRequestsPerMinutePerProjectPerModel-FreeTier")
    )
    assert cota.esgotamento is EsgotamentoDeCota.POR_MINUTO
    assert cota.espera_s == 12.0
    assert cota.provedor == "gemini"


def test_gemini_429_diario_le_quota_id_do_dia():
    cota = modulo_gemini.interpretar_429(
        429, {}, _corpo_do_gemini("GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    )
    assert cota.esgotamento is EsgotamentoDeCota.POR_DIA


def test_gemini_429_sem_pista_fica_desconhecido():
    corpo = '{"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota).", "status": "RESOURCE_EXHAUSTED"}}'
    cota = modulo_gemini.interpretar_429(429, {"retry-after": "30"}, corpo)
    assert cota.esgotamento is EsgotamentoDeCota.DESCONHECIDO
    assert cota.espera_s == 30.0


def _corpo_da_groq(mensagem: str) -> str:
    return json.dumps({"error": {"message": mensagem, "type": "tokens", "code": "rate_limit_exceeded"}})


def test_groq_429_por_minuto_le_tpm_e_o_tempo_da_mensagem():
    mensagem = (
        "Rate limit reached for model `openai/gpt-oss-120b` in organization `org_x` service tier "
        "`on_demand` on tokens per minute (TPM): Limit 30000, Used 30000, Requested 1000. "
        "Please try again in 2m59.56s."
    )
    cota = modulo_groq.interpretar_429(429, {}, _corpo_da_groq(mensagem))
    assert cota.esgotamento is EsgotamentoDeCota.POR_MINUTO
    assert cota.espera_s == pytest.approx(179.56)


def test_groq_429_diario_le_rpd():
    mensagem = (
        "Rate limit reached for model `openai/gpt-oss-120b` on requests per day (RPD): "
        "Limit 1000, Used 1000, Requested 1. Please try again in 1h2m3s."
    )
    cota = modulo_groq.interpretar_429(429, {"retry-after": "3723"}, _corpo_da_groq(mensagem))
    assert cota.esgotamento is EsgotamentoDeCota.POR_DIA
    assert cota.espera_s == 3723.0


def test_groq_429_sem_pista_no_texto_cai_nos_cabecalhos_de_cota():
    sem_pista = modulo_groq.interpretar_429(429, {}, _corpo_da_groq("Too Many Requests"))
    assert sem_pista.esgotamento is EsgotamentoDeCota.DESCONHECIDO

    # A Groq documenta: cap de requisições é diário, cap de tokens é por minuto.
    diario = modulo_groq.interpretar_429(
        429, {"x-ratelimit-remaining-requests": "0"}, _corpo_da_groq("Too Many Requests")
    )
    por_minuto = modulo_groq.interpretar_429(
        429, {"x-ratelimit-remaining-tokens": "0"}, _corpo_da_groq("Too Many Requests")
    )
    assert diario.esgotamento is EsgotamentoDeCota.POR_DIA
    assert por_minuto.esgotamento is EsgotamentoDeCota.POR_MINUTO


def test_sambanova_429_usa_texto_e_cabecalho_de_espera_e_assume_desconhecido():
    por_minuto = modulo_sambanova.interpretar_429(
        429, {}, '{"error": {"message": "rate limit exceeded: 20 RPM"}}'
    )
    diario = modulo_sambanova.interpretar_429(
        429, {}, '{"error": {"message": "Request would exceed rate limit: requests per day"}}'
    )
    sem_pista = modulo_sambanova.interpretar_429(
        429, {"retry-after": "45"}, '{"error": {"message": "429 Request would exceed rate limit"}}'
    )

    assert por_minuto.esgotamento is EsgotamentoDeCota.POR_MINUTO
    assert diario.esgotamento is EsgotamentoDeCota.POR_DIA
    assert sem_pista.esgotamento is EsgotamentoDeCota.DESCONHECIDO
    assert sem_pista.espera_s == 45.0
    assert sem_pista.provedor == "sambanova"


def test_interpretar_429_aguenta_corpo_que_nao_e_json():
    for interpretar in (modulo_gemini.interpretar_429, modulo_groq.interpretar_429, modulo_sambanova.interpretar_429):
        cota = interpretar(429, {}, "<html>429 Too Many Requests</html>")
        assert cota.esgotamento is EsgotamentoDeCota.DESCONHECIDO


# ---------------------------------------------------------------------------
# 11. a chave nunca aparece em exceção nenhuma
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("classe", [ProvedorGemini, ProvedorGroq, ProvedorSambaNova])
@pytest.mark.parametrize("estado", [400, 429, 500])
def test_a_chave_nunca_vaza_em_erro_de_http(classe, estado):
    def atender(_requisicao: httpx.Request) -> httpx.Response:
        # Servidor hostil: ecoa a chave no corpo do erro.
        return httpx.Response(estado, text=f'{{"error": {{"message": "bad key {CHAVE}"}}}}')

    provedor = classe(CHAVE, "modelo-do-parametro", cliente=_cliente(atender))
    with pytest.raises(ErroProvedor) as achado:
        provedor.completar(_pedido())

    assert CHAVE not in str(achado.value)
    assert CHAVE not in achado.value.mensagem
    if estado == 429:
        assert isinstance(achado.value, CotaEsgotada)


@pytest.mark.parametrize("classe", [ProvedorGemini, ProvedorGroq, ProvedorSambaNova])
def test_a_chave_nunca_vaza_em_falha_de_transporte(classe):
    def atender(_requisicao: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"falhou ao conectar com key={CHAVE}")

    provedor = classe(CHAVE, "modelo-do-parametro", cliente=_cliente(atender))
    with pytest.raises(ErroProvedor) as achado:
        provedor.completar(_pedido())
    assert CHAVE not in str(achado.value)


@pytest.mark.parametrize("classe", [ProvedorGemini, ProvedorGroq, ProvedorSambaNova])
def test_provedor_sem_chave_ou_sem_modelo_nao_e_construido(classe):
    with pytest.raises(ErroProvedor):
        classe("", "modelo")
    with pytest.raises(ErroProvedor):
        classe(CHAVE, "")


# ---------------------------------------------------------------------------
# Esforço de raciocínio: onde ele entra em cada API, e quanto ele gastou
# ---------------------------------------------------------------------------


def _atendente_do_gemini(requisicoes: list[httpx.Request], uso: dict[str, Any]):
    def atender(requisicao: httpx.Request) -> httpx.Response:
        requisicoes.append(requisicao)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": uso},
        )

    return atender


def test_gemini_2_5_traduz_esforco_baixo_em_thinking_budget_zero():
    requisicoes: list[httpx.Request] = []
    provedor = ProvedorGemini(
        CHAVE, "gemini-2.5-flash", cliente=_cliente(_atendente_do_gemini(requisicoes, {}))
    )
    provedor.completar(_pedido(com_schema=False, esforco="baixo"))

    geracao = _corpo_enviado(requisicoes)["generationConfig"]
    assert geracao["thinkingConfig"] == {"thinkingBudget": 0}
    assert "thinkingLevel" not in geracao["thinkingConfig"], "a série 2.5 não conhece thinkingLevel"


def test_gemini_3_traduz_esforco_em_thinking_level():
    requisicoes: list[httpx.Request] = []
    provedor = ProvedorGemini(
        CHAVE, "gemini-3.5-flash", cliente=_cliente(_atendente_do_gemini(requisicoes, {}))
    )
    provedor.completar(_pedido(com_schema=False, esforco="alto"))

    assert _corpo_enviado(requisicoes)["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "high"}


@pytest.mark.parametrize(
    "modelo, esforco",
    [("gemini-2.5-flash", None), ("gemini-2.5-flash", "alto"), ("modelo-sem-numero", "baixo")],
)
def test_gemini_nao_manda_thinking_config_sem_traducao_confirmada(modelo, esforco):
    requisicoes: list[httpx.Request] = []
    provedor = ProvedorGemini(CHAVE, modelo, cliente=_cliente(_atendente_do_gemini(requisicoes, {})))
    provedor.completar(_pedido(com_schema=False, esforco=esforco))

    assert "thinkingConfig" not in _corpo_enviado(requisicoes)["generationConfig"]


def test_gemini_le_os_tokens_de_raciocinio_do_usage_metadata():
    requisicoes: list[httpx.Request] = []
    uso = {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 512}
    provedor = ProvedorGemini(CHAVE, "gemini-2.5-flash", cliente=_cliente(_atendente_do_gemini(requisicoes, uso)))

    resposta = provedor.completar(_pedido(com_schema=False))

    assert resposta.tokens_raciocinio == 512
    assert resposta.tokens_saida == 20, "no Gemini o pensar é contado fora de candidatesTokenCount"


def _atendente_no_dialeto_openai(requisicoes: list[httpx.Request], uso: dict[str, Any]):
    def atender(requisicao: httpx.Request) -> httpx.Response:
        requisicoes.append(requisicao)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": uso},
        )

    return atender


def test_groq_manda_reasoning_effort_traduzido():
    requisicoes: list[httpx.Request] = []
    provedor = ProvedorGroq(CHAVE, "m", cliente=_cliente(_atendente_no_dialeto_openai(requisicoes, {})))

    provedor.completar(_pedido(com_schema=False, esforco="medio"))
    assert _corpo_enviado(requisicoes)["reasoning_effort"] == "medium"

    provedor.completar(_pedido(com_schema=False))
    assert "reasoning_effort" not in _corpo_enviado(requisicoes), "sem esforço declarado, nada é mandado"


def test_sambanova_ignora_o_esforco_porque_a_doc_nao_confirma_o_parametro():
    requisicoes: list[httpx.Request] = []
    provedor = ProvedorSambaNova(CHAVE, "m", cliente=_cliente(_atendente_no_dialeto_openai(requisicoes, {})))

    provedor.completar(_pedido(com_schema=False, esforco="alto"))

    assert "reasoning_effort" not in _corpo_enviado(requisicoes)


@pytest.mark.parametrize("classe", [ProvedorGroq, ProvedorSambaNova])
def test_dialeto_openai_le_os_tokens_de_raciocinio_quando_vem_no_detalhe(classe):
    requisicoes: list[httpx.Request] = []
    uso = {
        "prompt_tokens": 100,
        "completion_tokens": 300,
        "completion_tokens_details": {"reasoning_tokens": 250},
    }
    provedor = classe(CHAVE, "m", cliente=_cliente(_atendente_no_dialeto_openai(requisicoes, uso)))

    resposta = provedor.completar(_pedido(com_schema=False))

    assert resposta.tokens_raciocinio == 250
    assert resposta.tokens_saida == 300, "no dialeto OpenAI o raciocínio já está dentro de completion_tokens"


@pytest.mark.parametrize("classe", [ProvedorGroq, ProvedorSambaNova])
def test_dialeto_openai_sem_detalhe_de_raciocinio_conta_zero(classe):
    requisicoes: list[httpx.Request] = []
    uso = {"prompt_tokens": 10, "completion_tokens": 4}
    provedor = classe(CHAVE, "m", cliente=_cliente(_atendente_no_dialeto_openai(requisicoes, uso)))

    assert provedor.completar(_pedido(com_schema=False)).tokens_raciocinio == 0


def test_configuracao_de_raciocinio_e_pura_e_cobre_as_tres_intensidades():
    assert configuracao_de_raciocinio("gemini-3.8-flash", "baixo") == {"thinkingLevel": "low"}
    assert configuracao_de_raciocinio("gemini-3.8-flash", "medio") == {"thinkingLevel": "medium"}
    assert configuracao_de_raciocinio("gemini-3.8-flash", "alto") == {"thinkingLevel": "high"}
    assert configuracao_de_raciocinio("models/gemini-2.5-pro", "baixo") == {"thinkingBudget": 0}
    assert configuracao_de_raciocinio("gemini-2.5-flash", "medio") is None
    assert configuracao_de_raciocinio("gemini-2.5-flash", None) is None
