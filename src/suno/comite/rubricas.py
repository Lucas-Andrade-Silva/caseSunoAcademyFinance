"""As rubricas por dimensão. O prompt do juiz nunca menciona qual modelo ou provedor gerou o texto.

ADR 0008.

Uma rubrica por dimensão, com a escala inteira escrita: nota isolada, nunca média de
dimensões distintas. Misturar tom, clareza e coerência numa nota só esconde qual delas
falhou, e correções diferentes pedem diagnósticos diferentes.

Duas regras que quem editar este arquivo precisa manter:

- **Nenhum nome de provedor ou de modelo entra aqui.** Trocar de provedor evita a
  autopreferência direta; o silêncio sobre quem escreveu evita o viés de reputação.
  ``tests/test_comite.py`` varre as mensagens procurando esses nomes.
- **A rubrica de coerência pergunta pelo texto picado.** É o caso que o Flesch-BR não pega:
  frases curtas e desconexas pontuam bem na fórmula e leem mal.
"""

from __future__ import annotations

from suno.dominio import DimensaoSubjetiva

ESCALA = (
    "Escala de 1 a 5: 1 = falha grave, 2 = ruim, 3 = aceitável com ressalva, 4 = bom, "
    "5 = exemplar."
)

INSTRUCAO_DE_RESPOSTA = (
    "Responda apenas com um objeto JSON com dois campos: "
    '"nota" (inteiro de 1 a 5) e "justificativa" (uma frase curta, em português, '
    "citando o que no texto sustenta a nota). Não escreva nada fora do JSON."
)

PREAMBULO = (
    "Você julga uma única dimensão de um texto educativo sobre a decisão de juros do Banco "
    "Central do Brasil. Julgue só a dimensão descrita abaixo, nada mais: não comente fatos, "
    "números nem conformidade regulatória, que já foram conferidos por outra via. Você não "
    "sabe, e não precisa saber, quem escreveu o texto."
)

RUBRICAS: dict[DimensaoSubjetiva, str] = {
    DimensaoSubjetiva.TOM: (
        "Dimensão: tom.\n"
        "O registro combina com a Audiência indicada e com um material que informa e educa?\n"
        "1 — vende, promete resultado, ou trata o leitor com desdém.\n"
        "2 — oscila entre formal e coloquial sem razão, ou soa paternalista.\n"
        "3 — registro aceitável, com uma ou outra quebra.\n"
        "4 — registro estável e adequado à Audiência.\n"
        "5 — registro estável, adequado e acolhedor sem perder a sobriedade.\n"
        "Rebaixe a nota se o texto tenta convencer o leitor a agir em vez de explicar."
    ),
    DimensaoSubjetiva.CLAREZA: (
        "Dimensão: clareza.\n"
        "Um leitor da Audiência indicada entende o texto na primeira leitura?\n"
        "1 — incompreensível para essa Audiência.\n"
        "2 — exige reler várias passagens, ou usa termos técnicos sem apoio nenhum.\n"
        "3 — entende-se com esforço.\n"
        "4 — claro, com no máximo um ponto obscuro.\n"
        "5 — claro do começo ao fim, com as ideias na ordem em que ajudam.\n"
        "Julgue a compreensão, não o tamanho: texto curto pode ser obscuro e texto longo "
        "pode ser límpido."
    ),
    DimensaoSubjetiva.COERENCIA: (
        "Dimensão: coerência.\n"
        "O texto se sustenta como um todo, com as ideias encadeadas?\n"
        "Pergunte-se explicitamente: o texto parece cortado artificialmente, em frases "
        "curtas e desconexas, como se tivesse sido picado para caber num limite? Se parecer, "
        "a nota não passa de 2, por mais simples que cada frase seja isoladamente.\n"
        "1 — frases soltas, sem fio condutor; parece uma lista de fragmentos.\n"
        "2 — encadeamento frouxo, com saltos entre as partes.\n"
        "3 — encadeado, com uma transição brusca.\n"
        "4 — encadeado do começo ao fim.\n"
        "5 — encadeado e com uma linha de raciocínio que fecha onde abriu."
    ),
}


def rubrica(dimensao: DimensaoSubjetiva) -> str:
    """A instrução completa do juiz daquela dimensão: preâmbulo, rubrica, escala e formato."""
    return "\n\n".join((PREAMBULO, RUBRICAS[dimensao], ESCALA, INSTRUCAO_DE_RESPOSTA))


__all__ = ["ESCALA", "INSTRUCAO_DE_RESPOSTA", "PREAMBULO", "RUBRICAS", "rubrica"]
