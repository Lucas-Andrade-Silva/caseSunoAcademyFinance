# 0034 — Ata sem número gera conteúdo qualitativo

## Status

Aceita (13/10/2026). Altera o conjunto essencial de Âncoras fora do Copom do
[ADR 0018](0018-origens-e-categoria-da-ata.md) e a recusa antecipada da geração. O
[ADR 0013](0013-ciclo-de-correcao-com-teto-de-duas-rodadas.md) continua valendo: falha de extração
ainda reprova a Célula e vai à revisão humana.

## Contexto

Fora do Copom, a Célula só passava se a Ata tivesse uma data e um número com unidade. Comunicados
reais não têm: ofícios da B3, resoluções do BCB e fatos relevantes da CVM sobre sucessão,
licitação ou cancelamento de registro. O cartão da notícia mostrava "sem número" e a API recusava a
geração, para não gastar cota com Células que reprovariam. Um comunicado qualitativo é conteúdo
possível: a Aderência já tratava Célula sem número como Medida ausente, e não como reprovação.

## Decisão

1. **A data nunca falta.** Sem data no corpo do texto, vale a data de referência dos metadados da
   Ata, com o título como trecho (`extracao._data_dos_metadados`).
2. **O fato central pode ser uma afirmação.** O conjunto essencial genérico continua sendo
   `data_do_comunicado` e `numero_principal`, mas `numero_principal` também é satisfeito por uma
   Âncora textual com trecho (`avaliador.integridade`). Na Visão unida a regra vale por parte
   (`a2_numero_principal` aceita uma Âncora `a2_...`). No Copom a afirmação não substitui a decisão.
3. **A afirmação é conferida contra o texto.** Quando a Ata não traz número, o pedido de extração
   manda o LLM devolver de 1 a 5 afirmações centrais; as que não têm trecho literal na Ata são
   descartadas pelo código, como já eram. Se nenhuma sobrar, a Célula reprova por falha de extração.
4. **O Gerador escreve sem inventar número.** Com só datas na tabela de Âncoras, o prompt recebe a
   instrução de escrever um conteúdo qualitativo e a lista de afirmações centrais
   (`moldes.INSTRUCAO_SEM_NUMERO`). O prompt com números não muda.
5. **A API só recusa texto curto.** `extracao_completa` fica `False` fora do Copom apenas se não há
   número e o texto tem menos de 200 caracteres: não há afirmação a conferir. A tela mostra
   "texto curto" nesse caso e "sem número · conteúdo qualitativo" (informativo) nos demais
   (`ResumoDaAta.qualitativa`).

## Consequências

- Muito mais notícias passam a ser geráveis. Quem usa a plataforma vê o selo **não calibrado**
  nelas como antes: nenhuma categoria tem Calibração humana ainda.
- A Aderência não confere nada num conteúdo sem número, e a Aderência textual é só informativa
  (ADR 0011). A defesa contra invenção de fato é o prompt, o Comitê opcional e a revisão humana. Um
  teste de campo com o Gemini (fato relevante do Banco do Nordeste) saiu com 9 de 9 Células
  aprovadas e nenhum número inventado, com uma frase de fechamento genérica sobre "novos passos".
- A decisão sobre quais chaves são essenciais é da pessoa dona do Avaliador: este ADR é a proposta
  dela para validar.
