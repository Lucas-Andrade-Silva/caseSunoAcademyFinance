"""Comitê de juízes-LLM: um juiz por dimensão subjetiva (tom, clareza, coerência), dois
provedores, nunca o do Gerador. Só Texto analítico e Carrossel. Nasce desligado.

ADR 0008.

O que este módulo garante, e que ninguém deve relaxar sem reabrir o ADR:

- **Seis chamadas por Célula**, sempre: 3 dimensões × 2 juízes. Discordância não paga uma
  terceira chamada — vira ``REVISAO_HUMANA`` naquela dimensão, porque discordância é
  informação, não impasse a resolver automaticamente.
- **O juiz nunca é o provedor que gerou o texto** (autopreferência), e **o prompt nunca diz
  quem gerou** (viés de reputação). A primeira regra é um ``ValueError`` no construtor; a
  segunda é a ausência de qualquer nome de provedor nas rubricas.
- **O comitê não aprova nem reprova.** ``ResultadoComite`` entra no Laudo como informação;
  o veredito continua saindo das cinco medidas determinísticas.
- **Resposta fora do schema não vira nota.** A dimensão sai ausente com o voto que houver —
  nunca nota zero, nunca nota inventada. Falha de provedor e cota esgotada sobem para quem
  chamou: o Laudo decide sair sem comitê.
"""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field

from suno.comite.rubricas import rubrica
from suno.dominio import (
    Audiencia,
    Conteudo,
    DimensaoSubjetiva,
    ErroProvedor,
    EstadoMedida,
    Formato,
    JulgamentoDimensao,
    Mensagem,
    PapelLLM,
    PedidoLLM,
    RespostaMalformada,
    ResultadoComite,
    VotoJuiz,
)
from suno.provedores.base import Provedor
from suno.provedores.roteador import CONFIGURACAO, ORDEM_POR_PAPEL, roteador_para

_REGISTRO = logging.getLogger(__name__)

VARIAVEL_DO_COMITE = "SUNO_COMITE"
"""``1`` liga o comitê; ``0`` ou ausente o mantém desligado, que é o padrão da demo.

O argumento ``ligado`` de ``Comite.de_ambiente`` sobrepõe esta variável, nos dois sentidos:
é por aí que ``--comite`` na linha de comando liga o comitê sem exportar nada.
"""

FORMATOS_JULGADOS: tuple[Formato, ...] = (Formato.TEXTO_ANALITICO, Formato.CARROSSEL)
"""O Roteiro não passa pelo comitê: é a entrada do vídeo, primeiro item da ordem de corte."""

DIFERENCA_QUE_AINDA_E_CONSENSO = 1
"""Duas notas a um ponto de distância viram consenso; duas ou mais vão ao desempate humano."""

TETO_DE_TOKENS_DO_JUIZ = 400
"""Nota e uma frase de justificativa cabem folgado. Teto baixo pede esforço de raciocínio baixo."""

TEMPERATURA_DO_JUIZ = 0.0
"""Julgamento não é criação: a mesma Célula deve tender à mesma nota."""


class NotaDoJuiz(BaseModel):
    """A resposta estruturada de um juiz. O schema viaja no pedido (ADR 0007)."""

    nota: int = Field(ge=1, le=5, description="1 a 5, pela escala da rubrica da dimensão.")
    justificativa: str = Field(description="Uma frase curta citando o que sustenta a nota.")


class Comite:
    """Dois juízes em provedores distintos, um julgamento isolado por dimensão."""

    def __init__(
        self,
        juizes: tuple[Provedor, Provedor],
        provedor_gerador: str | None = None,
    ) -> None:
        nomes = [juiz.nome for juiz in juizes]
        if provedor_gerador is not None and provedor_gerador in nomes:
            raise ValueError(
                f"o juiz não pode ser o provedor que gerou a Célula ({provedor_gerador!r}): "
                "é autopreferência (ADR 0008)"
            )
        if nomes[0] == nomes[1]:
            raise ValueError(
                f"os dois juízes precisam ser provedores distintos, e ambos são {nomes[0]!r} "
                "(ADR 0008)"
            )
        self.juizes = juizes
        self.provedor_gerador = provedor_gerador

    # -- o julgamento -------------------------------------------------------

    def julgar(self, conteudo: Conteudo, audiencia: Audiencia) -> ResultadoComite | None:
        """None para o Roteiro: ele não passa pelo comitê."""
        if conteudo.formato not in FORMATOS_JULGADOS:
            return None
        texto = conteudo.texto_avaliavel()
        dimensoes = [
            self._julgar_dimensao(dimensao, texto, conteudo.formato, audiencia)
            for dimensao in DimensaoSubjetiva
        ]
        return ResultadoComite(
            dimensoes=dimensoes,
            provedores=[juiz.nome for juiz in self.juizes],
        )

    def _julgar_dimensao(
        self,
        dimensao: DimensaoSubjetiva,
        texto: str,
        formato: Formato,
        audiencia: Audiencia,
    ) -> JulgamentoDimensao:
        votos = [
            voto
            for juiz in self.juizes
            if (voto := self._votar(juiz, dimensao, texto, formato, audiencia)) is not None
        ]
        if len(votos) < 2:
            # Um juiz mudo ou fora do schema: ausente, com o voto que existir. Nunca zero.
            return JulgamentoDimensao(
                dimensao=dimensao, estado=EstadoMedida.AUSENTE, votos=votos, consenso=None
            )
        if abs(votos[0].nota - votos[1].nota) > DIFERENCA_QUE_AINDA_E_CONSENSO:
            # Discordância é informação: vai ao desempate humano (H3), sem terceira chamada.
            return JulgamentoDimensao(
                dimensao=dimensao,
                estado=EstadoMedida.REVISAO_HUMANA,
                votos=votos,
                consenso=None,
            )
        return JulgamentoDimensao(
            dimensao=dimensao,
            estado=EstadoMedida.MEDIDA,
            votos=votos,
            consenso=round((votos[0].nota + votos[1].nota) / 2),
        )

    def _votar(
        self,
        juiz: Provedor,
        dimensao: DimensaoSubjetiva,
        texto: str,
        formato: Formato,
        audiencia: Audiencia,
    ) -> VotoJuiz | None:
        """Uma chamada. ``None`` quando a resposta não bate com o schema."""
        pedido = self._pedido(dimensao, texto, formato, audiencia)
        try:
            resposta = juiz.completar_estruturado(pedido, NotaDoJuiz)
        except RespostaMalformada as erro:
            _REGISTRO.warning("juiz %s não respondeu no schema em %s: %s", juiz.nome, dimensao, erro)
            return None
        return VotoJuiz(
            dimensao=dimensao,
            nota=resposta.nota,
            justificativa=resposta.justificativa,
            provedor=juiz.nome,
        )

    def _pedido(
        self,
        dimensao: DimensaoSubjetiva,
        texto: str,
        formato: Formato,
        audiencia: Audiencia,
    ) -> PedidoLLM:
        """As mensagens do juiz. Nenhuma delas diz qual provedor ou modelo gerou o texto."""
        return PedidoLLM(
            papel=PapelLLM.JUIZ,
            rotulo=f"juiz:{dimensao}:{audiencia}:{formato}",
            mensagens=[
                Mensagem(autor="sistema", texto=rubrica(dimensao)),
                Mensagem(
                    autor="usuario",
                    texto=(
                        f"Audiência a que o texto se destina: {audiencia}.\n"
                        f"Formato: {formato}.\n\n"
                        f"Texto a julgar:\n{texto}"
                    ),
                ),
            ],
            max_tokens=TETO_DE_TOKENS_DO_JUIZ,
            temperatura=TEMPERATURA_DO_JUIZ,
            esforco_raciocinio="baixo",
        )

    # -- montagem a partir do ambiente --------------------------------------

    @classmethod
    def de_ambiente(
        cls,
        provedor_gerador: str,
        *,
        ligado: bool | None = None,
    ) -> "Comite | None":
        """Monta o comitê se ele estiver pedido, ou devolve ``None`` dizendo por quê.

        ``ligado=True`` e ``ligado=False`` sobrepõem a variável de ambiente — é por aí que a
        linha de comando liga o comitê com ``--comite`` sem exportar nada. ``ligado=None``, o
        padrão, obedece a ``SUNO_COMITE``: ``1`` liga, qualquer outra coisa (ou a ausência da
        variável) mantém desligado.

        Devolve ``None`` — com um aviso no log que nomeia as variáveis de ambiente que
        faltam — quando não sobram dois provedores distintos fora do que gerou a Célula.
        Comitê ausente é um Laudo sem comitê, não um Laudo pior (ADR 0008).
        """
        if not _esta_pedido(ligado):
            return None
        try:
            roteador = roteador_para(PapelLLM.JUIZ, excluir=(provedor_gerador,))
        except ErroProvedor as erro:
            _REGISTRO.warning(
                "comitê pedido mas não montado (%s). Falta preencher no .env: %s (ADR 0008)",
                erro,
                _variaveis_que_faltam(provedor_gerador),
            )
            return None

        # O roteador devolve um provedor só; o comitê precisa de dois nomes distintos, então
        # pega dois concretos da fila que ele montou na ordem do papel de juiz.
        distintos: list[Provedor] = []
        vistos: set[str] = set()
        for candidato in getattr(roteador, "provedores", [roteador]):
            if candidato.nome == provedor_gerador or candidato.nome in vistos:
                continue
            vistos.add(candidato.nome)
            distintos.append(candidato)
        if len(distintos) < 2:
            _REGISTRO.warning(
                "comitê pedido mas não montado: o papel de juiz precisa de dois provedores "
                "distintos fora de %r e o ambiente ofereceu %d (%s). Falta preencher no "
                ".env: %s (ADR 0008)",
                provedor_gerador,
                len(distintos),
                ", ".join(sorted(vistos)) or "nenhum",
                _variaveis_que_faltam(provedor_gerador),
            )
            return None
        return cls((distintos[0], distintos[1]), provedor_gerador)


# ---------------------------------------------------------------------------
# Ligar ou não ligar, e o que dizer quando não dá
# ---------------------------------------------------------------------------


def _esta_pedido(ligado: bool | None) -> bool:
    """O argumento manda; sem ele, manda ``SUNO_COMITE``. Na dúvida, desligado."""
    if ligado is not None:
        return ligado
    return os.environ.get(VARIAVEL_DO_COMITE, "0").strip() == "1"


def _variaveis_que_faltam(provedor_gerador: str) -> str:
    """As variáveis de ``.env`` que faltam para o papel de juiz ter dois provedores.

    Diz o nome exato de cada uma — chave **e** nome de modelo, porque o roteador exige as
    duas (ADR 0007) — e nunca cita as do provedor que gerou a Célula: ele está fora por
    princípio, não por falta de chave (ADR 0008).
    """
    ausentes = [
        variavel
        for nome in ORDEM_POR_PAPEL[PapelLLM.JUIZ]
        if nome != provedor_gerador
        for variavel in CONFIGURACAO[nome]
        if not os.environ.get(variavel)
    ]
    return ", ".join(ausentes) if ausentes else "nada (as chaves estão no lugar)"


__all__ = ["Comite", "NotaDoJuiz", "VARIAVEL_DO_COMITE"]
