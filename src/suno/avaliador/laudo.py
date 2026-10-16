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
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Callable, Sequence

from suno.avaliador.aderencia import medir_aderencia
from suno.avaliador.densidade import ResultadoDensidade, frase_em, medir_densidade
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
)

if TYPE_CHECKING:
    from suno.avaliador.fidelidade import VerificadorDeFidelidade
    from suno.avaliador.qualidade import AvaliadorDeQualidade

_REGISTRO = logging.getLogger(__name__)

NOME_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "Iniciante",
    Audiencia.INTERMEDIARIO: "Intermediário",
    Audiencia.AVANCADO: "Avançado",
}
"""Como a Audiência aparece dentro da instrução de Correção, que um humano também lê."""

RECOMENDACOES_ACEITAS = Faixa(maximo=1)
"""Zero é o único valor aceito: qualquer ocorrência reprova (CLAUDE.md, a linha que não se cruza)."""

_Achado = tuple[Medida, MotivoReprovacao | None, Correcao | None]


def avaliar(
    conteudo: Conteudo,
    ancoras: Sequence[Ancora],
    audiencia: Audiencia,
    *,
    limiares: Limiares | None = None,
    qualidade: "AvaliadorDeQualidade | None" = None,
    fidelidade: "VerificadorDeFidelidade | None" = None,
    chaves_essenciais: frozenset[str] = CHAVES_ESSENCIAIS,
    ao_etapa: Callable[[str], None] | None = None,
) -> Laudo:
    """``(Conteúdo, Âncora[], Audiência) → Laudo``: a costura inteira (ADR 0001).

    ``ao_etapa`` é só um aviso de andamento: recebe ``deterministica``, ``jev`` e ``llm`` quando
    cada camada começa a rodar (``jev`` e ``llm`` só avisam se a camada vai rodar de fato).

    Sem LLM e sem rede enquanto ``qualidade`` e ``fidelidade`` forem ``None``.

    ``qualidade`` (o Jev, ADR 0035) só é consultada depois que as cinco medidas aprovaram: é a
    única medida que pode reprovar sem ser determinística, e por isso nunca roda à toa.
    ``fidelidade`` (um LLM que confere a Célula contra a Ata, ADR 0036) vem por último: só depois de
    tudo o mais ter aprovado, porque é a chamada mais cara.

    ``chaves_essenciais`` é opcional e tem o padrão do Copom: só uma Ata de outra categoria
    passa o conjunto genérico (``dominio.chaves_essenciais_da``). Quem não o usa não muda.
    """
    def avisar(etapa: str) -> None:
        if ao_etapa is not None:
            ao_etapa(etapa)

    avisar("deterministica")
    limiares_aplicados = limiares or LIMIARES_PROVISORIOS[audiencia]
    texto = conteudo.texto_avaliavel()
    # Aderência e Recomendação cobrem também a rubrica de cena do Roteiro (dominio.py,
    # texto_de_conferencia): ela aparece no vídeo e na interface, e não há segundo caminho
    # de número ou de Recomendação livre de conferência (ADR 0011; CLAUDE.md).
    texto_conferido = conteudo.texto_de_conferencia()

    achados: list[_Achado] = [
        _medir_integridade(ancoras, chaves_essenciais),
        _medir_flesch_br(texto, limiares_aplicados, audiencia),
        _medir_densidade(texto, limiares_aplicados, audiencia, conteudo),
        _medir_aderencia(texto_conferido, ancoras, limiares_aplicados),
        _medir_recomendacao(texto_conferido),
    ]
    if qualidade is not None and all(motivo is None for _, motivo, _ in achados):
        avisar("jev")
        da_qualidade = _medir_qualidade(conteudo, audiencia, qualidade)
        if da_qualidade is not None:
            achados.append(da_qualidade)
    if fidelidade is not None and all(motivo is None for _, motivo, _ in achados):
        avisar("llm")
        da_fidelidade = _medir_fidelidade(conteudo, audiencia, fidelidade, ancoras)
        if da_fidelidade is not None:
            achados.append(da_fidelidade)

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
    )


def _destino(motivos: Sequence[MotivoReprovacao]) -> Destino:
    """Três destinos, não dois (ADR 0013). Falha de extração não passa pelo Ciclo."""
    if MotivoReprovacao.FALHA_DE_EXTRACAO in motivos:
        return Destino.REPROVADO_REVISAO_HUMANA
    if motivos:
        return Destino.REPROVADO_CORRIGIVEL
    return Destino.APROVADO


def _percentual(nota: float) -> str:
    return f"{round(nota * 100)}%"


def _medir_qualidade(
    conteudo: Conteudo, audiencia: Audiencia, avaliador: "AvaliadorDeQualidade"
) -> _Achado | None:
    """A Qualidade do Jev (ADR 0035). ``None`` quando o Jev não respondeu: o Laudo sai sem ela.

    A Medida carrega a menor das notas; a Correção nomeia cada dimensão abaixo do Limiar e o
    nível que o Jev viu nela, para o Gerador saber o que refazer.
    """
    try:
        resultado = avaliador.medir(conteudo, audiencia)
    except ErroProvedor as erro:
        _REGISTRO.warning(
            "Jev não mediu %s/%s: %s — o Laudo sai sem Qualidade (ADR 0035)",
            audiencia,
            conteudo.formato,
            erro,
        )
        return None
    except Exception:  # noqa: BLE001 - camada opcional nunca derruba a Célula (ADR 0035)
        _REGISTRO.exception(
            "Jev falhou de um jeito inesperado em %s/%s — o Laudo sai sem Qualidade", audiencia, conteudo.formato
        )
        return None
    faixa = Faixa(minimo=avaliador.limiar)
    abaixo = [d for d in resultado.dimensoes if d.nota < avaliador.limiar]
    menor = resultado.menor
    medida = Medida(
        metrica=Metrica.QUALIDADE,
        estado=EstadoMedida.MEDIDA,
        valor=menor.nota,
        faixa=faixa,
        atingiu=not abaixo,
        observacoes=[
            f"{d.rotulo.capitalize()}: {_percentual(d.nota)}"
            + (f" — {d.nivel}" if d in abaixo else "")
            for d in resultado.dimensoes
        ],
    )
    if not abaixo:
        return medida, None, None
    detalhes = "; ".join(f"{d.rotulo} {_percentual(d.nota)} (visto: {d.nivel})" for d in abaixo)
    correcao = Correcao(
        metrica=Metrica.QUALIDADE,
        valor_medido=menor.nota,
        faixa=faixa,
        distancia=faixa.distancia(menor.nota),
        instrucao=(
            f"Qualidade medida {_percentual(menor.nota)}; o Limiar é ≥ "
            f"{_percentual(avaliador.limiar)}. Abaixo do Limiar: {detalhes}"
        ),
    )
    return medida, MotivoReprovacao.QUALIDADE, correcao


def _medir_fidelidade(
    conteudo: Conteudo,
    audiencia: Audiencia,
    verificador: "VerificadorDeFidelidade",
    ancoras: Sequence[Ancora],
) -> _Achado | None:
    """A Fidelidade à Ata (ADR 0036). ``None`` quando o checador não respondeu: sai sem ela.

    Vale 1 sem achado que bloqueie e 0 com algum. Só bloqueia o que tem prova: ``distorce`` e
    ``contradiz`` trazem o trecho da Ata, que o código já conferiu. ``sem_suporte`` é a opinião do
    modelo e só entra nas observações, como aviso (ADR 0036).
    """
    try:
        resultado = verificador.verificar(conteudo, audiencia, ancoras)
    except ErroProvedor as erro:
        _REGISTRO.warning(
            "o checador não conferiu %s/%s: %s — o Laudo sai sem Fidelidade (ADR 0036)",
            audiencia,
            conteudo.formato,
            erro,
        )
        return None
    except Exception:  # noqa: BLE001 - camada opcional nunca derruba a Célula (ADR 0036)
        _REGISTRO.exception(
            "o checador falhou de um jeito inesperado em %s/%s — o Laudo sai sem Fidelidade",
            audiencia,
            conteudo.formato,
        )
        return None
    faixa = Faixa(minimo=1.0)
    bloqueiam = [achado for achado in resultado.achados if achado.bloqueia]
    avisos = [achado for achado in resultado.achados if not achado.bloqueia]
    limpa = not bloqueiam
    observacoes = [achado.descricao for achado in bloqueiam]
    observacoes += [f"Aviso (não reprova): {achado.descricao}" for achado in avisos]
    if resultado.descartados:
        observacoes.append(f"{resultado.descartados} apontamento(s) descartado(s): citação que não existe")
    medida = Medida(
        metrica=Metrica.FIDELIDADE,
        estado=EstadoMedida.MEDIDA,
        valor=1.0 if limpa else 0.0,
        faixa=faixa,
        atingiu=limpa,
        observacoes=observacoes,
    )
    if limpa:
        return medida, None, None
    correcao = Correcao(
        metrica=Metrica.FIDELIDADE,
        valor_medido=0.0,
        faixa=faixa,
        distancia=1.0,
        instrucao=(
            f"Fidelidade à Ata: {len(bloqueiam)} afirmação(ões) que a Ata contradiz ou diz de outro jeito. "
            + " | ".join(f"{i}) {achado.descricao}" for i, achado in enumerate(bloqueiam, 1))
        ),
    )
    return medida, MotivoReprovacao.FIDELIDADE, correcao


# ---------------------------------------------------------------------------
# 1. Integridade da extração
# ---------------------------------------------------------------------------


def _medir_integridade(
    ancoras: Sequence[Ancora], chaves_essenciais: frozenset[str] = CHAVES_ESSENCIAIS
) -> _Achado:
    """A tabela de Âncoras está completa? Sem Correção: reescrever não conserta (ADR 0013)."""
    medido = medir_integridade(ancoras, chaves_essenciais)
    total = len(chaves_essenciais)
    presentes = total - len(medido.faltantes)
    observacoes = [
        (
            f"Âncora essencial ausente: {chave} (sem número e sem afirmação central extraída)"
            if chave.endswith("numero_principal")
            else f"Âncora essencial ausente: {chave}"
        )
        for chave in medido.faltantes
    ]
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
        # Texto sem palavra não tem índice — a Medida sai ausente, nunca zero (ADR 0002). Mas
        # "ausente" é sobre não fabricar um número, não sobre aprovar o nada: Texto analítico,
        # Carrossel e Roteiro sempre têm campo de texto obrigatório, então zero palavras só
        # acontece quando o Gerador falhou (ex.: `preencher` apagou uma `{{chave}}`
        # desconhecida e não sobrou mais nada). Isso reprova pelo mesmo motivo, com Correção,
        # em vez de aprovar uma Célula que não diz nada (achado do revisor de erros, 2026-09-19).
        instrucao = (
            "A Célula saiu sem nenhuma palavra legível — não há texto para medir o Flesch-BR. "
            "Escreva o conteúdo de verdade (provavelmente uma chave de Âncora desconhecida foi "
            "apagada por `preencher`, deixando o campo vazio); confira que só chaves da lista "
            "de Âncoras aparecem entre `{{ }}`."
        )
        return (
            Medida(
                metrica=Metrica.FLESCH_BR,
                estado=EstadoMedida.AUSENTE,
                valor=None,
                faixa=faixa,
                atingiu=None,
                observacoes=["Texto sem palavra: não há base para medir o Flesch-BR."],
            ),
            MotivoReprovacao.FLESCH_BR,
            Correcao(
                metrica=Metrica.FLESCH_BR,
                valor_medido=None,
                faixa=faixa,
                distancia=None,
                instrucao=instrucao,
            ),
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


def _onde(conteudo: Conteudo | None, frase: str) -> str:
    """Em que slide ou bloco de fala está a frase. Texto analítico não tem divisão: devolve vazio."""
    if conteudo is None or not frase:
        return ""
    chave = re.sub(r"\s+", " ", frase.rstrip("…"))[:40]
    for i, slide in enumerate(conteudo.slides or [], start=1):
        if chave in re.sub(r"\s+", " ", f"{slide.titulo} {slide.corpo}"):
            return f"slide {i}"
    for i, bloco in enumerate(conteudo.blocos or [], start=1):
        if chave in re.sub(r"\s+", " ", bloco.fala):
            return f"bloco {i}"
    return ""


def _onde_esta_cada_termo(
    texto: str, conteudo: Conteudo | None, medido: ResultadoDensidade
) -> dict[str, str]:
    """Para cada termo sem explicação, a frase da primeira ocorrência (e o slide ou bloco dela)."""
    primeiras = {}
    for ocorrencia in medido.termos:
        primeiras.setdefault(ocorrencia.termo, ocorrencia)
    onde: dict[str, str] = {}
    for termo in medido.sem_explicacao:
        ocorrencia = primeiras.get(termo)
        if ocorrencia is None:
            continue
        frase = frase_em(texto, ocorrencia.posicao)
        local = _onde(conteudo, frase)
        onde[termo] = f"{local}: «{frase}»" if local else f"«{frase}»"
    return onde


def _medir_densidade(
    texto: str, limiares: Limiares, audiencia: Audiencia, conteudo: Conteudo | None = None
) -> _Achado:
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
        instrucao=_frase_da_densidade(
            medido.sem_explicacao,
            escassa,
            medido.proporcao,
            limiares,
            audiencia,
            _onde_esta_cada_termo(texto, conteudo, medido),
        ),
    )
    return medida, MotivoReprovacao.DENSIDADE, correcao


def _frase_da_densidade(
    sem_explicacao: Sequence[str],
    escassa: bool,
    proporcao: float,
    limiares: Limiares,
    audiencia: Audiencia,
    onde: dict[str, str] | None = None,
) -> str:
    nome = NOME_DA_AUDIENCIA[audiencia]
    partes: list[str] = []
    if sem_explicacao:
        partes.append(
            "Termos do Léxico sem explicação na primeira ocorrência: "
            f"{', '.join(sem_explicacao)}. A Audiência {nome} exige explicação ou analogia "
            "em todos."
        )
        if onde:
            # A frase exata de cada termo: o Gerador edita ali e não reescreve a Célula inteira.
            partes.append(
                "Onde cada um está:\n"
                + "\n".join(f"- {termo} — {onde[termo]}" for termo in sem_explicacao if termo in onde)
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
