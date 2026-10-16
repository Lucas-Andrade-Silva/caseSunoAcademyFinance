# 0037 — O Judge transversal e o Comitê foram removidos, o Jev está sempre ligado e o SambaNova saiu

## Status

Aceita (15/10/2026). **Revoga o [ADR 0016](0016-llm-judge-transversal-com-retorno-seletivo.md).**
Atualiza os [ADR 0035](0035-qualidade-pelo-jev-depois-do-deterministico.md) (o Jev deixa de nascer
desligado) e [ADR 0007](0007-roteador-de-provedores-distingue-tipo-de-429.md) (o SambaNova deixa a fila).

## Contexto

- **O Judge transversal quase nunca rodava.** Ele só entrava quando as nove Células já haviam passado nas
  regras fixas. Nas 18 execuções reais com o Gemini, foram 4 julgamentos em 15 execuções com ciclo, e a
  identidade do provedor que julgou ficava gravada só como "roteador". O custo de manter era real
  (ciclo de regeneração seletiva, cinco modelos de domínio, schema, testes); o benefício, quase nulo.
- **A Qualidade (Jev, ADR 0035) e a Fidelidade (ADR 0036)** olham cada Célula depois do determinístico e
  cobrem o que o Judge prometia (desenvolvimento, completude, fidelidade à Ata), por Célula e sempre.
- **O SambaNova passou a exigir cartão.** O teste de fumaça de 14/10/2026 voltou HTTP 402
  `PAYMENT_METHOD_REQUIRED` com saldo zero, e o orçamento é R$ 0 (mesmo caso da Cerebras, ADR 0007).

## Decisão

1. **O LLM Judge transversal sai.** Saem `AgenteAvaliadorTransversal`, o ciclo `rodar_ciclo_transversal`
   (regeneração seletiva pelas personas, no máximo duas correções transversais), as pendências H4 do
   Judge e os modelos `JulgamentoTransversal`, `ProblemaTransversal`, `CorrecaoTransversalAplicada`,
   `ResultadoCicloTransversal` e seus enumerados. `Execucao.ciclo_transversal` deixa de existir: as execuções
   antigas em disco continuam abrindo, porque o campo extra é ignorado.
2. **Fica a conferência determinística da Matriz** (`avaliar_matriz`, sem LLM): quantidade, unicidade,
   aprovação e referências das Células pedidas. Ela continua gravada em `Execucao.avaliacao_transversal`.
3. **O Jev está sempre ligado.** Sem `SUNO_JEV` no ambiente, a Qualidade vale ligada, desde que haja a
   chave (`JEV_API_KEY`). Só `SUNO_JEV=0` (os testes) e `--sem-jev` o desligam. Sem chave, o Laudo sai
   sem Qualidade e o log avisa.
4. **O SambaNova sai de todas as filas.** `suno.provedores.sambanova`, a variável `SAMBANOVA_*` e as
   ordens do roteador perdem o provedor. O Groq passa a ser a reserva do Gemini na geração.
5. **O Comitê de dois juízes-LLM foi removido** (decidido em 15/10/2026, depois de confirmado que não estava em
   uso). Sem o SambaNova sobram Groq e Gemini, e o Gemini gera: o juiz nunca pode ser quem gerou (ADR 0008), então
   ele já não montava. Saem o módulo `suno.comite`, a flag `--comite`, `SUNO_COMITE`, `Laudo.comite`,
   `Execucao.comite_ligado`, o papel `PapelLLM.JUIZ`, a fila H3 (desempate) e o estado de Medida `revisao_humana`.
   A Qualidade (Jev) cobre tom e clareza em todos os Formatos, e a Fidelidade cobre o que o Comitê não tocava.

## Consequências

- **Menos LLM por Matriz:** o Judge fazia de 1 a 3 chamadas extras por Matriz aprovada. A Qualidade custa
  uma chamada por Célula que passou no determinístico, e o checador (opcional) outra.
- **Não há mais revisão da Matriz como conjunto.** Contradição entre Células (progressão entre Audiências,
  consistência entre Formatos) deixa de ser conferida por qualquer camada. Era o que o Judge prometia e
  quase nunca chegava a fazer, mas a lacuna agora é aberta.
- **O Jev roda em créditos da Netlify** (plano Free, 300 créditos), não de graça sem limite: o orçamento
  "R$ 0" se sustenta enquanto a conta ficar no plano gratuito. O gasto por chamada não foi medido.
- **Geração e juízes ficam em dois provedores gratuitos** (Gemini e Groq), sem reserva para o Groq.
