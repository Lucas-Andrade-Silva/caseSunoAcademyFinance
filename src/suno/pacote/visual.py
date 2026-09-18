"""Conferência visual determinística: estouro de caixa (Pillow), contraste, dimensão exata,
número do gráfico contra as Âncoras. Vai ao H5, nunca ao Laudo.

ADR 0014.

Quatro verificações, todas sem rede e sem modelo, uma ``MedicaoVisual`` por verificação e por
imagem. ``defeito=None`` quando passa: a lista completa é o que o H5 lê, não só o que deu errado.

Falha aqui é **defeito de render** — refazer o render, nunca reescrever a Célula. Por isso
``conferir_imagens`` não devolve Laudo, não devolve Destino e não toca em ``execucao.json``.

O juiz de visão (``julgar_folha_de_contato``) fica montado mas desligado nesta etapa: ele está
abaixo da linha dos seis entregáveis, por decisão do próprio ADR 0014. ``ConferenciaVisual``
sai daqui sempre com ``juiz_visao=None``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from suno.dominio import (
    ALTURA_SLIDE,
    CONTRASTE_MINIMO,
    LARGURA_SLIDE,
    Ancoras,
    ConferenciaVisual,
    DefeitoRender,
    ImagemSlide,
    MedicaoVisual,
    Mensagem,
    PapelLLM,
    ParecerVisao,
    PedidoLLM,
)
from suno.pacote.carrossel import altura_da_linha, medir_largura, tipografia

if TYPE_CHECKING:  # pragma: no cover - só para o verificador de tipos
    from suno.provedores import Provedor


# ---------------------------------------------------------------------------
# Contraste (fórmula WCAG)
# ---------------------------------------------------------------------------


def _luminancia(cor: str) -> float:
    """Luminância relativa de uma cor ``#rrggbb``, como a WCAG define."""
    limpo = cor.lstrip("#")
    componentes = [int(limpo[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    corrigidos = [
        parte / 12.92 if parte <= 0.03928 else ((parte + 0.055) / 1.055) ** 2.4
        for parte in componentes
    ]
    return 0.2126 * corrigidos[0] + 0.7152 * corrigidos[1] + 0.0722 * corrigidos[2]


def razao_de_contraste(cor: str, cor_atras: str) -> float:
    """``(L_claro + 0,05) / (L_escuro + 0,05)``: vai de 1 (invisível) a 21 (preto no branco)."""
    primeira, segunda = _luminancia(cor), _luminancia(cor_atras)
    clara, escura = max(primeira, segunda), min(primeira, segunda)
    return (clara + 0.05) / (escura + 0.05)


# ---------------------------------------------------------------------------
# As quatro verificações
# ---------------------------------------------------------------------------


def _medir_dimensao(nome: str, caminho: Path) -> MedicaoVisual:
    """1080x1350 exatos em todo slide: proporção variando estraga o carrossel inteiro (ADR 0009)."""
    with Image.open(caminho) as aberta:
        largura, altura = aberta.size
    certa = (largura, altura) == (LARGURA_SLIDE, ALTURA_SLIDE)
    return MedicaoVisual(
        artefato=nome,
        defeito=None if certa else DefeitoRender.DIMENSAO_ERRADA,
        valor=float(largura),
        detalhe=f"{largura}x{altura}; todo slide precisa de {LARGURA_SLIDE}x{ALTURA_SLIDE}",
    )


def _medir_estouro(nome: str, caixa: dict[str, Any]) -> MedicaoVisual:
    """Mede o texto com a mesma letra do render e compara com o retângulo reservado."""
    letra = tipografia(str(caixa["fonte"]), int(caixa["tamanho"]))
    x0, y0, x1, y1 = caixa["retangulo"]
    linhas = str(caixa["texto"]).split("\n")
    entrelinha = int(caixa.get("entrelinha", 0))
    largura_usada = max(medir_largura(linha, letra) for linha in linhas)
    altura_usada = len(linhas) * altura_da_linha(letra) + (len(linhas) - 1) * entrelinha
    sobra_largura = max(0, largura_usada - (x1 - x0))
    sobra_altura = max(0, altura_usada - (y1 - y0))
    rotulo = caixa.get("nome", "sem nome")
    if sobra_largura or sobra_altura:
        return MedicaoVisual(
            artefato=nome,
            defeito=DefeitoRender.ESTOURO_DE_CAIXA,
            valor=float(max(sobra_largura, sobra_altura)),
            detalhe=(
                f"caixa {rotulo}: {sobra_largura} px além da largura e {sobra_altura} px além"
                " da altura do retângulo reservado"
            ),
        )
    return MedicaoVisual(
        artefato=nome,
        defeito=None,
        valor=float(altura_usada),
        detalhe=f"caixa {rotulo}: {len(linhas)} linha(s) dentro do retângulo reservado",
    )


def _medir_contraste(nome: str, caixa: dict[str, Any]) -> MedicaoVisual:
    razao = razao_de_contraste(str(caixa["cor"]), str(caixa["cor_fundo"]))
    rotulo = caixa.get("nome", "sem nome")
    return MedicaoVisual(
        artefato=nome,
        defeito=None if razao >= CONTRASTE_MINIMO else DefeitoRender.CONTRASTE_BAIXO,
        valor=round(razao, 2),
        detalhe=(
            f"caixa {rotulo}: {caixa['cor']} sobre {caixa['cor_fundo']} dá razão"
            f" {razao:.2f}; o mínimo é {CONTRASTE_MINIMO}"
        ),
    )


def _medir_numero(nome: str, numero: dict[str, Any], ancoras: Ancoras) -> MedicaoVisual:
    """O número desenhado tem a mesma obrigação do número escrito: sair da Âncora (ADR 0011)."""
    chave = str(numero.get("chave", ""))
    desenhado = str(numero.get("texto", ""))
    ancora = ancoras.numerica(chave)
    esperado = ancora.citacao() if ancora is not None else None
    if esperado is None:
        detalhe = f"{chave!r}: a imagem mostra {desenhado!r} e não existe Âncora com essa chave"
    else:
        detalhe = f"{chave!r}: a imagem mostra {desenhado!r} e a Âncora cita {esperado!r}"
    return MedicaoVisual(
        artefato=nome,
        defeito=None if esperado == desenhado else DefeitoRender.NUMERO_DIVERGENTE,
        valor=None,
        detalhe=detalhe,
    )


def _ler_manifesto(caminho: Path) -> dict[str, Any] | None:
    """O ``slide-<nn>.json`` gravado ao lado do PNG. Sem ele, só a dimensão é mensurável."""
    manifesto = caminho.with_suffix(".json")
    if not manifesto.exists():
        return None
    return json.loads(manifesto.read_text(encoding="utf-8"))


def conferir_imagens(imagens: list[ImagemSlide], ancoras: Ancoras) -> ConferenciaVisual:
    """Mede cada slide renderizado e devolve a lista que o H5 lê junto com o Pacote.

    Não reprova a Célula, não entra no Laudo e não decide nada sozinha (ADR 0014).
    """
    medicoes: list[MedicaoVisual] = []
    for imagem_slide in imagens:
        caminho = Path(imagem_slide.caminho)
        nome = caminho.name
        medicoes.append(_medir_dimensao(nome, caminho))
        manifesto = _ler_manifesto(caminho)
        if manifesto is None:
            continue
        for caixa in manifesto.get("caixas", []):
            medicoes.append(_medir_estouro(nome, caixa))
            medicoes.append(_medir_contraste(nome, caixa))
        for numero in manifesto.get("numeros", []):
            medicoes.append(_medir_numero(nome, numero, ancoras))
    return ConferenciaVisual(medicoes=medicoes, juiz_visao=None)


# ---------------------------------------------------------------------------
# Juiz de visão: montado, não chamado (ADR 0014, abaixo da linha)
# ---------------------------------------------------------------------------

PAPEL_DO_JUIZ_DE_VISAO = (
    "Você olha uma folha de contato com todos os slides de um carrossel financeiro e responde"
    " só o que não se mede: o layout parece quebrado, há texto cortado ou sobreposto, o gráfico"
    " comunica o mesmo que o texto ao lado, os slides são consistentes entre si."
    " Você NUNCA julga se o conteúdo recomenda comprar ou vender: isso é verificado no texto,"
    " antes da renderização, por regra fixa de código."
)

PERGUNTA_DO_JUIZ_DE_VISAO = (
    "Esta folha de contato parece quebrada? Responda em JSON com 'parece_quebrado' (booleano),"
    " 'observacoes' (lista curta do que está errado) e 'provedor' (seu nome)."
)


def julgar_folha_de_contato(caminho: Path, provedor: Provedor) -> ParecerVisao:
    """A camada opcional do ADR 0014: uma chamada de visão por Célula de Carrossel.

    Fica **fora** de ``montar_pacote`` nesta etapa, por decisão do próprio ADR 0014: o juiz de
    visão está abaixo da linha dos seis entregáveis e cai antes de qualquer coisa que valha nota.
    Quem ligar isto depois passa ``SUNO_JUIZ_VISAO=1`` e um provedor com entrada de imagem.

    A restrição de autopreferência do ADR 0008 não vale aqui: a imagem não foi feita por modelo
    nenhum, então qualquer provedor pode julgá-la.
    """
    pedido = PedidoLLM(
        papel=PapelLLM.JUIZ_VISAO,
        rotulo=f"juiz-visao:{caminho.stem}",
        mensagens=[
            Mensagem(autor="sistema", texto=PAPEL_DO_JUIZ_DE_VISAO),
            Mensagem(
                autor="usuario",
                texto=PERGUNTA_DO_JUIZ_DE_VISAO,
                imagem_png=caminho.read_bytes(),
            ),
        ],
        max_tokens=512,
        temperatura=0.0,
        esforco_raciocinio="baixo",
    )
    return provedor.completar_estruturado(pedido, ParecerVisao)
