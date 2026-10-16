"""Uma execução ponta a ponta: lê a Ata do disco, extrai Âncoras, gera a Matriz, avalia,
corrige e grava `data/execucoes/<id>/execucao.json`, o mesmo arquivo que a API e o pytest leem.

ADR 0001, 0006.

`execucao.json` é o **único** arquivo de estado. Os `.md` em `celulas/` são conveniência
para um humano ler sem abrir JSON; se divergirem, o JSON é quem vale.

Falha de extração não é exceção: as nove Células são geradas uma vez, o Avaliador reprova
cada uma com `FALHA_DE_EXTRACAO` e todas caem na fila humana H4 (ADR 0013). Uma Ata fora do
padrão não derruba a execução — ela aparece na fila.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel

from suno.dominio import (
    DuracaoDoVideo,
    MATRIZ,
    Audiencia,
    ComposicaoCarrossel,
    Custo,
    Destino,
    Execucao,
    FaseDaExecucao,
    FilaHumana,
    Formato,
    HistoricoCelula,
    Pendencia,
    PedidoLLM,
    PosicaoDaMatriz,
    RespostaLLM,
)
from suno.avaliador.transversal import avaliar_matriz
from suno.gerador.ciclo import Andou
from suno.gerador.curador import AgenteCurador, compor_uniao
from suno.gerador.matriz import gerar_matriz_do_dossie
from suno.ingestao.pdf import carregar_ata
from suno.provedores.base import Provedor, ProvedorBase
from suno.provedores.roteador import provedor_por_nome

_registro = logging.getLogger(__name__)

Estruturada = TypeVar("Estruturada", bound=BaseModel)

PASTA_RESPOSTAS_PRONTAS = Path(__file__).resolve().parents[3] / "data" / "respostas_prontas"
"""Onde a demo sem rede guarda as filas do LLM falso, uma por Ata.

Ancorado no arquivo, não no diretório de trabalho: a demo roda de qualquer lugar.
"""

ARQUIVO_DA_EXECUCAO = "execucao.json"
PASTA_DAS_CELULAS = "celulas"


class _Caderno:
    """A lista de ``RespostaLLM`` de uma execução, com trava: nove Células escrevem nela."""

    def __init__(self) -> None:
        self.respostas: list[RespostaLLM] = []
        self._trava = threading.Lock()

    def anotar(self, resposta: RespostaLLM) -> None:
        with self._trava:
            self.respostas.append(resposta)

    def custo(self, segundos: float) -> Custo:
        with self._trava:
            respostas = list(self.respostas)
        por_provedor: dict[str, int] = {}
        for resposta in respostas:
            por_provedor[resposta.provedor] = por_provedor.get(resposta.provedor, 0) + 1
        return Custo(
            chamadas=len(respostas),
            tokens_entrada=sum(r.tokens_entrada for r in respostas),
            tokens_saida=sum(r.tokens_saida + r.tokens_raciocinio for r in respostas),
            segundos=segundos,
            por_provedor=por_provedor,
        )


class ProvedorContado(ProvedorBase):
    """Um provedor embrulhado que anota cada ``RespostaLLM`` para o Custo.

    O Custo precisa de chamadas e tokens, e nenhum provedor concreto tem por que saber
    disso: embrulhar aqui mantém ``provedores/`` intacto.

    Dois cuidados que não são óbvios:

    - O roteador chama o ``completar`` dos provedores **da fila dele**, nunca o seu
      próprio, então o contador entra em cada um deles também. Sem isso, uma execução com
      ``--provedor roteador`` sairia com custo zero.
    - ``completar_estruturado`` do roteador é quem troca de provedor quando a resposta vem
      fora do schema (ADR 0007). Quando o embrulhado tem implementação própria, delegamos;
      quando é a padrão, usamos a nossa, que passa pelo ``completar`` contado.
    """

    def __init__(self, interno: Provedor, *, caderno: _Caderno | None = None) -> None:
        self.interno = interno
        self.nome = interno.nome
        self._caderno = caderno if caderno is not None else _Caderno()
        fila = getattr(interno, "provedores", None)
        if isinstance(fila, list):
            interno.provedores = [ProvedorContado(p, caderno=self._caderno) for p in fila]

    @property
    def respostas(self) -> list[RespostaLLM]:
        return list(self._caderno.respostas)

    def completar(self, pedido: PedidoLLM) -> RespostaLLM:
        resposta = self.interno.completar(pedido)
        self._caderno.anotar(resposta)
        return resposta

    def completar_estruturado(
        self, pedido: PedidoLLM, modelo: type[Estruturada]
    ) -> Estruturada:
        if type(self.interno).completar_estruturado is ProvedorBase.completar_estruturado:
            return super().completar_estruturado(pedido, modelo)
        return self.interno.completar_estruturado(pedido, modelo)

    def custo(self, segundos: float) -> Custo:
        return self._caderno.custo(segundos)


def _qualidade_de_ambiente(*, ligado: bool | None, exigir: bool = False):
    """O Jev (ADR 0035), sempre ligado. ``ligado=False`` ou ``SUNO_JEV=0`` o desligam (testes); sem chave, é ``None``.

    Qualidade ausente é um Laudo só com as medidas determinísticas, nunca um Laudo pior.
    """
    try:
        from suno.avaliador.qualidade import AvaliadorDeQualidade

        return AvaliadorDeQualidade.de_ambiente(ligado=ligado, exigir=exigir)
    except (ImportError, AttributeError, NotImplementedError) as erro:
        _registro.warning("Jev pedido mas indisponível, seguindo sem ele: %s", erro)
        return None


def _fidelidade_de_ambiente(texto_da_ata: str, *, ligado: bool | None):
    """O checador de fidelidade (ADR 0036). ``ligado`` sobrepõe ``SUNO_FIDELIDADE``.

    Sem Groq nem Gemini, ou desligado, é ``None``: o Laudo fica só com as outras medidas.
    """
    try:
        from suno.avaliador.fidelidade import VerificadorDeFidelidade

        return VerificadorDeFidelidade.de_ambiente(texto_da_ata, ligado=ligado)
    except (ImportError, AttributeError, NotImplementedError) as erro:
        _registro.warning("checador pedido mas indisponível, seguindo sem ele: %s", erro)
        return None


def motivo_da_pendencia(historico: HistoricoCelula) -> str:
    """Por que esta Célula está esperando um humano (H4)."""
    if historico.falha is not None:
        return historico.falha
    laudo = historico.laudo_final
    if laudo is None:
        return "nenhuma Célula foi produzida e o Ciclo não registrou falha"
    return (
        ", ".join(motivo.value for motivo in laudo.motivos) or "reprovada sem motivo registrado"
    )


def _pendencias(celulas: list[HistoricoCelula]) -> list[Pendencia]:
    return [
        Pendencia(
            fila=FilaHumana.H4_REVISAO,
            audiencia=historico.audiencia,
            formato=historico.formato,
            motivo=motivo_da_pendencia(historico),
        )
        for historico in celulas
        if historico.destino_final is Destino.REPROVADO_REVISAO_HUMANA
    ]


def _respostas_prontas_da_ata(identificador: str) -> Path | None:
    """Sem arquivo, o ``ProvedorFalso`` nasce vazio e o ``FilaVazia`` diz o que falta."""
    caminho = PASTA_RESPOSTAS_PRONTAS / f"{identificador}.json"
    if caminho.exists():
        return caminho
    _registro.warning("sem respostas prontas em %s: a demo vai parar em FilaVazia", caminho)
    return None


NOME_DE_PASTA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
"""O identificador vira nome de pasta: nada de barra, de ``..`` nem de nome vazio."""


def _identificador_estavel(bruto: str) -> str:
    """Recusa cedo o que quebraria ``carregar_execucao`` ou escaparia da pasta."""
    nome = bruto.strip()
    if not NOME_DE_PASTA.match(nome):
        raise ValueError(
            f"identificador {bruto!r} não serve como nome de pasta: use letras, dígitos, "
            "ponto, hífen e sublinhado, começando por letra ou dígito"
        )
    return nome


def _posicoes_do_pedido(
    pedido: Sequence[tuple[Audiencia, Formato]] | None,
) -> tuple[tuple[Audiencia, Formato], ...]:
    """Sem pedido valem as nove. Vazio ou repetido é recusado antes de qualquer chamada."""
    if pedido is None:
        return MATRIZ
    if len(pedido) == 0:
        raise ValueError("o pedido está vazio: escolha ao menos uma Célula")
    if len(set(pedido)) != len(pedido):
        raise ValueError("o pedido tem posição repetida")
    escolhidas = set(pedido)
    return tuple(posicao for posicao in MATRIZ if posicao in escolhidas)


def _avisar_fase(
    ao_mudar_fase: Callable[[FaseDaExecucao], None] | None, fase: FaseDaExecucao
) -> None:
    """Quem escuta é a tela; um aviso que quebra nunca derruba a execução."""
    if ao_mudar_fase is None:
        return
    try:
        ao_mudar_fase(fase)
    except Exception:  # noqa: BLE001 - o aviso é de cortesia
        _registro.exception("aviso de fase falhou em %s", fase)


def executar(
    caminho_ata: Path | Sequence[Path],
    provedor: str,
    pasta_execucoes: Path,
    *,
    jev: bool | None = None,
    fidelidade: bool | None = None,
    identificador: str | None = None,
    pedido: Sequence[tuple[Audiencia, Formato]] | None = None,
    nome: str | None = None,
    ao_mudar_fase: Callable[[FaseDaExecucao], None] | None = None,
    ao_andar: Andou | None = None,
    duracao: DuracaoDoVideo = DuracaoDoVideo.S60,
    composicao_visual: ComposicaoCarrossel | None = None,
    referencia_visual: str | None = None,
) -> Execucao:
    """A execução ponta a ponta de uma Ata, gravada em disco no fim (ADR 0001, 0006).

    ``identificador`` fixa o nome da pasta em vez do padrão
    ``<ata>-<provedor>-<AAAAMMDD-HHMMSS>``. É o que dá nome estável à demo versionada em
    ``data/execucoes/``, que a interface, o pytest e o relatório leem pelo mesmo caminho —
    com o carimbo de hora, cada regeneração criaria uma pasta nova e o link mudaria.
    Rodar de novo com o mesmo identificador **sobrescreve** o ``execucao.json`` e os
    ``.md``: é regeneração da demo, não uma segunda execução.

    ``caminho_ata`` pode ser uma lista de 2 a 5 caminhos: é a Visão unida, um só conteúdo que
    junta as Atas, com as Âncoras prefixadas por parte (``a1_``, ``a2_``…).

    ``pedido`` escolhe quais Células gerar (de uma a nove; sem ele, as nove). Com menos de
    duas, a avaliação da Matriz e o Judge não rodam: coerência entre Células pede ao menos
    duas. ``nome`` é o rótulo de tela; vazio vira o identificador. ``ao_mudar_fase`` e
    ``ao_andar`` são os avisos de andamento que a API grava em ``andamento.json`` (ADR 0017).
    ``jev`` é ``None`` por padrão e então a Qualidade (ADR 0035) está ligada, se houver a chave do Jev;
    ``jev=False`` a desliga.
    ``fidelidade`` liga o checador de fidelidade à Ata (ADR 0036); ``None`` obedece a
    ``SUNO_FIDELIDADE``, que nasce desligado.
    ``duracao`` é a duração que a pessoa escolheu para o Roteiro (40s a 3m); as outras duas
    formas não a leem.
    """
    iniciada_em = datetime.now(timezone.utc)
    relogio = time.perf_counter()
    nome_da_pasta = _identificador_estavel(identificador) if identificador is not None else None
    posicoes = _posicoes_do_pedido(pedido)

    caminhos = (
        [Path(caminho_ata)]
        if isinstance(caminho_ata, (str, Path))
        else [Path(caminho) for caminho in caminho_ata]
    )
    atas = [carregar_ata(caminho) for caminho in caminhos]
    unida = len(atas) > 1
    ata = compor_uniao(atas) if unida else atas[0]
    prontas = _respostas_prontas_da_ata(ata.identificador) if provedor == "falso" else None
    contado = ProvedorContado(provedor_por_nome(provedor, respostas_prontas=prontas))

    _avisar_fase(ao_mudar_fase, FaseDaExecucao.EXTRAINDO_ANCORAS)
    curador = AgenteCurador(contado)
    dossie = replace(
        curador.preparar_uniao(atas) if unida else curador.preparar(ata), duracao=duracao
    )
    # Com provedor real o Jev não pode ficar de fora em silêncio: sem chave, a execução para.
    qualidade = _qualidade_de_ambiente(ligado=jev, exigir=provedor != "falso")
    verificador = _fidelidade_de_ambiente(ata.texto, ligado=fidelidade)
    _avisar_fase(ao_mudar_fase, FaseDaExecucao.GERANDO_CELULAS)
    celulas = gerar_matriz_do_dossie(
        dossie,
        contado,
        qualidade=qualidade,
        fidelidade=verificador,
        posicoes=posicoes,
        ao_andar=ao_andar,
    )
    avaliacao_transversal = None
    if len(posicoes) >= 2:
        _avisar_fase(ao_mudar_fase, FaseDaExecucao.AVALIANDO_MATRIZ)
        avaliacao_transversal = avaliar_matriz(celulas, dossie.ancoras, posicoes=posicoes)
    _avisar_fase(ao_mudar_fase, FaseDaExecucao.GRAVANDO)

    concluida_em = datetime.now(timezone.utc)
    padrao = f"{ata.identificador}-{provedor}-{iniciada_em.strftime('%Y%m%d-%H%M%S')}"
    execucao = Execucao(
        identificador=nome_da_pasta if nome_da_pasta is not None else padrao,
        nome=nome or "",
        pedido=[PosicaoDaMatriz(audiencia=a, formato=f) for a, f in posicoes],
        categoria=ata.categoria,
        composicao_visual=composicao_visual,
        referencia_visual=referencia_visual,
        ata=ata.identificador,
        provedor_gerador=provedor,
        iniciada_em=iniciada_em,
        concluida_em=concluida_em,
        selecao=dossie.selecao,
        ancoras=dossie.ancoras,
        celulas=celulas,
        pendencias=_pendencias(celulas),
        custo=contado.custo(time.perf_counter() - relogio),
        avaliacao_transversal=avaliacao_transversal,
    )
    gravar_execucao(execucao, Path(pasta_execucoes))
    return execucao


# ---------------------------------------------------------------------------
# Disco
# ---------------------------------------------------------------------------


def _markdown_da_celula(historico: HistoricoCelula) -> str:
    """O texto final de uma Célula, legível por humano. Conveniência; o JSON é a origem."""
    celula = historico.celula_final
    cabecalho = [
        f"<!-- {historico.audiencia.value} × {historico.formato.value} -->",
        f"<!-- destino: {historico.destino_final.value} · rodadas: {len(historico.tentativas)} -->",
        "",
    ]
    if celula is None:
        return "\n".join([*cabecalho, "_Nenhuma Célula foi produzida._", ""])

    conteudo = celula.conteudo
    if conteudo.texto is not None:
        corpo = [conteudo.texto]
    elif conteudo.slides is not None:
        corpo = []
        for numero, slide in enumerate(conteudo.slides, start=1):
            corpo.append(f"## Slide {numero} — {slide.titulo}\n\n{slide.corpo}\n")
            if slide.dado:
                corpo.append(f"_dado a plotar: {slide.dado}_\n")
    else:
        corpo = [
            f"**{bloco.inicio_s:.0f}s–{bloco.fim_s:.0f}s** — {bloco.fala}\n\n_tela: {bloco.tela}_\n"
            for bloco in conteudo.blocos or []
        ]
    return "\n".join([*cabecalho, *corpo, ""])


def gravar_execucao(execucao: Execucao, pasta_execucoes: Path) -> Path:
    """Grava ``<pasta>/<id>/execucao.json`` e os ``.md`` de leitura. Devolve o JSON."""
    raiz = Path(pasta_execucoes) / execucao.identificador
    raiz.mkdir(parents=True, exist_ok=True)
    arquivo = raiz / ARQUIVO_DA_EXECUCAO
    arquivo.write_text(execucao.model_dump_json(indent=2), encoding="utf-8")

    pasta_celulas = raiz / PASTA_DAS_CELULAS
    pasta_celulas.mkdir(exist_ok=True)
    for historico in execucao.celulas:
        nome = f"{historico.audiencia.value}-{historico.formato.value}.md"
        (pasta_celulas / nome).write_text(_markdown_da_celula(historico), encoding="utf-8")
    return arquivo


def carregar_execucao(identificador: str, pasta_execucoes: Path) -> Execucao:
    """Lê de volta o que ``gravar_execucao`` escreveu."""
    arquivo = Path(pasta_execucoes) / identificador / ARQUIVO_DA_EXECUCAO
    return Execucao.model_validate_json(arquivo.read_text(encoding="utf-8"))


def listar_execucoes(pasta_execucoes: Path) -> list[str]:
    """Os identificadores gravados nesta pasta, em ordem estável."""
    raiz = Path(pasta_execucoes)
    if not raiz.exists():
        return []
    return sorted(
        caminho.name for caminho in raiz.iterdir() if (caminho / ARQUIVO_DA_EXECUCAO).exists()
    )
