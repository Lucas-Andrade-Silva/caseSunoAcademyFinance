"""Junta as cinco medidas num Laudo com três destinos. Métrica sem base sai `ausente`,
nunca zero. O comitê é opcional e roda depois das medidas determinísticas, nunca antes.

ADR 0001, 0008, 0013.

As regras que este arquivo fixa, e que alguém vai querer "corrigir" sem saber:

- **As cinco medidas saem sempre**, inclusive quando a primeira já reprovou. Quem lê a fila
  de revisão humana (H4) precisa ver o texto inteiro julgado, não só o primeiro defeito.
- **Falha de extração não gera Correção.** É a leitura da Ata que está sob suspeita, não a
  Célula: reescrever não conserta documento mal lido (ADR 0013). As outras quatro medidas
  continuam a render Correção, mas o destino é a revisão humana de qualquer forma.
- **Ausente nunca é zero.** Texto sem palavra não tem Flesch-BR; texto sem número não tem
  Aderência. Nesses casos ``valor`` é ``None``, ``atingiu`` é ``None`` e não há motivo de
  reprovação — ausência de base não é reprovação.
- **A Correção carrega o valor medido e a distância**, nunca "melhore o texto" (ADR 0013).
- **O comitê nunca move o veredito.** Ele entra em ``laudo.comite`` como informação; o
  destino e os motivos saem só das medidas determinísticas (ADR 0008). Comitê que falhou
  sai ausente, nunca nota zero.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Sequence

from suno.avaliador.aderencia import medir_aderencia
from suno.avaliador.densidade import medir_densidade
from suno.avaliador.flesch_br import flesch_br
from suno.avaliador.integridade import medir_integridade
from suno.avaliador.recomendacao import detectar_recomendacao
from suno.dominio import (
    CHAVES_ESSENCIAIS,
    LIMIARES_PROVISORIOS,
    Ancora,
    AncoraNumerica,
    Audiencia,
    Conteudo,
    Correcao,
    Destino,
    ErroProvedor,
    EstadoMedida,
    Faixa,
    Formato,
    Laudo,
    Limiares,
    Medida,
    Metrica,
    MotivoReprovacao,
    ResultadoComite,
)

if TYPE_CHECKING:
    from suno.comite import Comite

_REGISTRO = logging.getLogger(__name__)

NOME_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "Iniciante",
    Audiencia.INTERMEDIARIO: "Intermediário",
    Audiencia.AVANCADO: "Avançado",
}
"""Como a Audiência aparece dentro da instrução de Correção, que um humano também lê."""

FORMATOS_JULGADOS_PELO_COMITE: tuple[Formato, ...] = (
    Formato.TEXTO_ANALITICO,
    Formato.CARROSSEL,
)
"""O Roteiro passa só pelas medidas determinísticas (ADR 0008)."""

RECOMENDACOES_ACEITAS = Faixa(maximo=1)
"""Zero é o único valor aceito: qualquer ocorrência reprova (CLAUDE.md, a linha que não se cruza)."""

_Achado = tuple[Medida, MotivoReprovacao | None, Correcao | None]


def avaliar(
    conteudo: Conteudo,
    ancoras: Sequence[Ancora],
    audiencia: Audiencia,
    *,
    limiares: Limiares | None = None,
    comite: "Comite | None" = None,
) -> Laudo:
    """``(Conteúdo, Âncora[], Audiência) → Laudo``: a costura inteira (ADR 0001).

    Sem LLM e sem rede enquanto ``comite`` for ``None``, que é o padrão.
    """
    limiares_aplicados = limiares or LIMIARES_PROVISORIOS[audiencia]
    texto = conteudo.texto_avaliavel()

    achados: list[_Achado] = [
        _medir_integridade(ancoras),
        _medir_flesch_br(texto, limiares_aplicados, audiencia),
        _medir_densidade(texto, limiares_aplicados, audiencia),
        _medir_aderencia(texto, ancoras, limiares_aplicados),
        _medir_recomendacao(texto),
    ]

    medidas = [medida for medida, _, _ in achados]
    motivos: list[MotivoReprovacao] = []
    for _, motivo, _ in achados:
        if motivo is not None and motivo not in motivos:
            motivos.append(motivo)
    correcoes = [correcao for _, _, correcao in achados if correcao is not None]

    return Laudo(
        audiencia=audiencia,
        formato=conteudo.formato,
        medidas=medidas,
        destino=_destino(motivos),
        motivos=motivos,
        correcoes=correcoes,
        comite=_julgamento_do_comite(conteudo, audiencia, comite),
    )


def _destino(motivos: Sequence[MotivoReprovacao]) -> Destino:
    """Três destinos, não dois (ADR 0013). Falha de extração não passa pelo Ciclo."""
    if MotivoReprovacao.FALHA_DE_EXTRACAO in motivos:
        return Destino.REPROVADO_REVISAO_HUMANA
    if motivos:
        return Destino.REPROVADO_CORRIGIVEL
    return Destino.APROVADO


def _julgamento_do_comite(
    conteudo: Conteudo,
    audiencia: Audiencia,
    comite: "Comite | None",
) -> ResultadoComite | None:
    """Roda depois das medidas, nunca antes, e nunca para o Roteiro (ADR 0008).

    Falha de provedor — inclusive cota esgotada — devolve ``None``: o Laudo sai sem comitê,
    o erro fica no log, e o veredito determinístico não muda.
    """
    if comite is None or conteudo.formato not in FORMATOS_JULGADOS_PELO_COMITE:
        return None
    try:
        return comite.julgar(conteudo, audiencia)
    except ErroProvedor as erro:  # CotaEsgotada herda daqui
        _REGISTRO.warning(
            "comitê não julgou %s/%s: %s — o Laudo sai sem comitê (ADR 0008)",
            audiencia,
            conteudo.formato,
            erro,
        )
        return None


# ---------------------------------------------------------------------------
# 1. Integridade da extração
# ---------------------------------------------------------------------------


def _medir_integridade(ancoras: Sequence[Ancora]) -> _Achado:
    """A tabela de Âncoras está completa? Sem Correção: reescrever não conserta (ADR 0013)."""
    medido = medir_integridade(ancoras)
    total = len(CHAVES_ESSENCIAIS)
    presentes = total - len(medido.faltantes)
    observacoes = [f"Âncora essencial ausente: {chave}" for chave in medido.faltantes]
    observacoes += [
        f"Âncora sem trecho da Ata para conferir: {chave}"
        for chave in medido.ancoras_com_trecho_vazio
    ]
    medida = Medida(
        metrica=Metrica.INTEGRIDADE,
        estado=EstadoMedida.MEDIDA,
        valor=presentes / total if total else 1.0,
        faixa=Faixa(minimo=1.0),
        atingiu=medido.completa,
        observacoes=observacoes,
    )
    motivo = None if medido.completa else MotivoReprovacao.FALHA_DE_EXTRACAO
    return medida, motivo, None


# ---------------------------------------------------------------------------
# 2. Flesch-BR
# ---------------------------------------------------------------------------


def _medir_flesch_br(texto: str, limiares: Limiares, audiencia: Audiencia) -> _Achado:
    indice = flesch_br(texto)
    faixa = limiares.flesch_br
    if indice is None:
        # Texto sem palavra não tem índice. Ausente, nunca zero (ADR 0002).
        return (
            Medida(
                metrica=Metrica.FLESCH_BR,
                estado=EstadoMedida.AUSENTE,
                valor=None,
                faixa=faixa,
                atingiu=None,
                observacoes=["Texto sem palavra: não há base para medir o Flesch-BR."],
            ),
            None,
            None,
        )

    atingiu = faixa.contem(indice)
    medida = Medida(
        metrica=Metrica.FLESCH_BR,
        estado=EstadoMedida.MEDIDA,
        valor=indice,
        faixa=faixa,
        atingiu=atingiu,
        observacoes=[] if atingiu else [_frase_do_flesch(indice, faixa, audiencia)],
    )
    if atingiu:
        return medida, None, None
    correcao = Correcao(
        metrica=Metrica.FLESCH_BR,
        valor_medido=indice,
        faixa=faixa,
        distancia=faixa.distancia(indice),
        instrucao=_frase_do_flesch(indice, faixa, audiencia),
    )
    return medida, MotivoReprovacao.FLESCH_BR, correcao


def _frase_do_flesch(indice: float, faixa: Faixa, audiencia: Audiencia) -> str:
    """A frase que o Ciclo de correção recebe, com o valor medido e a distância.

    Duas formas, uma por lado da Faixa: "Flesch-BR medido 47,2; o Limiar da Audiência
    Iniciante é >= 50 (faltam 2,8 pontos...)" e "... é < 25 (sobram 5,0 pontos...)".
    Nunca um pedido genérico de simplificar (ADR 0013).
    """
    nome = NOME_DA_AUDIENCIA[audiencia]
    distancia = _uma_casa(faixa.distancia(indice))
    medido = _uma_casa(indice)
    if faixa.minimo is not None and indice < faixa.minimo:
        return (
            f"Flesch-BR medido {medido}; o Limiar da Audiência {nome} é ≥ "
            f"{_limiar(faixa.minimo)} (faltam {distancia} pontos para ficar mais fácil)"
        )
    teto = faixa.maximo if faixa.maximo is not None else indice
    return (
        f"Flesch-BR medido {medido}; o Limiar da Audiência {nome} é < "
        f"{_limiar(teto)} (sobram {distancia} pontos: o texto está fácil "
        f"demais para {nome})"
    )


# ---------------------------------------------------------------------------
# 3. Densidade
# ---------------------------------------------------------------------------


def _medir_densidade(texto: str, limiares: Limiares, audiencia: Audiencia) -> _Achado:
    medido = medir_densidade(texto, limiares.explicacao)
    minima = limiares.densidade_minima
    faixa = Faixa(minimo=minima) if minima is not None else None

    if medido.proporcao is None:
        return (
            Medida(
                metrica=Metrica.DENSIDADE,
                estado=EstadoMedida.AUSENTE,
                valor=None,
                faixa=faixa,
                atingiu=None,
                observacoes=["Texto sem palavra: não há base para medir a Densidade."],
            ),
            None,
            None,
        )

    escassa = minima is not None and medido.proporcao < minima
    atingiu = not medido.sem_explicacao and not escassa
    observacoes = [
        f"Termo do Léxico sem explicação na primeira ocorrência: {termo}"
        for termo in medido.sem_explicacao
    ]
    if escassa:
        observacoes.append(
            f"Densidade medida {_duas_casas(medido.proporcao)}, abaixo do Limiar "
            f"{_duas_casas(minima or 0.0)}."
        )
    medida = Medida(
        metrica=Metrica.DENSIDADE,
        estado=EstadoMedida.MEDIDA,
        valor=medido.proporcao,
        faixa=faixa,
        atingiu=atingiu,
        observacoes=observacoes,
    )
    if atingiu:
        return medida, None, None
    correcao = Correcao(
        metrica=Metrica.DENSIDADE,
        valor_medido=medido.proporcao,
        faixa=faixa,
        distancia=faixa.distancia(medido.proporcao) if faixa is not None else None,
        instrucao=_frase_da_densidade(medido.sem_explicacao, escassa, medido.proporcao, limiares, audiencia),
    )
    return medida, MotivoReprovacao.DENSIDADE, correcao


def _frase_da_densidade(
    sem_explicacao: Sequence[str],
    escassa: bool,
    proporcao: float,
    limiares: Limiares,
    audiencia: Audiencia,
) -> str:
    nome = NOME_DA_AUDIENCIA[audiencia]
    partes: list[str] = []
    if sem_explicacao:
        partes.append(
            "Termos do Léxico sem explicação na primeira ocorrência: "
            f"{', '.join(sem_explicacao)}. A Audiência {nome} exige explicação ou analogia "
            "em todos."
        )
    if escassa:
        partes.append(
            f"Densidade medida {_duas_casas(proporcao)}; o Limiar da Audiência {nome} é ≥ "
            f"{_duas_casas(limiares.densidade_minima or 0.0)}: traga mais termos do Léxico."
        )
    return " ".join(partes)


# ---------------------------------------------------------------------------
# 4. Aderência
# ---------------------------------------------------------------------------


def _medir_aderencia(
    texto: str,
    ancoras: Sequence[Ancora],
    limiares: Limiares,
) -> _Achado:
    """A Audiência não entra aqui: o Limiar de Aderência é o mesmo para as três."""
    medido = medir_aderencia(texto, ancoras)
    faixa = Faixa(minimo=limiares.aderencia_minima)

    if medido.proporcao is None:
        # Célula sem número não reprova por Aderência: não há o que conferir (ADR 0011).
        return (
            Medida(
                metrica=Metrica.ADERENCIA,
                estado=EstadoMedida.AUSENTE,
                valor=None,
                faixa=faixa,
                atingiu=None,
                observacoes=["Texto sem número: não há o que conferir contra as Âncoras."],
            ),
            None,
            None,
        )

    atingiu = faixa.contem(medido.proporcao)
    # A forma legível ("15%", "0,75 p.p.") é a que vai para o humano e para o Ciclo: sem a
    # unidade a instrução não diz qual número está errado, e `%` ≠ `p.p.` ≠ `pb`. O literal
    # cru fica de reserva para quem construir o resultado sem o campo pareado.
    fora = medido.numeros_fora_com_unidade or medido.numeros_fora_das_ancoras
    observacoes = [f"Número sem Âncora que o sustente: {numero}" for numero in fora]
    medida = Medida(
        metrica=Metrica.ADERENCIA,
        estado=EstadoMedida.MEDIDA,
        valor=medido.proporcao,
        faixa=faixa,
        atingiu=atingiu,
        observacoes=observacoes,
    )
    if atingiu:
        return medida, None, None
    correcao = Correcao(
        metrica=Metrica.ADERENCIA,
        valor_medido=medido.proporcao,
        faixa=faixa,
        distancia=faixa.distancia(medido.proporcao),
        instrucao=_frase_da_aderencia(fora, ancoras),
    )
    return medida, MotivoReprovacao.ADERENCIA, correcao


def _frase_da_aderencia(fora: Sequence[str], ancoras: Sequence[Ancora]) -> str:
    """As Âncoras são a única origem de número do sistema (ADR 0011): a Correção lista quais."""
    disponiveis = ", ".join(
        f"{ancora.chave}={ancora.citacao()}"
        for ancora in ancoras
        if isinstance(ancora, AncoraNumerica)
    )
    inicio = (
        f"Números sem Âncora: {', '.join(fora)}."
        if fora
        else "A Aderência ficou abaixo do Limiar."
    )
    if not disponiveis:
        return f"{inicio} Não há Âncora numérica: não cite número nenhum."
    return f"{inicio} Use só os valores das Âncoras: {disponiveis}."


# ---------------------------------------------------------------------------
# 5. Recomendação
# ---------------------------------------------------------------------------


def _medir_recomendacao(texto: str) -> _Achado:
    """A linha que não se cruza. Detectada por código, com regra fixa, nunca por LLM."""
    ocorrencias = detectar_recomendacao(texto)
    atingiu = not ocorrencias
    medida = Medida(
        metrica=Metrica.RECOMENDACAO,
        estado=EstadoMedida.MEDIDA,
        valor=float(len(ocorrencias)),
        faixa=RECOMENDACOES_ACEITAS,
        atingiu=atingiu,
        observacoes=[
            f"Recomendação ({ocorrencia.padrao}): {ocorrencia.frase}"
            for ocorrencia in ocorrencias
        ],
    )
    if atingiu:
        return medida, None, None
    frases: list[str] = []
    for ocorrencia in ocorrencias:
        if ocorrencia.frase not in frases:
            frases.append(ocorrencia.frase)
    correcao = Correcao(
        metrica=Metrica.RECOMENDACAO,
        valor_medido=float(len(ocorrencias)),
        faixa=RECOMENDACOES_ACEITAS,
        distancia=float(len(ocorrencias)),
        instrucao=(
            "Remova as frases que recomendam: "
            + "; ".join(f"«{frase}»" for frase in frases)
            + ". O sistema informa e educa, não aconselha: fale do que a decisão significa, "
            "sem dizer ao leitor o que fazer com o dinheiro dele."
        ),
    )
    return medida, MotivoReprovacao.RECOMENDACAO, correcao


# ---------------------------------------------------------------------------
# Números em português: vírgula decimal, como um humano lê
# ---------------------------------------------------------------------------


def _uma_casa(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def _duas_casas(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _limiar(valor: float) -> str:
    """O Limiar sai inteiro quando é inteiro: "≥ 50", não "≥ 50,0"."""
    return str(int(valor)) if float(valor).is_integer() else _uma_casa(valor)
