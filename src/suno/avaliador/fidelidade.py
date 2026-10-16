"""Fidelidade: um LLM lê a Ata inteira e a Célula e aponta o que a Célula diz que a Ata não diz.

ADR 0036. É o Factuality & Grounding Checker do enunciado, para o que a Aderência não alcança: a
afirmação em prosa, sem número.

As regras que este arquivo fixa, e que alguém vai querer "relaxar" sem saber:

- **O LLM aponta, o código confere.** Todo achado traz o trecho da Célula copiado literalmente, e o
  código verifica que ele existe na Célula. Achado de "distorce" ou "contradiz" traz também o trecho
  da Ata, e o código verifica que ele existe na Ata. Citação que não existe é invenção do juiz, e o
  achado é descartado (ADR 0008: há registro de juiz alucinando evidência).
- **Na dúvida, não aponta.** Explicação de termo e analogia escrita para a Audiência não são
  afirmação sobre a Ata. O pedido diz isso, porque sem isso todo Iniciante reprovaria.
- **Só bloqueia o que tem prova.** `distorce` e `contradiz` trazem o trecho da Ata, e o código o
  confere: com a prova, a Célula é reprovada e o Ciclo a devolve ao Gerador. `sem_suporte` é só a
  opinião do modelo de que "a Ata não diz isso" (não há trecho a conferir) e **só avisa** no Laudo.
  Medido em 6 Células reais aprovadas, bloquear por `sem_suporte` reprovaria metade delas, quase
  sempre por conclusão correta tirada de fato da Ata (7 votos a favor, logo "unânime").
- **Falha do provedor nunca reprova.** Sem chave, sem cota, resposta fora do schema, Ata grande
  demais: o Laudo sai sem a Fidelidade (ADR 0008).
- **Só roda depois de tudo o mais ter aprovado**, inclusive a Qualidade: é a chamada mais cara, com a
  Ata inteira no pedido.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from suno.configuracoes import carregar
from suno.dominio import (
    Ancora,
    AncoraNumerica,
    Audiencia,
    Conteudo,
    ErroProvedor,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    RespostaMalformada,
)
from suno.provedores.base import Provedor

_REGISTRO = logging.getLogger(__name__)

VARIAVEL_LIGAR = "SUNO_FIDELIDADE"
LIMITE_DA_ATA_EM_CARACTERES = 350_000
"""Acima disso a Ata não cabe na janela do modelo: a Célula sai sem Fidelidade, nunca reprovada."""
TRECHO_MINIMO_DA_CELULA = 15
"""Menos que isso é vago demais para ser uma afirmação (e casa em qualquer lugar)."""
MAXIMO_DE_ACHADOS = 8
TETO_DE_TOKENS = 2500
TEMPERATURA = 0.0

Problema = Literal["sem_suporte", "distorce", "contradiz"]

PROBLEMAS_QUE_BLOQUEIAM = frozenset({"distorce", "contradiz"})
"""Os dois que trazem o trecho da Ata. ``sem_suporte`` é opinião do modelo e só avisa."""

DESCRICAO_DO_PROBLEMA: dict[str, str] = {
    "sem_suporte": "a Ata não diz isso",
    "distorce": "a Ata diz outra coisa",
    "contradiz": "a Ata diz o contrário",
}

PREAMBULO = (
    "Você confere a fidelidade de um conteúdo educativo ao documento que o originou. Receberá o "
    "documento inteiro e o conteúdo. Aponte somente as afirmações do conteúdo sobre o documento que "
    "o documento não sustenta, de um destes tipos:\n"
    "- sem_suporte: o conteúdo afirma um fato sobre o documento que o documento não diz.\n"
    "- distorce: o conteúdo muda o sentido do que o documento diz (por exemplo, trocar 'pode' por "
    "'vai', 'manteve' por 'subiu', ou atribuir a decisão a quem não decidiu).\n"
    "- contradiz: o conteúdo afirma o contrário do que o documento diz.\n\n"
    "NÃO aponte: explicação de termo, analogia do cotidiano ou exemplo escritos para o leitor "
    "(são didática, não afirmação sobre o documento); simplificação de linguagem; opinião sobre "
    "estilo; números (outra verificação já os confere); conclusão direta dos FATOS JÁ CONFERIDOS "
    "(por exemplo, 7 votos a favor e nenhum contra é uma decisão unânime). Na dúvida, não aponte. "
    "Se o conteúdo é fiel, devolva a lista vazia.\n\n"
    "Para cada achado, copie LITERALMENTE o trecho do conteúdo em 'trecho_da_celula'. Para 'distorce' "
    "e 'contradiz', copie LITERALMENTE o trecho do documento que mostra o que ele diz, em "
    "'trecho_da_ata'. Nunca parafraseie um trecho: ele será conferido caractere a caractere. "
    "Responda apenas com o objeto JSON pedido."
)


class AfirmacaoSuspeita(BaseModel):
    trecho_da_celula: str = Field(description="Copiado literalmente do conteúdo.")
    problema: Problema
    trecho_da_ata: str = Field(
        default="",
        description="Copiado literalmente do documento. Obrigatório em distorce e contradiz.",
    )
    explicacao: str = Field(description="Uma frase curta, em português.")


class RespostaDeFidelidade(BaseModel):
    problemas: list[AfirmacaoSuspeita] = Field(default_factory=list, max_length=MAXIMO_DE_ACHADOS)


@dataclass(frozen=True)
class AchadoConfirmado:
    trecho_da_celula: str
    problema: Problema
    trecho_da_ata: str
    explicacao: str

    @property
    def bloqueia(self) -> bool:
        """Só o que tem a citação da Ata (já conferida pelo código) reprova a Célula."""
        return self.problema in PROBLEMAS_QUE_BLOQUEIAM

    @property
    def descricao(self) -> str:
        base = f"«{self.trecho_da_celula}» — {DESCRICAO_DO_PROBLEMA[self.problema]}"
        if self.trecho_da_ata:
            base += f"; a Ata diz: «{self.trecho_da_ata}»"
        return base


@dataclass(frozen=True)
class ResultadoDeFidelidade:
    achados: tuple[AchadoConfirmado, ...]
    descartados: int
    """Quantos achados o código recusou por citação que não existe: invenção do juiz."""


def _fatos_conferidos(ancoras: Sequence[Ancora]) -> str:
    """Os fatos que o sistema já tirou do documento por regra: o checador não os reaponta."""
    linhas = [
        f"- {a.rotulo}: {a.valor_literal}" if isinstance(a, AncoraNumerica) else f"- {a.afirmacao}"
        for a in ancoras
    ]
    if not linhas:
        return ""
    return "FATOS JÁ CONFERIDOS PELO SISTEMA (extraídos do documento):\n" + "\n".join(linhas) + "\n\n"


def _plano(texto: str) -> str:
    """Para comparar trechos: minúsculo, sem mudança de espaço, aspas e travessão uniformes."""
    sem_variantes = (
        texto.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
        .replace("–", "-").replace("—", "-")
    )
    normal = unicodedata.normalize("NFC", sem_variantes)
    return re.sub(r"\s+", " ", normal).strip().casefold()


class VerificadorDeFidelidade:
    """Confere uma Célula contra a Ata a que ela pertence. Uma instância por Ata."""

    def __init__(self, provedor: Provedor, texto_da_ata: str) -> None:
        self.provedor = provedor
        self.texto_da_ata = texto_da_ata
        self._ata_plana = _plano(texto_da_ata)

    def verificar(
        self,
        conteudo: Conteudo,
        audiencia: Audiencia,
        ancoras: Sequence[Ancora] = (),
    ) -> ResultadoDeFidelidade:
        """Levanta ``ErroProvedor`` quando o provedor falha ou a Ata não cabe; quem chama decide."""
        if len(self.texto_da_ata) > LIMITE_DA_ATA_EM_CARACTERES:
            raise ErroProvedor(
                "checador",
                f"a Ata tem {len(self.texto_da_ata)} caracteres; o limite é {LIMITE_DA_ATA_EM_CARACTERES}",
            )
        texto = conteudo.texto_avaliavel()
        resposta = self._perguntar(texto, conteudo, audiencia, ancoras)
        return self._conferir(resposta, _plano(texto))

    def _perguntar(
        self, texto: str, conteudo: Conteudo, audiencia: Audiencia, ancoras: Sequence[Ancora]
    ) -> RespostaDeFidelidade:
        pedido = PedidoLLM(
            papel=PapelLLM.CHECADOR,
            rotulo=f"fidelidade:{audiencia.value}:{conteudo.formato.value}",
            mensagens=[
                Mensagem(autor="sistema", texto=PREAMBULO),
                Mensagem(
                    autor="usuario",
                    texto=(
                        f"DOCUMENTO:\n{self.texto_da_ata}\n\n"
                        f"{_fatos_conferidos(ancoras)}"
                        f"CONTEÚDO (para a Audiência {audiencia.value}, {conteudo.formato.value}):\n{texto}"
                    ),
                ),
            ],
            max_tokens=TETO_DE_TOKENS,
            temperatura=TEMPERATURA,
            esforco_raciocinio="baixo",
        )
        try:
            return self.provedor.completar_estruturado(pedido, RespostaDeFidelidade)
        except RespostaMalformada as erro:
            raise ErroProvedor("checador", f"resposta fora do schema: {erro.mensagem}") from None

    def _conferir(self, resposta: RespostaDeFidelidade, celula_plana: str) -> ResultadoDeFidelidade:
        confirmados: list[AchadoConfirmado] = []
        descartados = 0
        for achado in resposta.problemas:
            trecho_celula = _plano(achado.trecho_da_celula)
            trecho_ata = _plano(achado.trecho_da_ata)
            if len(trecho_celula) < TRECHO_MINIMO_DA_CELULA or trecho_celula not in celula_plana:
                descartados += 1
                continue
            if achado.problema in ("distorce", "contradiz") and (
                not trecho_ata or trecho_ata not in self._ata_plana
            ):
                descartados += 1
                continue
            if achado.problema == "sem_suporte" and trecho_ata and trecho_ata not in self._ata_plana:
                trecho_ata = ""  # citação inventada num achado que não precisava dela: some a citação
            confirmados.append(
                AchadoConfirmado(
                    trecho_da_celula=achado.trecho_da_celula.strip(),
                    problema=achado.problema,
                    trecho_da_ata=achado.trecho_da_ata.strip() if trecho_ata else "",
                    explicacao=achado.explicacao.strip(),
                )
            )
        return ResultadoDeFidelidade(achados=tuple(confirmados), descartados=descartados)

    @classmethod
    def de_ambiente(cls, texto_da_ata: str, *, ligado: bool | None = None) -> "VerificadorDeFidelidade | None":
        """Monta o verificador se foi pedido e há Groq ou Gemini. ``None`` diz o motivo no log.

        ``ligado`` sobrepõe ``SUNO_FIDELIDADE`` nos dois sentidos (``--fidelidade`` na linha de comando).
        """
        if not _esta_pedido(ligado):
            return None
        from suno.provedores.roteador import roteador_para

        try:
            provedor = roteador_para(PapelLLM.CHECADOR)
        except ErroProvedor as erro:
            _REGISTRO.warning(
                "checador de fidelidade pedido mas não montado: falta GROQ_API_KEY ou GEMINI_API_KEY no .env (%s) — ADR 0036",
                erro,
            )
            return None
        return cls(provedor, texto_da_ata)


def _esta_pedido(ligado: bool | None) -> bool:
    if ligado is not None:
        return ligado
    return carregar().fidelidade_ligada


__all__ = [
    "AchadoConfirmado",
    "AfirmacaoSuspeita",
    "RespostaDeFidelidade",
    "ResultadoDeFidelidade",
    "VerificadorDeFidelidade",
]
