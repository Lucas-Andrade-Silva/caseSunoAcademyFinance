# As Âncoras numéricas são extraídas antes do Gerador e citadas literalmente, nunca reescritas em prosa

Aderência é a métrica que separa este sistema de um resumidor qualquer, e o número é onde ela
quebra primeiro. Se o Gerador escreve "a Selic subiu para 15% ao ano" em prosa livre, o Avaliador
só consegue conferir isso comparando texto com texto — e a comparação vira julgamento subjetivo
disfarçado de métrica.

Decisão: antes de qualquer Célula ser gerada, o sistema extrai da Ata uma **tabela estruturada de
Âncoras numéricas** — valor da Selic, variação em pontos base, IPCA, placar da votação, data da
reunião, data da próxima. Cada uma é um registro com valor, unidade e o trecho literal da Ata de
onde veio.

O Gerador não reescreve esses valores: ele **substitui em molde**. O prompt entrega a tabela e a
instrução é de preenchimento, não de redação livre do número. E o Avaliador confere cada número
presente na Célula contra a tabela — igualdade exata de valor e unidade, sem LLM, sem julgamento.
Número que aparece na Célula e não está na tabela reprova a Célula.

Essa é a correção mais citada na literatura para alucinação numérica em texto financeiro:
grounding por citação, não geração livre com verificação posterior.

## Consequências

A extração da tabela vira um estágio próprio do Gerador, anterior à Matriz, e roda uma vez por
Ata — não nove. É também o ponto onde a leitura da Ata pode falhar de forma silenciosa, e por isso
o [ADR 0013](0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md) trata
falha de extração como motivo de reprovação distinto, não como falha de Aderência.

A tabela é o insumo único de número no sistema: o texto da Célula, a legenda do Pacote de
publicação e o gráfico do Carrossel ([ADR 0009](0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md))
leem todos dela. Não existe segundo caminho pelo qual um número chegue à saída.

Números que a Ata expressa por extenso ("quinze por cento") ou de forma relativa ("acima do
projetado no trimestre anterior") não entram na tabela e continuam sujeitos só à Aderência
textual. Essa fronteira precisa estar documentada junto do extrator, porque é o lugar onde alguém
vai supor cobertura que não existe.
