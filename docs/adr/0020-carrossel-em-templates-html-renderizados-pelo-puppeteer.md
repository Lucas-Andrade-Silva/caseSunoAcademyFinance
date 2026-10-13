# O Carrossel é renderizado por templates HTML/CSS e Puppeteer

Substitui o mecanismo de render do [ADR 0009](0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md)
(matplotlib + Pillow). A regra do 0009 continua: imagem é gerada pelo sistema, nunca raspada, 1080×1350.

> **Ampliado pelo [ADR 0030](0030-familias-visuais-do-carrossel.md):** além dos seis layouts escuros
> abaixo, o Carrossel tem famílias visuais recriadas dos posts reais da Suno, e as fotos reais
> entram pelo [ADR 0031](0031-fotos-reais-e-licenciadas-nos-slides.md). O motor e a reserva Pillow
> continuam como aqui.

## Decisão

O Gemini gera só a **estrutura e o texto**: cada Slide tem `tipo` (`hook`, `ponto`, `citacao`,
`cta`), `titulo`, `corpo`, `destaque` opcional e `dado` opcional. O primeiro slide é `hook`, o
último é `cta`, os do meio são `ponto` ou `citacao`. A direção de arte escolhe uma das seis
composições ativas (`editorial`, `minimalista`, `infografico`, `comparativo`, `estatistico` e
`narrativo`); o pipeline preenche o template correspondente em `src/suno/pacote/templates/` e o
Puppeteer (`render/render.mjs`) captura o PNG.

Geração de imagem por IA (Nano Banana) **não** desenha os slides: consistência pixel-perfect é
difícil com imagem pura. Quando entrar, entra só como ilustração ou fundo decorativo opcional de
um template, fora do caminho crítico (a regra do 0009 sobre geração por modelo segue valendo).

Paleta (anexo do case): `#FF0000`, `#AF0404`, `#414141`, `#252525` e branco `#FFFFFF`. Texto é
branco; vermelho puro só pinta formas e números grandes (3,8:1 sobre o fundo, abaixo do mínimo de
4,5 para texto corrido); o realce de palavra usa branco sobre `#AF0404` (7,4:1).

## Consequências

- A conferência visual (ADR 0014) lê o manifesto `slide-<nn>.json`; no motor HTML as caixas vêm
  medidas no navegador (`usado` = scrollWidth × scrollHeight), então estouro continua detectável.
- Puppeteer exige Node e Chromium (`cd render && npm install`). O Pillow do 0009 fica como
  **reserva**: entra sozinho sem Node/Puppeteer e é forçado por `SUNO_RENDER=pillow`. O pytest usa
  a reserva, para a suíte seguir sem rede e sem navegador; `tests/test_carrossel_html.py` cobre o
  motor novo e pula quando ele não está instalado.
- A letra continua sendo a DejaVu do matplotlib, lida do disco: nada é baixado.
- A interface mostra o design embutido no Carrossel (ligável) e o botão de aprovar vira
  "Aprovar e gerar carrossel", que aprova a Célula e monta o Pacote.
