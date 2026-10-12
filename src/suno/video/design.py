"""O design system do vídeo: a fonte única de cores, tempos, cenas, ícones, transições,
efeitos e sons.

Três consumidores leem daqui, e por isso nenhum deles inventa nome:

- o **prompt** do Roteiro (``instrucao_de_direcao``): o LLM só escolhe nomes do catálogo;
- o **JSON** para gerador de vídeo com avatar (``suno.video.plano``): cada cena sai com os
  mesmos nomes e os mesmos tokens;
- o **render** local em CPU (``suno.video.render``): desenha a partir dos mesmos tokens.

Este módulo é só dado e funções puras — sem Pillow, sem ffmpeg, sem rede — para o Gerador e
o Avaliador poderem importá-lo sem arrastar o extra ``video``. As cores espelham as do
Carrossel (``suno.pacote.carrossel``); ``tests/test_video_direcao.py`` confere que continuam
iguais. ADR 0004, 0021.
"""

from __future__ import annotations

from dataclasses import dataclass

from suno.dominio import (
    AnimacaoDoTexto,
    BlocoFala,
    DuracaoDoVideo,
    EfeitoDeCena,
    IconeDeCena,
    SomDeCena,
    TipoDeCena,
    TransicaoDeEntrada,
)

VERSAO_DO_DESIGN = "1"
"""Sobe quando um token ou um nome de catálogo muda de sentido; vai no JSON de saída."""

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

LARGURA = 1080
ALTURA = 1920
FPS_DO_RENDER = 12

CORES: dict[str, str] = {
    "fundo": "#252525",
    "texto": "#FFFFFF",
    "apoio": "#E6E6E6",
    "destaque": "#AF0404",
    "trilho": "#1B2536",
}

TIPOGRAFIA: dict[str, object] = {
    "familia": "DejaVu Sans",
    "titulo": {"tamanho_px": 58, "peso": "bold", "caixa": "como_escrito"},
    "dado": {"tamanho_px": 190, "peso": "bold", "caixa": "como_escrito"},
    "legenda": {"tamanho_px": 42, "peso": "regular", "caixa": "como_escrito"},
}

AREA_SEGURA = {"margem_px": 84, "topo_px": 220, "base_px": 360}
"""Margem lateral e as faixas de topo e de base que as redes cobrem com a interface."""

TEMPOS: dict[str, float] = {
    "transicao_s": 0.4,
    "entrada_do_texto_s": 0.35,
    "duracao_minima_da_cena_s": 2.0,
}

# ---------------------------------------------------------------------------
# A duração: palavras e cenas por duração escolhida
# ---------------------------------------------------------------------------

PALAVRAS_POR_SEGUNDO = 2.5
"""Cerca de 150 palavras por minuto: a fala de apresentador em português, sem pressa."""

TOLERANCIA_DA_DURACAO = 0.25
"""O vídeo mede entre 75% e 125% da duração escolhida. Fora disso, a medição acusa."""

DURACAO_MINIMA_ABSOLUTA_S = 5.0


@dataclass(frozen=True, slots=True)
class Orcamento:
    """O que cabe em uma duração: palavras de fala e quantidade de cenas."""

    segundos: int
    palavras_alvo: int
    palavras_minimas: int
    palavras_maximas: int
    cenas_minimas: int
    cenas_maximas: int

    @property
    def faixa_de_duracao_s(self) -> tuple[float, float]:
        return (
            max(DURACAO_MINIMA_ABSOLUTA_S, self.segundos * (1 - TOLERANCIA_DA_DURACAO)),
            self.segundos * (1 + TOLERANCIA_DA_DURACAO),
        )


def orcamento_de(duracao: DuracaoDoVideo | int) -> Orcamento:
    segundos = duracao.segundos if isinstance(duracao, DuracaoDoVideo) else int(duracao)
    alvo = round(segundos * PALAVRAS_POR_SEGUNDO)
    return Orcamento(
        segundos=segundos,
        palavras_alvo=alvo,
        palavras_minimas=round(alvo * 0.9),
        palavras_maximas=round(alvo * 1.05),
        cenas_minimas=max(2, round(segundos / 8)),
        cenas_maximas=max(3, round(segundos / 5)),
    )


def duracoes_aceitas() -> list[int]:
    return [d.segundos for d in DuracaoDoVideo]


def duracao_valida(segundos: int) -> DuracaoDoVideo:
    """A duração escolhida, ou ``ValueError`` listando as cinco que existem."""
    try:
        return DuracaoDoVideo(str(segundos))
    except ValueError:
        validas = ", ".join(f"{s}s" for s in duracoes_aceitas())
        raise ValueError(f"duração de {segundos}s não existe; as opções são {validas}") from None


# ---------------------------------------------------------------------------
# Os catálogos: nome → quando usar
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LayoutDeCena:
    """Como uma cena se organiza: onde o texto cai e o que o avatar faz."""

    uso: str
    zona_do_texto: str
    avatar: str
    """``grande_centro`` ocupa o quadro; ``canto`` fica pequeno; ``oculto`` sai de cena."""
    tamanho_do_texto: str


CENAS: dict[TipoDeCena, LayoutDeCena] = {
    TipoDeCena.GANCHO: LayoutDeCena(
        "A abertura: uma pergunta ou um contraste que prende nos três primeiros segundos.",
        "terco_superior", "grande_centro", "titulo",
    ),
    TipoDeCena.DADO_GRANDE: LayoutDeCena(
        "Um número da Ata em destaque, com o ícone ao lado. Só `{{chave}}` de Âncora.",
        "centro", "canto", "dado",
    ),
    TipoDeCena.TEXTO_DESTAQUE: LayoutDeCena(
        "Uma ideia curta em texto grande. A cena padrão do meio do vídeo.",
        "terco_superior", "canto", "titulo",
    ),
    TipoDeCena.LISTA: LayoutDeCena(
        "Dois ou três itens curtos em sequência, separados por ' | ' na rubrica.",
        "centro", "canto", "titulo",
    ),
    TipoDeCena.COMPARACAO: LayoutDeCena(
        "Antes e depois, ou dois lados: dois trechos separados por ' | ' na rubrica.",
        "centro", "oculto", "titulo",
    ),
    TipoDeCena.CITACAO: LayoutDeCena(
        "Um trecho curto da Ata, parafraseado, com ícone de documento.",
        "centro", "canto", "legenda",
    ),
    TipoDeCena.ENCERRAMENTO: LayoutDeCena(
        "O fechamento: convida a ler a Ata ou acompanhar o tema. Nunca a comprar ou vender.",
        "terco_superior", "grande_centro", "titulo",
    ),
}

ICONES: dict[IconeDeCena, str] = {
    IconeDeCena.JUROS: "taxa de juros, Selic",
    IconeDeCena.INFLACAO: "inflação, preços",
    IconeDeCena.GRAFICO_ALTA: "algo que sobe",
    IconeDeCena.GRAFICO_QUEDA: "algo que cai",
    IconeDeCena.GRAFICO_ESTAVEL: "algo que se mantém",
    IconeDeCena.CALENDARIO: "data, próxima reunião, prazo",
    IconeDeCena.BANCO: "Banco Central, instituição",
    IconeDeCena.BOLSO: "impacto no dia a dia, no orçamento",
    IconeDeCena.ALERTA: "risco, ponto de atenção",
    IconeDeCena.LUPA: "o que observar adiante",
    IconeDeCena.DOCUMENTO: "a Ata, uma citação",
    IconeDeCena.BALANCA: "equilíbrio, balanço de riscos",
    IconeDeCena.RELOGIO: "tempo, prazo, defasagem",
    IconeDeCena.PERGUNTA: "gancho em forma de pergunta",
    IconeDeCena.CHECK: "decisão tomada, confirmação",
}

TRANSICOES: dict[TransicaoDeEntrada, str] = {
    TransicaoDeEntrada.CORTE: "corte seco; a escolha padrão e a da primeira cena",
    TransicaoDeEntrada.FADE: "dissolve suave; troca de assunto",
    TransicaoDeEntrada.DESLIZAR_ESQUERDA: "a cena nova entra pela direita; avanço na sequência",
    TransicaoDeEntrada.DESLIZAR_CIMA: "a cena nova sobe; entrada de um dado novo",
    TransicaoDeEntrada.ZOOM: "aproximação rápida; ênfase, no máximo uma vez no vídeo",
}

ANIMACOES_DO_TEXTO: dict[AnimacaoDoTexto, str] = {
    AnimacaoDoTexto.APARECER: "aparece inteiro de uma vez",
    AnimacaoDoTexto.FADE: "surge com fade; o padrão",
    AnimacaoDoTexto.DESLIZAR_BAIXO: "desce de cima até o lugar",
    AnimacaoDoTexto.POP: "cresce de pequeno ao tamanho final; para dados",
    AnimacaoDoTexto.DIGITAR: "letra por letra; para pergunta de gancho",
}

EFEITOS: dict[EfeitoDeCena, str] = {
    EfeitoDeCena.NENHUM: "sem efeito; a escolha mais comum",
    EfeitoDeCena.ZOOM_LENTO: "aproximação lenta durante toda a cena",
    EfeitoDeCena.PULSO: "o texto pulsa uma vez; destaque de um ponto",
    EfeitoDeCena.SUBLINHADO: "uma barra de destaque sob o texto",
    EfeitoDeCena.CONTAGEM: "o número sobe até o valor; só em dado_grande",
}


@dataclass(frozen=True, slots=True)
class DescricaoDeSom:
    uso: str
    duracao_s: float
    volume: float


SONS: dict[SomDeCena, DescricaoDeSom] = {
    SomDeCena.WHOOSH: DescricaoDeSom("acompanha transição deslizar ou zoom", 0.35, 0.35),
    SomDeCena.POP: DescricaoDeSom("marca o texto que aparece em pop", 0.12, 0.45),
    SomDeCena.CLIQUE: DescricaoDeSom("marca item de lista ou texto que digita", 0.05, 0.4),
    SomDeCena.DING: DescricaoDeSom("marca o dado ou a decisão", 0.6, 0.3),
    SomDeCena.SWELL: DescricaoDeSom("sobe antes de uma revelação; no máximo uma vez", 0.8, 0.25),
}

# ---------------------------------------------------------------------------
# O prompt
# ---------------------------------------------------------------------------


def _catalogo(titulo: str, itens: dict) -> str:
    linhas = "\n".join(f"  - {nome.value}: {uso}" for nome, uso in itens.items())
    return f"{titulo}\n{linhas}"


def diretriz_de_duracao(duracao: DuracaoDoVideo | int) -> str:
    """O trecho do pedido que fixa quanto cabe: palavras, cenas e segundos."""
    o = orcamento_de(duracao)
    return (
        f"Duração escolhida: {o.segundos} segundos. A fala soma de {o.palavras_minimas} a "
        f"{o.palavras_maximas} palavras (cerca de {o.palavras_alvo}; o ritmo é de "
        f"{PALAVRAS_POR_SEGUNDO:g} palavras por segundo) e se divide em {o.cenas_minimas} a "
        f"{o.cenas_maximas} cenas. 'inicio_s' e 'fim_s' acompanham o ritmo da fala; as cenas "
        "são consecutivas, sem buraco, e a última termina perto de "
        f"{o.segundos} segundos."
    )


def instrucao_de_direcao() -> str:
    """O catálogo inteiro, para o LLM escolher por nome. Nada fora dele é aceito."""
    cenas = "\n".join(
        f"  - {tipo.value}: {layout.uso}" for tipo, layout in CENAS.items()
    )
    sons = "\n".join(f"  - {nome.value}: {d.uso}" for nome, d in SONS.items())
    return "\n".join(
        [
            "Direção de cena: cada bloco também diz como a cena é editada, escolhendo só "
            "nomes destas listas. Edição sóbria, de mercado financeiro: o padrão é pouco "
            "efeito; use `nenhum` e `corte` quando não houver motivo.",
            f"cena (o layout):\n{cenas}",
            _catalogo("icone (opcional):", ICONES),
            _catalogo("entrada (transição; a primeira cena é sempre corte):", TRANSICOES),
            _catalogo("texto_anima (como a rubrica 'tela' aparece):", ANIMACOES_DO_TEXTO),
            (
                "texto_entra_em_s: segundos depois do início da cena em que a rubrica aparece "
                "(0 a 2; o gancho entra em 0)."
            ),
            _catalogo("efeito (um por cena):", EFEITOS),
            f"som_de_entrada e som_de_efeito (opcionais, nunca mais de um por cena de cada tipo):\n{sons}",
            (
                "A rubrica 'tela' é curta: até 8 palavras no gancho e no dado, até 14 nas "
                "demais. Em `lista` e `comparacao`, separe os trechos com ' | '. Todo número "
                "na rubrica entra como `{{chave}}`."
            ),
        ]
    )


# ---------------------------------------------------------------------------
# A cronometragem e a higiene da direção
# ---------------------------------------------------------------------------


def contar_palavras(texto: str) -> int:
    return len(texto.split())


def duracao_da_fala(texto: str) -> float:
    """O tempo de fala estimado de ``texto``, no ritmo do design system, com piso por cena."""
    return max(TEMPOS["duracao_minima_da_cena_s"], contar_palavras(texto) / PALAVRAS_POR_SEGUNDO)


def cronometrar(blocos: list[BlocoFala]) -> list[BlocoFala]:
    """Recalcula ``inicio_s`` e ``fim_s`` pelo número de palavras de cada fala, em sequência.

    O LLM erra a conta do tempo com facilidade (e erra sempre no mesmo sentido: escreve mais do
    que cabe). O tempo de fala é uma conta, não uma escolha — então o código a faz. A direção é
    higienizada junto: a primeira cena entra em corte, o texto nunca aparece depois que a cena
    já está acabando, e o efeito de contagem só vale no ``dado_grande``.
    """
    saida: list[BlocoFala] = []
    relogio = 0.0
    for indice, bloco in enumerate(blocos):
        duracao = duracao_da_fala(bloco.fala)
        entra = min(bloco.texto_entra_em_s, max(0.0, duracao - 1.0))
        efeito = bloco.efeito
        if efeito is EfeitoDeCena.CONTAGEM and bloco.cena is not TipoDeCena.DADO_GRANDE:
            efeito = EfeitoDeCena.NENHUM
        saida.append(
            bloco.model_copy(
                update={
                    "inicio_s": round(relogio, 2),
                    "fim_s": round(relogio + duracao, 2),
                    "entrada": TransicaoDeEntrada.CORTE if indice == 0 else bloco.entrada,
                    "som_de_entrada": None if indice == 0 else bloco.som_de_entrada,
                    "texto_entra_em_s": round(entra, 2),
                    "efeito": efeito,
                }
            )
        )
        relogio += duracao
    return saida
