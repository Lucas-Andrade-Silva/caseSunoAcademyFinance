# Calibração — o formato do arquivo de rótulos

A Calibração é o conjunto de Células rotuladas à mão que justifica cada Limiar. Sem ela,
os Limiares de `LIMIARES_PROVISORIOS` são as faixas publicadas pelo NILC e nada mais — é
o que o campo `origem` dessas faixas diz em texto: `"NILC, aguardando Calibração"`.

Este arquivo descreve **como** as duas pessoas do time preenchem `rotulos.csv`. Ele não
contém rótulo nenhum. `rotulos.exemplo.csv` também não: as duas linhas de lá estão
marcadas com `pessoa=exemplo` e servem só para mostrar o formato.

## O arquivo

- Nome: `data/calibracao/rotulos.csv` (o `.exemplo.csv` fica versionado ao lado; o de
  verdade entra quando existir).
- CSV, UTF-8, separador `;`. É o que o Excel em português escreve e lê sem perguntar
  nada. O leitor (`suno.avaliador.calibracao.ler_rotulos`) aceita o BOM que o Excel do
  Windows põe no começo.
- Uma linha por **(Célula, pessoa)**. Trinta Células rotuladas pelas duas pessoas dão
  sessenta linhas.
- Cabeçalho exato, nesta ordem:

```
execucao;audiencia;formato;rodada;pessoa;audiencia_percebida;aprovaria;motivo;observacao
```

## As colunas

| Coluna | O que vai nela |
|---|---|
| `execucao` | Identificador da pasta em `data/execucoes/`, ex. `2026-09-18T14-02-copom-280`. |
| `audiencia` | A Audiência **pretendida** da Célula: `iniciante`, `intermediario` ou `avancado`. Sai da Matriz, não da sua opinião. |
| `formato` | `texto_analitico`, `carrossel` ou `roteiro`. |
| `rodada` | `0` para a Célula original; `1` ou `2` para as do Ciclo de correção. |
| `pessoa` | Quem rotulou. Um apelido curto e estável, sempre o mesmo. Nunca `exemplo`. |
| `audiencia_percebida` | A Audiência para a qual **você acha** que este texto está calibrado. As mesmas três opções. É a coluna que vira a matriz de confusão. |
| `aprovaria` | `sim` ou `nao`: você publicaria esta Célula para a Audiência pretendida? |
| `motivo` | Texto livre, curto, só quando `aprovaria=nao`. "Frase longa demais", "usa Selic sem explicar", "número não bate". |
| `observacao` | Texto livre, opcional. O que não coube em `motivo`. |

Vírgula dentro de `motivo` ou `observacao` não atrapalha (o separador é `;`), mas ponto e
vírgula atrapalha: troque por vírgula.

## Como rotular: às cegas

Rótulo que enxergou o Laudo não é rótulo, é concordância com o Laudo — e aí o Kappa mede
a nossa própria obediência à métrica, não a opinião de duas pessoas.

1. Abra a Célula pelo texto, não pela interface do Avaliador: `data/execucoes/<id>/` tem
   as Células gravadas. Não abra o `execucao.json` aberto no Laudo ao lado.
2. Leia o texto inteiro uma vez, sem voltar.
3. Responda `audiencia_percebida` antes de qualquer outra coisa, pela pergunta: *"para
   quem este texto foi escrito?"* — não *"para quem ele deveria ter sido escrito?"*.
4. Só então olhe qual era a Audiência pretendida e preencha `aprovaria` e `motivo`.
5. As duas pessoas rotulam **separadamente**, sem conversar sobre as Células, e só
   comparam depois de as duas terem terminado. Conversar antes infla o Kappa.
6. Rotule as Células em ordem embaralhada, não na ordem da Matriz: rotular as três do
   Iniciante em sequência cria inércia.

Meta de volume: **~30 Células**, as duas pessoas rotulando as mesmas trinta.

## O que a Calibração produz

- `matriz_de_confusao(caminho)` — Audiência pretendida × `audiencia_percebida`, agregada
  ou filtrada por `pessoa`. A diagonal é acerto de calibragem; o que cai fora dela diz
  para onde o Gerador está escorregando. Mais massa acima da diagonal (pretendido
  Iniciante, percebido Intermediário ou Avançado) é o *overshoot* que o ADR 0002
  descreve: LLM pedido para escrever fácil escreve mais difícil do que pediram.
- `kappa_do_arquivo(caminho, pessoa_a, pessoa_b)` — o Kappa de Cohen entre as duas
  pessoas sobre as Células que **as duas** rotularam, pareadas por
  `(execucao, audiencia, formato, rodada)` e não pela ordem das linhas.

## O Kappa alvo é 0,6–0,8

O ADR 0002 põe a faixa: `KAPPA_ALVO = (0.6, 0.8)`, e `dentro_do_alvo(kappa)` responde.

- **Abaixo de 0,6**: as duas pessoas não estão vendo a mesma coisa. Não dá para mover
  Limiar com base nesses rótulos. Alinhe o critério — não as respostas — e rotule de
  novo.
- **Entre 0,6 e 0,8**: concordância substancial. É o que sustenta ajustar um Limiar e
  reportar no Entregável 6 que ele foi ajustado.
- **Acima de 0,8 em ~30 Células**: desconfie. Normalmente quer dizer que as duas pessoas
  rotularam juntas, ou que uma delas viu o Laudo. Vale conferir o item 5 acima antes de
  comemorar.
- **`nan`**: não há base. Nenhuma Célula em comum, ou as duas usaram uma categoria só —
  aí não há acaso a descontar. `nan` é diferente de zero, e zero aqui seria uma mentira
  confortável.

## Enquanto a Calibração não existe

O relatório mostra a matriz **automática**, produzida por
`matriz_de_confusao_da_execucao(execucao)`: ela cruza a Audiência pretendida com a
Audiência em que o Flesch-BR medido colocaria o texto, pelas faixas do NILC. Essa matriz
não tem rótulo humano nenhum, e sai carimbada com `origem: "NILC, aguardando
Calibração"`. Citá-la como concordância entre pessoas seria falsificar o Entregável 2.
