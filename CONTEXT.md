# Suno Content

Adapta comunicados financeiros densos para três públicos e três formatos, e julga cada
saída com métricas objetivas antes de considerá-la pronta.

## Language

### O documento e suas saídas

**Ata**:
O comunicado financeiro público que entra no sistema. Por padrão, uma ata do Copom.
_Avoid_: documento, fonte, input, PDF

**Âncora**:
Uma afirmação factual extraída da Ata — um número, uma data, uma decisão — que toda
saída derivada dela precisa preservar sem distorcer.
_Avoid_: fato, claim, evidência, ponto-chave

**Audiência**:
O nível de sofisticação do leitor a quem uma saída se destina. São três: **Iniciante**,
**Intermediário** e **Avançado**.
_Avoid_: persona, público, nível, perfil

**Formato**:
A forma que uma saída assume. São três: **Texto analítico**, **Carrossel** e
**Roteiro**.
_Avoid_: mídia, tipo, canal

**Célula**:
Uma saída concreta, para uma Audiência num Formato. "Iniciante × Carrossel" é uma
Célula.
_Avoid_: variante, versão, output, item

**Matriz**:
O conjunto das nove Células geradas a partir de uma Ata.
_Avoid_: grade, tabela, combinações

### O julgamento

**Laudo**:
O resultado da avaliação de uma Célula: as métricas medidas, o veredito, e o que
precisa mudar se reprovou.
_Avoid_: score, relatório, avaliação, feedback

**Flesch-BR**:
O índice de facilidade de leitura adaptado ao português brasileiro, usado para aferir
se a Célula está calibrada para a sua Audiência.
_Avoid_: legibilidade, Flesch-Kincaid, readability

**Densidade**:
A proporção de termos do Léxico presentes na Célula, e se apareceram acompanhados de
explicação quando a Audiência exigia.
_Avoid_: jargão, complexidade, technical density

**Aderência**:
O grau em que as afirmações da Célula correspondem às Âncoras da Ata de origem.
_Avoid_: fidelidade, grounding, factualidade, veracidade

**Recomendação**:
Sugestão de compra, venda ou manutenção de um ativo, ou promessa de retorno. É o que o
sistema está proibido de produzir, e o Laudo reprova a Célula que contiver uma.
_Avoid_: conselho, dica, call, sugestão de investimento

**Limiar**:
O valor que uma métrica precisa atingir para a Célula ser aprovada naquela Audiência.
_Avoid_: threshold, corte, nota mínima, meta

**Ciclo de correção**:
A reescrita de uma Célula reprovada, guiada pelo Laudo que a reprovou.
_Avoid_: retry, reflection loop, refinamento, iteração

### Insumos e entregas

**Léxico**:
A lista de termos do mercado financeiro brasileiro contra a qual a Densidade é medida.
Distinto deste glossário, que define a linguagem do projeto.
_Avoid_: glossário, dicionário, vocabulário

**Calibração**:
O conjunto de Atas e Células rotuladas à mão que justifica cada Limiar.
_Avoid_: dataset, golden set, baseline, amostra

**Pacote de publicação**:
O conjunto pronto para um humano publicar: vídeo, legenda, hashtags e imagens de uma
Célula aprovada.
_Avoid_: post, bundle, export, entrega
