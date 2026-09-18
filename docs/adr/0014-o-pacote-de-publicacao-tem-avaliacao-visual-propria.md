# O Pacote de publicação tem avaliação visual própria, e ela não reprova a Célula

O [ADR 0009](0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md) fecha a imagem do
Carrossel em template determinístico, e o [ADR 0004](0004-renderizacao-de-video-fora-do-grafo.md)
deixa o vídeo fora do grafo. Nenhum dos dois responde a uma pergunta que sobra: **quem olha o
resultado?**

O Avaliador julga o texto da Célula, e o julga antes da renderização existir. Um render
determinístico pode estar tecnicamente correto e visualmente quebrado: texto estourando a caixa,
rótulo sobreposto no gráfico, contraste ilegível, slide com espaço vazio onde devia ter dado. O
texto passou; a imagem que carrega esse texto não foi olhada por ninguém.

Decisão: o Pacote de publicação ganha uma etapa de **avaliação visual**, em duas camadas, no mesmo
padrão que o resto do projeto já usa — determinístico primeiro, LLM como camada aditiva.

## Camada determinística, sempre ligada

Roda sem rede e sem modelo, e é a que decide se o render precisa ser refeito:

- **Estouro de caixa.** O Pillow mede a caixa do texto renderizado e compara com a região
  reservada. Isso é medição, não opinião, e juiz multimodal nenhum faz melhor.
- **Contraste**, pela razão de luminância entre texto e fundo, contra o mínimo de acessibilidade.
- **Dimensão e proporção**: 1080×1350 exatos em todo slide, 9:16 no vídeo.
- **Número na imagem contra a tabela de Âncoras numéricas** do
  [ADR 0011](0011-ancoras-numericas-sao-citadas-nunca-reescritas.md). O número que aparece no
  gráfico tem a mesma obrigação do número que aparece no texto.
- **Duração e presença de trilha de áudio** no vídeo.

Falha aqui é **defeito de render**: refazer o render, não reescrever a Célula.

## Camada de juiz multimodal, opcional

Um juiz de visão olha o artefato pronto e responde o que não se mede: isto parece quebrado?
O layout está equilibrado? O gráfico comunica o que a legenda diz que comunica? A pergunta é
holística de propósito — aqui não há um número a atingir, e por isso é o único lugar do projeto
onde um juiz holístico é aceitável.

Quatro restrições:

**O juiz visual nunca julga compliance.** Ausência de Recomendação é verificada no texto da
Célula, antes da renderização, pelas regras do
[ADR 0012](0012-recomendacao-detectada-por-padrao-sintatico-nao-por-lista-de-palavras.md). O
mesmo argumento do [ADR 0008](0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md) vale
aqui e vale mais: um veredito que reprova não pode mudar entre duas execuções do mesmo input.

**A regra de autopreferência do ADR 0008 não se aplica.** Ela existe porque um modelo avalia
melhor o que ele mesmo produziu. A imagem não foi produzida por modelo nenhum — saiu de matplotlib
e Pillow — então o juiz visual pode rodar em qualquer provedor, inclusive no mesmo que gerou o
texto. É uma exceção com razão, não um descuido.

**Só o Carrossel vai a juiz de visão.** O vídeo não passa por juiz nenhum — nem por amostragem de
quadros, nem inteiro. Ele fica coberto apenas pela camada determinística: duração, proporção e
presença de áudio.

**O Carrossel é julgado em folha de contato, não slide por slide.** Três Células de Carrossel a
seis slides são 18 imagens por Ata; uma chamada de visão por imagem não cabe no tier gratuito. Os
slides de uma Célula são compostos numa única imagem em grade e julgados juntos — o que também
deixa o juiz ver inconsistência entre slides, que é o defeito mais provável e o que ele avaliaria
pior isolado. São três chamadas de visão por Ata.

## O resultado alimenta o humano, não o Laudo

A avaliação visual **não entra no Laudo e não reprova a Célula**. A Célula já foi aprovada como
texto, e o Ciclo de correção do
[ADR 0013](0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md) não
conserta um rótulo sobreposto — reescrever o texto é a ferramenta errada para um problema de
render.

O resultado é anexado ao Pacote e apresentado no **H5**, a aprovação humana que já existia no
fluxo. O que antes era "um humano olha e decide" passa a ser "um humano olha, com uma lista do que
o sistema achou suspeito". O ponto de decisão continua sendo humano; ele só deixa de ser cego.

## Consequências

Isto fica **abaixo da linha dos seis entregáveis**. A camada determinística é barata e roda em CI,
então entra junto com o render. O juiz multimodal é extensão: se o prazo apertar, ele cai antes de
qualquer coisa que valha nota, e o H5 volta a ser inspeção humana sem lista — que é como estava.

**NÃO VERIFICADO:** cota de entrada de imagem no tier gratuito do Gemini, e quais modelos de visão
Groq e SambaNova expõem hoje. Precisa ir para
[viabilidade-tecnica.md](../research/viabilidade-tecnica.md) antes de qualquer implementação, no
mesmo padrão dos outros provedores.

O **vídeo está deliberadamente fora do juiz de visão**, e a amostragem de quadros foi considerada
e recusada. Três razões, na ordem em que pesam. O vídeo já é o artefato mais frágil do projeto e é
o item 3 da ordem de corte do CLAUDE.md — investir cota e código numa avaliação do que pode não
ser entregue é a troca errada. Julgar quadro amostrado é o uso mais fraco de um juiz de visão:
ele não vê movimento, ritmo nem sincronia, que é onde o vídeo realmente falha, e responde com
confiança sobre o que não observou. E o vídeo tem um revisor que a imagem não tem — alguém
assiste antes de publicar, no H5, o que para 60 segundos é revisão completa, não amostra.

A camada determinística cobre o vídeo desde o início, e é ela que pega a falha que passa
desapercebida numa exibição: proporção errada, áudio ausente, duração fora da faixa da plataforma.
