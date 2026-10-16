"""Qualidade: uma nota de 0 a 1 por dimensão, dada pelo Jev (TypeSafe) depois das cinco medidas
determinísticas. Abaixo do Limiar a Célula volta ao Gerador.

ADR 0035.

O Jev é um classificador, não um gerador: recebe o texto e perguntas com níveis ordenados e devolve
uma nota por pergunta, numa chamada só. O que ele mede é o que o determinístico não alcança: o
quanto a ideia está desenvolvida, se o texto foi cortado, se se lê de primeira, se o registro serve
à Audiência. Não confere fato (isso é do Factuality & Grounding Checker, ADR 0035) e não cita trecho.

As regras que este arquivo fixa:

- **Roda depois do determinístico e só se ele aprovou.** Célula já reprovada por Flesch-BR ou
  Aderência não gasta chamada: o Ciclo a devolve ao Gerador de qualquer jeito.
- **Uma nota por dimensão, e a Medida carrega a menor.** Uma porcentagem só esconderia qual dimensão
  falhou; a Correção diz "desenvolvimento 33%", não "melhore o texto" (ADR 0013).
- **Falha do Jev nunca reprova.** Rede fora, cota, resposta fora do formato: o Laudo sai sem a
  Qualidade, igual ao Comitê (ADR 0008). Ausência de medida não é nota zero.
- **O Limiar é provisório** (``dominio.LIMIAR_DE_QUALIDADE``), como o Flesch-BR: sem Calibração.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from suno.configuracoes import carregar
from suno.dominio import (
    LIMIAR_DE_QUALIDADE,
    Audiencia,
    Conteudo,
    ErroProvedor,
    Formato,
)

_REGISTRO = logging.getLogger(__name__)

NOME = "jev"
URL_PADRAO = "https://api.typesafe.ai/v1/systemone"
MODELO = "jev-latest"
VARIAVEL_LIGAR = "SUNO_JEV"
VARIAVEL_URL = "JEV_URL"
VARIAVEIS_DA_CHAVE = ("JEV_API_KEY", "TYPESAFE_API_KEY")
VARIAVEL_LIMIAR = "SUNO_JEV_LIMIAR"

TEMPO_LIMITE_S = 30.0
TENTATIVAS = 5
ESPERA_INICIAL_S = 1.0
STATUS_QUE_ESPERAM = frozenset({429, 529})
"""O Jev pede para tentar de novo com espera crescente em 429 e 529."""

NOME_DO_FORMATO: dict[Formato, str] = {
    Formato.TEXTO_ANALITICO: "texto analítico",
    Formato.CARROSSEL: "carrossel de slides",
    Formato.ROTEIRO: "fala de um roteiro de vídeo",
}
NOME_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "Iniciante (quem está começando e não conhece o vocabulário do mercado)",
    Audiencia.INTERMEDIARIO: "Intermediário (quem já acompanha o mercado e conhece o vocabulário básico)",
    Audiencia.AVANCADO: "Avançado (quem trabalha com o mercado e domina o jargão)",
}


@dataclass(frozen=True)
class Dimensao:
    """Uma pergunta ao Jev: a instrução e os níveis, do pior ao melhor."""

    chave: str
    rotulo: str
    instrucao: str
    niveis: tuple[str, ...]


DIMENSOES: tuple[Dimensao, ...] = (
    Dimensao(
        chave="desenvolvimento",
        rotulo="desenvolvimento",
        instrucao=(
            "Em que medida o conteúdo desenvolve a ideia: apresenta o fato, explica o porquê e "
            "conclui? Julgue só o desenvolvimento, não a exatidão dos números nem o tamanho."
        ),
        niveis=(
            "Lista fatos soltos, sem explicar nada nem ligar uma ideia à outra",
            "Explica pouco: o raciocínio fica incompleto ou salta etapas",
            "Desenvolve a ideia, com uma lacuna na explicação ou na conclusão",
            "Desenvolve a ideia do começo ao fim, com os fatos encadeados e uma conclusão",
        ),
    ),
    Dimensao(
        chave="completude",
        rotulo="completude",
        instrucao=(
            "O conteúdo está completo ou foi cortado? Procure frase interrompida, item "
            "inacabado, parte anunciada e nunca entregue, ou final abrupto."
        ),
        niveis=(
            "Termina no meio de uma frase, de um slide ou de uma fala",
            "Termina de forma abrupta, sem fechamento, ou promete algo que não entrega",
            "Fecha, mas falta uma parte que o próprio conteúdo anuncia",
            "Começa, desenvolve e termina por inteiro, sem nada cortado",
        ),
    ),
    Dimensao(
        chave="clareza",
        rotulo="clareza",
        instrucao=(
            "Um leitor da Audiência indicada entende o conteúdo na primeira leitura? Julgue a "
            "compreensão, não o tamanho: texto curto pode ser obscuro e texto longo, límpido."
        ),
        niveis=(
            "Incompreensível para essa Audiência",
            "Exige reler várias passagens, ou usa termos técnicos sem apoio nenhum",
            "Entende-se com esforço",
            "Claro do começo ao fim, com as ideias na ordem em que ajudam",
        ),
    ),
    Dimensao(
        chave="tom",
        rotulo="tom",
        instrucao=(
            "O registro combina com a Audiência indicada e com um material que informa e educa, "
            "sem vender nem tratar o leitor com desdém?"
        ),
        niveis=(
            "Vende, promete resultado ou trata o leitor com desdém",
            "Oscila entre formal e coloquial sem razão, ou soa paternalista",
            "Registro aceitável, com uma ou outra quebra",
            "Registro estável e adequado à Audiência, sóbrio e acolhedor",
        ),
    ),
)


@dataclass(frozen=True)
class NotaDaDimensao:
    chave: str
    rotulo: str
    nota: float
    """De 0 a 1: o nível ponderado pela probabilidade, dividido pelo nível mais alto."""
    confianca: float | None
    nivel: str
    """O texto do nível mais próximo da nota, para a Correção dizer o que o Jev viu."""


@dataclass(frozen=True)
class ResultadoDaQualidade:
    dimensoes: tuple[NotaDaDimensao, ...]

    @property
    def menor(self) -> NotaDaDimensao:
        return min(self.dimensoes, key=lambda d: d.nota)


def perguntas_do_jev() -> dict[str, dict[str, Any]]:
    """O corpo ``questions`` do pedido: uma pergunta ``score`` por dimensão."""
    return {
        d.chave: {"type": "score", "instructions": d.instrucao, "criteria": list(d.niveis)}
        for d in DIMENSOES
    }


def estado_do_jev(conteudo: Conteudo, audiencia: Audiencia) -> dict[str, str]:
    """O que o Jev lê: a Audiência, o Formato e o texto. Nunca diz quem gerou."""
    return {
        "audiencia": NOME_DA_AUDIENCIA[audiencia],
        "formato": NOME_DO_FORMATO[conteudo.formato],
        "conteudo": conteudo.texto_avaliavel(),
    }


class ClienteJev:
    """O pedido HTTP ao Jev: ``POST <url>`` com ``Authorization: Bearer``.

    ``url`` é o endereço completo do ``systemone``. Serve a API direta da TypeSafe e qualquer
    ponte que repasse o mesmo corpo, como uma Netlify Function (``JEV_URL``).
    """

    def __init__(
        self,
        url: str,
        chave: str,
        *,
        cliente: httpx.Client | None = None,
        dormir: Callable[[float], None] = time.sleep,
        tentativas: int = TENTATIVAS,
    ) -> None:
        self._url = url
        self._chave = chave
        self._cliente = cliente or httpx.Client(timeout=TEMPO_LIMITE_S)
        self._dormir = dormir
        self._tentativas = tentativas

    def pontuar(self, estado: dict[str, str], perguntas: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """As ``answers`` do Jev, por chave de pergunta. Levanta ``ErroProvedor`` em qualquer falha."""
        corpo = {"state": estado, "model": MODELO, "questions": perguntas}
        cabecalhos = {"Authorization": f"Bearer {self._chave}", "Content-Type": "application/json"}
        espera = ESPERA_INICIAL_S
        for tentativa in range(1, self._tentativas + 1):
            try:
                resposta = self._cliente.post(self._url, json=corpo, headers=cabecalhos)
            except httpx.HTTPError as erro:
                raise ErroProvedor(NOME, f"a chamada não chegou: {type(erro).__name__}") from None
            if resposta.status_code in STATUS_QUE_ESPERAM and tentativa < self._tentativas:
                self._dormir(espera)
                espera *= 2
                continue
            return self._respostas(resposta)
        raise ErroProvedor(NOME, "sem resposta depois das tentativas")  # pragma: no cover

    @staticmethod
    def _respostas(resposta: httpx.Response) -> dict[str, Any]:
        if resposta.status_code != 200:
            raise ErroProvedor(NOME, f"HTTP {resposta.status_code}: {resposta.text[:200]}")
        try:
            answers = resposta.json()["answers"]
        except (ValueError, KeyError, TypeError):
            raise ErroProvedor(NOME, "resposta sem o campo answers") from None
        if not isinstance(answers, dict):
            raise ErroProvedor(NOME, "answers não é um objeto")
        return answers


class AvaliadorDeQualidade:
    """Pergunta ao Jev as quatro dimensões de uma Célula e devolve as notas de 0 a 1."""

    def __init__(self, cliente: ClienteJev, limiar: float = LIMIAR_DE_QUALIDADE) -> None:
        self.cliente = cliente
        self.limiar = limiar

    def medir(self, conteudo: Conteudo, audiencia: Audiencia) -> ResultadoDaQualidade:
        answers = self.cliente.pontuar(estado_do_jev(conteudo, audiencia), perguntas_do_jev())
        notas = []
        for dimensao in DIMENSOES:
            notas.append(_nota(dimensao, answers.get(dimensao.chave)))
        return ResultadoDaQualidade(dimensoes=tuple(notas))

    @classmethod
    def de_ambiente(
        cls,
        *,
        ligado: bool | None = None,
        cliente_http: httpx.Client | None = None,
        exigir: bool = False,
    ) -> "AvaliadorDeQualidade | None":
        """Monta o avaliador se ele foi pedido e há chave. ``None`` diz o motivo no log.

        O Jev está **sempre ligado** (ADR 0035): sem ``ligado`` e sem ``SUNO_JEV=0`` no ambiente, vale
        ligado. ``SUNO_JEV=0`` existe só para os testes e para quem não tem a chave. Sem chave o Laudo
        sai sem Qualidade: nada aqui pode travar a execução.
        """
        if not _esta_pedido(ligado):
            return None
        chave = next((os.environ[v] for v in VARIAVEIS_DA_CHAVE if os.environ.get(v)), "")
        if not chave and exigir:
            raise ErroProvedor(
                NOME,
                f"o Jev é obrigatório e falta {' ou '.join(VARIAVEIS_DA_CHAVE)} no .env "
                "(use --sem-jev só se aceitar rodar sem Qualidade)",
            )
        if not chave:
            _REGISTRO.warning(
                "Qualidade (Jev) sem chave: falta %s no .env, e o Laudo sai sem ela (ADR 0035)",
                " ou ".join(VARIAVEIS_DA_CHAVE),
            )
            return None
        url = carregar().jev_url or URL_PADRAO
        return cls(
            ClienteJev(url, chave, cliente=cliente_http),
            limiar=_limiar_do_ambiente(),
        )


def _nota(dimensao: Dimensao, resposta: Any) -> NotaDaDimensao:
    """Uma resposta ``score`` do Jev vira ``NotaDaDimensao``. Fora do formato, levanta."""
    if not isinstance(resposta, dict) or not isinstance(resposta.get("score"), (int, float)):
        raise ErroProvedor(NOME, f"a dimensão {dimensao.chave} voltou sem nota")
    ultimo = len(dimensao.niveis) - 1
    nota = min(1.0, max(0.0, float(resposta["score"]) / ultimo))
    confianca = resposta.get("confidence")
    return NotaDaDimensao(
        chave=dimensao.chave,
        rotulo=dimensao.rotulo,
        nota=nota,
        confianca=float(confianca) if isinstance(confianca, (int, float)) else None,
        nivel=dimensao.niveis[round(nota * ultimo)],
    )


def _esta_pedido(ligado: bool | None) -> bool:
    if ligado is not None:
        return ligado
    return carregar().jev_ligado


def _limiar_do_ambiente() -> float:
    salvo = carregar().jev_limiar
    if salvo is not None:
        return salvo
    bruto = os.environ.get(VARIAVEL_LIMIAR, "").strip().replace(",", ".")
    if not bruto:
        return LIMIAR_DE_QUALIDADE
    try:
        valor = float(bruto)
    except ValueError:
        _REGISTRO.warning("%s=%r não é número; vale o Limiar padrão", VARIAVEL_LIMIAR, bruto)
        return LIMIAR_DE_QUALIDADE
    if not 0.0 <= valor <= 1.0:
        _REGISTRO.warning("%s=%r fora de 0 a 1; vale o Limiar padrão", VARIAVEL_LIMIAR, bruto)
        return LIMIAR_DE_QUALIDADE
    return valor


__all__ = [
    "AvaliadorDeQualidade",
    "ClienteJev",
    "DIMENSOES",
    "NotaDaDimensao",
    "ResultadoDaQualidade",
]
