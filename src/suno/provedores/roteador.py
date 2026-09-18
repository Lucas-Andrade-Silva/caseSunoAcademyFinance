"""Roteador: Gemini -> Groq -> SambaNova. Lê o tipo de 429 antes de decidir entre esperar e
trocar. O schema viaja no pedido, então a troca não perde saída estruturada. O juiz nunca
resolve para o provedor do Gerador.

ADR 0007.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, Sequence, TypeVar

from pydantic import BaseModel

from suno.dominio import (
    CotaEsgotada,
    ErroProvedor,
    EsgotamentoDeCota,
    PapelLLM,
    PedidoLLM,
    RespostaLLM,
    RespostaMalformada,
)
from suno.provedores.base import Provedor, ProvedorBase, validar_resposta
from suno.provedores.falso import ProvedorFalso

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

# Espera usada quando o 429 por minuto não sugere tempo nenhum.
ESPERA_PADRAO_S = 20.0

# Chave e nome de modelo por provedor. Nome de modelo é configuração (ADR 0007).
CONFIGURACAO = {
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODELO"),
    "groq": ("GROQ_API_KEY", "GROQ_MODELO"),
    "sambanova": ("SAMBANOVA_API_KEY", "SAMBANOVA_MODELO"),
}

# Gemini gera (só ele aguenta a Ata inteira), Groq julga (prompt curto), SambaNova é
# reserva. O juiz de visão precisa de entrada de imagem, e aí o Gemini volta à frente.
ORDEM_POR_PAPEL: dict[PapelLLM, tuple[str, ...]] = {
    PapelLLM.GERADOR: ("gemini", "groq", "sambanova"),
    PapelLLM.JUIZ: ("groq", "sambanova", "gemini"),
    PapelLLM.JUIZ_VISAO: ("gemini", "groq", "sambanova"),
}


class Roteador(ProvedorBase):
    """Uma fila ordenada de provedores com memória do que já morreu no dia.

    Um 429 por minuto se resolve sozinho: espera o tempo que o próprio provedor sugerir e
    insiste no mesmo. Um 429 diário não passa: marca o provedor como esgotado pelo resto da
    vida do roteador e vai para o próximo. DESCONHECIDO conta como diário — é o erro que
    "nunca passa" que o ADR 0007 cita, e esperar por ele custa a execução inteira.
    """

    nome = "roteador"

    def __init__(
        self,
        provedores: Sequence[Provedor],
        *,
        excluir: Sequence[str] = (),
        dormir: Callable[[float], None] = time.sleep,
        espera_maxima_s: float = 90.0,
        tentativas_por_minuto: int = 3,
    ) -> None:
        excluidos = set(excluir)
        self.provedores: list[Provedor] = [p for p in provedores if p.nome not in excluidos]
        self.excluidos = excluidos
        self.dormir = dormir
        self.espera_maxima_s = espera_maxima_s
        self.tentativas_por_minuto = tentativas_por_minuto
        self.historico: list[str] = []
        self.esgotados: set[str] = set()
        if not self.provedores:
            raise ErroProvedor(self.nome, f"nenhum provedor sobrou depois de excluir {sorted(excluidos)}")

    # -- contrato -----------------------------------------------------------

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        return self._percorrer(pedido, lambda resposta, _nome: resposta)

    def completar_estruturado(self, pedido: PedidoLLM, modelo: type[T]) -> T:
        """A validação acontece dentro da volta: resposta fora do schema troca de provedor.

        O schema é anexado uma vez e viaja no pedido, então o segundo provedor recebe
        exatamente o mesmo pedido estruturado que o primeiro recebeu (ADR 0007).
        """
        pedido_com_schema = pedido.model_copy(
            update={"schema_saida": pedido.schema_saida or modelo.model_json_schema()}
        )
        return self._percorrer(
            pedido_com_schema,
            lambda resposta, nome: validar_resposta(nome, resposta.texto, modelo),
        )

    # -- a volta ------------------------------------------------------------

    def _percorrer(self, pedido: PedidoLLM, converter: Callable[[RespostaLLM, str], R]) -> R:
        for provedor in self.provedores:
            nome = provedor.nome
            if nome in self.esgotados:
                self._anotar(f"{nome}: já esgotado no dia, pulando")
                continue
            esperas = 0
            erros = 0
            while True:
                try:
                    return converter(provedor.completar(pedido), nome)
                except CotaEsgotada as erro:
                    if erro.esgotamento is EsgotamentoDeCota.POR_MINUTO:
                        if esperas < self.tentativas_por_minuto:
                            espera_s = min(erro.espera_s or ESPERA_PADRAO_S, self.espera_maxima_s)
                            self._anotar(f"{nome}: 429 por minuto, esperando {espera_s:g} s")
                            self.dormir(espera_s)
                            esperas += 1
                            continue
                        self._anotar(
                            f"{nome}: 429 por minuto {esperas}x sem passar, trocando de provedor"
                        )
                        break
                    self.esgotados.add(nome)
                    razao = "esgotado no dia" if erro.esgotamento is EsgotamentoDeCota.POR_DIA else (
                        "429 sem pista, tratado como diário"
                    )
                    self._anotar(f"{nome}: {razao}, trocando para o próximo")
                    break
                except RespostaMalformada as erro:
                    # O formato não bateu; outro provedor pode acertar. Não é cota.
                    self._anotar(f"{nome}: resposta fora do schema ({erro.mensagem}), trocando")
                    break
                except ErroProvedor as erro:
                    if erros == 0:
                        erros += 1
                        self._anotar(f"{nome}: erro do provedor ({erro.mensagem}), tentando mais uma vez")
                        continue
                    self._anotar(f"{nome}: erro do provedor de novo ({erro.mensagem}), trocando")
                    break
        raise CotaEsgotada(
            self.nome,
            EsgotamentoDeCota.POR_DIA,
            mensagem="nenhum provedor respondeu: " + " | ".join(self.historico),
        )

    def _anotar(self, linha: str) -> None:
        self.historico.append(linha)


# ---------------------------------------------------------------------------
# Montagem a partir do ambiente
# ---------------------------------------------------------------------------


def provedor_por_nome(nome: str, *, respostas_prontas: Path | None = None) -> Provedor:
    """'falso' | 'gemini' | 'groq' | 'sambanova' | 'roteador'. Lê chaves e modelos do ambiente.

    Quem carrega o ``.env`` é a linha de comando, não esta função: assim o pytest continua
    enxergando um ambiente sem chave nenhuma, mesmo numa máquina que tem ``.env``.
    """
    escolhido = (nome or "").strip().lower()
    if escolhido == "falso":
        return ProvedorFalso.de_arquivo(respostas_prontas) if respostas_prontas else ProvedorFalso()
    if escolhido == "roteador":
        return roteador_para(PapelLLM.GERADOR)
    if escolhido in CONFIGURACAO:
        return _concreto(escolhido)
    raise ErroProvedor(
        "roteador",
        f"provedor {nome!r} desconhecido: use falso, gemini, groq, sambanova ou roteador",
    )


def roteador_para(papel: PapelLLM, *, excluir: Sequence[str] = ()) -> Provedor:
    """Monta o roteador com os provedores que têm chave, na ordem do papel.

    O juiz recebe ``excluir`` com o provedor que gerou a Célula: ele nunca pode resolver
    para o mesmo provedor do Gerador (ADR 0008).
    """
    excluidos = {e.strip().lower() for e in excluir}
    disponiveis: list[Provedor] = []
    for nome in ORDEM_POR_PAPEL.get(papel, ORDEM_POR_PAPEL[PapelLLM.GERADOR]):
        if nome in excluidos or not os.environ.get(CONFIGURACAO[nome][0]):
            continue
        disponiveis.append(_concreto(nome))
    if not disponiveis:
        raise ErroProvedor(
            "roteador",
            "nenhuma chave de provedor no ambiente: copie .env.example para .env e preencha "
            "GEMINI_API_KEY, GROQ_API_KEY ou SAMBANOVA_API_KEY — ou rode com --provedor falso",
        )
    return Roteador(disponiveis)


def _concreto(nome: str) -> Provedor:
    """Importa tarde de propósito: quem roda com ``falso`` não paga o custo do httpx."""
    variavel_da_chave, variavel_do_modelo = CONFIGURACAO[nome]
    chave = os.environ.get(variavel_da_chave, "")
    if not chave:
        raise ErroProvedor(nome, f"{variavel_da_chave} ausente: preencha o .env (veja .env.example)")
    modelo = os.environ.get(variavel_do_modelo, "")
    if not modelo:
        raise ErroProvedor(
            nome,
            f"{variavel_do_modelo} ausente: o nome do modelo é configuração, nunca constante "
            "em código (ADR 0007) — confira o tier gratuito no painel do provedor",
        )
    if nome == "gemini":
        from suno.provedores.gemini import ProvedorGemini

        return ProvedorGemini(chave, modelo)
    if nome == "groq":
        from suno.provedores.groq import ProvedorGroq

        return ProvedorGroq(chave, modelo)
    from suno.provedores.sambanova import ProvedorSambaNova

    return ProvedorSambaNova(chave, modelo)
