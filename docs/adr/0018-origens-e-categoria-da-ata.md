# Origens e categoria da Ata: o Copom é o único calibrado

A guia Fontes traz Atas de fora do Copom: Fatos Relevantes da CVM e documentos importados. O
Avaliador foi calibrado só com Atas do Copom: as Âncoras essenciais (`selic_decidida`,
`data_reuniao`, `placar_votacao`), os Limiares e o Léxico.

Decidimos que **toda Ata tem uma `categoria`** (`copom`, `comunicado_relevante`, `release`,
`importada`) e que a categoria escolhe o conjunto de Âncoras essenciais:

- **Copom:** o conjunto de sempre. Nada muda para quem só usa o Copom.
- **Demais categorias:** `data_do_comunicado` (uma data de verdade achada no texto) e
  `numero_principal` (o primeiro valor em reais, ou o primeiro número que não seja data), as duas por
  regra fixa. O LLM só escolhe e nomeia até 12 números a mais, nunca decide se a extração está completa.

A Saída de uma categoria diferente do Copom leva o selo **não calibrado** em todas as telas. Os
Limiares e o Léxico continuam os do Copom: o Laudo vale como triagem, não como a mesma régua.

O código usa `Origem` e `Ata`, não `Fonte` e `ItemDeFonte`: "fonte" e "item" estão na lista _Avoid_ de
**Ata** e de **Célula**. "Fonte" e "item" ficam como rótulo de tela, como "Saída".

## O que a costura mudou

`avaliar(conteudo, ancoras, audiencia, ...)` ganhou `chaves_essenciais`, opcional, com o padrão do
Copom ([ADR 0001](0001-gerador-e-avaliador-como-modulos-separados.md): a costura continua
`(Conteúdo, Âncora[], Audiência) → Laudo`). O Ciclo só passa o conjunto genérico quando a Ata não é
do Copom; o Copom segue pelo caminho de antes.

## Um achado da primeira execução real

O adaptador da CVM, rodado de verdade em 2026-10-10, baixou o Fato Relevante mais recente
(Porto Seguro, pedido de cancelamento de registro): tem a data e **nenhum número com unidade**. Pelo
conjunto genérico, toda Célula reprovaria por `falha de extração` e a geração só gastaria cota. Por
isso o resumo de cada Ata traz `extracao_completa`, a sugestão da curadoria prefere quem consegue
gerar, o cartão mostra "sem número" e a rota recusa o pedido com o motivo.

Quais chaves valem de fato para um comunicado fora do Copom é decisão da pessoa dona do Avaliador.
Exigir um número deixa de fora comunicados puramente administrativos; aceitar só a data os deixaria
entrar sem nada a conferir na Aderência.

## Alternativas recusadas

- **Medir Limiares para Fatos Relevantes.** Exigiria rotular à mão um conjunto novo de comunicados.
  Não cabe nas duas semanas, e o selo diz com franqueza o que não foi medido.
- **Tratar toda Ata como Copom e deixar o LLM achar o que der.** Reprovaria tudo por extração sem
  explicar, e o pedido de extração falaria de Selic para um comunicado de aquisição.
- **Guardar a categoria só no catálogo.** A `execucao.json` precisa dizer sozinha se a Saída é
  calibrada: o arquivo é a fonte de verdade ([ADR 0006](0006-atas-do-copom-como-documento-fonte-principal.md)).

## Onde ficam os arquivos

O Copom continua em `data/atas/` (versionado: a demo roda sem rede). As outras Origens ficam em
`data/fontes/<origem>/`, fora do git. `data/fontes/catalogo.json` é versionado; o que a pessoa liga e
desliga fica em `data/fontes/preferencias.json`, fora do git. A CVM respeita o `Crawl-Delay: 10`, tenta
o zip do ano corrente e cai para o anterior, e detecta PDF pelos bytes `%PDF`, nunca pelo
`Content-Type`.
