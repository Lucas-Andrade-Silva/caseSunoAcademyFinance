# 0030 — O Carrossel tem famílias visuais, recriadas dos posts reais da Suno

## Status

Aceita. Amplia o [ADR 0020](0020-carrossel-em-templates-html-renderizados-pelo-puppeteer.md) e o
[ADR 0024](0024-diretor-de-arte-ia-com-fallback-deterministico.md); não os revoga.

## Contexto

Os seis layouts escuros do ADR 0020 foram inventados pela equipe. A Suno entregou cinco
carrosséis reais (`templates/suno/`) e o visual deles é outro: miolo claro, título vermelho ou em
condensada pesada, números em vermelho, capa com foto, papel rasgado numa conta e aviso legal em
outra. Imitar o estilo de cada conta exige tratar o carrossel como um conjunto, não como slides
soltos de uma lista única.

## Decisão

**Família visual** é o conjunto coerente de layouts de uma conta: `noticia`, `explicativo`,
`jornal` (Suno Notícias), `dados`, `asset` (Suno Asset) e `suno_escuro` (os seis antigos). Um
carrossel usa **uma** família e os slides variam de layout dentro dela, como nos posts reais.

- Cada layout continua sendo um valor de `ComposicaoCarrossel`, prefixado pela família
  (`explicativo_capa`, `dados_numero_gigante`, ...). Histórico, referências e API seguem sem
  migração.
- Cada família é **autodescritiva**: `src/suno/pacote/templates/familias/<familia>/familia.json`
  declara, por layout, papéis compatíveis, uso de imagem, exigência de dado, cor de fundo para o
  contraste, pontuação por papel, slots e a referência visual semeada no banco. O HTML marca o
  conteúdo variável com `data-slot`; `suno.pacote.familias` troca só esse conteúdo.
  Cada template continua renderizável sozinho, com o texto de exemplo.
- O planejador recebe a família (`planejar_direcao_de_arte(..., familia=)`) e o Diretor de Arte IA
  também: o catálogo, as referências e a validação ficam restritos a ela.
  `escolher_familia` decide: a referência escolhida na curadoria manda; senão vence a família menos
  usada no histórico recente que cobre todos os slides, com desempate por hash do conteúdo.
- A escolha automática usa `noticia`, `explicativo`, `jornal` e `dados`. **`asset` só entra por
  pedido**: carrega a marca e o aviso legal da Suno Asset (fundos).
- As famílias existem só no motor de navegador. A reserva Pillow segue com o layout escuro e não
  usa foto; é o que a suíte do CI roda (ADR 0020).

### Texto de tamanho variável

O Gerador escreve títulos de ~35 caracteres e corpos de ~150 num parágrafo só; os templates foram
calibrados para o texto de exemplo. Todo texto vai num contêiner `data-ajustar` com altura máxima,
dimensionado em `em`; um script encolhe a letra de 2 em 2 px até caber (mínimo 26 px). O estouro
real é `scrollHeight > clientHeight` com folga de um quarto da letra: o leading apertado faz o
contorno do glifo passar da linha em ~5 px, e a regra de 1 px do render antigo levaria todo texto
ao mínimo.

### Nenhum campo de texto novo

O Avaliador julga `titulo + corpo` do slide. Por isso o `Slide` não ganhou campo de texto: a frase
em vermelho dos layouts é a **última frase do corpo**, e todo texto fixo dos layouts é neutro (sem
recomendação, sem promessa, sem número). O único campo novo é `Slide.imagem`, o assunto da foto,
que não aparece no post ([ADR 0031](0031-fotos-reais-e-licenciadas-nos-slides.md)).

## Consequências

- 17 layouts novos de 20 recriados. Ficam de fora, por exigirem dado estruturado que o sistema não
  produz: `jornal_painel` (série de rentabilidade), `dados_linha_do_tempo` (três colunas) e
  `asset_tabela` (tabela de fundos).
- O editor da guia Carrossel (navegador) continua desenhando só as seis composições antigas. As
  referências das famílias aparecem na lista de exemplos com a miniatura renderizada pelo servidor.
- A recriação é fiel mas não idêntica: fontes (Montserrat e a serifa de exibição do original não
  estão no conjunto OFL do projeto), ilustrações 3D, o papel rasgado (gerado por SVG) e as alças de
  seleção de texto da capa Notícia.
- `asset_aviso` mostra o título do slide e o texto jurídico fixo da Suno Asset; o `corpo` gerado
  não aparece na imagem. A família é explícita justamente por isso.
