# ADR 0027 — o Eval visual auxilia o H5 e a aprovação humana fecha o ciclo

## Decisão

O Eval existente passa a avaliar automaticamente a folha de contato do Carrossel quando há um
provedor multimodal configurado. Não criamos outro agente. Em uma única chamada por Carrossel,
o Eval registra legibilidade, coerência visual e aderência à marca, além de indicar se o artefato
parece quebrado.

O parecer é consultivo. Ausência, erro ou resposta inválida do provedor não bloqueia o Pacote e
jamais aprova ou reprova a Célula. A pessoa continua vendo o artefato no H5 e decide se vai usá-lo.

A aprovação humana grava no mesmo SQLite uma linha idempotente por execução, audiência e formato,
junto das composições e referências efetivamente renderizadas. Nome e observação do revisor ficam
locais. O Diretor de Arte recebe somente contagens agregadas de composições e referências antes
aprovadas, tratadas no prompt como preferência fraca: compatibilidade, clareza e diversidade
continuam obrigatórias.

## Migração e rollback

A migração cria apenas a tabela `feedback_visual_pacotes`; nenhuma tabela existente é alterada.
Código anterior ignora a tabela e continua lendo `pacote.json`, portanto o rollback consiste em
voltar ao leitor anterior sem remover dados. O campo booleano `aprovado_por_humano` foi mantido
para compatibilidade; o novo `feedback_visual_humano` é opcional.

## Consequências

- Um parecer do Eval nunca é confundido com aprovação humana.
- Remontar a mesma execução não usa o próprio feedback anterior como preferência.
- Aprovar duas vezes o mesmo Pacote atualiza o sinal, sem aumentar artificialmente a contagem.
- O aprendizado é contextual, não treinamento ou ajuste automático de pesos do modelo.
