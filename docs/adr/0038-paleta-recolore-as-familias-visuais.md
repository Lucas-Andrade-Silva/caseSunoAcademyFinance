# 0038 — A paleta do editor recolore as famílias visuais

## Status

Aceita. Amplia o [ADR 0030](0030-familias-visuais-do-carrossel.md); não o revoga.

## Contexto

As famílias do ADR 0030 têm as cores dos posts reais da Suno escritas no HTML de cada Layout. A
paleta do editor só valia no Suno escuro, que o navegador desenha: com uma família escolhida, trocar
a paleta não mudava nem a prévia nem o carrossel montado, e a pessoa não entendia por quê. Ela quer
poder recolorir qualquer família.

Reescrever os 17 templates com variáveis de cor seria o caminho limpo, mas mexe em todos eles e
afasta o HTML do post recriado. Mapear cada hexadecimal de cada template à mão, num manifesto, não
escala: são dezenas de cores, com degradês e transparências.

## Decisão

`suno.pacote.recolorir` troca as cores do CSS pelo **papel** que cada uma tem, não pelo valor:

- **Neutra** (branco, cinza, preto) desliza entre `fundo` e `texto` da paleta conforme a distância
  dela até o fundo do Layout, lido do `data-fundo-cor` que o `<body>` já carrega. Num Layout claro
  o branco vira fundo; num escuro, o preto. A hierarquia dos cinzas se mantém.
- **Com cor** vira `destaque` quando viva e `apoio` quando escura; um pastel fica entre o destaque e
  o fundo. A transparência de `rgba` se mantém.
- Só muda cor de CSS: dentro de `<style>` e dos atributos de estilo e de SVG. Texto do slide e foto
  não mudam. `url(#id)` do SVG não é cor.

A paleta **Suno** quer dizer "cores do post": com ela nada é recolorido e a família sai como o
original. As outras vão à rota de montar como `paleta=fundo,texto,destaque,apoio` e ficam gravadas
em `Execucao.paleta_visual`, ao lado da referência escolhida.

A prévia do editor não espera o Puppeteer. O render grava cada slide também em `slide-<nn>.html`,
com as cores originais, e duas rotas devolvem HTML recolorido e autossuficiente (fontes e foto como
`data:`), que o celular da prévia mostra em `iframe`:

- `/api/referencias-visuais/{id}/previa`: o Layout com o texto de exemplo, antes de montar;
- `/api/execucoes/{id}/pacotes/{audiencia}/carrossel/{slide}/previa`: o slide já montado.

## Consequências

- A paleta muda a prévia na hora, também numa família. O zip continua sendo dos PNGs: com outra
  paleta, exportar exige montar de novo, e a tela diz isso.
- A regra é genérica: um Layout novo é recolorido sem configuração, desde que declare o fundo.
- A regra não garante contraste em todo par. Um texto claro sobre um destaque claro (Floresta num
  Layout escuro com caixa vermelha) pode ficar fraco. A medição de contraste do render continua
  valendo como alerta.
- As cores ficam uniformes: o verde do botão e o amarelo das moedas da Asset viram destaque, como o
  vermelho. Recolorir apaga essa variedade de propósito.
- A prévia de exemplo não tem foto: o Layout degrada como no render sem foto (`sem-imagem`).
- As prévias abrem `/api` em `iframe`, então o service worker do PWA não pode responder essas
  navegações com o `index.html` (`navigateFallbackDenylist` em `web/vite.config.ts`).
