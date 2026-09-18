"""A função tarefa que a suíte `pydantic-evals` roda, e os modelos que o caso YAML usa.

ADR 0003: os casos ficam em `evals/casos/*.yaml`, versionados; a tarefa só monta
`Conteudo` e `Âncora[]` a partir do caso e chama `avaliar`. Nada aqui vai à rede nem chama
LLM — a suíte inteira é determinística (ADR 0001).

O caso escreve um `texto` só, em qualquer Formato; a conversão para Carrossel e Roteiro é
convenção deste módulo, escolhida para o texto medido não mudar:

- **Carrossel**: cada parágrafo vira um Slide; a primeira linha é o título, o resto é o
  corpo. ``Conteudo.texto_avaliavel`` recompõe ``título\\ncorpo``, então o Flesch-BR do
  caso é o Flesch-BR do texto escrito.
- **Roteiro**: cada parágrafo vira um Bloco de fala de ``SEGUNDOS_POR_BLOCO`` segundos. A
  rubrica de cena fica vazia de propósito: ela não é medida.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from suno.avaliador import avaliar
from suno.dominio import (
    Ancora,
    AncoraNumerica,
    AncoraTextual,
    Audiencia,
    BlocoFala,
    Conteudo,
    Destino,
    EstadoMedida,
    Formato,
    Laudo,
    Metrica,
    MotivoReprovacao,
    Slide,
    Unidade,
)

SEGUNDOS_POR_BLOCO = 5.0
"""Duração de cada Bloco de fala montado a partir de um parágrafo. Só a fala é medida."""


class AncoraSimples(BaseModel):
    """A Âncora como o caso YAML a escreve: chave e literal bastam.

    Com ``afirmacao`` preenchida vira Âncora textual; sem ela, Âncora numérica. ``trecho``
    cai no próprio literal quando o caso não o escreve — o caso é sintético e não tem Ata
    de onde copiar a frase.
    """

    model_config = ConfigDict(extra="forbid")

    chave: str
    literal: str = ""
    unidade: Unidade = Unidade.NUMERO
    numero: float | None = None
    trecho: str = ""
    rotulo: str = ""
    data_iso: date | None = None
    qualificador: str | None = None
    afirmacao: str | None = None

    def materializar(self) -> Ancora:
        """Vira a Âncora do domínio que o Avaliador recebe."""
        if self.afirmacao is not None:
            return AncoraTextual(
                identificador=self.chave,
                afirmacao=self.afirmacao,
                trecho=self.trecho or self.afirmacao,
            )
        return AncoraNumerica(
            chave=self.chave,
            rotulo=self.rotulo or self.chave.replace("_", " "),
            valor_literal=self.literal,
            valor=self.numero,
            unidade=self.unidade,
            trecho=self.trecho or self.literal,
            data_iso=self.data_iso,
            qualificador=self.qualificador,
        )


class Entrada(BaseModel):
    """O ``inputs`` de um caso: o texto da Célula, a posição na Matriz e as Âncoras."""

    model_config = ConfigDict(extra="forbid")

    texto: str = ""
    audiencia: Audiencia
    formato: Formato = Formato.TEXTO_ANALITICO
    ancoras: list[AncoraSimples] = Field(default_factory=list)
    ancoras_citadas: list[str] = Field(default_factory=list)

    def conteudo(self) -> Conteudo:
        """O Conteúdo no Formato pedido, pela convenção do módulo."""
        paragrafos = _paragrafos(self.texto)
        if self.formato is Formato.CARROSSEL:
            return Conteudo(
                formato=self.formato,
                slides=[_slide(p) for p in paragrafos],
                ancoras_citadas=list(self.ancoras_citadas),
            )
        if self.formato is Formato.ROTEIRO:
            return Conteudo(
                formato=self.formato,
                blocos=[_bloco(i, p) for i, p in enumerate(paragrafos)],
                ancoras_citadas=list(self.ancoras_citadas),
            )
        return Conteudo(
            formato=self.formato,
            texto=self.texto,
            ancoras_citadas=list(self.ancoras_citadas),
        )


class MedidaResumida(BaseModel):
    """Uma Medida do Laudo reduzida ao que os avaliadores da suíte leem."""

    model_config = ConfigDict(extra="forbid")

    estado: EstadoMedida | None = None
    valor: float | None = None
    atingiu: bool | None = None


class SaidaLaudo(BaseModel):
    """O Laudo reduzido ao que o caso afirma — e o que o caso YAML escreve em
    ``expected_output``.

    Campo em ``None`` no ``expected_output`` quer dizer "este caso não afirma nada sobre
    isto": é assim que um caso de medida ausente pode não opinar sobre o destino.
    """

    model_config = ConfigDict(extra="forbid")

    destino: Destino | None = None
    motivos: list[MotivoReprovacao] | None = None
    medidas: dict[Metrica, MedidaResumida] = Field(default_factory=dict)

    @classmethod
    def do_laudo(cls, laudo: Laudo) -> "SaidaLaudo":
        return cls(
            destino=laudo.destino,
            motivos=list(laudo.motivos),
            medidas={
                m.metrica: MedidaResumida(estado=m.estado, valor=m.valor, atingiu=m.atingiu)
                for m in laudo.medidas
            },
        )


def julgar(entrada: Entrada) -> SaidaLaudo:
    """A tarefa que ``Dataset.evaluate_sync`` chama: monta a Célula e pede o Laudo.

    Assinatura do ADR 0001 e nada mais: ``(Conteúdo, Âncora[], Audiência) → Laudo``.
    """
    ancoras = [a.materializar() for a in entrada.ancoras]
    laudo = avaliar(entrada.conteudo(), ancoras, entrada.audiencia)
    return SaidaLaudo.do_laudo(laudo)


# ---------------------------------------------------------------------------
# Conversão de texto em Formato
# ---------------------------------------------------------------------------


def _paragrafos(texto: str) -> list[str]:
    """Parágrafos separados por linha em branco. Texto vazio não vira parágrafo nenhum."""
    limpo = texto.replace("\r\n", "\n").replace("\r", "\n")
    return [bloco.strip() for bloco in limpo.split("\n\n") if bloco.strip()]


def _slide(paragrafo: str) -> Slide:
    linhas = paragrafo.split("\n")
    return Slide(titulo=linhas[0], corpo="\n".join(linhas[1:]))


def _bloco(indice: int, paragrafo: str) -> BlocoFala:
    inicio = indice * SEGUNDOS_POR_BLOCO
    return BlocoFala(inicio_s=inicio, fim_s=inicio + SEGUNDOS_POR_BLOCO, fala=paragrafo)


__all__ = [
    "AncoraSimples",
    "Entrada",
    "MedidaResumida",
    "SaidaLaudo",
    "SEGUNDOS_POR_BLOCO",
    "julgar",
]
