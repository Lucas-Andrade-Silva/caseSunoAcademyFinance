# 0032 — As fotos dos slides vêm de uma busca de imagens na web, sem verificar licença (MVP)

## Status

Aceita. **A fonte (item 1) e o papel do juiz (item 3) passam a seguir o [ADR 0033](0033-busca-de-imagens-propria-do-mercado-e-juiz-so-na-duvida.md):
Serper (Google Imagens) quando há chave, Bing como reserva, e juiz só na dúvida.** Substitui o [ADR 0031](0031-fotos-reais-e-licenciadas-nos-slides.md) nos itens 1 (fonte
única e filtro de licença) e 5 (crédito por licença).** O resto do 0031 continua: a demo roda sem
rede, o Gerador sugere só o assunto, o juiz de visão decide a relevância, foto sem acerto não quebra
o slide.

## Contexto

O Wikimedia Commons deu cobertura fraca para o assunto de finanças: nos testes, só instituição e
figura pública tinham foto, e "B3", "pregão" e "dólar" voltavam errados ou vazios. A decisão do
projeto é buscar a foto onde um humano buscaria: na busca de imagens da web. O projeto é um MVP
acadêmico que não vai para produção, e a responsabilidade pelo direito autoral das fotos é de quem
decidiu, o dono do projeto (decisão de 13/10/2026). O risco que o ADR 0009 descreveu continua
real: **este caminho não serve para publicar de verdade**.

## Decisão

1. **Fonte: Bing Imagens**, por HTTP simples e sem chave (`suno.imagens.web.ClienteWeb`). O Google
   Imagens foi testado e descartado: não tem API gratuita e o navegador automatizado cai em CAPTCHA
   (`google.com/sorry`); o projeto não contorna CAPTCHA. A busca pede imagem grande
   (`imagesize-large`), tira duplicatas e tira banco de imagem pago (iStock, Shutterstock, Getty…),
   que serve a foto com marca d'água.
2. **Nenhuma licença é verificada.** O crédito sai igual, pela mesma linha `Foto: autor / licença /
   url`, com o domínio do site como `autor`, `licença não verificada (MVP)` como `licença` e a
   página onde a imagem foi achada como `url`. A legenda diz a verdade sobre o que se sabe.
3. **O juiz de visão é o filtro.** Quem garante que a foto é da B3, e não da vitamina B3, é o
   `PapelLLM.JUIZ_VISAO`. Como a web traz mais ruído que o Commons, o prompt do juiz rejeita também
   marca d'água, banner de venda, captura de tela e homônimo; aceita fachada, pregão e logo quando o
   assunto é uma instituição. Sem juiz, a foto baixada fica pendente de aprovação humana.
4. **Resolução mínima de 800 px de largura**, conferida depois do download (o Bing não informa o
   tamanho antes). Imagem pequena ou download bloqueado (hotlink, 403) não gasta chamada de visão e
   não conta no limite de cinco candidatos avaliados.
5. **Nova tentativa na busca.** O Bing às vezes devolve uma página degradada, com um resultado,
   para a mesma requisição que antes trouxe 25. Com menos de cinco resultados, a busca tenta de
   novo (até quatro vezes, com pausa crescente).
6. **O Wikimedia Commons sai do código.** As fotos já semeadas em `data/imagens/` continuam na
   biblioteca local, com os créditos de origem que já tinham.
7. O recorte para as dimensões do slide (1080×1350) é do CSS de cada espaço de foto
   (`object-fit: cover`), como já era.

## Consequências

- **Para publicar de verdade, este ADR tem de ser revertido** e a fonte voltar a ter licença
  verificada (Commons, Openverse ou banco com licença própria). A troca é local: `ClienteWeb`
  implementa a mesma interface de `buscar` e `baixar`.
- O Bing não é API: o formato da página pode mudar sem aviso, e a busca pode ser bloqueada. Quando
  isso acontece, o resolvedor devolve `None` e o slide degrada para o layout sem foto.
- O juiz de visão só funciona no Gemini hoje: a Groq do `.env` usa `gpt-oss-120b`, que não aceita
  imagem (HTTP 400). Quando o Gemini dá 503, a foto fica pendente (`imagens aprovar <id>`).
- A mesma foto de uma página já conhecida (aprovada, pendente ou rejeitada) não é baixada de novo;
  duas fotos da mesma página contam como uma.
