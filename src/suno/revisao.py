"""A decisão humana sobre uma Célula: aprovar ou reprovar, e quando isso é proibido.

Compliance é métrica do Laudo (CLAUDE.md): a Célula cujo Laudo final carrega
``MotivoReprovacao.RECOMENDACAO`` não pode ser aprovada por ninguém. A regra mora aqui, e não
na tela, para que a API a imponha mesmo a quem chamar a rota sem passar pela interface.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from suno.avaliador import avaliar
from suno.dominio import (
    CHAVES_ESSENCIAIS_GENERICAS,
    Audiencia,
    CategoriaDaAta,
    Celula,
    Conteudo,
    DecisaoHumana,
    Destino,
    EstadoDecisao,
    Execucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    MotivoReprovacao,
    Pendencia,
    Tentativa,
    chaves_essenciais_da,
)


class CelulaNaoEncontrada(LookupError):
    """A posição não existe nesta execução."""


class DecisaoInvalida(ValueError):
    """O pedido não faz sentido para esta Célula: sem conteúdo, em correção ou sem motivo."""


class DecisaoBloqueada(Exception):
    """O Laudo proíbe a decisão: a Célula cruzou a linha da Recomendação."""


def celula_bloqueada(historico: HistoricoCelula) -> bool:
    """O Laudo final detectou Recomendação: esta Célula não pode ser aprovada."""
    laudo = historico.laudo_final
    return laudo is not None and MotivoReprovacao.RECOMENDACAO in laudo.motivos


def decidir(
    execucao: Execucao,
    audiencia: Audiencia,
    formato: Formato,
    estado: EstadoDecisao,
    *,
    motivo: str | None = None,
    revisor: str | None = None,
) -> DecisaoHumana:
    """Registra a decisão em ``execucao.decisoes`` e resolve a Pendência H4 da posição.

    Muda o objeto em memória; quem chama grava em disco. Uma decisão nova na mesma posição
    substitui a anterior.
    """
    historico = execucao.historico(audiencia, formato)
    if historico is None:
        raise CelulaNaoEncontrada("Célula não encontrada nesta execução")
    if historico.celula_final is None:
        raise DecisaoInvalida("a Célula não tem conteúdo gerado: não há o que decidir")

    motivo_limpo = (motivo or "").strip() or None
    if estado is EstadoDecisao.REPROVADA and motivo_limpo is None:
        raise DecisaoInvalida("reprovar exige motivo")

    if estado is EstadoDecisao.APROVADA:
        if celula_bloqueada(historico):
            raise DecisaoBloqueada(
                "o Laudo detectou Recomendação: esta Célula não pode ser aprovada"
            )
        if historico.destino_final is Destino.REPROVADO_CORRIGIVEL:
            raise DecisaoInvalida("a Célula ainda está em correção: espere o Ciclo terminar")

    decisao = DecisaoHumana(
        audiencia=audiencia,
        formato=formato,
        estado=estado,
        motivo=motivo_limpo,
        revisor=(revisor or "").strip() or None,
    )
    execucao.decisoes = [
        anterior
        for anterior in execucao.decisoes
        if (anterior.audiencia, anterior.formato) != (audiencia, formato)
    ] + [decisao]

    resumo_da_decisao = estado.value if motivo_limpo is None else f"{estado.value}: {motivo_limpo}"
    for pendencia in execucao.pendencias:
        if (
            pendencia.fila is FilaHumana.H4_REVISAO
            and (pendencia.audiencia, pendencia.formato) == (audiencia, formato)
            and not pendencia.resolvida
        ):
            pendencia.resolvida = True
            pendencia.decisao = resumo_da_decisao
    return decisao


# ---------------------------------------------------------------------------
# Edição humana do texto
# ---------------------------------------------------------------------------


class EdicaoDeSlide(BaseModel):
    titulo: str
    corpo: str


class EdicaoDeBloco(BaseModel):
    fala: str
    tela: str = ""


class EdicaoDeTexto(BaseModel):
    """O texto que a pessoa corrigiu, na ordem da Célula. Só o campo do Formato da Célula vale.

    Só entram os campos que a pessoa pode mexer: o que é direção (tipo, dado, ícone, tempos)
    fica como o Gerador deixou.
    """

    texto: str | None = None
    slides: list[EdicaoDeSlide] | None = None
    blocos: list[EdicaoDeBloco] | None = None


class EdicaoInvalida(ValueError):
    """A edição não cabe na Célula: Formato trocado, outro número de itens ou texto vazio."""


def _chaves_essenciais_da_execucao(execucao: Execucao) -> dict[str, frozenset[str]]:
    """O mesmo conjunto essencial que o Ciclo usou ao gerar; o Copom segue pelo padrão."""
    if execucao.categoria is CategoriaDaAta.COPOM:
        return {}
    if execucao.categoria is not CategoriaDaAta.UNIDA:
        return {"chaves_essenciais": chaves_essenciais_da(execucao.categoria)}
    partes = {
        int(achado.group(1))
        for chave in (a.chave for a in execucao.ancoras.todas())
        if (achado := re.match(r"a(\d+)_", chave))
    }
    return {
        "chaves_essenciais": frozenset(
            f"a{posicao}_{chave}"
            for posicao in sorted(partes)
            for chave in CHAVES_ESSENCIAIS_GENERICAS
        )
    }


def _conteudo_editado(atual: Conteudo, edicao: EdicaoDeTexto) -> Conteudo:
    def preenchido(valor: str, onde: str) -> str:
        if not valor.strip():
            raise EdicaoInvalida(f"{onde} não pode ficar vazio")
        return valor.strip()

    if atual.formato is Formato.TEXTO_ANALITICO:
        if edicao.texto is None:
            raise EdicaoInvalida("esta Célula é um texto: envie o campo 'texto'")
        return atual.model_copy(update={"texto": preenchido(edicao.texto, "o texto")})

    if atual.formato is Formato.CARROSSEL:
        if edicao.slides is None:
            raise EdicaoInvalida("esta Célula é um carrossel: envie o campo 'slides'")
        if len(edicao.slides) != len(atual.slides or []):
            raise EdicaoInvalida("o número de quadros não pode mudar")
        novos = []
        for indice, (slide, nova) in enumerate(zip(atual.slides or [], edicao.slides), start=1):
            titulo = preenchido(nova.titulo, f"o título do quadro {indice}")
            corpo = preenchido(nova.corpo, f"o corpo do quadro {indice}")
            destaque = slide.destaque if slide.destaque and slide.destaque in titulo else None
            novos.append(slide.model_copy(update={"titulo": titulo, "corpo": corpo, "destaque": destaque}))
        return atual.model_copy(update={"slides": novos})

    if edicao.blocos is None:
        raise EdicaoInvalida("esta Célula é um roteiro: envie o campo 'blocos'")
    if len(edicao.blocos) != len(atual.blocos or []):
        raise EdicaoInvalida("o número de cenas não pode mudar")
    blocos = [
        bloco.model_copy(
            update={"fala": preenchido(nova.fala, f"a fala da cena {indice}"), "tela": nova.tela.strip()}
        )
        for indice, (bloco, nova) in enumerate(zip(atual.blocos or [], edicao.blocos), start=1)
    ]
    return atual.model_copy(update={"blocos": blocos})


def revisar_texto(
    execucao: Execucao, audiencia: Audiencia, formato: Formato, edicao: EdicaoDeTexto
) -> HistoricoCelula:
    """Aplica o texto corrigido por uma pessoa e o julga de novo, sem LLM e sem rede.

    O Laudo novo entra como uma Tentativa a mais (na mesma rodada, sem gastar o teto do Ciclo),
    então o Pacote e o render passam a ler o texto editado e o histórico guarda o original.
    Uma decisão humana anterior sobre a posição deixa de valer: o texto é outro. Muda o objeto
    em memória; quem chama grava em disco. A avaliação da Matriz inteira não é refeita.
    """
    historico = execucao.historico(audiencia, formato)
    if historico is None:
        raise CelulaNaoEncontrada("Célula não encontrada nesta execução")
    ultima = historico.tentativas[-1] if historico.tentativas else None
    if ultima is None:
        raise DecisaoInvalida("a Célula não tem conteúdo gerado: não há o que editar")

    conteudo = _conteudo_editado(ultima.celula.conteudo, edicao)
    laudo = avaliar(
        conteudo,
        execucao.ancoras.todas(),
        audiencia,
        **_chaves_essenciais_da_execucao(execucao),
    )
    celula = Celula(
        audiencia=audiencia,
        formato=formato,
        conteudo=conteudo,
        rodada=ultima.rodada,
        provedor="humano",
    )
    historico.tentativas.append(Tentativa(rodada=ultima.rodada, celula=celula, laudo=laudo))
    historico.falha = None
    aprovada = laudo.destino is Destino.APROVADO
    historico.destino_final = Destino.APROVADO if aprovada else Destino.REPROVADO_REVISAO_HUMANA

    execucao.decisoes = [
        d for d in execucao.decisoes if (d.audiencia, d.formato) != (audiencia, formato)
    ]
    na_posicao = [
        p
        for p in execucao.pendencias
        if p.fila is FilaHumana.H4_REVISAO and (p.audiencia, p.formato) == (audiencia, formato)
    ]
    if aprovada:
        for pendencia in na_posicao:
            if not pendencia.resolvida:
                pendencia.resolvida = True
                pendencia.decisao = "texto revisado: o Laudo aprovou"
    elif all(p.resolvida for p in na_posicao):
        execucao.pendencias.append(
            Pendencia(
                fila=FilaHumana.H4_REVISAO,
                audiencia=audiencia,
                formato=formato,
                motivo=", ".join(m.value for m in laudo.motivos) or "reprovada sem motivo registrado",
            )
        )
    return historico
