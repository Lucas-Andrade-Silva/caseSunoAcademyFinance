"""O plano de edição de um Roteiro: o mesmo conteúdo em duas leituras.

- **JSON** (``plano.json``): autocontido e versionado, pensado para ser colado em um gerador de
  vídeo com avatar sintético. Cada cena diz o que o avatar fala, onde ele fica, o que aparece
  escrito, o ícone, como a cena entra, o efeito e os sons, com tempos absolutos em segundos e
  os tokens do design system embutidos — quem recebe o JSON não precisa de mais nada.
- **Markdown** (``plano.md``): a mesma coisa em tabela, para uma pessoa conferir a edição.

Tudo é derivado do ``Conteudo`` do Roteiro: nenhuma informação nova nasce aqui, e por isso nada
disto passa pelo Avaliador (ADR 0001). O vídeo só nasce de Roteiro aprovado (ADR 0004).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from suno.dominio import Audiencia, BlocoFala, Conteudo, Destino, Formato
from suno.video import design

ESQUEMA = "suno.roteiro-de-video"
VERSAO_DO_ESQUEMA = "1"

NOME_DO_PLANO = "plano.json"
NOME_DO_PLANO_LEGIVEL = "plano.md"

TOM_DA_VOZ: dict[Audiencia, str] = {
    Audiencia.INICIANTE: "acolhedor e didático, sem jargão",
    Audiencia.INTERMEDIARIO: "claro e objetivo",
    Audiencia.AVANCADO: "técnico e direto",
}

SEPARADOR_DE_PARTES = " | "

_AVATAR_POR_LAYOUT: dict[str, dict[str, Any]] = {
    "grande_centro": {"visivel": True, "posicao": "centro", "escala": 1.0},
    "canto": {"visivel": True, "posicao": "canto_inferior_direito", "escala": 0.35},
    "oculto": {"visivel": False, "posicao": None, "escala": 0.0},
}


def _sons_da_cena(bloco: BlocoFala) -> list[dict[str, Any]]:
    sons: list[dict[str, Any]] = []
    marcas = (
        (bloco.som_de_entrada, bloco.inicio_s, "entrada"),
        (bloco.som_de_efeito, bloco.inicio_s + bloco.texto_entra_em_s, "efeito"),
    )
    for som, instante, papel in marcas:
        if som is None:
            continue
        descricao = design.SONS[som]
        sons.append(
            {
                "nome": som.value,
                "papel": papel,
                "em_s": round(instante, 2),
                "duracao_s": descricao.duracao_s,
                "volume": descricao.volume,
            }
        )
    return sons


def _cena_do_plano(ordem: int, bloco: BlocoFala) -> dict[str, Any]:
    layout = design.CENAS[bloco.cena]
    partes = [p.strip() for p in bloco.tela.split(SEPARADOR_DE_PARTES.strip()) if p.strip()]
    return {
        "ordem": ordem,
        "inicio_s": bloco.inicio_s,
        "fim_s": bloco.fim_s,
        "duracao_s": round(bloco.fim_s - bloco.inicio_s, 2),
        "tipo": bloco.cena.value,
        "fala": bloco.fala,
        "avatar": dict(_AVATAR_POR_LAYOUT[layout.avatar]),
        "texto_na_tela": (
            {
                "conteudo": bloco.tela,
                "partes": partes,
                "animacao": bloco.texto_anima.value,
                "aparece_em_s": round(bloco.inicio_s + bloco.texto_entra_em_s, 2),
                "zona": layout.zona_do_texto,
                "estilo": layout.tamanho_do_texto,
            }
            if bloco.tela
            else None
        ),
        "icone": (
            {"nome": bloco.icone.value, "significado": design.ICONES[bloco.icone]}
            if bloco.icone is not None
            else None
        ),
        "entrada": {
            "transicao": bloco.entrada.value,
            "duracao_s": 0.0 if bloco.entrada.value == "corte" else design.TEMPOS["transicao_s"],
        },
        "efeito": bloco.efeito.value,
        "sons": _sons_da_cena(bloco),
    }


def montar_plano(conteudo: Conteudo, audiencia: Audiencia) -> dict[str, Any]:
    """O plano de edição completo, serializável em JSON, a partir de um Roteiro."""
    if conteudo.formato is not Formato.ROTEIRO or not conteudo.blocos:
        raise ValueError("só um Roteiro com blocos tem plano de edição")
    blocos = conteudo.blocos
    palavras = sum(design.contar_palavras(b.fala) for b in blocos)
    return {
        "esquema": ESQUEMA,
        "versao": VERSAO_DO_ESQUEMA,
        "design_system": {
            "versao": design.VERSAO_DO_DESIGN,
            "cores": design.CORES,
            "tipografia": design.TIPOGRAFIA,
            "area_segura": design.AREA_SEGURA,
            "tempos": design.TEMPOS,
        },
        "video": {
            "proporcao": "9:16",
            "largura_px": design.LARGURA,
            "altura_px": design.ALTURA,
            "idioma": "pt-BR",
            "audiencia": audiencia.value,
            "duracao_alvo_s": conteudo.duracao_alvo_s,
            "duracao_estimada_s": blocos[-1].fim_s,
            "palavras": palavras,
        },
        "avatar": {
            "tipo": "apresentador",
            "enquadramento": "busto",
            "fundo": {"tipo": "cor_solida", "cor": design.CORES["fundo"]},
            "voz": {
                "idioma": "pt-BR",
                "tom": TOM_DA_VOZ[audiencia],
                "ritmo_palavras_por_segundo": design.PALAVRAS_POR_SEGUNDO,
            },
            "sincronia_labial": True,
        },
        "cenas": [_cena_do_plano(ordem, bloco) for ordem, bloco in enumerate(blocos, start=1)],
    }


def plano_em_markdown(plano: dict[str, Any]) -> str:
    """A tabela de edição, para uma pessoa conferir antes de mandar para o gerador de avatar."""
    video = plano["video"]
    linhas = [
        f"# Plano de edição — Roteiro {video['audiencia']}",
        "",
        (
            f"{video['duracao_estimada_s']:.0f}s estimados "
            f"(alvo {video['duracao_alvo_s']}s) · {video['palavras']} palavras · "
            f"{video['largura_px']}×{video['altura_px']} ({video['proporcao']})"
        ),
        "",
        "| # | Tempo | Cena | O que o avatar diz | Na tela | Ícone | Entrada | Efeito | Sons |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for cena in plano["cenas"]:
        tela = cena["texto_na_tela"]
        na_tela = (
            f"{tela['conteudo']} _({tela['animacao']}, em {tela['aparece_em_s']:.1f}s)_"
            if tela
            else "—"
        )
        sons = ", ".join(f"{s['nome']} em {s['em_s']:.1f}s" for s in cena["sons"]) or "—"
        icone = cena["icone"]["nome"] if cena["icone"] else "—"
        linhas.append(
            f"| {cena['ordem']} | {cena['inicio_s']:.1f}–{cena['fim_s']:.1f}s | {cena['tipo']} | "
            f"{cena['fala']} | {na_tela} | {icone} | {cena['entrada']['transicao']} | "
            f"{cena['efeito']} | {sons} |"
        )
    return "\n".join(linhas) + "\n"


def plano_do_roteiro(identificador_execucao: str, audiencia: Audiencia, pasta_execucoes: Path) -> Path:
    """Grava ``plano.json`` e ``plano.md`` ao lado do vídeo e devolve o caminho do JSON.

    Levanta ``ValueError`` se a Célula não existe ou não foi aprovada: o plano é o roteiro
    do vídeo, e vídeo nunca nasce de Roteiro reprovado (ADR 0004).
    """
    from suno.gerador.execucao import carregar_execucao

    execucao = carregar_execucao(identificador_execucao, pasta_execucoes)
    historico = execucao.historico(audiencia, Formato.ROTEIRO)
    if historico is None or historico.destino_final is not Destino.APROVADO or historico.celula_final is None:
        raise ValueError("só Roteiro aprovado tem plano de edição (ADR 0004)")
    plano = montar_plano(historico.celula_final.conteudo, audiencia)
    pasta = Path(pasta_execucoes) / identificador_execucao / "pacote" / f"{audiencia.value}-roteiro"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / NOME_DO_PLANO
    caminho.write_text(json.dumps(plano, ensure_ascii=False, indent=2), encoding="utf-8")
    (pasta / NOME_DO_PLANO_LEGIVEL).write_text(plano_em_markdown(plano), encoding="utf-8")
    return caminho
