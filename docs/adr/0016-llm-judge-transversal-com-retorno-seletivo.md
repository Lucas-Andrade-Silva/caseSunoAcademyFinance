# LLM Judge transversal com retorno seletivo

A Matriz pode ter nove Células individualmente corretas e ainda assim apresentar repetição,
contradição editorial, salto inadequado entre personas ou formatos que contam histórias
incompatíveis. Essas propriedades não cabem nas métricas determinísticas de uma Célula isolada.

Adotamos um LLM Judge transversal depois da aprovação determinística das nove Células.

1. Integridade, Flesch-BR, Léxico/Densidade, Aderência e Recomendação continuam soberanos.
2. Matriz reprovada por regra fixa nunca chega ao Judge.
3. O Judge devolve schema fechado: `aprovado`, `corrigivel` ou `grave`.
4. Todo problema localiza Audiência e Formato, cita evidência e prescreve uma correção.
5. `corrigivel` regenera somente as Células afetadas pela persona responsável.
6. Toda regeneração repassa pelas regras determinísticas antes do Judge seguinte.
7. O teto é de duas correções transversais. Esgotamento, falha ou `grave` vai para H4.
8. A versão substituída, as instruções e cada julgamento ficam no `execucao.json`.
9. O Pacote de publicação só nasce quando o ciclo transversal termina aprovado.

O Judge usa o provedor ativo sob o papel `JUIZ`. Sua decisão nunca libera uma falha
determinística. A identidade do provedor fica gravada para auditoria. Usar o mesmo modelo que
gerou pode introduzir autopreferência; o risco é limitado ao julgamento editorial, enquanto fatos,
números, léxico e conformidade permanecem protegidos por código. Uma segunda credencial pode
separar os provedores depois, sem mudar o contrato do ciclo.

O fluxo tem estados e limites fixos. Uma função Python explícita o orquestra; LangGraph e MCP não
entram enquanto não houver pausa persistente, retomada distribuída ou escolha dinâmica de tools.
