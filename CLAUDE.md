# Suno Content

Adapta uma Ata em nove Células e reprova as que não atingem o Limiar da sua Audiência.
Case acadêmico: 2 pessoas, 2 semanas, e os seis entregáveis do enunciado são o que vale
nota.

## A linha que não se cruza

O conteúdo nunca produz **Recomendação**. Recomendar compra ou venda é atividade
regulada no Brasil; este sistema informa e educa. Compliance é métrica do Laudo e reprova
a Célula que cruzar a linha — não é instrução de prompt.

## O caminho óbvio está errado nestes cinco pontos

Cada um foi verificado. O palpite natural, aqui, é o errado.

- **Legibilidade**: `textstat` calcula português errado e não avisa — cai no inglês em
  silêncio, com 20 pontos de erro. O Flesch-BR é nosso.
  → [ADR 0002](docs/adr/0002-flesch-br-implementado-no-projeto.md)
- **Avaliação**: use `pydantic-evals`. DeepEval e Ragas foram examinados e recusados,
  apesar de o enunciado sugerir os dois.
  → [ADR 0003](docs/adr/0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md)
- **Interface**: React + Vite + Tailwind sobre FastAPI, com o cliente TypeScript gerado
  do OpenAPI. Streamlit e Next.js foram considerados e recusados.
  → [ADR 0005](docs/adr/0005-interface-em-react-vite-sobre-fastapi.md)
- **Vídeo**: renderiza fora do grafo, consumindo Roteiros já aprovados.
  → [ADR 0004](docs/adr/0004-renderizacao-de-video-fora-do-grafo.md)
- **Publicação**: o sistema entrega o Pacote de publicação pronto e um humano publica.
  Instagram, TikTok e Drive são destinos manuais, sem integração de API.

## A demo roda sem rede

As Atas da demo ficam versionadas em `data/atas/`; buscar do BCB é um comando separado,
rodado antes. Execuções gravam em disco e a interface lê do disco — o mesmo arquivo que
o pytest lê e o relatório cita.
→ [ADR 0006](docs/adr/0006-atas-do-copom-como-documento-fonte-principal.md)

## Os dois módulos

**Gerador** produz, **Avaliador** julga, e entre eles passa só
`(Conteúdo, Âncora[], Audiência) → Laudo`. O Avaliador roda sem LLM e sem rede: é o que
o mantém testável em CI, e vale defender.
→ [ADR 0001](docs/adr/0001-gerador-e-avaliador-como-modulos-separados.md)

As nove Células geram em paralelo. Em sequência, uma Ata leva minutos e a demo morre
esperando.

A pessoa com conhecimento de mercado é dona do Avaliador — Léxico, Limiares, Calibração
e linguagem de Recomendação são conhecimento de domínio, não de pipeline.

## Modelos dentro do pipeline

Gemini Flash gera, Groq julga, SambaNova é reserva. Tier gratuito, atrás de uma interface
única de provedor, com tratamento de 429. Chaves em `.env`. O orçamento é R$ 0: nenhuma
chamada paga entra no pipeline, e isso vale inclusive para a API da Anthropic.

Cerebras foi descartada como reserva: encerrou o tier gratuito permanente em 17/08/2026 e
hoje exige cartão de crédito verificado. → [ADR 0007](docs/adr/0007-roteador-de-provedores-distingue-tipo-de-429.md)

## Quando atrasar, corte nesta ordem

1. Teste de retenção nas redes
2. Publicação automática → humano publica
3. Avatar falante → vídeo sem rosto

Os seis entregáveis não caem. Esqueleto ponta a ponta até o dia 4, feio e completo.
A interface vem por último.

## Onde olhar

- [CONTEXT.md](CONTEXT.md) — a linguagem do projeto. Consulte antes de nomear qualquer coisa.
- [docs/adr/](docs/adr/) — o porquê de cada decisão estrutural. Leia antes de propor mudar uma.
- [docs/research/viabilidade-tecnica.md](docs/research/viabilidade-tecnica.md) — cotas,
  licenças, URLs testadas e ferramentas mortas. Consulte antes de adotar biblioteca,
  modelo ou fonte de dados nova.
- <docs/Case Suno __ Academy __ Finance.pdf> — o enunciado, que define a nota.
