"""A linguagem do projeto em modelos Pydantic fechados.

Os nomes vêm do CONTEXT.md. Nenhuma palavra da lista _Avoid_ entra em nome de classe,
campo ou valor enumerado. Este arquivo é o contrato entre todos os módulos:

- ADR 0001: ``(Conteúdo, Âncora[], Audiência) → Laudo`` é tudo o que atravessa a costura
  entre Gerador e Avaliador.
- ADR 0008: o comitê de juízes-LLM nasce desligado; Laudo sem comitê tem o campo
  ausente, nunca nota zero. ``revisão humana`` é um terceiro estado de medida.
- ADR 0011: as Âncoras numéricas são a única origem de número do sistema.
- ADR 0013: o Laudo tem três destinos e o motivo de reprovação é enumerado.
- ADR 0014: a conferência visual do Pacote não entra no Laudo e não reprova a Célula.

Ninguém renomeia modelo daqui sem atualizar o CONTEXT.md e avisar o coordenador.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

CaminhoPortavel = Annotated[
    Path,
    PlainSerializer(lambda p: p.as_posix(), return_type=str, when_used="json"),
]
"""Um Path que sempre serializa com `/`, nunca `\\`: execucao.json e pacote.json são lidos por
Windows, Linux e pelo navegador (via API), e um caminho gravado com barra invertida numa máquina
Windows quebraria em qualquer outra."""

# ---------------------------------------------------------------------------
# A Matriz: Audiência × Formato
# ---------------------------------------------------------------------------


class Audiencia(StrEnum):
    """O nível de sofisticação do leitor a quem uma Célula se destina."""

    INICIANTE = "iniciante"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"


class Formato(StrEnum):
    """A forma que uma Célula assume."""

    TEXTO_ANALITICO = "texto_analitico"
    CARROSSEL = "carrossel"
    ROTEIRO = "roteiro"


MATRIZ: tuple[tuple[Audiencia, Formato], ...] = tuple(
    (audiencia, formato) for audiencia in Audiencia for formato in Formato
)
"""As nove combinações. A ordem é estável e é a ordem de gravação em disco."""


class ModoSelecao(StrEnum):
    """Como os itens aprovados pela curadoria humana alimentam a Matriz."""

    UNIDA = "unida"
    SEPARADA = "separada"


class SelecaoCuradoria(BaseModel):
    """Regra determinística da seleção: unida aceita vários itens; separada, um."""

    modo: ModoSelecao
    itens: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _quantidade_conforme_modo(self) -> SelecaoCuradoria:
        if any(not item.strip() for item in self.itens):
            raise ValueError("a seleção não aceita identificador vazio")
        if len(set(self.itens)) != len(self.itens):
            raise ValueError("a seleção não aceita item repetido")
        if self.modo is ModoSelecao.SEPARADA and len(self.itens) != 1:
            raise ValueError("a seleção separada exige exatamente um item")
        return self


# ---------------------------------------------------------------------------
# A Ata
# ---------------------------------------------------------------------------


class Ata(BaseModel):
    """O comunicado financeiro público que entra no sistema (ADR 0006)."""

    model_config = ConfigDict(frozen=True)

    identificador: str = Field(
        description="Nome estável do arquivo em data/atas/, ex. 'copom-280-2026-08-05'."
    )
    titulo: str
    reuniao: int | None = Field(default=None, description="Número da reunião do Copom.")
    data_referencia: date
    origem_url: str | None = Field(
        default=None, description="URL de onde o arquivo foi buscado, quando foi."
    )
    arquivo: CaminhoPortavel | None = Field(default=None, description="Caminho local do arquivo original.")
    texto: str = Field(description="Texto já extraído; é o que o Gerador lê.")
    idioma: Literal["pt", "en"] = "pt"


# ---------------------------------------------------------------------------
# As Âncoras (ADR 0011)
# ---------------------------------------------------------------------------


class Unidade(StrEnum):
    """Unidade de uma Âncora numérica. ``p.p.`` ≠ ``%`` e ambos ≠ ``pb`` (pesquisa §3)."""

    PERCENTUAL_AO_ANO = "% a.a."
    PERCENTUAL = "%"
    PONTO_PERCENTUAL = "p.p."
    PONTOS_BASE = "pb"
    VOTOS = "votos"
    DATA = "data"
    REAIS = "R$"
    NUMERO = "numero"


class ChaveAncora(StrEnum):
    """Chaves canônicas das Âncoras numéricas que uma Ata do Copom deve ter.

    A integridade da extração (ADR 0013) é medida pela presença das chaves marcadas como
    essenciais em ``CHAVES_ESSENCIAIS``. Chaves fora deste enum são permitidas como texto
    livre no campo ``chave``, mas não contam para integridade.
    """

    SELIC_DECIDIDA = "selic_decidida"
    SELIC_ANTERIOR = "selic_anterior"
    VARIACAO_PB = "variacao_pb"
    PLACAR_VOTACAO = "placar_votacao"
    DATA_REUNIAO = "data_reuniao"
    DATA_PROXIMA_REUNIAO = "data_proxima_reuniao"
    IPCA_PROJECAO_ANO_CORRENTE = "ipca_projecao_ano_corrente"
    IPCA_PROJECAO_ANO_SEGUINTE = "ipca_projecao_ano_seguinte"
    ALVO_INFLACAO = "alvo_inflacao"
    NUMERO_REUNIAO = "numero_reuniao"


CHAVES_ESSENCIAIS: frozenset[str] = frozenset(
    {
        ChaveAncora.SELIC_DECIDIDA,
        ChaveAncora.DATA_REUNIAO,
        ChaveAncora.PLACAR_VOTACAO,
    }
)
"""Sem estas, a extração está degradada e a Célula reprova por ``falha de extração``."""


class AncoraNumerica(BaseModel):
    """Um número da Ata, com valor, unidade e o trecho literal de onde veio.

    O Gerador copia ``valor_literal`` para dentro da Célula; o Avaliador confere por
    igualdade exata de valor e unidade. Nunca é reescrito por LLM.
    """

    model_config = ConfigDict(frozen=True)

    chave: str = Field(description="Chave canônica (ver ChaveAncora) ou livre.")
    rotulo: str = Field(description="Como um humano chamaria: 'Selic decidida'.")
    valor_literal: str = Field(
        description="Exatamente como a Ata escreve: '14,00', '7 a 0', '4 e 5 de agosto de 2026'."
    )
    valor: float | None = Field(
        default=None, description="Valor numérico normalizado, quando faz sentido."
    )
    unidade: Unidade
    trecho: str = Field(description="A frase literal da Ata onde o número aparece.")
    data_iso: date | None = Field(default=None, description="Para unidade DATA.")
    qualificador: str | None = Field(
        default=None,
        description="O que distingue 'CDI+2%' ('CDI+') de '110% do CDI' ('do CDI'); None na maioria.",
    )

    def citacao(self) -> str:
        """A forma canônica de citar a Âncora dentro de uma Célula."""
        if self.unidade in (Unidade.DATA, Unidade.VOTOS, Unidade.NUMERO):
            return self.valor_literal
        if self.unidade is Unidade.REAIS:
            return f"R$ {self.valor_literal}"
        if self.unidade is Unidade.PERCENTUAL:
            if self.qualificador and self.qualificador.endswith("+"):
                return f"{self.qualificador}{self.valor_literal}%"
            if self.qualificador:
                return f"{self.valor_literal}% {self.qualificador}"
            return f"{self.valor_literal}%"
        if self.unidade is Unidade.PERCENTUAL_AO_ANO:
            return f"{self.valor_literal}% a.a."  # como a Ata escreve: sem espaço antes do %
        return f"{self.valor_literal} {self.unidade}"


class AncoraTextual(BaseModel):
    """Uma afirmação factual em prosa, contra a qual a Aderência textual é medida."""

    model_config = ConfigDict(frozen=True)

    identificador: str = Field(description="Ex. 'decisao', 'balanco_de_riscos_1'.")
    afirmacao: str = Field(description="A afirmação, em uma frase, nas palavras da Ata.")
    trecho: str = Field(description="O trecho literal da Ata que a sustenta.")


Ancora: TypeAlias = AncoraNumerica | AncoraTextual
"""O ``Âncora[]`` do ADR 0001 é ``Sequence[Ancora]``."""


class Ancoras(BaseModel):
    """O resultado do estágio de extração: roda uma vez por Ata, antes da Matriz."""

    ata: str = Field(description="Identificador da Ata de origem.")
    numericas: list[AncoraNumerica] = Field(default_factory=list)
    textuais: list[AncoraTextual] = Field(default_factory=list)
    extraida_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def todas(self) -> list[Ancora]:
        return [*self.numericas, *self.textuais]

    def numerica(self, chave: str) -> AncoraNumerica | None:
        for ancora in self.numericas:
            if ancora.chave == chave:
                return ancora
        return None

    def chaves_faltantes(self) -> frozenset[str]:
        presentes = {a.chave for a in self.numericas}
        return frozenset(CHAVES_ESSENCIAIS - presentes)


# ---------------------------------------------------------------------------
# O Conteúdo de uma Célula
# ---------------------------------------------------------------------------


class Slide(BaseModel):
    """Um registro do roteiro de slides do Carrossel. O Avaliador julga o texto, não a imagem."""

    titulo: str
    corpo: str
    dado: str | None = Field(
        default=None,
        description="Chave da Âncora numérica a plotar neste slide, se houver (ADR 0009).",
    )


class BlocoFala(BaseModel):
    """Um bloco de fala cronometrada do Roteiro. O primeiro bloco é o gancho."""

    inicio_s: float = Field(ge=0)
    fim_s: float = Field(gt=0)
    fala: str = Field(description="O que é dito. Os Limiares de Flesch-BR valem sobre isto.")
    tela: str = Field(default="", description="Rubrica de cena: o que aparece na tela.")

    @model_validator(mode="after")
    def _fim_depois_do_inicio(self) -> BlocoFala:
        if self.fim_s <= self.inicio_s:
            raise ValueError("fim_s precisa ser maior que inicio_s")
        return self


class Conteudo(BaseModel):
    """O texto de uma Célula, num dos três Formatos.

    Exatamente um dos três campos de corpo é preenchido, conforme ``formato``.
    ``texto_avaliavel()`` devolve a prosa que as métricas medem: para o Roteiro só a fala,
    nunca a rubrica de cena; para o Carrossel, título e corpo de cada slide.
    """

    formato: Formato
    texto: str | None = Field(default=None, description="Texto analítico, em Markdown.")
    slides: list[Slide] | None = None
    blocos: list[BlocoFala] | None = None
    ancoras_citadas: list[str] = Field(
        default_factory=list,
        description="Chaves das Âncoras numéricas preenchidas em molde nesta Célula.",
    )

    @model_validator(mode="after")
    def _corpo_conforme_formato(self) -> Conteudo:
        esperado = {
            Formato.TEXTO_ANALITICO: self.texto is not None,
            Formato.CARROSSEL: self.slides is not None,
            Formato.ROTEIRO: self.blocos is not None,
        }
        if not esperado[self.formato]:
            raise ValueError(f"Conteúdo no Formato {self.formato} está sem corpo")
        return self

    def texto_avaliavel(self) -> str:
        if self.formato is Formato.TEXTO_ANALITICO:
            return self.texto or ""
        if self.formato is Formato.CARROSSEL:
            return "\n\n".join(f"{s.titulo}\n{s.corpo}" for s in self.slides or [])
        return "\n".join(b.fala for b in self.blocos or [])

    def texto_de_conferencia(self) -> str:
        """O texto sobre o qual Aderência e Recomendação são medidas.

        Igual a ``texto_avaliavel()``, mais a rubrica de cena (``tela``) do Roteiro: ela é
        pintada como o texto maior de cada quadro do vídeo e mostrada na interface, então um
        número ou uma Recomendação ali é tão real quanto na fala — o ADR 0011 não abre exceção
        para um segundo caminho de número, e a linha do CLAUDE.md não abre exceção nenhuma.
        Flesch-BR e Densidade continuam sobre ``texto_avaliavel()`` só: a rubrica não é lida em
        voz alta nem julgada por Audiência (ARQUITETURA.md).
        """
        base = self.texto_avaliavel()
        if self.formato is not Formato.ROTEIRO:
            return base
        rubricas = "\n".join(b.tela for b in self.blocos or [] if b.tela)
        return f"{base}\n{rubricas}" if rubricas else base


class Celula(BaseModel):
    """Uma saída concreta: uma Audiência num Formato, numa rodada do Ciclo de correção."""

    audiencia: Audiencia
    formato: Formato
    conteudo: Conteudo
    rodada: int = Field(default=0, ge=0, le=2, description="0 = original; 1 e 2 = correções.")
    gerada_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provedor: str | None = Field(default=None, description="Qual provedor gerou; nunca vai ao juiz.")

    @model_validator(mode="after")
    def _formato_coerente(self) -> Celula:
        if self.conteudo.formato is not self.formato:
            raise ValueError("o Formato da Célula e do seu Conteúdo divergem")
        return self


# ---------------------------------------------------------------------------
# Limiares (ADR 0002; H2)
# ---------------------------------------------------------------------------


class Faixa(BaseModel):
    """Intervalo fechado em ``minimo``, aberto em ``maximo``. ``None`` é sem limite daquele lado."""

    model_config = ConfigDict(frozen=True)

    minimo: float | None = None
    maximo: float | None = None

    def contem(self, valor: float) -> bool:
        if self.minimo is not None and valor < self.minimo:
            return False
        if self.maximo is not None and valor >= self.maximo:
            return False
        return True

    def distancia(self, valor: float) -> float:
        """Quanto falta para entrar na Faixa. Zero se já está dentro."""
        if self.minimo is not None and valor < self.minimo:
            return self.minimo - valor
        if self.maximo is not None and valor >= self.maximo:
            return valor - self.maximo
        return 0.0


class ExigenciaDeExplicacao(StrEnum):
    """O que a Densidade exige de um termo do Léxico na primeira ocorrência."""

    SEMPRE = "sempre"
    FORA_DO_NUCLEO = "fora_do_nucleo"
    NUNCA = "nunca"


class Limiares(BaseModel):
    """Os Limiares de uma Audiência. ``origem`` diz de onde vieram."""

    model_config = ConfigDict(frozen=True)

    audiencia: Audiencia
    flesch_br: Faixa
    explicacao: ExigenciaDeExplicacao
    densidade_minima: float | None = Field(
        default=None, description="Proporção mínima de termos do Léxico; None = sem exigência."
    )
    aderencia_minima: float = Field(default=1.0, ge=0, le=1)
    origem: str = Field(default="NILC, aguardando Calibração")


LIMIARES_PROVISORIOS: dict[Audiencia, Limiares] = {
    Audiencia.INICIANTE: Limiares(
        audiencia=Audiencia.INICIANTE,
        flesch_br=Faixa(minimo=50.0),
        explicacao=ExigenciaDeExplicacao.SEMPRE,
    ),
    Audiencia.INTERMEDIARIO: Limiares(
        audiencia=Audiencia.INTERMEDIARIO,
        flesch_br=Faixa(minimo=25.0, maximo=50.0),
        explicacao=ExigenciaDeExplicacao.FORA_DO_NUCLEO,
    ),
    Audiencia.AVANCADO: Limiares(
        audiencia=Audiencia.AVANCADO,
        flesch_br=Faixa(maximo=25.0),
        explicacao=ExigenciaDeExplicacao.NUNCA,
    ),
}
"""Faixas publicadas pelo NILC (ADR 0002). Marcadas como provisórias até a Calibração (H2)."""


# ---------------------------------------------------------------------------
# O Laudo (ADR 0001, 0008, 0013)
# ---------------------------------------------------------------------------


class Metrica(StrEnum):
    """As cinco medidas determinísticas."""

    FLESCH_BR = "flesch_br"
    DENSIDADE = "densidade"
    ADERENCIA = "aderencia"
    RECOMENDACAO = "recomendacao"
    INTEGRIDADE = "integridade"


class EstadoMedida(StrEnum):
    """Medida calculada, sem base para calcular, ou aguardando desempate humano (H3)."""

    MEDIDA = "medida"
    AUSENTE = "ausente"
    REVISAO_HUMANA = "revisao_humana"


class Medida(BaseModel):
    """Uma métrica medida numa Célula, com o Limiar aplicado e o que se observou."""

    metrica: Metrica
    estado: EstadoMedida = EstadoMedida.MEDIDA
    valor: float | None = Field(default=None, description="None quando ``estado`` é AUSENTE.")
    faixa: Faixa | None = Field(default=None, description="O Limiar aplicado, se houver.")
    atingiu: bool | None = Field(default=None, description="None quando não há base para julgar.")
    observacoes: list[str] = Field(
        default_factory=list,
        description="O que foi visto: termos sem explicação, números fora das Âncoras, a frase que recomenda.",
    )

    @model_validator(mode="after")
    def _ausente_sem_valor(self) -> Medida:
        if self.estado is EstadoMedida.AUSENTE and self.valor is not None:
            raise ValueError("Medida ausente não carrega valor; nunca sai como zero")
        return self


class MotivoReprovacao(StrEnum):
    """Enumerado, não texto livre: é o que permite contar reprovação por motivo (ADR 0013)."""

    FLESCH_BR = "flesch_br"
    DENSIDADE = "densidade"
    ADERENCIA = "aderencia"
    RECOMENDACAO = "recomendacao"
    FALHA_DE_EXTRACAO = "falha_de_extracao"


class Destino(StrEnum):
    """Os três destinos de um Laudo (ADR 0013)."""

    APROVADO = "aprovado"
    REPROVADO_CORRIGIVEL = "reprovado_corrigivel"
    REPROVADO_REVISAO_HUMANA = "reprovado_revisao_humana"


class Correcao(BaseModel):
    """O que precisa mudar, com o valor medido e a distância — nunca 'melhore o texto'."""

    metrica: Metrica
    valor_medido: float | None
    faixa: Faixa | None
    distancia: float | None = Field(default=None, description="Quanto falta para entrar na Faixa.")
    instrucao: str = Field(
        description="Ex.: 'Flesch-BR medido 47,2; o Limiar da Audiência Iniciante é 50.'"
    )


class DimensaoSubjetiva(StrEnum):
    """As dimensões que só o comitê julga (ADR 0008)."""

    TOM = "tom"
    CLAREZA = "clareza"
    COERENCIA = "coerencia"


class VotoJuiz(BaseModel):
    dimensao: DimensaoSubjetiva
    nota: int = Field(ge=1, le=5)
    justificativa: str
    provedor: str = Field(description="Qual provedor julgou. Nunca o que gerou a Célula.")


class JulgamentoDimensao(BaseModel):
    """Dois votos por dimensão. Discordância marca REVISAO_HUMANA (H3), sem terceira chamada."""

    dimensao: DimensaoSubjetiva
    estado: EstadoMedida
    votos: list[VotoJuiz] = Field(default_factory=list)
    consenso: int | None = Field(default=None, ge=1, le=5)


class ResultadoComite(BaseModel):
    """Presente no Laudo só quando o comitê rodou. Informação, nunca Limiar de aprovação."""

    dimensoes: list[JulgamentoDimensao]
    provedores: list[str] = Field(description="Os dois provedores usados, em ordem.")


class Laudo(BaseModel):
    """O resultado da avaliação de uma Célula: medidas, veredito e o que precisa mudar."""

    audiencia: Audiencia
    formato: Formato
    medidas: list[Medida]
    destino: Destino
    motivos: list[MotivoReprovacao] = Field(default_factory=list)
    correcoes: list[Correcao] = Field(default_factory=list)
    comite: ResultadoComite | None = Field(
        default=None, description="None = comitê desligado. Nunca nota zero (ADR 0008)."
    )
    avaliado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def medida(self, metrica: Metrica) -> Medida | None:
        for m in self.medidas:
            if m.metrica is metrica:
                return m
        return None

    @model_validator(mode="after")
    def _coerencia_do_destino(self) -> Laudo:
        if self.destino is Destino.APROVADO and self.motivos:
            raise ValueError("Laudo aprovado não carrega motivo de reprovação")
        if self.destino is not Destino.APROVADO and not self.motivos:
            raise ValueError("Laudo reprovado precisa de ao menos um motivo")
        if MotivoReprovacao.FALHA_DE_EXTRACAO in self.motivos and (
            self.destino is not Destino.REPROVADO_REVISAO_HUMANA
        ):
            raise ValueError("falha de extração vai direto à revisão humana (ADR 0013)")
        return self


# ---------------------------------------------------------------------------
# A execução em disco e as filas humanas
# ---------------------------------------------------------------------------


class Tentativa(BaseModel):
    """Uma rodada do Ciclo de correção: a Célula e o Laudo que a julgou."""

    rodada: int = Field(ge=0, le=2)
    celula: Celula
    laudo: Laudo


class HistoricoCelula(BaseModel):
    """As tentativas de uma posição da Matriz, e onde ela terminou."""

    audiencia: Audiencia
    formato: Formato
    tentativas: list[Tentativa] = Field(default_factory=list)
    destino_final: Destino
    provedores_usados: list[str] = Field(default_factory=list)
    falha: str | None = Field(
        default=None,
        description="Erro de provedor que interrompeu o Ciclo antes do teto, se houve. Vai à Pendencia H4.",
    )

    @property
    def celula_final(self) -> Celula | None:
        return self.tentativas[-1].celula if self.tentativas else None

    @property
    def laudo_final(self) -> Laudo | None:
        return self.tentativas[-1].laudo if self.tentativas else None


class FilaHumana(StrEnum):
    """Os pontos de interferência humana que a interface expõe como fila."""

    H3_DESEMPATE = "h3_desempate"
    H4_REVISAO = "h4_revisao"
    H5_APROVACAO_PACOTE = "h5_aprovacao_pacote"


class Pendencia(BaseModel):
    """Uma Célula esperando decisão humana numa fila."""

    fila: FilaHumana
    audiencia: Audiencia
    formato: Formato
    motivo: str
    criada_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolvida: bool = False
    decisao: str | None = None


class EstadoDecisao(StrEnum):
    """O que um humano decidiu sobre uma Célula."""

    APROVADA = "aprovada"
    REPROVADA = "reprovada"


class DecisaoHumana(BaseModel):
    """A decisão de um revisor sobre uma Célula. Sem registro, a Célula está pendente."""

    audiencia: Audiencia
    formato: Formato
    estado: EstadoDecisao
    motivo: str | None = Field(default=None, description="Obrigatório quando reprovada.")
    revisor: str | None = None
    em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _reprovada_exige_motivo(self) -> DecisaoHumana:
        if self.estado is EstadoDecisao.REPROVADA and not (self.motivo or "").strip():
            raise ValueError("reprovar exige motivo")
        return self


class Custo(BaseModel):
    """Quanto custou de verdade: chamadas, tokens e tempo. Entra no relatório."""

    chamadas: int = 0
    tokens_entrada: int = 0
    tokens_saida: int = 0
    segundos: float = 0.0
    por_provedor: dict[str, int] = Field(default_factory=dict)


class EstadoAvaliacaoTransversal(StrEnum):
    """Veredito único sobre a Matriz completa, depois dos nove ciclos individuais."""

    APROVADA = "aprovada"
    REVISAO_HUMANA = "revisao_humana"


class AvaliacaoTransversal(BaseModel):
    """Conferência determinística de completude e coerência das nove Células."""

    estado: EstadoAvaliacaoTransversal
    total_esperado: int = len(MATRIZ)
    total_recebido: int
    total_com_conteudo: int
    posicoes_faltantes: list[str] = Field(default_factory=list)
    posicoes_duplicadas: list[str] = Field(default_factory=list)
    posicoes_reprovadas: list[str] = Field(default_factory=list)
    referencias_invalidas: list[str] = Field(default_factory=list)
    observacoes: list[str] = Field(default_factory=list)
    avaliada_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EstadoJulgamentoTransversal(StrEnum):
    """Decisão do LLM Judge sobre a Matriz que já passou pelas regras fixas."""

    APROVADO = "aprovado"
    CORRIGIVEL = "corrigivel"
    GRAVE = "grave"
    FALHA = "falha"


class GravidadeProblemaTransversal(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    GRAVE = "grave"


class CriterioTransversal(StrEnum):
    FIDELIDADE_DOSSIE = "fidelidade_dossie"
    COERENCIA_MATRIZ = "coerencia_matriz"
    PROGRESSAO_PERSONAS = "progressao_personas"
    ADEQUACAO_PERSONA = "adequacao_persona"
    CONSISTENCIA_FORMATOS = "consistencia_formatos"
    CLAREZA_NARRATIVA = "clareza_narrativa"
    OMISSAO_RELEVANTE = "omissao_relevante"
    AFIRMACAO_SEM_EVIDENCIA = "afirmacao_sem_evidencia"


class ProblemaTransversal(BaseModel):
    """Problema subjetivo localizado pelo Judge em uma Célula concreta."""

    audiencia: Audiencia
    formato: Formato
    gravidade: GravidadeProblemaTransversal
    criterio: CriterioTransversal
    evidencia: str = Field(min_length=1)
    correcao: str = Field(min_length=1)


class JulgamentoTransversal(BaseModel):
    """Uma resposta auditável do LLM Judge, inclusive quando o provedor falha."""

    rodada: int = Field(ge=0, le=2)
    estado: EstadoJulgamentoTransversal
    problemas: list[ProblemaTransversal] = Field(default_factory=list)
    provedor: str
    falha: str | None = None
    avaliado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _estado_coerente(self) -> JulgamentoTransversal:
        if self.estado is EstadoJulgamentoTransversal.FALHA:
            if not self.falha or self.problemas:
                raise ValueError("falha do Judge exige mensagem e não carrega problemas")
            return self
        if self.falha:
            raise ValueError("julgamento respondido não carrega falha de provedor")
        if self.estado is EstadoJulgamentoTransversal.APROVADO and self.problemas:
            raise ValueError("Judge aprovado não carrega problemas")
        if self.estado is not EstadoJulgamentoTransversal.APROVADO and not self.problemas:
            raise ValueError("Judge corrigível ou grave precisa localizar problema")
        return self


class CorrecaoTransversalAplicada(BaseModel):
    """Versão substituída e instruções enviadas de volta à persona."""

    rodada: int = Field(ge=0, le=1)
    audiencia: Audiencia
    formato: Formato
    instrucoes: list[str] = Field(min_length=1)
    historico_anterior: HistoricoCelula


class ResultadoCicloTransversal(BaseModel):
    """Estado final depois das regras fixas e do LLM Judge."""

    estado: EstadoAvaliacaoTransversal
    avaliacao_deterministica: AvaliacaoTransversal
    julgamentos: list[JulgamentoTransversal] = Field(default_factory=list)
    correcoes_aplicadas: list[CorrecaoTransversalAplicada] = Field(default_factory=list)
    motivo_final: str

    @model_validator(mode="after")
    def _aprovacao_exige_as_duas_camadas(self) -> ResultadoCicloTransversal:
        if self.estado is EstadoAvaliacaoTransversal.APROVADA:
            if self.avaliacao_deterministica.estado is not EstadoAvaliacaoTransversal.APROVADA:
                raise ValueError("ciclo não aprova Matriz reprovada deterministicamente")
            if not self.julgamentos or (
                self.julgamentos[-1].estado is not EstadoJulgamentoTransversal.APROVADO
            ):
                raise ValueError("ciclo aprovado exige aprovação final do LLM Judge")
        return self


class Execucao(BaseModel):
    """O único arquivo de estado de uma execução: ``data/execucoes/<id>/execucao.json``."""

    identificador: str
    ata: str
    provedor_gerador: str
    iniciada_em: datetime
    concluida_em: datetime | None = None
    selecao: SelecaoCuradoria | None = Field(
        default=None,
        description="Seleção que originou o dossiê; ausente apenas em execuções antigas.",
    )
    ancoras: Ancoras
    celulas: list[HistoricoCelula] = Field(default_factory=list)
    pendencias: list[Pendencia] = Field(default_factory=list)
    custo: Custo = Field(default_factory=Custo)
    comite_ligado: bool = False
    avaliacao_transversal: AvaliacaoTransversal | None = Field(
        default=None,
        description="Veredito da Matriz completa; ausente apenas em execuções antigas.",
    )
    ciclo_transversal: ResultadoCicloTransversal | None = Field(
        default=None,
        description="Ciclo do LLM Judge e correções; ausente apenas em execuções antigas.",
    )
    nome: str = Field(
        default="",
        description="Nome dado pelo usuário à Saída; vazio vira o identificador.",
    )
    decisoes: list[DecisaoHumana] = Field(
        default_factory=list,
        description="Decisões humanas por Célula; posição sem registro está pendente.",
    )

    @model_validator(mode="after")
    def _nome_padrao(self) -> Execucao:
        if not self.nome.strip():
            self.nome = self.identificador
        return self

    def historico(self, audiencia: Audiencia, formato: Formato) -> HistoricoCelula | None:
        for h in self.celulas:
            if h.audiencia is audiencia and h.formato is formato:
                return h
        return None

    def decisao_de(self, audiencia: Audiencia, formato: Formato) -> DecisaoHumana | None:
        for decisao in self.decisoes:
            if decisao.audiencia is audiencia and decisao.formato is formato:
                return decisao
        return None

    def contagem_por_motivo(self) -> dict[MotivoReprovacao, int]:
        contagem: dict[MotivoReprovacao, int] = {m: 0 for m in MotivoReprovacao}
        for h in self.celulas:
            for t in h.tentativas:
                for motivo in t.laudo.motivos:
                    contagem[motivo] += 1
        return contagem


# ---------------------------------------------------------------------------
# O Pacote de publicação (ADR 0009, 0014)
# ---------------------------------------------------------------------------


class DefeitoRender(StrEnum):
    """O que a camada determinística da conferência visual consegue medir."""

    ESTOURO_DE_CAIXA = "estouro_de_caixa"
    CONTRASTE_BAIXO = "contraste_baixo"
    DIMENSAO_ERRADA = "dimensao_errada"
    NUMERO_DIVERGENTE = "numero_divergente"
    DURACAO_FORA_DA_FAIXA = "duracao_fora_da_faixa"
    SEM_AUDIO = "sem_audio"


LARGURA_SLIDE = 1080
ALTURA_SLIDE = 1350
"""4:5 em todos os slides de todas as nove Células (ADR 0009). Requisito técnico, não estética."""

CONTRASTE_MINIMO = 4.5
"""Razão de luminância mínima (WCAG AA para texto normal)."""


class MedicaoVisual(BaseModel):
    """Uma medição sobre um artefato renderizado."""

    artefato: str = Field(description="Caminho relativo da imagem ou do vídeo.")
    defeito: DefeitoRender | None = Field(default=None, description="None = passou.")
    valor: float | None = None
    detalhe: str = ""


class ParecerVisao(BaseModel):
    """Resposta holística do juiz de visão sobre a folha de contato. Opcional."""

    parece_quebrado: bool
    observacoes: list[str] = Field(default_factory=list)
    provedor: str


class ConferenciaVisual(BaseModel):
    """O resultado da avaliação visual do Pacote. Vai ao H5, nunca ao Laudo."""

    medicoes: list[MedicaoVisual] = Field(default_factory=list)
    juiz_visao: ParecerVisao | None = None

    @property
    def defeitos(self) -> list[MedicaoVisual]:
        return [m for m in self.medicoes if m.defeito is not None]

    @property
    def precisa_refazer_render(self) -> bool:
        return bool(self.defeitos)


class ImagemSlide(BaseModel):
    indice: int = Field(ge=0)
    caminho: CaminhoPortavel
    largura: int
    altura: int


class PacotePublicacao(BaseModel):
    """O conjunto pronto para um humano publicar, só de Célula aprovada."""

    execucao: str
    audiencia: Audiencia
    formato: Formato
    legenda: str
    hashtags: list[str] = Field(default_factory=list)
    imagens: list[ImagemSlide] = Field(default_factory=list)
    folha_de_contato: CaminhoPortavel | None = None
    video: CaminhoPortavel | None = None
    conferencia: ConferenciaVisual = Field(default_factory=ConferenciaVisual)
    montado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    aprovado_por_humano: bool = False


# ---------------------------------------------------------------------------
# Contratos de provedor de LLM (ADR 0007)
# ---------------------------------------------------------------------------


class PapelLLM(StrEnum):
    """Que papel a chamada cumpre. O roteador escolhe o provedor por papel."""

    GERADOR = "gerador"
    JUIZ = "juiz"
    JUIZ_VISAO = "juiz_visao"


class Mensagem(BaseModel):
    model_config = ConfigDict(frozen=True)

    autor: Literal["sistema", "usuario"]
    texto: str
    imagem_png: bytes | None = Field(default=None, description="Só para JUIZ_VISAO.")


class PedidoLLM(BaseModel):
    """Um pedido a qualquer provedor. O schema de saída viaja no pedido, nunca fica no cliente."""

    papel: PapelLLM
    rotulo: str = Field(
        description=(
            "Identifica o pedido para o LLM falso e para o log: "
            "'extracao', 'celula:iniciante:carrossel:0'."
        )
    )
    mensagens: list[Mensagem]
    schema_saida: dict[str, Any] | None = Field(
        default=None, description="JSON Schema da resposta esperada, quando estruturada."
    )
    max_tokens: int = Field(default=2048, gt=0)
    temperatura: float = Field(default=0.2, ge=0, le=2)
    esforco_raciocinio: Literal["baixo", "medio", "alto"] | None = Field(
        default=None,
        description=(
            "Em modelo de raciocínio, o 'pensar' gasta o mesmo teto de max_tokens (pesquisa §4): "
            "papel com teto baixo pede esforço baixo. None = padrão do provedor."
        ),
    )


class RespostaLLM(BaseModel):
    texto: str
    provedor: str
    modelo: str
    tokens_entrada: int = 0
    tokens_saida: int = 0
    tokens_raciocinio: int = Field(
        default=0, description="Tokens gastos pensando (Gemini: thoughtsTokenCount). Contam na cota."
    )
    latencia_s: float = 0.0


class EsgotamentoDeCota(StrEnum):
    """O que o 429 quer dizer: espera (minuto) ou troca de provedor (dia)."""

    POR_MINUTO = "por_minuto"
    POR_DIA = "por_dia"
    DESCONHECIDO = "desconhecido"


class ErroProvedor(Exception):
    """Qualquer falha de um provedor que não seja cota."""

    def __init__(self, provedor: str, mensagem: str) -> None:
        super().__init__(f"[{provedor}] {mensagem}")
        self.provedor = provedor
        self.mensagem = mensagem


class CotaEsgotada(ErroProvedor):
    """Um 429 já interpretado: o roteador decide entre esperar e trocar."""

    def __init__(
        self,
        provedor: str,
        esgotamento: EsgotamentoDeCota,
        espera_s: float | None = None,
        mensagem: str = "",
    ) -> None:
        super().__init__(provedor, mensagem or f"cota esgotada ({esgotamento})")
        self.esgotamento = esgotamento
        self.espera_s = espera_s


class RespostaMalformada(ErroProvedor):
    """O provedor respondeu, mas não no schema pedido."""
