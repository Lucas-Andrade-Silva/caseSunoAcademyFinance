"""A direção de atuação do avatar: olhar, gesto, voz e legenda.

O padrão é fixo, em código: o que o avatar faz com o rosto e as mãos, como a voz pausa e
pronuncia sigla e número, onde a legenda cai. Uma LLM só **preenche** os campos que variam com
o conteúdo (expressão, gesto, entonação e pausa de cada cena), sempre por nome de um catálogo
fechado, como a direção de cena (ADR 0021). Sem LLM, vale o preenchimento padrão da Audiência.

Nada daqui passa pelo Avaliador (ADR 0001): é instrução de edição derivada do Roteiro já aprovado,
e a linha que não se cruza vale igual — a atuação nunca pede tom de convencimento.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from suno.dominio import (
    Audiencia,
    Conteudo,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    TipoDeCena,
)
from suno.provedores.base import Provedor
from suno.video import design

Gesto = Literal["nenhum", "minimo", "apontar_para_tela", "enumerar_nos_dedos"]
Entonacao = Literal["firme", "ascendente", "descendente", "neutra"]
Expressao = Literal["serena", "acolhedora", "atenta", "seria"]

GESTOS: dict[str, str] = {
    "nenhum": "mãos paradas, fora do quadro ou juntas",
    "minimo": "um movimento curto de mão para marcar a ideia",
    "apontar_para_tela": "mão aponta para o texto ou o dado que aparece (só com avatar em canto)",
    "enumerar_nos_dedos": "marca itens de uma lista, um por vez (só em `lista`)",
}
ENTONACOES: dict[str, str] = {
    "firme": "frase afirmativa, cai no fim; o padrão da decisão e do dado",
    "ascendente": "sobe no fim; só em pergunta, como o gancho",
    "descendente": "desacelera e baixa; o fechamento de uma ideia",
    "neutra": "leitura plana, sem ênfase; transições e contexto",
}
EXPRESSOES: dict[str, str] = {
    "serena": "rosto calmo, sobrancelhas relaxadas, sem sorriso",
    "acolhedora": "leve sorriso contido, sobrancelhas levemente erguidas",
    "atenta": "olhar firme, sobrancelhas levemente erguidas na ênfase",
    "seria": "rosto composto, sem sorriso; para decisão que pesa",
}

PAUSA_MAXIMA_S = 1.2

# ---------------------------------------------------------------------------
# O padrão fixo
# ---------------------------------------------------------------------------

ATUACAO_BASE: dict[str, Any] = {
    "olhar": "direto para a câmera durante toda a fala; nunca desvia para os lados ou para baixo",
    "postura": "busto reto, ombros relaxados, leve inclinação para a frente ao abrir e fechar",
    "movimento_da_cabeca": "acenos curtos e raros, só para marcar ênfase; sem balançar",
    "gestos": "mínimos: no máximo um gesto de mão por cena, abaixo da linha do queixo",
    "expressao_geral": "serena, sem sorriso exagerado; o assunto é dinheiro dos outros, sem festa",
    "proibido": [
        "olhar fixo sem piscar",
        "sorriso aberto ou riso",
        "gesto brusco ou acima do ombro",
        "tom de vendedor, urgência ou convencimento",
    ],
}

ATUACAO_POR_AUDIENCIA: dict[Audiencia, dict[str, str]] = {
    Audiencia.INICIANTE: {
        "expressao": "acolhedora",
        "gesto_padrao": "minimo",
        "energia": "calorosa e próxima, como explicar para um amigo",
    },
    Audiencia.INTERMEDIARIO: {
        "expressao": "atenta",
        "gesto_padrao": "minimo",
        "energia": "direta e organizada, de quem já acompanha o mercado",
    },
    Audiencia.AVANCADO: {
        "expressao": "seria",
        "gesto_padrao": "nenhum",
        "energia": "contida e analítica, sem dramatizar",
    },
}

VOZ_BASE: dict[str, Any] = {
    "estilo": "natural, de apresentador de jornal econômico; nunca leitura de texto",
    "ritmo_palavras_por_segundo": design.PALAVRAS_POR_SEGUNDO,
    "pausas": {
        "entre_ideias_s": 0.35,
        "antes_de_numero_s": 0.25,
        "depois_de_numero_s": 0.4,
        "depois_do_gancho_s": 0.5,
        "maxima_s": PAUSA_MAXIMA_S,
    },
    "entonacao": {
        "numero": "firme: dígito claro, leve ênfase no valor e na unidade",
        "sigla": "dita por inteiro e sem pressa, sem emendar na palavra seguinte",
        "pergunta": "sobe no fim, só no gancho",
        "fechamento": "desacelera e baixa na última frase",
    },
    "numeros": "sempre por extenso e com a unidade: '14,50%' vira 'catorze vírgula cinquenta por cento'",
    "se_voz_clonada": (
        "marque as pausas e a pronúncia abaixo no texto enviado; sem isso a voz clonada "
        "cai no tom de leitor de texto"
    ),
}

PRONUNCIA: dict[str, str] = {
    "a.a.": "ao ano",
    "a.m.": "ao mês",
    "p.p.": "pontos percentuais",
    "bps": "pontos-base",
    "%": "por cento",
    "IPCA": "I-P-C-A, letra por letra",
    "CDI": "C-D-I, letra por letra",
    "PIB": "pib, como palavra",
    "Copom": "cópom, tônica no 'có'",
    "Selic": "sélic, tônica no 'sé'",
    "7 a 0": "sete a zero",
    "9 a 0": "nove a zero",
}
"""Termos e siglas que a voz erra ou lê como texto. Quem clona a voz confere a lista no áudio."""

# A legenda mora em ``render.py`` (TAMANHO_LEGENDA, Y_LEGENDA, LINHAS_DA_LEGENDA); estes valores
# descrevem o que ela já faz, para quem recebe o JSON, e só mudam junto com o render.
_FAIXA_DA_LEGENDA_Y_PX = 1360


def _legendas() -> dict[str, Any]:
    margem = design.AREA_SEGURA["margem_px"]
    largura_util = design.LARGURA - 2 * margem
    return {
        "posicao": "faixa_inferior",
        "y_px": _FAIXA_DA_LEGENDA_Y_PX,
        "margem_lateral_px": margem,
        "largura_px": largura_util,
        "largura_com_avatar_em_canto_px": largura_util - 400,
        "alinhamento": "esquerda",
        "tamanho_px": design.TIPOGRAFIA["legenda"]["tamanho_px"],  # type: ignore[index]
        "peso": "regular",
        "cor": design.CORES["apoio"],
        "contorno": {"cor": design.CORES["fundo"], "largura_px": 3},
        "linhas_maximas": 2,
        "palavras_por_linha": "até 5",
        "segue_a_fala": "sim, palavra por palavra, sem adiantar o que ainda não foi dito",
        "regras_de_colisao": [
            "nunca sobre o texto da cena: ele ocupa o terço superior ou o centro",
            "com avatar em canto (inferior direito, 35%), a legenda encolhe a largura e não passa dele",
            "sem avatar (`comparacao`), a legenda usa a largura toda",
            f"nada abaixo de {design.ALTURA - design.AREA_SEGURA['base_px']}px: a interface da rede cobre",
        ],
    }


# ---------------------------------------------------------------------------
# O que a LLM preenche
# ---------------------------------------------------------------------------


class AtuacaoDaCena(BaseModel):
    ordem: int = Field(ge=1, description="Número da cena, como no Roteiro.")
    expressao: Expressao
    gesto: Gesto
    entonacao: Entonacao
    pausa_depois_s: float = Field(ge=0, le=PAUSA_MAXIMA_S)


class DirecaoDeAtuacao(BaseModel):
    """O preenchimento: uma linha por cena, sempre por nome do catálogo."""

    cenas: list[AtuacaoDaCena]


def _catalogo(titulo: str, itens: dict[str, str]) -> str:
    linhas = "\n".join(f"  - {nome}: {descricao}" for nome, descricao in itens.items())
    return f"{titulo}\n{linhas}"


def instrucao_de_atuacao(audiencia: Audiencia) -> str:
    padrao = ATUACAO_POR_AUDIENCIA[audiencia]
    return "\n".join(
        [
            "Você dirige a atuação de um avatar apresentador de vídeo financeiro. Para cada cena, "
            "escolha só nomes destas listas. O padrão do avatar já está fixado (olhar na câmera, "
            "gestos mínimos, sem sorriso exagerado); você só ajusta cena a cena.",
            f"Audiência {audiencia.value}: {padrao['energia']}. Expressão padrão: {padrao['expressao']}.",
            _catalogo("expressao:", EXPRESSOES),
            _catalogo("gesto:", GESTOS),
            _catalogo("entonacao:", ENTONACOES),
            (
                f"pausa_depois_s: de 0 a {PAUSA_MAXIMA_S} segundos. Curta entre ideias, mais longa "
                "depois de número e do gancho. `apontar_para_tela` só vale com o avatar em canto; "
                "`enumerar_nos_dedos` só em `lista`. `ascendente` só no gancho. Nada de tom de "
                "convencimento ou urgência."
            ),
            "Devolva exatamente uma linha por cena, na ordem do Roteiro.",
        ]
    )


def pedido_de_atuacao(conteudo: Conteudo, audiencia: Audiencia) -> PedidoLLM:
    cenas = "\n".join(
        f"{ordem}. [{bloco.cena.value}] {bloco.fala}"
        for ordem, bloco in enumerate(conteudo.blocos or [], start=1)
    )
    return PedidoLLM(
        papel=PapelLLM.VIDEO,
        rotulo=f"atuacao:{audiencia.value}",
        mensagens=[
            Mensagem(autor="sistema", texto=instrucao_de_atuacao(audiencia)),
            Mensagem(autor="usuario", texto=f"Cenas do Roteiro aprovado:\n{cenas}"),
        ],
        max_tokens=1024,
        temperatura=0.2,
    )


def direcao_padrao(conteudo: Conteudo, audiencia: Audiencia) -> DirecaoDeAtuacao:
    """O preenchimento sem LLM: determinístico, pela Audiência e pelo tipo da cena."""
    padrao = ATUACAO_POR_AUDIENCIA[audiencia]
    pausas = VOZ_BASE["pausas"]
    cenas: list[AtuacaoDaCena] = []
    total = len(conteudo.blocos or [])
    for ordem, bloco in enumerate(conteudo.blocos or [], start=1):
        eh_gancho = bloco.cena is TipoDeCena.GANCHO
        fecha = ordem == total
        cenas.append(
            AtuacaoDaCena(
                ordem=ordem,
                expressao=padrao["expressao"],  # type: ignore[arg-type]
                gesto="enumerar_nos_dedos" if bloco.cena is TipoDeCena.LISTA and padrao["gesto_padrao"] != "nenhum"
                else padrao["gesto_padrao"],  # type: ignore[arg-type]
                entonacao="ascendente" if eh_gancho else "descendente" if fecha else "firme",
                pausa_depois_s=pausas["depois_do_gancho_s"] if eh_gancho
                else pausas["depois_de_numero_s"] if bloco.cena is TipoDeCena.DADO_GRANDE
                else pausas["entre_ideias_s"],
            )
        )
    return DirecaoDeAtuacao(cenas=cenas)


def _sanear(direcao: DirecaoDeAtuacao, conteudo: Conteudo, audiencia: Audiencia) -> DirecaoDeAtuacao:
    """Fecha o que o LLM pode errar: cena faltando, gesto que o layout não comporta."""
    padrao = {c.ordem: c for c in direcao_padrao(conteudo, audiencia).cenas}
    escolhidas = {c.ordem: c for c in direcao.cenas if c.ordem in padrao}
    cenas: list[AtuacaoDaCena] = []
    for ordem, bloco in enumerate(conteudo.blocos or [], start=1):
        cena = escolhidas.get(ordem, padrao[ordem])
        layout = design.CENAS[bloco.cena]
        gesto = cena.gesto
        if gesto == "apontar_para_tela" and layout.avatar != "canto":
            gesto = padrao[ordem].gesto
        if gesto == "enumerar_nos_dedos" and bloco.cena is not TipoDeCena.LISTA:
            gesto = padrao[ordem].gesto
        entonacao = cena.entonacao
        if entonacao == "ascendente" and bloco.cena is not TipoDeCena.GANCHO:
            entonacao = padrao[ordem].entonacao
        cenas.append(cena.model_copy(update={"gesto": gesto, "entonacao": entonacao}))
    return DirecaoDeAtuacao(cenas=cenas)


def _pedir_a_llm(
    conteudo: Conteudo, audiencia: Audiencia, provedor: Provedor
) -> DirecaoDeAtuacao | None:
    try:
        resposta = provedor.completar_estruturado(pedido_de_atuacao(conteudo, audiencia), DirecaoDeAtuacao)
    except Exception:  # noqa: BLE001 — a atuação é acabamento: o vídeo não pode parar por ela
        return None
    return _sanear(resposta, conteudo, audiencia)


def preencher_direcao(
    conteudo: Conteudo, audiencia: Audiencia, provedor: Provedor | None = None
) -> DirecaoDeAtuacao:
    """A LLM preenche a atuação cena a cena; qualquer falha cai no padrão da Audiência."""
    if provedor is not None:
        direcao = _pedir_a_llm(conteudo, audiencia, provedor)
        if direcao is not None:
            return direcao
    return direcao_padrao(conteudo, audiencia)


NOME_DO_ARQUIVO = "atuacao.json"


def direcao_em_disco(
    pasta_do_pacote: Path, conteudo: Conteudo, audiencia: Audiencia, provedor: Provedor | None
) -> DirecaoDeAtuacao:
    """A atuação gravada ao lado do plano: a LLM é chamada uma vez por Roteiro, não por leitura.

    Só o que a LLM devolveu é gravado; o padrão de contingência não, para que uma cota esgotada
    hoje não congele o preenchimento fraco amanhã. Sem ``provedor``, lê o que existe ou usa o padrão.
    """
    caminho = Path(pasta_do_pacote) / NOME_DO_ARQUIVO
    if caminho.exists():
        try:
            gravada = DirecaoDeAtuacao.model_validate_json(caminho.read_text(encoding="utf-8"))
        except ValueError:
            gravada = None
        if gravada is not None and len(gravada.cenas) == len(conteudo.blocos or []):
            return gravada
    if provedor is not None:
        direcao = _pedir_a_llm(conteudo, audiencia, provedor)
        if direcao is not None:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_text(direcao.model_dump_json(indent=2), encoding="utf-8")
            return direcao
    return direcao_padrao(conteudo, audiencia)


def bloco_do_plano(audiencia: Audiencia) -> dict[str, Any]:
    """O que entra no ``plano.json`` além das cenas: padrão fixo, voz, pronúncia e legendas."""
    return {
        "atuacao": {**ATUACAO_BASE, **ATUACAO_POR_AUDIENCIA[audiencia]},
        "voz": VOZ_BASE,
        "pronuncia": PRONUNCIA,
        "legendas": _legendas(),
    }
