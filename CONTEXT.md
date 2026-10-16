# Suno Content

Adapta comunicados financeiros densos para três públicos e três formatos, e julga cada
saída com métricas objetivas antes de considerá-la pronta.

## Language

### O documento e suas saídas

**Ata**:
O comunicado financeiro público que entra no sistema. Por padrão, uma ata do Copom; também vale
um comunicado relevante da CVM ou um documento importado, cada um com a sua **categoria**.
_Avoid_: documento, fonte, input, PDF

**Origem**:
De onde as Atas vêm: o Copom (BCB), os Fatos Relevantes da CVM, os Releases de Resultados da B3
(ainda "em breve") e os documentos importados. Pode ser ligada ou desligada. Na tela se chama
"Fonte", e cada Ata dela é um "item": esses dois são só rótulo de tela, como "Saída".

**Destaque único** e **Visão unida**:
As duas sugestões da curadoria. O Destaque único é uma Ata só (a mais recente que consegue gerar):
todas as Células citam os mesmos fatos. A Visão unida junta de duas a cinco Atas num só conteúdo,
com cada número citando o comunicado de onde vem; só gera no modo Real e leva o selo
**não calibrado**. No código são os modos `separada` e `unida` da seleção.

**Categoria da Ata**:
`copom`, `comunicado_relevante`, `release`, `importada` ou `unida` (a Visão unida). Decide o conjunto de Âncoras
essenciais: o Copom exige a decisão, a data e o placar; as demais, uma data e um número com
unidade. Fora do Copom a Saída leva o selo **não calibrado**, porque Limiares e Léxico foram
medidos só com Atas do Copom.

**Âncora**:
Uma afirmação factual extraída da Ata — um número, uma data, uma decisão — que toda
saída derivada dela precisa preservar sem distorcer. Fora do Copom, uma Ata sem número tem como
fato central uma Âncora textual conferida contra o texto, e o conteúdo sai qualitativo
([ADR 0034](adr/0034-ata-sem-numero-gera-conteudo-qualitativo.md)).
_Avoid_: fato, claim, evidência, ponto-chave

**Audiência**:
O nível de sofisticação do leitor a quem uma saída se destina. São três: **Iniciante**,
**Intermediário** e **Avançado**.
_Avoid_: persona, público, nível, perfil

**Formato**:
A forma que uma saída assume. São três: **Texto analítico**, **Carrossel** e
**Roteiro**.
_Avoid_: mídia, tipo, canal

**Direção de cena**:
O que a edição precisa para executar um bloco do Roteiro: layout, ícone, transição, animação e
momento do texto, efeito e sons, escolhidos de um catálogo fechado. Não é texto: o único texto
na tela é a rubrica `tela`.
_Avoid_: storyboard, efeitos livres

**Plano de edição**:
O JSON versionado (para avatar sintético) e a tabela legível que descrevem, cena a cena, o vídeo
de um Roteiro aprovado. Derivado do Roteiro; não passa pelo Avaliador.
_Avoid_: prompt do vídeo, script do avatar

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

**Qualidade**:
A nota, de 0 a 100%, que o Jev (um classificador da TypeSafe AI que não gera texto) dá a uma Célula
depois das cinco medidas determinísticas, em quatro dimensões: desenvolvimento, completude (o texto foi
cortado?), clareza e tom. A Medida vale a menor das quatro. Abaixo do Limiar, a Célula volta ao Gerador
([ADR 0035](adr/0035-qualidade-pelo-jev-depois-do-deterministico.md)). Sempre ligada: só falta quando não há chave.
_Avoid_: nota do LLM, score, avaliação subjetiva

**Fidelidade**:
A conferência de uma Célula contra a Ata inteira por um LLM (Groq, com o Gemini de reserva), depois de tudo o mais ter
aprovado. O modelo aponta a afirmação que a Ata não sustenta, copiando o trecho da Célula (e o da Ata,
quando a Ata diz outra coisa); o código confere que as citações existem e descarta as que não.
Só o que a Ata contradiz ou diz de outro jeito (com o trecho da Ata conferido) reprova a Célula e o
Ciclo a devolve ao Gerador; "a Ata não diz isso" só avisa
([ADR 0036](adr/0036-fidelidade-a-ata-por-llm-que-cita-e-o-codigo-confere.md)). Explicação de termo e
analogia escritas para a Audiência não contam. É o Factuality & Grounding Checker do enunciado.
_Avoid_: grounding, factualidade, veracidade (**Aderência** é só de número)

**Tom**:
Dimensão da Qualidade: a Célula soa adequada à Audiência, sem ser condescendente
com o Iniciante nem árida demais com o Avançado.
_Avoid_: estilo

**Clareza**:
Dimensão da Qualidade: o texto se lê de primeira, sem exigir reler a frase.
_Avoid_: legibilidade (reservado ao Flesch-BR), fluência

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

**Família visual**:
O conjunto coerente de Layouts de uma conta da Suno (Notícia, Explicativo, Jornal, Dados, Asset,
mais o Suno escuro, que são os seis Layouts antigos). Um Carrossel usa uma só; os slides variam
de Layout dentro dela. Vem dos carrosséis reais da Suno em `templates/suno/`. Asset só entra por
pedido, porque carrega a marca e o aviso legal da Suno Asset.
_Avoid_: tema, estilo, template (template é o arquivo HTML de um Layout)

**Layout**:
Um tipo de slide dentro de uma Família visual (capa, texto com foto, número gigante). No código é
um valor de `ComposicaoCarrossel`, prefixado pela família.
_Avoid_: composição visual solta, modelo, página

**Foto do slide**:
A foto real que um slide mostra. O Gerador só diz o assunto (`Slide.imagem`); a foto vem da
biblioteca local ou da busca de imagens na web (Bing), com relevância verificada por um juiz de
visão e crédito na legenda. No MVP a licença não é verificada ([ADR 0032](adr/0032-fotos-da-web-pelo-bing-imagens-sem-verificar-licenca.md)).

**Assunto visual**:
A entrada do catálogo (`src/suno/imagens/assuntos.json`) que ensina a busca de foto a achar o
assunto de um slide: o nome, as consultas, o que o resultado precisa citar e o que o desclassifica
(a vitamina B3 não é a B3). Texto aprova ou descarta; o juiz de visão só decide a dúvida
([ADR 0033](adr/0033-busca-de-imagens-propria-do-mercado-e-juiz-so-na-duvida.md)).
_Avoid_: léxico (é do Avaliador)
_Avoid_: imagem gerada, banco de imagens, stock

### A interface

**Saída**:
Uma execução vista pela interface: tem um nome dado pelo usuário, registra quais Células
foram pedidas e o que foi decidido sobre cada uma. No código é a `Execucao`; "Saída" é só o
rótulo de tela.

**Decisão humana**:
Aprovar ou reprovar uma Célula, registrada com motivo (obrigatório ao reprovar) e o nome do
revisor. Não vale para a Célula cujo Laudo detectou Recomendação: essa não pode ser aprovada.

**Pedido**:
As Células que a pessoa marcou na Matriz antes de gerar: de uma a nove, em combinações soltas.
Fica gravado na Saída. Sem pedido gravado (execução antiga), valem as nove.

**Janela de notícias**:
Os últimos 30 dias. A Ingestão só mostra Atas com `data_referencia` dentro dela, e a busca nas Origens
lista só o que saiu nela; é regra do produto.

**Notícias guardadas**:
As (até 3) Atas que a pessoa marcou na Ingestão e confirmou com ATUALIZAR. Valem só na sessão do
navegador e são a entrada das guias Texto analítico, Carrossel e Vídeo. Na tela, uma Ata é uma "notícia".
