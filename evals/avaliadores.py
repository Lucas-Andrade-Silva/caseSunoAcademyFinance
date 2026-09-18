"""Os `Evaluator` próprios da suíte. Todos determinísticos e offline (ADR 0001, 0003).

Nenhum deles chama LLM: `LLMJudge` e `GEval` do `pydantic-evals` existem e ficam de fora
de propósito — a suíte é o que mantém o Avaliador testável em CI, e um juiz-LLM a tornaria
não-determinística e dependente de cota.

Cada avaliador devolve um mapeamento `{nome: EvaluationReason}`, porque é isso que faz o
relatório do `pydantic-evals` mostrar um nome legível por asserção em vez de um só nome por
classe. Mapeamento vazio quer dizer "este caso não afirma nada sobre isto": é como um caso
de medida ausente pode não opinar sobre o destino do Laudo.

A comparação de faixa usa `Faixa` do domínio, fechada no mínimo e aberta no máximo — a
mesma regra que aprova 50,0 na Audiência Iniciante e reprova 49,9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.evaluators.evaluator import EvaluationReason

from evals.tarefas import Entrada, MedidaResumida, SaidaLaudo
from suno.dominio import EstadoMedida, Faixa, Metrica

Contexto = EvaluatorContext[Entrada, SaidaLaudo, str]
Achados = Mapping[str, EvaluationReason]


def _medida(saida: SaidaLaudo, metrica: Metrica) -> MedidaResumida | None:
    return saida.medidas.get(metrica)


@dataclass(repr=False)
class DestinoEsperado(Evaluator[Entrada, SaidaLaudo, str]):
    """O Laudo terminou no destino que o caso espera (ADR 0013)."""

    def evaluate(self, ctx: Contexto) -> Achados:
        esperado = ctx.expected_output
        if esperado is None or esperado.destino is None:
            return {}
        obtido = ctx.output.destino
        return {
            "destino": EvaluationReason(
                value=obtido == esperado.destino,
                reason=f"esperado {esperado.destino}, obtido {obtido}",
            )
        }


@dataclass(repr=False)
class MotivosEsperados(Evaluator[Entrada, SaidaLaudo, str]):
    """Os motivos de reprovação são exatamente os que o caso espera, sem sobra nem falta.

    Compara como conjunto: a ordem dos motivos no Laudo é do Avaliador, não do caso.
    Lista vazia no caso é uma afirmação — "este Laudo não reprova por nada".
    """

    def evaluate(self, ctx: Contexto) -> Achados:
        esperado = ctx.expected_output
        if esperado is None or esperado.motivos is None:
            return {}
        obtidos = set(ctx.output.motivos or [])
        alvo = set(esperado.motivos)
        faltando = sorted(str(m) for m in alvo - obtidos)
        sobrando = sorted(str(m) for m in obtidos - alvo)
        return {
            "motivos": EvaluationReason(
                value=obtidos == alvo,
                reason=f"faltando {faltando}, sobrando {sobrando}" if obtidos != alvo else "iguais",
            )
        }


@dataclass(repr=False)
class MedidaNaFaixa(Evaluator[Entrada, SaidaLaudo, str]):
    """A métrica foi medida e o valor caiu na faixa que o caso declara.

    ``minimo`` inclusivo, ``maximo`` exclusivo, como toda `Faixa` do projeto. Medida
    ausente reprova a asserção: um caso que declara faixa está afirmando que há base
    para medir.
    """

    metrica: Metrica
    minimo: float | None = None
    maximo: float | None = None

    def __post_init__(self) -> None:
        # O YAML entrega a métrica como texto; o `pydantic-evals` chama o construtor cru.
        self.metrica = Metrica(self.metrica)

    def evaluate(self, ctx: Contexto) -> Achados:
        nome = f"{self.metrica}_na_faixa"
        medida = _medida(ctx.output, self.metrica)
        faixa = Faixa(minimo=self.minimo, maximo=self.maximo)
        if medida is None:
            return {nome: EvaluationReason(value=False, reason=f"{self.metrica} não está no Laudo")}
        if medida.valor is None:
            return {
                nome: EvaluationReason(
                    value=False, reason=f"{self.metrica} sem valor (estado {medida.estado})"
                )
            }
        return {
            nome: EvaluationReason(
                value=faixa.contem(medida.valor),
                reason=f"valor {medida.valor:.4f}; faixa [{self.minimo}, {self.maximo})",
            )
        }


@dataclass(repr=False)
class MedidaAusente(Evaluator[Entrada, SaidaLaudo, str]):
    """A métrica saiu ausente — sem base para medir, nunca zero (`dominio.EstadoMedida`).

    É o caso-limite que o ADR 0008 e o `Medida._ausente_sem_valor` protegem: texto sem
    palavra nenhuma não vira Flesch-BR zero, vira medida ausente.
    """

    metrica: Metrica

    def __post_init__(self) -> None:
        self.metrica = Metrica(self.metrica)

    def evaluate(self, ctx: Contexto) -> Achados:
        nome = f"{self.metrica}_ausente"
        medida = _medida(ctx.output, self.metrica)
        if medida is None:
            return {nome: EvaluationReason(value=False, reason=f"{self.metrica} não está no Laudo")}
        ausente = medida.estado is EstadoMedida.AUSENTE and medida.valor is None
        return {
            nome: EvaluationReason(
                value=ausente,
                reason=f"estado {medida.estado}, valor {medida.valor}",
            )
        }


AVALIADORES_PROPRIOS: tuple[type[Evaluator], ...] = (
    DestinoEsperado,
    MotivosEsperados,
    MedidaNaFaixa,
    MedidaAusente,
)
"""Passado em ``custom_evaluator_types`` para o YAML poder nomear qualquer um deles."""


__all__ = [
    "AVALIADORES_PROPRIOS",
    "DestinoEsperado",
    "MedidaAusente",
    "MedidaNaFaixa",
    "MotivosEsperados",
]
