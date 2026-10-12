# A Visão unida: um dossiê com chaves de Âncora prefixadas

A curadoria sugere duas pautas: o **Destaque único** (uma Ata) e a **Visão unida** (várias Atas num só
conteúdo). O pipeline foi desenhado para uma Ata por vez: `DossieCurado` tem uma `Ata` e as chaves de
Âncora (`selic_decidida`, `numero_principal`) colidiriam entre Atas diferentes.

Decidimos que a Visão unida é **uma Ata composta**, e que o resto do pipeline não muda:

- `compor_uniao` (em `gerador/curador.py`) devolve uma `Ata` de categoria `unida` com os textos sob
  cabeçalhos `[a1]`, `[a2]`… e `partes` com os identificadores. O identificador (`uniao-<hash>`) vem
  dos das partes: estável, curto, serve de nome de pasta. Vão de 2 a 5 Atas.
- A extração roda **por parte** e cada chave ganha o prefixo da parte (`a1_selic_decidida`,
  `a2_numero_principal`). O rótulo diz de onde vem o número (`[a2] Empresa Exemplo: Número principal`),
  e é o que a Célula aberta mostra ao lado do conteúdo. Nenhuma chave colide e nenhuma Âncora de uma
  parte vira a de outra.
- O conjunto essencial é o genérico **de cada parte** (`chaves_essenciais_da_ata`): se um dos
  comunicados não tem data e número com unidade, a Matriz inteira reprova por falha de extração. Reunir
  um comunicado sem nada a conferir não dá conteúdo conferível.
- O molde ganha uma instrução só para a categoria `unida`: dizer de qual comunicado vem cada número e
  nunca atribuir a um o número de outro.
- A `Execucao` grava `selecao.modo = unida` com os itens, e `categoria = unida`.

## O que não muda

O Avaliador, o Ciclo de correção e o Judge recebem uma `Ata` e uma tabela de Âncoras, como antes. A
Aderência continua conferindo cada número contra as Âncoras, agora prefixadas.

## Limites assumidos

- **Só no modo Real.** A Demo depende de respostas prontas gravadas para uma Ata; para cada combinação
  possível não há. A interface desabilita a Demo e diz por quê.
- **Não calibrado**, sempre: a categoria `unida` nunca é a do Copom.
- **Custo.** Uma chamada de extração por parte, além das Células, do Judge e das correções. O teto de
  cinco Atas existe por causa do prompt (o texto de todas viaja junto) e da cota gratuita.
- **Leitura de uma Célula citando um número de duas Atas na mesma frase** não é conferida pela regra
  fixa: o Judge transversal é quem pode apontar a mistura (a instrução do molde pede para evitá-la).

## Alternativas recusadas

- **Chaves sem prefixo, com a colisão resolvida por "a última vence".** Perderia número sem avisar, e o
  Avaliador não saberia mais de que comunicado é cada Âncora.
- **Um dossiê com uma lista de Atas** (`DossieCurado.atas`). Mudaria o Ciclo, o Judge, o molde e a
  extração; a Ata composta mexe só em quem a compõe.
- **Uma Matriz por Ata.** É o Destaque único repetido, não uma visão unida.
