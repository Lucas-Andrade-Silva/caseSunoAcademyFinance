# O Ciclo de correção tem teto de duas rodadas, e o que sobra vai para revisão humana

O Ciclo de correção reescreve a Célula reprovada guiado pelo Laudo. Sem teto, ele é um loop: uma
Célula que o Gerador não consegue consertar consome cota até a execução morrer, e numa Matriz de
nove Células basta uma teimosa para travar a demo.

Decisão: **duas rodadas, no máximo**. A literatura de controle de nível de leitura mede o ganho
concentrado na primeira rodada (RMSE caindo de 0,755 para 0,552 com uma rodada de feedback do
score real); a terceira não paga a cota que custa.

O feedback é **o valor medido, não uma instrução genérica**. O Gerador recebe "Flesch-BR medido
47,2; o Limiar da Audiência Iniciante é 50" em vez de "simplifique o texto". A correção precisa
saber de quanto é a distância.

Célula que reprova depois da segunda rodada não é descartada nem publicada: entra na **fila de
revisão humana**, com o Laudo que a reprovou e o histórico das tentativas. A interface mostra
essa fila; um humano decide entre reescrever à mão, ajustar o Limiar, ou aceitar que aquela
combinação de Audiência e Formato não funciona para aquela Ata.

## Falha de extração é motivo de reprovação distinto

Um pipeline fixo sem agente tem um modo de falha real: uma Ata fora do padrão testado — seção
faltando, tabela em formato diferente — faz a extração degradar silenciosamente, e o sistema gera
nove Células bem escritas sobre dados incompletos.

A resposta não é virar agente ([ADR 0010](0010-gerador-nao-e-agente-com-tools-nem-usa-mcp.md)
continua valendo). É o Avaliador reprovar por isso: se a tabela de Âncoras numéricas do
[ADR 0011](0011-ancoras-numericas-sao-citadas-nunca-reescritas.md) vier incompleta, o Laudo
reprova a Célula com motivo `falha de extração`, e essa reprovação **não** aciona o Ciclo de
correção — reescrever não conserta um documento mal lido. Vai direto para revisão humana.

## Consequências

O Laudo passa a ter três destinos, não dois: aprovado, reprovado com correção possível, e
reprovado para revisão humana. A interface precisa expor os três, e a view de reprovação mostra
qual foi e por quê.

Motivo de reprovação vira um valor enumerado no Laudo — Flesch-BR, Densidade, Aderência,
Recomendação, falha de extração — e não texto livre. É o que permite contar reprovações por tipo
no relatório final.

O teto de duas rodadas limita o custo por Ata a um número previsível: 9 Células vezes até 3
gerações (original mais 2 correções) dá 27 chamadas de Gerador no pior caso. Isso cabe no tier
gratuito e é o que torna o orçamento de R$ 0 uma afirmação verificável, não uma esperança.
