"""Os moldes de prompt por Audiência e Formato. O número entra por preenchimento de
`{{chave}}` a partir das Âncoras, nunca por escrita livre. O alvo interno de Flesch-BR é
mais folgado que o Limiar (overshoot calibrado, ADR 0002).

ADR 0011.

## Por que o alvo interno é mais folgado que o Limiar

Medições citadas no ADR 0002 mostram LLM errando sistematicamente para cima quando se pede
nível de leitura — pedir "fácil" entrega "médio", e o efeito é pior em português e na ponta
mais fácil, que é exatamente a Audiência Iniciante. Então o molde pede mais do que o Limiar
cobra. O Avaliador não sabe que ``ALVO_FLESCH_BR`` existe: ele continua aplicando
``LIMIARES_PROVISORIOS``, e o Laudo continua publicando o Limiar do NILC.

## Por que o número nunca é escrito pelo LLM

O molde entrega a lista de Âncoras como ``{{chave}}: rótulo (unidade)`` e manda escrever a
chave. ``preencher`` troca a chave pela ``citacao()`` da Âncora depois que o LLM respondeu,
então o caminho do número da Ata até a Célula não passa por geração — é cópia (ADR 0011).
Chave que o LLM inventa não vira número: some do texto e a Aderência/Densidade decidem.
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from suno.avaliador.densidade import medir_densidade
from suno.dominio import (
    LIMIARES_PROVISORIOS,
    Ancoras,
    Audiencia,
    BlocoFala,
    CategoriaDaAta,
    Conteudo,
    Correcao,
    DuracaoDoVideo,
    Faixa,
    ExigenciaDeExplicacao,
    Formato,
    Mensagem,
    Metrica,
    PapelLLM,
    PedidoLLM,
    Slide,
)
from suno.video.design import cronometrar, diretriz_de_duracao, instrucao_de_direcao

_registro = logging.getLogger(__name__)

MOLDE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
"""O marcador que o LLM escreve no lugar de um número."""

PONTO_DOBRADO = re.compile(r"([A-Za-zÀ-ÿ]\.[A-Za-zÀ-ÿ]\.)\.")
"""``14,00% a.a..`` → ``14,00% a.a.``: a abreviação da unidade já trouxe o ponto.

Casa só a forma ``x.x.`` seguida de mais um ponto — ``a.a.``, ``p.p.``, as duas unidades
abreviadas do domínio. Reticências não casam, e o número nunca é tocado: o que sai é o
ponto final que o LLM escreveu depois da citação, não um dígito.
"""

SLIDES_MINIMOS = 5
SLIDES_MAXIMOS = 7
DURACAO_PADRAO_DO_ROTEIRO = DuracaoDoVideo.S60
"""A duração do Roteiro quando a pessoa não escolhe: um minuto (ARQUITETURA.md). As opções são
as de ``DuracaoDoVideo``: 40s, 1m, 1m30, 2m e 3m."""

ALVO_FLESCH_BR: dict[Audiencia, Faixa] = {
    Audiencia.INICIANTE: Faixa(minimo=60.0),
    Audiencia.INTERMEDIARIO: Faixa(minimo=30.0, maximo=45.0),
    Audiencia.AVANCADO: Faixa(maximo=18.0),
}
"""Alvo interno do Gerador, mais folgado que o Limiar. Provisório, aguardando Calibração."""

MAX_TOKENS_DA_CELULA = 4096
"""A Ata inteira entra no pedido; a resposta estruturada é curta, mas o Carrossel tem sete slides."""


def max_tokens_do_roteiro(duracao: DuracaoDoVideo) -> int:
    """Cada cena carrega fala, rubrica e a direção de cena: o teto cresce com a duração."""
    return min(8192, 2048 + 30 * duracao.segundos)


# ---------------------------------------------------------------------------
# O que o LLM devolve, por Formato
# ---------------------------------------------------------------------------


class RespostaTextoAnalitico(BaseModel):
    """As três partes fixas do Texto analítico (ARQUITETURA.md)."""

    titulo: str
    o_que_foi_decidido: str = Field(description="A Âncora numérica principal, citada por chave.")
    por_que: str = Field(description="O argumento da Ata, parafraseado.")
    o_que_observar_adiante: str = Field(
        description="Só o que a Ata sinaliza. Nenhuma projeção sua, nenhuma direção de ação."
    )


class RespostaCarrossel(BaseModel):
    """De cinco a sete slides: gancho, corpo, conclusão."""

    slides: list[Slide] = Field(min_length=SLIDES_MINIMOS, max_length=SLIDES_MAXIMOS)


class RespostaRoteiro(BaseModel):
    """Blocos de fala com direção de cena; o primeiro é o gancho. O tempo de cada um é
    recalculado em ``montar_conteudo`` pelo número de palavras."""

    blocos: list[BlocoFala] = Field(min_length=2)


MODELO_POR_FORMATO: dict[Formato, type[BaseModel]] = {
    Formato.TEXTO_ANALITICO: RespostaTextoAnalitico,
    Formato.CARROSSEL: RespostaCarrossel,
    Formato.ROTEIRO: RespostaRoteiro,
}


# ---------------------------------------------------------------------------
# As instruções
# ---------------------------------------------------------------------------

LINHA_QUE_NAO_SE_CRUZA = (
    "Você informa e educa. Nunca sugira comprar, vender, manter, reduzir ou aumentar "
    "posição, nem prometa retorno. Não se dirija ao leitor com 'você deve', 'você precisa' "
    "ou 'convém'. Recomendar investimento é atividade regulada no Brasil e reprova a Célula."
)

INSTRUCAO_DA_AUDIENCIA: dict[Audiencia, str] = {
    Audiencia.INICIANTE: (
        "Audiência Iniciante: quem nunca acompanhou uma decisão de juros. Nenhum termo de "
        "mercado entra sem uma analogia do dia a dia na mesma frase — se escrever 'Selic', "
        "explique ali mesmo com 'ou seja', travessão ou parêntese. O foco é o impacto no "
        "bolso de quem lê. Frases curtas, uma ideia por frase."
    ),
    Audiencia.INTERMEDIARIO: (
        "Audiência Intermediário: quem já acompanha o mercado. Use o vocabulário padrão "
        "(CDI, Selic, IPCA, dividendos) sem explicar. Explique só o que está fora desse "
        "núcleo. O foco é alocação e tendência, descritas em terceira pessoa — descreva o "
        "cenário, nunca diga o que o leitor deve fazer com ele."
    ),
    Audiencia.AVANCADO: (
        "Audiência Avançado: quem trabalha com isso. Termos plenos, sem explicação: curva "
        "de juros, forward guidance, hiato do produto, balanço de riscos. O foco é "
        "analítico — mecanismo de transmissão, assimetria do balanço de riscos, "
        "consistência entre a decisão e as projeções."
    ),
}

INSTRUCAO_DO_FORMATO: dict[Formato, str] = {
    Formato.TEXTO_ANALITICO: (
        "Formato Texto analítico, em Markdown, com três partes na ordem: o que foi decidido "
        "(a Âncora numérica principal, citada), por quê (o argumento da Ata, parafraseado) "
        "e o que observar adiante (só o que a Ata sinaliza; nenhuma projeção sua)."
    ),
    Formato.CARROSSEL: (
        f"Formato Carrossel: de {SLIDES_MINIMOS} a {SLIDES_MAXIMOS} slides. O primeiro tem "
        "'tipo' hook (a chamada que abre uma pergunta ou um contraste), o último tem 'tipo' cta "
        "(chamada para ação que convida a ler a Ata ou acompanhar o tema — nunca a comprar, "
        "vender ou manter algo) e os do meio têm 'tipo' ponto (um ponto, chave ou dica por "
        "slide) ou citacao (um trecho curto da Ata, parafraseado). Cada slide tem 'titulo' de "
        "até 8 palavras e 'corpo' de até 32; 'destaque' é opcional e repete literalmente uma "
        "expressão do título para realçar; 'dado' é opcional e recebe a chave da Âncora a "
        "plotar naquele slide (só a chave, sem chaves duplas); 'imagem' é opcional e dá o "
        "assunto da foto do slide em até quatro palavras de busca (ex.: 'sede do Banco "
        "Central'): só um lugar, instituição ou objeto concreto, ou uma autoridade em "
        "exercício do cargo; nunca uma pessoa privada, e nada que sugira comprar ou vender."
    ),
    Formato.ROTEIRO: (
        "Formato Roteiro: blocos de fala, cada um uma cena. O primeiro bloco é o gancho. "
        "'fala' é o que é dito e é o que a Facilidade de leitura mede; 'tela' é a rubrica "
        "de cena, não é lida em voz alta, mas aparece escrita no vídeo — todo número em "
        "'tela' também entra escrevendo `{{chave}}`, do mesmo jeito que em 'fala'."
    ),
}


COMO_ESCREVER_NO_ALVO: dict[Audiencia, str] = {
    Audiencia.INICIANTE: (
        "Como chegar lá: frases de 8 a 12 palavras, nunca acima de 15. Uma ideia por frase; "
        "troque vírgula por ponto. Prefira palavras de duas ou três sílabas ('alta' em vez de "
        "'elevação', 'caro' em vez de 'oneroso'). Corte advérbios em '-mente'."
    ),
    Audiencia.INTERMEDIARIO: (
        "Como chegar lá: frases de 15 a 22 palavras, alternando curtas e médias. Vocabulário "
        "de mercado, sem empilhar orações subordinadas na mesma frase."
    ),
    Audiencia.AVANCADO: (
        "Como chegar lá: frases longas, de 28 a 40 palavras, com orações subordinadas "
        "encadeadas ('à medida que', 'na medida em que', 'conquanto'). Vocabulário técnico "
        "polissilábico (transmissão, desancoragem, contracionista, assimetria). Evite frases "
        "curtas: cada uma delas deixa o texto fácil demais para esta Audiência."
    ),
}
"""O Flesch-BR é 248,835 − 1,015 × palavras por frase − 84,6 × sílabas por palavra. O LLM não
calcula o índice, mas controla as duas variáveis: este texto traduz o alvo nelas."""

MAXIMO_DE_TERMOS_LISTADOS = 25

MARCAS_DE_EXPLICACAO = (
    "Como explicar um termo de forma que conte: logo depois dele, na mesma frase, abra "
    "parêntese, dois-pontos ou travessão — 'a inflação (a alta geral dos preços)' — ou escreva 'ou seja', 'isto é', 'que é', 'que são', 'significa', 'é como' ou "
    "'funciona como'. Vírgula seguida de 'que representa', 'que consiste' ou 'onde' não conta "
    "como explicação. Só a primeira vez que o termo aparece é conferida, e o título também "
    "conta: não ponha termo técnico no título, deixe-o para o corpo, onde dá para explicar. "
    "A explicação também é conferida: escreva-a só com palavras comuns, sem outro termo da "
    "lista abaixo dentro dela ('a volta da confiança', não 'o retorno da confiança')."
)


def _bloco_de_explicacao(ata_texto: str, audiencia: Audiencia) -> str | None:
    """As regras de explicação e os termos do Léxico desta Ata que a Audiência cobra explicados.

    Mede a própria Ata com a Densidade: os termos que nela saem ``sem_explicacao`` são os que o
    LLM tende a copiar, e são exatamente os que o Avaliador vai cobrar.
    """
    exigencia = LIMIARES_PROVISORIOS[audiencia].explicacao
    if exigencia is ExigenciaDeExplicacao.NUNCA:
        return None
    termos = medir_densidade(ata_texto, exigencia).sem_explicacao[:MAXIMO_DE_TERMOS_LISTADOS]
    if not termos:
        return MARCAS_DE_EXPLICACAO
    return (
        f"{MARCAS_DE_EXPLICACAO}\nTermos desta Ata que exigem explicação se você usar (ou "
        f"troque por palavra comum): {', '.join(termos)}."
    )


DICA_POR_METRICA: dict[Metrica, str] = {
    Metrica.DENSIDADE: (
        "Para cada termo listado: explique-o na primeira vez em que aparece, com parêntese "
        "logo depois dele, ou troque-o por uma palavra comum. Se o termo está no título, "
        "tire-o do título. Se ele aparece dentro da explicação de outro termo, troque-o por um "
        "sinônimo comum ('volta' em vez de 'retorno', 'chance de perda' em vez de 'risco')."
    ),
    Metrica.ADERENCIA: (
        "Todo número sai de uma `{{chave}}` da lista; apague o número que não tem chave."
    ),
}


def _dica_de_flesch(correcao: Correcao) -> str:
    faixa = correcao.faixa
    facil_demais = (
        faixa is not None
        and faixa.maximo is not None
        and correcao.valor_medido is not None
        and correcao.valor_medido >= faixa.maximo
    )
    if facil_demais:
        return "O texto está fácil demais: junte frases curtas em frases longas e use termos técnicos."
    return "O texto está difícil demais: quebre as frases longas e troque palavras longas por curtas."


def _alvo_em_palavras(audiencia: Audiencia) -> str:
    faixa = ALVO_FLESCH_BR[audiencia]
    if faixa.minimo is not None and faixa.maximo is not None:
        return f"entre {faixa.minimo:.0f} e {faixa.maximo:.0f}"
    if faixa.minimo is not None:
        return f"de {faixa.minimo:.0f} para cima"
    return f"de {faixa.maximo:.0f} para baixo"


def _lista_de_ancoras(ancoras: Ancoras) -> str:
    return "\n".join(
        f"- {{{{{ancora.chave}}}}}: {ancora.rotulo} ({ancora.unidade.value})"
        for ancora in ancoras.numericas
    )


def _bloco_de_correcoes(correcoes: list[Correcao], rascunho: str | None = None) -> str:
    linhas: list[str] = []
    for correcao in correcoes:
        dica = (
            _dica_de_flesch(correcao)
            if correcao.metrica is Metrica.FLESCH_BR
            else DICA_POR_METRICA.get(correcao.metrica)
        )
        linhas.append(f"- {correcao.instrucao}" + (f" {dica}" if dica else ""))
    partes = [
        "O que precisa mudar (o Avaliador mediu a Célula da rodada anterior e reprovou):\n"
        + "\n".join(linhas)
    ]
    if rascunho:
        # Sem o rascunho, a "correção" é uma geração nova do zero: o que estava certo some e
        # entram termos novos sem explicação (execução copom-281, 2026-10-10).
        partes.append(f"A Célula da rodada anterior, já com os números preenchidos:\n{rascunho}")
    partes.append(
        "Reescreva a Célula inteira partindo dessa versão e corrija exatamente isso. Não mude o "
        "que já estava certo nem introduza termo técnico novo. Os números continuam entrando "
        "como `{{chave}}`."
    )
    return "\n\n".join(partes)


def _bloco_transversal(orientacoes: list[str]) -> str:
    linhas = "\n".join(f"- {orientacao}" for orientacao in orientacoes)
    return (
        "Correções do avaliador transversal para esta Célula:\n"
        f"{linhas}\n"
        "Reescreva a Célula inteira. Preserve todos os fatos e Âncoras que já estavam certos."
    )


DESCRICAO_DO_COMUNICADO: dict[CategoriaDaAta, str] = {
    CategoriaDaAta.COPOM: "uma Ata do Copom",
    CategoriaDaAta.COMUNICADO_RELEVANTE: "um Fato Relevante da CVM",
    CategoriaDaAta.RELEASE: "um release de resultados",
    CategoriaDaAta.IMPORTADA: "um comunicado financeiro",
    CategoriaDaAta.UNIDA: "um conjunto de comunicados financeiros",
}
"""Como o pedido chama o documento de origem. Só o Copom diz "Ata do Copom"."""


INSTRUCAO_DA_VISAO_UNIDA = (
    "Este conteúdo reúne vários comunicados, marcados no texto como [a1], [a2]… e nas chaves de "
    "Âncora pelo mesmo prefixo (a1_, a2_…). Diga de qual comunicado vem cada número que citar e "
    "nunca atribua a um comunicado o número de outro."
)
"""Só na categoria ``unida``: cada número cita a sua origem (spec do front, seção 4.2)."""


def descricao_do_comunicado(categoria: CategoriaDaAta) -> str:
    return DESCRICAO_DO_COMUNICADO[categoria]


def montar_pedido(
    ata_texto: str,
    ancoras: Ancoras,
    audiencia: Audiencia,
    formato: Formato,
    rodada: int = 0,
    correcoes: list[Correcao] | None = None,
    orientacoes_transversais: list[str] | None = None,
    comunicado: str = DESCRICAO_DO_COMUNICADO[CategoriaDaAta.COPOM],
    instrucoes_do_conjunto: str | None = None,
    duracao: DuracaoDoVideo = DURACAO_PADRAO_DO_ROTEIRO,
    rascunho: str | None = None,
) -> PedidoLLM:
    """O pedido de uma Célula. Em ``rodada > 0``, as ``correcoes`` entram como valor medido, e
    ``rascunho`` (o texto da rodada anterior) entra para a correção partir dele.

    ``duracao`` só vale para o Roteiro: fixa o orçamento de palavras e de cenas e liga o catálogo
    de direção de cena.
    """
    sistema = "\n\n".join(
        [
            f"Você adapta {comunicado} para uma Audiência num Formato.",
            INSTRUCAO_DA_AUDIENCIA[audiencia],
            INSTRUCAO_DO_FORMATO[formato],
            *(
                [diretriz_de_duracao(duracao), instrucao_de_direcao()]
                if formato is Formato.ROTEIRO
                else []
            ),
            (
                "Facilidade de leitura alvo (índice Flesch-BR): "
                f"{_alvo_em_palavras(audiencia)}. {COMO_ESCREVER_NO_ALVO[audiencia]}"
            ),
            *([explicacao] if (explicacao := _bloco_de_explicacao(ata_texto, audiencia)) else []),
            (
                "Todo número entra escrevendo `{{chave}}`, e só chave da lista de Âncoras do "
                "pedido. Nunca escreva um número, por extenso ou em dígitos, que não seja uma "
                "chave dessa lista. A chave já sai com a unidade ('13,75% a.a.'): não repita "
                "'ao ano' nem '%' depois dela. Chave sem unidade sai só o valor: escreva a palavra junto "
                "(se a chave da reunião sai só o número, escreva 'ª reunião' logo depois dela)."
            ),
            *([instrucoes_do_conjunto] if instrucoes_do_conjunto else []),
            LINHA_QUE_NAO_SE_CRUZA,
        ]
    )
    partes_do_usuario = [
        f"Ata:\n{ata_texto}",
        (
            "Âncoras numéricas disponíveis:\n"
            f"{_lista_de_ancoras(ancoras)}\n\n"
            "Todo número entra escrevendo `{{chave}}`; nunca escreva um número por extenso "
            "ou em dígitos que não seja uma chave desta lista."
        ),
    ]
    if rodada > 0 and correcoes:
        partes_do_usuario.append(_bloco_de_correcoes(correcoes, rascunho))
    if orientacoes_transversais:
        partes_do_usuario.append(_bloco_transversal(orientacoes_transversais))
    return PedidoLLM(
        papel=PapelLLM.GERADOR,
        rotulo=f"celula:{audiencia}:{formato}:{rodada}",
        mensagens=[
            Mensagem(autor="sistema", texto=sistema),
            Mensagem(autor="usuario", texto="\n\n".join(partes_do_usuario)),
        ],
        max_tokens=(
            max_tokens_do_roteiro(duracao)
            if formato is Formato.ROTEIRO
            else MAX_TOKENS_DA_CELULA
        ),
        temperatura=0.3,
    )


# ---------------------------------------------------------------------------
# Preenchimento
# ---------------------------------------------------------------------------


def preencher(texto_com_moldes: str, ancoras: Ancoras) -> tuple[str, list[str]]:
    """Substitui `{{chave}}` pela citação da Âncora. Devolve o texto e as chaves usadas.

    Chave que não existe nas Âncoras perde o marcador e vira nada: o texto sai sem número,
    e a Aderência e a Densidade decidem se aquilo ainda é uma Célula (ADR 0011).

    Uma citação que termina em abreviação (``14,00% a.a.``) encosta no ponto final da
    frase e produziria ``a.a...``. O ponto sobrando é retirado — só o ponto; o número sai
    da Âncora e não é reescrito aqui nem em lugar nenhum.
    """
    usadas: list[str] = []

    def trocar(casado: re.Match[str]) -> str:
        chave = casado.group(1)
        ancora = ancoras.numerica(chave)
        if ancora is None:
            _registro.warning("molde com chave desconhecida, marcador removido: %r", chave)
            return ""
        if chave not in usadas:
            usadas.append(chave)
        return ancora.citacao()

    return PONTO_DOBRADO.sub(r"\1", MOLDE.sub(trocar, texto_com_moldes)), usadas


def _preencher_varios(textos: list[str], ancoras: Ancoras) -> tuple[list[str], list[str]]:
    preenchidos: list[str] = []
    usadas: list[str] = []
    for texto in textos:
        preenchido, chaves = preencher(texto, ancoras)
        preenchidos.append(preenchido)
        for chave in chaves:
            if chave not in usadas:
                usadas.append(chave)
    return preenchidos, usadas


def montar_markdown(resposta_estruturada: RespostaTextoAnalitico) -> str:
    """As três partes viram Markdown. Separado de ``montar_conteudo`` para o teste ler."""
    return (
        f"# {resposta_estruturada.titulo}\n\n"
        f"## O que foi decidido\n\n{resposta_estruturada.o_que_foi_decidido}\n\n"
        f"## Por quê\n\n{resposta_estruturada.por_que}\n\n"
        f"## O que observar adiante\n\n{resposta_estruturada.o_que_observar_adiante}\n"
    )


def montar_conteudo(
    resposta_estruturada: BaseModel,
    formato: Formato,
    ancoras: Ancoras,
    duracao: DuracaoDoVideo = DURACAO_PADRAO_DO_ROTEIRO,
) -> Conteudo:
    """Aplica ``preencher`` em todo campo de texto, inclusive a rubrica ``tela`` do Roteiro:
    ela aparece escrita no vídeo, então um número ali também vem das Âncoras, nunca da memória
    do LLM (ADR 0011)."""
    if formato is Formato.TEXTO_ANALITICO:
        assert isinstance(resposta_estruturada, RespostaTextoAnalitico)
        campos = [
            resposta_estruturada.titulo,
            resposta_estruturada.o_que_foi_decidido,
            resposta_estruturada.por_que,
            resposta_estruturada.o_que_observar_adiante,
        ]
        preenchidos, usadas = _preencher_varios(campos, ancoras)
        titulo, decidido, porque, adiante = preenchidos
        texto = montar_markdown(
            RespostaTextoAnalitico(
                titulo=titulo,
                o_que_foi_decidido=decidido,
                por_que=porque,
                o_que_observar_adiante=adiante,
            )
        )
        return Conteudo(formato=formato, texto=texto, ancoras_citadas=usadas)

    if formato is Formato.CARROSSEL:
        assert isinstance(resposta_estruturada, RespostaCarrossel)
        campos = [campo for slide in resposta_estruturada.slides for campo in (slide.titulo, slide.corpo)]
        preenchidos, usadas = _preencher_varios(campos, ancoras)
        slides = [
            Slide(
                tipo=slide.tipo,
                titulo=preenchidos[2 * i],
                corpo=preenchidos[2 * i + 1],
                dado=slide.dado,
                destaque=slide.destaque,
                imagem=slide.imagem,
            )
            for i, slide in enumerate(resposta_estruturada.slides)
        ]
        return Conteudo(formato=formato, slides=slides, ancoras_citadas=usadas)

    assert isinstance(resposta_estruturada, RespostaRoteiro)
    falas, usadas_fala = _preencher_varios(
        [bloco.fala for bloco in resposta_estruturada.blocos], ancoras
    )
    telas, usadas_tela = _preencher_varios(
        [bloco.tela for bloco in resposta_estruturada.blocos], ancoras
    )
    usadas = usadas_fala + [chave for chave in usadas_tela if chave not in usadas_fala]
    blocos = [
        bloco.model_copy(update={"fala": falas[i], "tela": telas[i]})
        for i, bloco in enumerate(resposta_estruturada.blocos)
    ]
    return Conteudo(
        formato=formato,
        blocos=cronometrar(blocos),
        duracao_alvo_s=duracao.segundos,
        ancoras_citadas=usadas,
    )
