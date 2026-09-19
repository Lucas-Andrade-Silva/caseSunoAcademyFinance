"""Ciclo de correção: no máximo duas rodadas; o feedback é o valor medido. Falha de extração
nem tenta: vai direto à fila humana (H4).

ADR 0013.

Três gerações no pior caso — a original mais duas correções — e nunca uma quarta. É o que
torna o custo por Ata previsível: nove Células × três gerações = 27 chamadas de Gerador no
teto, e é isso que faz do orçamento de R$ 0 uma afirmação verificável.

Os três desfechos de uma rodada:

- ``APROVADO`` — o Ciclo para, a Célula está pronta.
- ``REPROVADO_REVISAO_HUMANA`` — falha de extração. **Não** há nova rodada: reescrever não
  conserta um documento mal lido (ADR 0013).
- ``REPROVADO_CORRIGIVEL`` — nova rodada com ``laudo.correcoes``, até o teto. Depois do
  teto, o destino final vira revisão humana com as três tentativas preservadas.

Falha de provedor no meio do Ciclo termina o histórico em revisão humana com o que já
existia: uma Célula reprovada em mão vale mais que nenhuma, e quem decide é o humano do H4.
O erro que interrompeu fica em ``HistoricoCelula.falha``, já sem credencial — é o que a
``Pendencia`` do H4 mostra, e é o que separa "o Gerador não conseguiu consertar" de "a cota
acabou no meio".
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from suno.avaliador import avaliar
from suno.dominio import (
    Ancoras,
    Ata,
    Audiencia,
    Celula,
    Correcao,
    Destino,
    ErroProvedor,
    Formato,
    HistoricoCelula,
    Tentativa,
)
from suno.gerador.moldes import MODELO_POR_FORMATO, montar_conteudo, montar_pedido
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.comite import Comite

_registro = logging.getLogger(__name__)

TETO_DE_RODADAS = 2
"""Duas correções depois da original: o ganho se concentra na primeira (ADR 0013)."""

CREDENCIAL_OCULTA = "<credencial oculta>"

_SEGREDOS = (
    # Chave nomeada no próprio texto do erro: "api_key=AIza…", "Authorization: Bearer …".
    re.compile(r"(?i)\b(?:api[-_]?key|apikey|authorization|token)\b\s*[:=]\s*[^\s,;)\]]+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]+"),
    # Os prefixos que os provedores do projeto usam (ADR 0007).
    re.compile(r"\b(?:AIza|gsk_|sk-|sn_)[A-Za-z0-9_\-]{8,}"),
    # Sobra opaca e longa: 32 caracteres de letra e dígito não são palavra em português.
    re.compile(r"\b(?=[A-Za-z0-9_\-]*[0-9])(?=[A-Za-z0-9_\-]*[A-Za-z])[A-Za-z0-9_\-]{32,}\b"),
)
"""O erro de um provedor vai para o disco e para a interface: nenhuma chave viaja junto."""


def sem_credencial(texto: str) -> str:
    """Tira do texto o que parecer chave de API antes de ele virar estado gravado."""
    limpo = texto
    for padrao in _SEGREDOS:
        limpo = padrao.sub(CREDENCIAL_OCULTA, limpo)
    return limpo


def gerar_celula(
    ata: Ata,
    ancoras: Ancoras,
    audiencia: Audiencia,
    formato: Formato,
    provedor: Provedor,
    rodada: int = 0,
    correcoes: list[Correcao] | None = None,
) -> Celula:
    """Uma chamada estruturada ao provedor. Sem ferramenta, sem decisão dinâmica (ADR 0010)."""
    pedido = montar_pedido(ata.texto, ancoras, audiencia, formato, rodada, correcoes)
    modelo = MODELO_POR_FORMATO[formato]
    resposta_estruturada = provedor.completar_estruturado(pedido, modelo)
    conteudo = montar_conteudo(resposta_estruturada, formato, ancoras)
    return Celula(
        audiencia=audiencia,
        formato=formato,
        conteudo=conteudo,
        rodada=rodada,
        provedor=getattr(provedor, "nome", None),
    )


def interrompido_por_provedor(historico: HistoricoCelula) -> bool:
    """O Ciclo parou por falha de provedor? Atalho de leitura de ``HistoricoCelula.falha``.

    O campo é a resposta, não a dedução: um histórico que esgotou o teto reprovou por
    mérito e sai com ``falha is None``; um que parou no meio carrega o erro.
    """
    return historico.falha is not None


def rodar_ciclo(
    ata: Ata,
    ancoras: Ancoras,
    audiencia: Audiencia,
    formato: Formato,
    provedor: Provedor,
    *,
    comite: "Comite | None" = None,
) -> HistoricoCelula:
    """Gera, avalia e corrige uma posição da Matriz até o teto de duas rodadas (ADR 0013)."""
    tentativas: list[Tentativa] = []
    provedores_usados: list[str] = []
    correcoes: list[Correcao] | None = None
    destino_final = Destino.REPROVADO_REVISAO_HUMANA
    falha: str | None = None

    for rodada in range(TETO_DE_RODADAS + 1):
        try:
            celula = gerar_celula(ata, ancoras, audiencia, formato, provedor, rodada, correcoes)
            laudo = avaliar(celula.conteudo, ancoras.todas(), audiencia, comite=comite)
        except ErroProvedor as erro:
            falha = (
                f"o provedor {erro.provedor} falhou na rodada {rodada}: "
                f"{sem_credencial(erro.mensagem)}"
            )
            _registro.warning("Célula %s:%s parou — %s", audiencia, formato, falha)
            break
        except Exception as erro:  # noqa: BLE001 — deliberado, ver docstring do módulo
            # Uma Célula teimosa não pode derrubar a Matriz inteira: as outras oito perderiam
            # o trabalho junto, e `executar` só grava no fim (achado do revisor de erros,
            # 2026-09-19 — `ProvedorFalso` documenta e aceita `BaseException` arbitrária na
            # fila, então isto não é hipotético). O traceback completo vai ao log; o que chega
            # ao `HistoricoCelula` é a versão sem credencial, igual ao caminho de `ErroProvedor`.
            falha = f"erro inesperado na rodada {rodada}: {sem_credencial(str(erro))}"
            _registro.exception("Célula %s:%s parou com erro inesperado", audiencia, formato)
            break
        tentativas.append(Tentativa(rodada=rodada, celula=celula, laudo=laudo))
        if celula.provedor and celula.provedor not in provedores_usados:
            provedores_usados.append(celula.provedor)

        if laudo.destino is Destino.APROVADO:
            destino_final = Destino.APROVADO
            break
        if laudo.destino is Destino.REPROVADO_REVISAO_HUMANA:
            # Falha de extração: reescrever não conserta documento mal lido (ADR 0013).
            destino_final = Destino.REPROVADO_REVISAO_HUMANA
            break
        correcoes = list(laudo.correcoes)
        destino_final = Destino.REPROVADO_REVISAO_HUMANA

    return HistoricoCelula(
        audiencia=audiencia,
        formato=formato,
        tentativas=tentativas,
        destino_final=destino_final,
        provedores_usados=provedores_usados,
        falha=falha,
    )
