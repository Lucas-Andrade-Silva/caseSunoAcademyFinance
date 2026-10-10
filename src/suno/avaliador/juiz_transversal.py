"""LLM as a Judge da Matriz completa, depois de todas as regras determinísticas."""

from __future__ import annotations

import json
from typing import Literal, Sequence

from pydantic import BaseModel, Field, model_validator

from suno.dominio import (
    Ancoras,
    Ata,
    EstadoJulgamentoTransversal,
    GravidadeProblemaTransversal,
    HistoricoCelula,
    JulgamentoTransversal,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    ProblemaTransversal,
)
from suno.provedores.base import Provedor

ROTULO_JUIZ_TRANSVERSAL = "juiz_transversal"
MAX_TOKENS_JUIZ_TRANSVERSAL = 3000


class RespostaJuizTransversal(BaseModel):
    """Schema estrito devolvido pelo Judge; metadados de execução entram depois."""

    estado: Literal["aprovado", "corrigivel", "grave"]
    problemas: list[ProblemaTransversal] = Field(default_factory=list)

    @model_validator(mode="after")
    def _problemas_conforme_estado(self) -> RespostaJuizTransversal:
        if self.estado == "aprovado" and self.problemas:
            raise ValueError("julgamento aprovado não carrega problemas")
        if self.estado != "aprovado" and not self.problemas:
            raise ValueError("julgamento corrigível ou grave precisa localizar um problema")
        tem_grave = any(
            problema.gravidade is GravidadeProblemaTransversal.GRAVE
            for problema in self.problemas
        )
        if self.estado == "corrigivel" and tem_grave:
            raise ValueError("problema grave exige estado grave")
        if self.estado == "grave" and not tem_grave:
            raise ValueError("estado grave exige ao menos um problema de gravidade grave")
        return self


class AgenteAvaliadorTransversal:
    """Julga coerência editorial; nunca substitui as travas determinísticas."""

    def __init__(self, provedor: Provedor) -> None:
        self.provedor = provedor

    def julgar(
        self,
        ata: Ata,
        ancoras: Ancoras,
        celulas: Sequence[HistoricoCelula],
        *,
        rodada: int,
    ) -> JulgamentoTransversal:
        resposta = self.provedor.completar_estruturado(
            self._pedido(ata, ancoras, celulas, rodada), RespostaJuizTransversal
        )
        return JulgamentoTransversal(
            rodada=rodada,
            estado=EstadoJulgamentoTransversal(resposta.estado),
            problemas=resposta.problemas,
            provedor=self.provedor.nome,
        )

    def _pedido(
        self,
        ata: Ata,
        ancoras: Ancoras,
        celulas: Sequence[HistoricoCelula],
        rodada: int,
    ) -> PedidoLLM:
        sistema = (
            "Você é o avaliador editorial transversal de uma Matriz 3x3 de educação "
            "financeira. As regras determinísticas de números, léxico, legibilidade e "
            "recomendação já aprovaram cada Célula. Não refaça essas medições e nunca "
            "autorize um número fora das Âncoras. Julgue somente: fidelidade ao dossiê, "
            "coerência entre as nove Células, progressão Iniciante→Intermediário→Avançado, "
            "adequação real à persona, consistência entre Formatos, clareza narrativa, "
            "omissão relevante e afirmação sem evidência.\n\n"
            "Use estado 'aprovado' quando não houver problema. Use 'corrigivel' quando uma "
            "reescrita localizada resolver. Use 'grave' para contradição factual, perda de "
            "fidelidade ao dossiê ou problema que exige decisão humana. Todo problema precisa "
            "indicar uma Audiência e um Formato concretos, citar a evidência encontrada e dar "
            "uma instrução de correção. Não escreva conteúdo substituto."
        )
        matriz = []
        for historico in celulas:
            celula = historico.celula_final
            if celula is None:
                continue
            matriz.append(
                {
                    "audiencia": historico.audiencia.value,
                    "formato": historico.formato.value,
                    "texto": celula.conteudo.texto_de_conferencia(),
                }
            )
        usuario = "\n\n".join(
            [
                f"Rodada transversal: {rodada}.",
                f"Fonte: {ata.identificador} — {ata.titulo}.",
                "Dossiê factual (somente evidências conferidas):\n"
                + ancoras.model_dump_json(indent=2),
                "Matriz 3x3:\n" + json.dumps(matriz, ensure_ascii=False, indent=2),
            ]
        )
        return PedidoLLM(
            papel=PapelLLM.JUIZ,
            rotulo=f"{ROTULO_JUIZ_TRANSVERSAL}:{rodada}",
            mensagens=[
                Mensagem(autor="sistema", texto=sistema),
                Mensagem(autor="usuario", texto=usuario),
            ],
            max_tokens=MAX_TOKENS_JUIZ_TRANSVERSAL,
            temperatura=0.0,
            esforco_raciocinio="baixo",
        )


__all__ = [
    "AgenteAvaliadorTransversal",
    "ROTULO_JUIZ_TRANSVERSAL",
    "RespostaJuizTransversal",
]
