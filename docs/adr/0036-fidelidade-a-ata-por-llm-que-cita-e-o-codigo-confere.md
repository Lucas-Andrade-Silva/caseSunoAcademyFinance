# 0036 — A Fidelidade à Ata: um LLM aponta o que a Ata não sustenta, o código confere a citação, e o apontamento confirmado reprova

## Status

Aceita (14/10/2026). Complementa o [ADR 0035](0035-qualidade-pelo-jev-depois-do-deterministico.md) e
**abre uma exceção calculada ao [ADR 0008](0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md)**,
que mantinha Aderência e Compliance fora de qualquer LLM: aqui o LLM entra na fidelidade da afirmação
em prosa, que a Aderência (só número) nunca cobriu, e não tem poder sobre número nem Recomendação.

## Contexto

O enunciado pede um "Factuality & Grounding Checker". A Aderência (ADR 0011) confere cada número por
igualdade exata e é soberana. Mas uma Célula pode dizer em prosa o que a Ata não diz ("o Comitê
prometeu cortar os juros") sem número nenhum, e nada determinístico pega isso.

O ADR 0008 recusou LLM nesse papel por um motivo medido: há registro de juiz alucinando evidência
para justificar um veredito.

## Decisão

1. **Um LLM por Célula, com a Ata inteira no pedido.** Devolve uma lista de apontamentos de três tipos:
   `sem_suporte`, `distorce` e `contradiz`. A lista vazia é a resposta normal.
2. **O modelo aponta, o código confere.** Todo apontamento traz o trecho da Célula copiado
   literalmente; `distorce` e `contradiz` trazem também o trecho da Ata. O código verifica que cada
   citação existe (sem diferença de caixa, espaço, aspas ou travessão). Citação que não existe é
   invenção do juiz, e o apontamento é **descartado**. Trecho da Célula com menos de 15 caracteres
   também: é vago demais.
3. **Na dúvida, não aponta.** O pedido manda ignorar explicação de termo, analogia e exemplo (didática
   escrita para a Audiência), simplificação, estilo e número. Sem isso todo texto do Iniciante reprovaria.
4. **Roda no Groq e, se ele não der conta, no Gemini, com a Ata inteira.** O papel `checador` do roteador
   segue essa ordem e troca no 429 como os outros. O SambaNova, a primeira escolha, saiu: o teste de fumaça
   de 14/10/2026 voltou HTTP 402 `PAYMENT_METHOD_REQUIRED` com saldo zero, e o orçamento é R$ 0 (como a
   Cerebras no [ADR 0007](0007-roteador-de-provedores-distingue-tipo-de-429.md)). Sem nenhuma das duas chaves,
   não monta e avisa no log.
5. **Só bloqueia o que tem prova.** `distorce` e `contradiz` trazem o trecho da Ata, que o código
   conferiu: reprovam a Célula (motivo `fidelidade`) e o Ciclo a devolve ao Gerador com os dois trechos.
   `sem_suporte` é a opinião do modelo de que "a Ata não diz isso" e não há trecho a conferir: **só
   avisa**, nas observações do Laudo ("Aviso (não reprova)"). Vale 1 sem bloqueio e 0 com algum.
   Decidido em 14/10/2026 depois da medição abaixo.
5a. **As Âncoras vão ao pedido como "fatos já conferidos".** Conclusão direta de um fato verificado (7 votos
   a favor e nenhum contra é decisão unânime) não é apontamento.
6. **Por último.** Só depois das cinco medidas e da Qualidade terem aprovado: é a chamada mais cara.
7. **Falha nunca reprova.** Sem chave, sem cota, resposta fora do schema, Ata acima de 350 mil
   caracteres: o Laudo sai sem a Fidelidade.
8. **Nasce desligado.** `SUNO_FIDELIDADE=1` ou `--fidelidade`.

## Consequências

- **O esperado é reprovar quase nunca, e a medição foi o que mudou a regra.** Em 6 Células reais já
  aprovadas (Ata do Copom 281), bloquear por qualquer apontamento reprovaria 3 de 6, e dois deles eram
  "decisão unânime" tirada dos 7 membros que votaram a favor. Com a regra de só bloquear o que tem prova
  e as Âncoras no pedido, **0 de 6** bloqueiam e 3 viram aviso. A amostra é pequena e de uma Ata só.
- **O checador é lento no plano grátis do Groq:** o 429 por minuto mandou esperar de 5 a 37 s em várias
  das chamadas; seis Células levaram alguns minutos. O Gemini não foi necessário na medição.
- **Falso positivo existe.** A conferência de citação impede a invenção de trecho, não o juízo errado
  de que um trecho verdadeiro não é sustentado. Por isso cada apontamento aparece na Correção e no
  Laudo com a citação, e dá para auditar à mão.
- **Falso negativo, agora de propósito:** uma afirmação inventada sem trecho da Ata para contrapor
  (`sem_suporte`) passa com aviso. É o preço de não reescrever Célula certa. Um modelo também pode deixar passar. Fidelidade 1 não prova que a Célula é fiel.
- **Custo:** uma chamada por Célula que passou em tudo, com a Ata inteira (várias mil palavras) no pedido,
  mais uma por rodada de correção. O limite por minuto do Groq no plano grátis pode não comportar a Ata
  inteira, e aí o Gemini assume: **não medi**, e é o que o teste de fumaça deve mostrar.
- **Autopreferência:** quando o Groq não aguenta e o Gemini assume, o provedor que gera também confere. Para
  comparar um texto com a fonte o viés pesa menos do que num juiz de tom, mas existe. Se a Célula foi
  gerada pelo Gemini, o Laudo registra isso no provedor da Célula.
- **Documento longo:** uma DFP de 300 mil caracteres ainda cabe; acima de 350 mil, não, e a Célula sai
  sem Fidelidade.
