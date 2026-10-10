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
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from suno.dominio import (
    MATRIZ,
    Custo,
    Destino,
    EstadoAvaliacaoTransversal,
    Execucao,
    FilaHumana,
    HistoricoCelula,
    Pendencia,
    PedidoLLM,
    ResultadoCicloTransversal,
    RespostaLLM,
)
from suno.gerador.curador import AgenteCurador
from suno.gerador.matriz import gerar_matriz_do_dossie
from suno.gerador.orquestracao import rodar_ciclo_transversal
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


def _comite_de_ambiente(provedor_gerador: str, *, ligado: bool):
    """``ligado`` vem da linha de comando e sobrepõe ``SUNO_COMITE`` (ADR 0008).

    Comitê ausente é um Laudo sem comitê, nunca um Laudo pior: se ele não puder ser montado,
    ``de_ambiente`` já explica no log e devolve ``None``, e a execução segue.
    """
    try:
        from suno.comite import Comite

        return Comite.de_ambiente(provedor_gerador, ligado=ligado)
    except (ImportError, AttributeError, NotImplementedError) as erro:
        _registro.warning("comitê pedido mas indisponível, seguindo sem ele: %s", erro)
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


def _pendencias_transversais(ciclo: ResultadoCicloTransversal) -> list[Pendencia]:
    """Problema do Judge entra na H4 por Célula, sem duplicar falha determinística."""
    if ciclo.estado is EstadoAvaliacaoTransversal.APROVADA:
        return []
    if ciclo.avaliacao_deterministica.estado is not EstadoAvaliacaoTransversal.APROVADA:
        return []

    ultimo = ciclo.julgamentos[-1] if ciclo.julgamentos else None
    posicoes = (
        {(problema.audiencia, problema.formato) for problema in ultimo.problemas}
        if ultimo is not None and ultimo.problemas
        else set(MATRIZ)
    )
    return [
        Pendencia(
            fila=FilaHumana.H4_REVISAO,
            audiencia=audiencia,
            formato=formato,
            motivo=ciclo.motivo_final,
        )
        for audiencia, formato in MATRIZ
        if (audiencia, formato) in posicoes
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


def executar(
    caminho_ata: Path,
    provedor: str,
    pasta_execucoes: Path,
    *,
    comite: bool = False,
    identificador: str | None = None,
) -> Execucao:
    """A execução ponta a ponta de uma Ata, gravada em disco no fim (ADR 0001, 0006).

    ``identificador`` fixa o nome da pasta em vez do padrão
    ``<ata>-<provedor>-<AAAAMMDD-HHMMSS>``. É o que dá nome estável à demo versionada em
    ``data/execucoes/``, que a interface, o pytest e o relatório leem pelo mesmo caminho —
    com o carimbo de hora, cada regeneração criaria uma pasta nova e o link mudaria.
    Rodar de novo com o mesmo identificador **sobrescreve** o ``execucao.json`` e os
    ``.md``: é regeneração da demo, não uma segunda execução.
    """
    iniciada_em = datetime.now(timezone.utc)
    relogio = time.perf_counter()
    nome = _identificador_estavel(identificador) if identificador is not None else None

    ata = carregar_ata(Path(caminho_ata))
    prontas = _respostas_prontas_da_ata(ata.identificador) if provedor == "falso" else None
    contado = ProvedorContado(provedor_por_nome(provedor, respostas_prontas=prontas))

    dossie = AgenteCurador(contado).preparar(ata)
    juizes = _comite_de_ambiente(contado.nome, ligado=comite)
    celulas = gerar_matriz_do_dossie(dossie, contado, comite=juizes)
    celulas, ciclo_transversal = rodar_ciclo_transversal(
        dossie, celulas, contado, comite=juizes
    )
    avaliacao_transversal = ciclo_transversal.avaliacao_deterministica

    concluida_em = datetime.now(timezone.utc)
    padrao = f"{ata.identificador}-{provedor}-{iniciada_em.strftime('%Y%m%d-%H%M%S')}"
    execucao = Execucao(
        identificador=nome if nome is not None else padrao,
        ata=ata.identificador,
        provedor_gerador=provedor,
        iniciada_em=iniciada_em,
        concluida_em=concluida_em,
        selecao=dossie.selecao,
        ancoras=dossie.ancoras,
        celulas=celulas,
        pendencias=[*_pendencias(celulas), *_pendencias_transversais(ciclo_transversal)],
        custo=contado.custo(time.perf_counter() - relogio),
        comite_ligado=juizes is not None,
        avaliacao_transversal=avaliacao_transversal,
        ciclo_transversal=ciclo_transversal,
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
