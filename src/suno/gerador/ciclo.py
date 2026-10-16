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
from typing import TYPE_CHECKING, Callable

from suno.avaliador import avaliar
from suno.dominio import (
    Ancoras,
    Ata,
    Audiencia,
    CategoriaDaAta,
    Celula,
    Correcao,
    Destino,
    DuracaoDoVideo,
    ErroProvedor,
    EtapaDaCelula,
    Formato,
    HistoricoCelula,
    Tentativa,
    chaves_essenciais_da_ata,
)
from suno.gerador.moldes import (
    INSTRUCAO_DA_VISAO_UNIDA,
    MODELO_POR_FORMATO,
    descricao_do_comunicado,
    montar_conteudo,
    montar_pedido,
)
from suno.configuracoes import carregar as carregar_configuracoes
from suno.provedores.base import Provedor

if TYPE_CHECKING:
    from suno.avaliador.fidelidade import VerificadorDeFidelidade
    from suno.avaliador.qualidade import AvaliadorDeQualidade

_registro = logging.getLogger(__name__)

TETO_DE_RODADAS = 2
"""O teto antigo (ADR 0013). Hoje o valor vem de ``configuracoes.rodadas_de_correcao`` (padrão 4),
editável na aba Configurações: o Ciclo regenera e roda o determinístico de novo até passar ou até o teto."""

Andou = Callable[[Audiencia, Formato, EtapaDaCelula, int], None]
"""Aviso de andamento de uma Célula: (Audiência, Formato, etapa, rodada). Quem escuta é a API."""

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
    duracao: DuracaoDoVideo = DuracaoDoVideo.S60,
    rascunho: str | None = None,
) -> Celula:
    """Uma chamada estruturada ao provedor. Sem ferramenta, sem decisão dinâmica (ADR 0010)."""
    pedido = montar_pedido(
        ata.texto,
        ancoras,
        audiencia,
        formato,
        rodada,
        correcoes,
        comunicado=descricao_do_comunicado(ata.categoria),
        instrucoes_do_conjunto=(
            INSTRUCAO_DA_VISAO_UNIDA if ata.categoria is CategoriaDaAta.UNIDA else None
        ),
        duracao=duracao,
        rascunho=rascunho,
    )
    modelo = MODELO_POR_FORMATO[formato]
    resposta_estruturada = provedor.completar_estruturado(pedido, modelo)
    conteudo = montar_conteudo(resposta_estruturada, formato, ancoras, duracao)
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


def _avisar(
    ao_andar: Andou | None,
    audiencia: Audiencia,
    formato: Formato,
    etapa: EtapaDaCelula,
    rodada: int,
) -> None:
    """Um callback quebrado (a tela caiu) nunca pode derrubar o Ciclo de uma Célula."""
    if ao_andar is None:
        return
    try:
        ao_andar(audiencia, formato, etapa, rodada)
    except Exception:  # noqa: BLE001 - o aviso é de cortesia; a geração segue
        _registro.exception("aviso de andamento falhou em %s:%s", audiencia, formato)


_ETAPA_DA_CAMADA = {
    "deterministica": EtapaDaCelula.AVALIANDO_DETERMINISTICA,
    "jev": EtapaDaCelula.AVALIANDO_JEV,
    "llm": EtapaDaCelula.AVALIANDO_LLM,
}
"""As camadas do Avaliador (``laudo.avaliar``) e a etapa que cada uma mostra ao vivo."""


def rodar_ciclo(
    ata: Ata,
    ancoras: Ancoras,
    audiencia: Audiencia,
    formato: Formato,
    provedor: Provedor,
    *,
    qualidade: "AvaliadorDeQualidade | None" = None,
    fidelidade: "VerificadorDeFidelidade | None" = None,
    ao_andar: Andou | None = None,
    duracao: DuracaoDoVideo = DuracaoDoVideo.S60,
) -> HistoricoCelula:
    """Gera, avalia e corrige uma posição da Matriz até o teto de rodadas configurado (ADR 0013).

    ``ao_andar`` recebe ``gerando`` na rodada 0, ``corrigindo`` nas seguintes e, no fim,
    ``aprovada`` ou ``revisao_humana``.
    """
    tentativas: list[Tentativa] = []
    provedores_usados: list[str] = []
    correcoes: list[Correcao] | None = None
    destino_final = Destino.REPROVADO_REVISAO_HUMANA
    falha: str | None = None

    # Só uma Ata de outra categoria muda o conjunto essencial; o Copom segue pelo padrão.
    essenciais = (
        {}
        if ata.categoria is CategoriaDaAta.COPOM
        else {"chaves_essenciais": chaves_essenciais_da_ata(ata)}
    )
    # Qualidade (Jev, ADR 0035) e Fidelidade (ADR 0036) só viajam quando existem: quem não as liga
    # chama `avaliar` como antes.
    opcionais = {
        nome: camada
        for nome, camada in (("qualidade", qualidade), ("fidelidade", fidelidade))
        if camada is not None
    }

    def avisos_de_camada(rodada: int) -> dict:
        # Sem quem escute o andamento, `avaliar` é chamado como sempre foi.
        if ao_andar is None:
            return {}
        return {
            "ao_etapa": lambda camada: _avisar(
                ao_andar, audiencia, formato, _ETAPA_DA_CAMADA[camada], rodada
            )
        }

    ultima_rodada = 0
    teto_de_rodadas = carregar_configuracoes().rodadas_de_correcao
    for rodada in range(teto_de_rodadas + 1):
        ultima_rodada = rodada
        _avisar(
            ao_andar,
            audiencia,
            formato,
            EtapaDaCelula.GERANDO if rodada == 0 else EtapaDaCelula.CORRIGINDO,
            rodada,
        )
        try:
            celula = gerar_celula(
                ata,
                ancoras,
                audiencia,
                formato,
                provedor,
                rodada,
                correcoes,
                duracao,
                rascunho=tentativas[-1].celula.conteudo.texto_avaliavel() if tentativas else None,
            )
            laudo = avaliar(
                celula.conteudo,
                ancoras.todas(),
                audiencia,
                **opcionais,
                **avisos_de_camada(rodada),
                **essenciais,
            )
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

    _avisar(
        ao_andar,
        audiencia,
        formato,
        EtapaDaCelula.APROVADA
        if destino_final is Destino.APROVADO
        else EtapaDaCelula.REVISAO_HUMANA,
        ultima_rodada,
    )
    return HistoricoCelula(
        audiencia=audiencia,
        formato=formato,
        tentativas=tentativas,
        destino_final=destino_final,
        provedores_usados=provedores_usados,
        falha=falha,
    )
