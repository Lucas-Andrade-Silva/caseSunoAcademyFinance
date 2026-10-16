# 0035 — A Qualidade: o Jev dá uma nota por dimensão e, abaixo do Limiar, a Célula é escrita de novo

## Status

Aceita (14/10/2026). **Atualiza o [ADR 0008](0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md):**
o Comitê informa e nunca reprova; a Qualidade reprova. As duas camadas convivem, e a Qualidade
é a que o Ciclo de correção lê.

## Contexto

As cinco medidas determinísticas não alcançam o que um leitor nota primeiro: a ideia desenvolvida
ou jogada em fatos soltos, o texto cortado no meio, a frase que não se lê de primeira. O Comitê
(dois juízes-LLM, seis chamadas por Célula, só Texto e Carrossel, desligado, sem poder de reprovar)
não resolve isso, e o Judge transversal (ADR 0016) só roda quando as nove Células já passaram nas
regras fixas, o que quase não acontece com modelo real.

O Jev (TypeSafe AI, setembro de 2026) é um modelo que não gera texto: recebe um estado e perguntas
com níveis ordenados e devolve, para cada pergunta, uma nota ponderada pela probabilidade e uma
confiança, tudo numa chamada.

## Decisão

1. **Depois do determinístico, e só se ele aprovou.** `avaliar(..., qualidade=...)` consulta o Jev
   quando as cinco medidas passaram. Célula já reprovada por Flesch-BR ou Aderência não gasta chamada.
2. **Quatro perguntas `score` numa chamada, uma por dimensão:** desenvolvimento, completude (o texto
   foi cortado?), clareza e tom. Quatro níveis cada, do pior ao melhor, escritos em
   `suno.avaliador.qualidade.DIMENSOES`. Vale para os **três Formatos**, o Roteiro inclusive: o Jev
   lê a fala, não a rubrica de cena.
3. **A Medida carrega a menor das quatro notas, em 0 a 1.** Uma porcentagem só esconderia qual
   dimensão falhou. A Correção nomeia cada dimensão abaixo do Limiar e o nível que o Jev viu nela
   ("desenvolvimento 33% (visto: lista fatos soltos…)"), com o valor medido e o Limiar, como manda o
   [ADR 0013](0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md).
4. **Abaixo do Limiar a Célula volta ao Gerador**, dentro do mesmo teto de duas rodadas e com o
   rascunho anterior na mão. O motivo é `qualidade`, enumerado como os outros. A dica ao Gerador
   proíbe "corrigir" encurtando.
5. **Falha do Jev nunca reprova.** Rede, cota, chave, resposta fora do formato: o Laudo sai sem a
   Medida, como o Comitê (ADR 0008). Ausência não é nota zero.
6. **Sempre ligado** (decidido em 15/10/2026, [ADR 0037](0037-judge-transversal-removido-jev-sempre-ligado-sem-sambanova.md)).
   Sem `SUNO_JEV` no ambiente a Qualidade vale ligada. Só `SUNO_JEV=0` (os testes, que seguem sem rede) e
   `--sem-jev` a desligam. Sem a chave (`JEV_API_KEY`), não monta e avisa no log.
7. **O endereço é configuração.** `JEV_URL` (padrão `https://api.typesafe.ai/v1/systemone`) e
   `JEV_API_KEY`. Serve a API direta e qualquer ponte que repasse o mesmo corpo, como uma Netlify
   Function. `SUNO_JEV_LIMIAR` troca o Limiar sem mexer no código.

## Consequências

- **Um classificador entra no veredito.** A frase "o veredito é só código" passa a ser "o veredito é
  código mais um classificador de saída tipada". A defesa é que o Limiar é código, a saída é um número
  e a ordem é fixa: o Jev nunca libera o que o determinístico reprovou. Compliance e Aderência
  continuam fora de qualquer modelo (ADR 0008).
- **O Limiar (60%) é um chute.** Ninguém o calibrou com Células rotuladas à mão (H2), como os de
  Flesch-BR. Limiar alto demais reprova Célula boa e gasta cota; baixo demais não pega nada.
- **O Jev não explica.** Não dá justificativa nem cita trecho; a Correção só diz a dimensão, a nota e
  o nível. É por isso que a checagem de fidelidade à Ata continua sendo trabalho de um LLM que cita
  (ADR a escrever).
- **Custo de cota:** uma chamada por Célula aprovada pelo determinístico e uma a mais por rodada de
  correção. Preço e camada gratuita do Jev **não foram verificados**; o orçamento do projeto é R$ 0.
- **O Comitê foi removido** (ADR 0037): sem o SambaNova, sobrava um juiz que não é o gerador, e a Qualidade o
  substitui.
- A janela de 32 mil tokens do Jev cobre uma Célula com folga; não cobre uma Ata longa, e por isso o
  Jev nunca recebe a Ata.
