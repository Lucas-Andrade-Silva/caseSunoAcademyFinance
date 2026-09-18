# O roteador de provedores fica atrás de uma interface única e distingue o tipo de erro antes de trocar

O orçamento é R$ 0 (ver [docs/research/viabilidade-tecnica.md §4](../research/viabilidade-tecnica.md)),
então o pipeline depende de três contas de tier gratuito — Gemini gera, Groq julga, SambaNova
Cloud é reserva —, cada uma com uma cota diferente e um jeito diferente de recusar quando estoura. Um
roteador ingênuo que trata todo 429 do mesmo jeito, ou que reconstrói o cliente do zero ao trocar
de provedor, quebra de duas formas específicas que dois projetos irmãos já sofreram na prática e
documentaram.

A primeira: nem todo 429 pede troca de provedor. Cota por minuto se resolve sozinha em segundos;
cota diária ou total, não. Tratar as duas do mesmo jeito ou esgota a cota do próximo provedor por
um erro que ia passar sozinho, ou fica esperando um erro que nunca vai passar. O roteador precisa
ler a mensagem de erro de cada provedor para saber qual dos dois é, e usar o tempo de espera que o
próprio provedor sugerir quando ele vier na mensagem.

A segunda: trocar de provedor não pode perder a capacidade de pedir saída estruturada (o schema da
Célula) ou tool-calling, se algum papel do pipeline depender disso. Reconstruir o cliente sem
reaplicar essas capacidades produz uma falha silenciosa — o pipeline continua rodando, mas o papel
afetado perde uma capacidade que o resto do código assume que existe.

Adotamos: uma interface única de provedor — nenhum outro módulo importa o SDK do Gemini, da Groq ou
da SambaNova diretamente —, com uma lista ordenada de fallback (Gemini → Groq → SambaNova), detecção
do tipo de erro por provedor antes de decidir entre esperar e trocar, e reaplicação explícita de
qualquer binding de schema ou tool ao trocar de cliente.

## Consequências

A lista de modelos gratuitos por provedor deve ser consultada, não fixada em código — um modelo
pode sair do tier gratuito sem aviso (aconteceu com o Gemini Pro em abr/2026, e com modelos do
OpenRouter durante o desenvolvimento de um projeto irmão). Isso é responsabilidade da configuração,
não da arquitetura do roteador.

Um LLM falso e roteirizado — fila de respostas programadas, sem chamada de API real — cobre a
lógica de troca de provedor em teste, sem custo e sem depender de rede. É o que mantém essa suíte
rodando em CI junto com o resto do pipeline.

## Nota de atualização (15/09/2026)

A reserva original desta decisão era Cerebras. Pesquisa de viabilidade confirmou, contra a
documentação oficial da Cerebras, que o tier gratuito permanente foi encerrado em 17/08/2026 —
contas novas exigem cartão de crédito verificado para US$5 em créditos que expiram em 30 dias.
Isso viola o orçamento R$0 do projeto mesmo sem cobrança efetiva (é uma barreira de entrada que
o caso não pode assumir que toda dupla vai querer cruzar). Trocamos a reserva para **SambaNova
Cloud**, que roda o mesmo modelo usado na Groq (`gpt-oss-120b`) em tier gratuito sem cartão — o
que também simplifica manter o mesmo schema de saída estruturada entre os dois provedores.

Cota do Gemini também está mais instável do que quando esta pesquisa começou: o próprio Google
parou de publicar limites fixos na documentação oficial e recomenda checar o painel ao vivo do
AI Studio, depois de um corte não avisado de 50–92% no free tier em dez/2025. Não muda a decisão
de arquitetura, mas reforça o ponto já registrado nas Consequências: nunca fixar cota em código.
