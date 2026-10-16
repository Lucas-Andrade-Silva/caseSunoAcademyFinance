# 0033 — A busca de imagens conhece o mercado e o juiz de visão só decide a dúvida

## Status

Aceita. Complementa o [ADR 0032](0032-fotos-da-web-pelo-bing-imagens-sem-verificar-licenca.md) e
**substitui o seu item 1 (a fonte é o Bing) e o item 3 do [ADR 0031](0031-fotos-reais-e-licenciadas-nos-slides.md)
(todo resultado da web passa pelo juiz de visão).**

## Contexto

Buscar "B3" no buscador traz a vitamina B3. O Gerador entrega só até quatro palavras
(`Slide.imagem`), e o juiz de visão (Gemini) era chamado para toda foto, gastando a cota gratuita
para recusar o que um olhar no título já recusaria. O pedido do dono do projeto (13/10/2026): busca
com jeito próprio para o nosso assunto, foto da empresa ou o logo dela quando o slide fala de uma
empresa, e o Gemini só nos casos de dúvida.

Um teste de campo descobriu um segundo problema: **o Bing reconhece robô** (`httpx` e Puppeteer) e
serve imagens sem relação nenhuma com a consulta ("Federal Reserve" devolveu calendários, tintas,
um anime), enquanto o navegador do app devolve a sede certa. O DuckDuckGo responde com desafio
anti-bot e o Google Imagens com CAPTCHA. O projeto não contorna CAPTCHA nem disfarça robô.

## Decisão

1. **Catálogo de assuntos visuais** (`src/suno/imagens/assuntos.json`): para cada empresa,
   instituição, conceito e setor, dá as chaves pelas quais o assunto aparece no slide, as consultas
   a digitar, o que o resultado precisa citar (`exigir`) e o que o desclassifica (`proibidas`).
   Empresa e instituição buscam a foto da sede e depois o logo; se o slide pede "logo", o logo vem
   primeiro. As palavras proibidas viram `-palavra` na consulta (no máximo quatro) e também
   descartam o resultado. Assunto fora do catálogo cai numa busca de "<assunto> mercado financeiro
   Brasil". A pessoa com conhecimento de mercado mantém o catálogo (o Léxico do Avaliador é outra
   coisa e não se mistura).
2. **Pontuação por texto, sem LLM** (`suno.imagens.consulta.pontuar`): o assunto citado no nome do
   arquivo vale 3 pontos, no título 2, na página 1; palavra de contexto financeiro 1; site oficial
   ou de confiança 1. Cinco pontos ou mais **aprova direto**, desde que o nome esteja no arquivo da
   imagem ou o assunto seja empresa ou instituição (nome próprio no título já indica logo ou sede;
   "China" no título de uma matéria com foto de ouro não indica nada) (`validada_por = "texto"`); palavra
   proibida **descarta sem baixar**; o resto é **dúvida**.
3. **O juiz de visão só decide a dúvida**, no máximo três vezes por assunto, e só resultado com
   pelo menos um ponto de indício no texto: resultado sem relação nenhuma é lixo do buscador e nem
   gasta o juiz. Sem juiz, a foto em dúvida fica pendente de aprovação humana.
4. **Proporção de slide:** largura mínima de 800 px e proporção entre 0,4 e 2,5; faixa e banner são
   descartados antes de qualquer juiz.
5. **Duas fontes, a mesma interface.** `ClienteSerper`: Google Imagens pela API do Serper.dev,
   com chave gratuita em `SERPER_API_KEY` (a fonte confiável, e a que informa o tamanho antes do
   download). `ClienteWeb`: Bing por HTTP, só como reserva sem chave, ciente de que rende pouco.
   `buscador_padrao()` escolhe pela chave.

6. **Foto sem acerto não ocupa slide; foto achada vai para onde cabe** (decisão de 13/10/2026).
   O slide cujo assunto não achou foto recebe um layout que não precisa de imagem: a regra é dura
   no catálogo candidato (`direcao_de_arte._candidatos`), não mais só uma penalidade, e vale para o
   Diretor IA também. Foto achada que o plano não pode desenhar no slide que a pediu (slide de
   gráfico na família Dados, CTA) é realocada por `fotos.acomodar_fotos` para o slide mais próximo
   que ainda não tem foto e aceita layout de foto, e o plano é refeito. Sem destino, a foto é
   descartada e o crédito sai da legenda: nunca se credita foto que não aparece.

## Consequências

- **Sem `SERPER_API_KEY` a qualidade cai muito:** a pontuação por texto segura o lixo do Bing, mas
  muitos assuntos voltam sem foto. A chave é grátis (2.500 consultas, sem cartão, segundo fontes de
  terceiros; confira no site). A API de Custom Search do próprio Google está fechada a clientes
  novos e acaba em 01/01/2027; a Brave Search API deixou de ter plano grátis sem cartão.
- Aprovar pelo texto é apostar que a página que cita "B3" mostra a B3. Para um MVP é o preço de
  não gastar o juiz; o `validada_por = "texto"` no índice permite reauditar essas fotos depois.
- **A biblioteca local também confere o catálogo:** a busca dela casa por qualquer termo em comum, e
  uma foto da Caixa voltava para "Federal Reserve" por causa de "federal". Foto da biblioteca só vale
  se as tags (os assuntos para os quais ela foi achada) citarem o assunto do catálogo; o título é de
  matéria e cita de tudo ("tensões entre EUA e China" numa foto de ouro).
- O catálogo cobre o essencial (cerca de 75 assuntos); o que não está nele funciona, mas pior.
  Cada foto nova que o MVP precisar e vier errada é uma entrada a acrescentar.
- O juiz de visão só roda no Gemini (a Groq do `.env` não aceita imagem), e o tier gratuito dá 503 em
  horário de pico: no teste de campo, 3 de 4 chamadas falharam. A foto fica pendente (`imagens aprovar`).
- `scripts/testar_busca_de_imagens.py` roda um teste de campo na rede e monta folhas de contato
  para conferir a olho; não é teste de CI.
