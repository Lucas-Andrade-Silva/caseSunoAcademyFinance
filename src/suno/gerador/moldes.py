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

from suno.dominio import (
    Ancoras,
    Audiencia,
    BlocoFala,
    Conteudo,
    Correcao,
    Faixa,
    Formato,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    Slide,
)

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
SEGUNDOS_DO_ROTEIRO = 60
"""Teto de duração do Roteiro, em segundos (ARQUITETURA.md)."""

ALVO_FLESCH_BR: dict[Audiencia, Faixa] = {
    Audiencia.INICIANTE: Faixa(minimo=60.0),
    Audiencia.INTERMEDIARIO: Faixa(minimo=30.0, maximo=45.0),
    Audiencia.AVANCADO: Faixa(maximo=18.0),
}
"""Alvo interno do Gerador, mais folgado que o Limiar. Provisório, aguardando Calibração."""

MAX_TOKENS_DA_CELULA = 4096
"""A Ata inteira entra no pedido; a resposta estruturada é curta, mas o Carrossel tem sete slides."""


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
    """Blocos de fala cronometrados; o primeiro é o gancho."""

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
        f"Formato Carrossel: de {SLIDES_MINIMOS} a {SLIDES_MAXIMOS} slides, o primeiro é o "
        "gancho, os do meio são o corpo e o último é a conclusão. Cada slide tem 'titulo' e "
        "'corpo'; 'dado' é opcional e recebe a chave da Âncora a plotar naquele slide "
        "(só a chave, sem chaves duplas)."
    ),
    Formato.ROTEIRO: (
        f"Formato Roteiro: blocos de fala cronometrados somando no máximo {SEGUNDOS_DO_ROTEIRO} "
        "segundos. O primeiro bloco é o gancho. 'fala' é o que é dito e é o que a Facilidade de "
        "leitura mede; 'tela' é a rubrica de cena, não é lida em voz alta, mas aparece escrita "
        "no vídeo — todo número em 'tela' também entra escrevendo `{{chave}}`, do mesmo jeito "
        "que em 'fala'."
    ),
}


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


def _bloco_de_correcoes(correcoes: list[Correcao]) -> str:
    linhas = "\n".join(f"- {correcao.instrucao}" for correcao in correcoes)
    return (
        "O que precisa mudar (o Avaliador mediu a Célula da rodada anterior e reprovou):\n"
        f"{linhas}\n"
        "Reescreva a Célula inteira corrigindo exatamente isso. Não mude o que já estava certo."
    )


def _bloco_transversal(orientacoes: list[str]) -> str:
    linhas = "\n".join(f"- {orientacao}" for orientacao in orientacoes)
    return (
        "Correções do avaliador transversal para esta Célula:\n"
        f"{linhas}\n"
        "Reescreva a Célula inteira. Preserve todos os fatos e Âncoras que já estavam certos."
    )


def montar_pedido(
    ata_texto: str,
    ancoras: Ancoras,
    audiencia: Audiencia,
    formato: Formato,
    rodada: int = 0,
    correcoes: list[Correcao] | None = None,
    orientacoes_transversais: list[str] | None = None,
) -> PedidoLLM:
    """O pedido de uma Célula. Em ``rodada > 0``, as ``correcoes`` entram como valor medido."""
    sistema = "\n\n".join(
        [
            "Você adapta uma Ata do Copom para uma Audiência num Formato.",
            INSTRUCAO_DA_AUDIENCIA[audiencia],
            INSTRUCAO_DO_FORMATO[formato],
            (
                "Facilidade de leitura alvo (índice Flesch-BR): "
                f"{_alvo_em_palavras(audiencia)}."
            ),
            (
                "Todo número entra escrevendo `{{chave}}`, e só chave da lista de Âncoras do "
                "pedido. Nunca escreva um número, por extenso ou em dígitos, que não seja uma "
                "chave dessa lista."
            ),
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
        partes_do_usuario.append(_bloco_de_correcoes(correcoes))
    if orientacoes_transversais:
        partes_do_usuario.append(_bloco_transversal(orientacoes_transversais))
    return PedidoLLM(
        papel=PapelLLM.GERADOR,
        rotulo=f"celula:{audiencia}:{formato}:{rodada}",
        mensagens=[
            Mensagem(autor="sistema", texto=sistema),
            Mensagem(autor="usuario", texto="\n\n".join(partes_do_usuario)),
        ],
        max_tokens=MAX_TOKENS_DA_CELULA,
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
    resposta_estruturada: BaseModel, formato: Formato, ancoras: Ancoras
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
            Slide(titulo=preenchidos[2 * i], corpo=preenchidos[2 * i + 1], dado=slide.dado)
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
        BlocoFala(inicio_s=bloco.inicio_s, fim_s=bloco.fim_s, fala=falas[i], tela=telas[i])
        for i, bloco in enumerate(resposta_estruturada.blocos)
    ]
    return Conteudo(formato=formato, blocos=blocos, ancoras_citadas=usadas)
