# Viabilidade técnica — achados verificados

Pesquisa de 13–14/09/2026. Tudo aqui foi verificado contra fonte primária (documentação
oficial, código-fonte, ou requisição HTTP real) salvo onde está escrito **NÃO VERIFICADO**.

Este arquivo é insumo para ADRs. Ele registra *fatos*, não decisões.

> **Por que este arquivo existe:** metade destes achados contradiz o que tutoriais e
> respostas de LLM recomendam. Essa stack apodrece rápido — várias ferramentas que
> todo mundo ainda indica morreram entre 2024 e 2026. Reconfirme antes de adotar
> qualquer coisa daqui com mais de uns meses.

---

## 1. Fontes de documentos

### Atas do Copom — fonte principal recomendada

API interna do site do BCB, **não documentada**, sem autenticação e sem Cloudflare:

```
https://www.bcb.gov.br/api/servico/sitebcb/atascopom/ultimas?quantidade=500&filtro=
```

- Retorna JSON com 520 atas (histórico completo). Campos: `DataReferencia`, `Titulo`,
  `Url` (caminho do PDF), `LinkPagina`.
- `filtro=` é obrigatório mesmo vazio; sem `/ultimas` retorna 400/500.
- PDF: concatenar `https://www.bcb.gov.br` + campo `Url`. São PDFs *tagged*, com
  `/Lang(pt)` e camada de texto real — extração limpa, não é scan.
- **Versão oficial em inglês** no mesmo padrão, trocando o slug para `copomminutes`.
  Mesmo `DataReferencia`. É um corpus paralelo traduzido por humanos, de graça.
- `robots.txt` do BCB libera `/api/servico/` e `/content/`. Sem `Crawl-delay` declarado.
  **NÃO VERIFICADO:** rate limit desse endpoint. Ser conservador (~1 req/s).
- **Risco:** endpoint não documentado pode mudar ou sumir sem aviso.

**NÃO VERIFICADO:** slug para comunicados/decisões do Copom (todos os nomes testados
deram 400/500). Não existe endpoint que devolva o corpo da ata em HTML — o `LinkPagina`
é shell Angular. Trate o PDF como fonte canônica.

Olinda (`olinda.bcb.gov.br`) **não** tem dataset de atas — só séries numéricas.
A API SGS (`api.bcb.gov.br/dados/serie/bcdata.sgs.NNN/dados?formato=json`) serve para
Selic/IPCA, não para texto.

### CVM — fatos relevantes (fonte secundária)

```
https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/   → ipe_cia_aberta_YYYY.zip
```

- O CSV traz **só metadados** (`;`, latin-1). O texto está a um segundo salto, no campo
  `Link_Download`, que aponta para o sistema RAD/Empresas.NET.
- O download do RAD funciona sem autenticação e sem cookie, mas **o `Content-Type` mente**:
  diz `text/html` e entrega PDF. Detectar por magic bytes `%PDF`, nunca pelo header.
- **`ipe_cia_aberta_2026.zip` está 404 hoje**, apesar de anunciado na página. Só há dados
  até 2025 — ancore a demo em 2025.
- `robots.txt`: **`Crawl-Delay: 10`**. Respeitar 10 s entre requisições ao portal.
- **Não confundir com o dataset de Ofertas Públicas de Distribuição** (`OFERTA/DISTRIB`,
  também CVM Dados Abertos). É outro dataset: tabular, sobre emissões de mercado primário
  (debêntures, ações, FIIs), sem texto narrativo e sem um "hoje" natural — visto num
  projeto irmão, não adotado aqui. O que usamos é o IPE (fatos relevantes), que chega em
  texto corrido pelo RAD, como descrito acima.

### B3 — descartada como origem de documentos

Está atrás de Cloudflare, e só *indexa*: os documentos moram no RAD da CVM de qualquer
forma. Raspar a B3 é mais trabalho para chegar no mesmo lugar. O `robots.txt` dela tem
13 bytes e nenhuma diretiva — malformado, não concede nada explicitamente.

**NÃO VERIFICADO:** termos de uso de cada domínio (foram lidos os `robots.txt`, não os ToS).
Usar User-Agent identificado com contato institucional em todas as requisições.

---

## 2. Legibilidade em português — a métrica central

### A fórmula

**Índice de Facilidade de Leitura de Flesch adaptado ao português**, Martins, Ghiraldelo,
Nunes & Oliveira Jr. (1996), NILC/ICMC-USP:

```
ILF = 248.835 − 1.015 × (palavras/frases) − 84.6 × (sílabas/palavras)
```

Confirmado no código oficial do NILC (`nilc-nlp/nilcmetrix`, AGPL-3.0,
`text_metrics/metrics/basic_counts.py`, classe `Flesch`).

**O case erra o nome.** Ele pede "Flesch-Kincaid adaptado ao português", mas
Flesch-Kincaid é outra fórmula — grade level, `0.39×(w/s) + 11.8×(syl/w) − 15.59`.
Corrigir isso no relatório final e citar a referência correta.

Não confundir com a adaptação **espanhola** de Fernández-Huerta
(`206.84 − 1.02×(w/s) − 60.0×(syl/w)`) — coeficientes diferentes.

Existe uma segunda adaptação brasileira, de 2022 (arXiv 2203.12135, software ALT):
`227 − 1.04×(w/s) − 72×(syl/w)`, R²=0.891 sobre 100 textos. Vale citar as duas e usar
a de Martins, que é o padrão consolidado.

### Faixas de interpretação

Confirmadas em artigo revisado por pares (Língu@ Nostr@ v.10 n.2, 2022, UESB):

| Índice | Dificuldade | Escolaridade |
|---|---|---|
| 100–75 | muito fácil | 1º ao 5º ano |
| 75–50 | fácil | 6º ao 9º ano |
| 50–25 | difícil | Ensino Médio |
| 25–0 | muito difícil | Ensino Superior |

Mapeamento direto para os níveis do case: **iniciante ≥ 50, intermediário 25–50,
avançado < 25**. Isso transforma a calibragem de chute em limiar citável.

### `textstat` está errada para português — não usar

Duas falhas, a primeira fatal:

1. **Fórmula errada.** `LANG_CONFIGS` (em `textstat/backend/utils/constants.py`) tem
   en, de, es, fr, it, nl, pl, ru, hu — **não tem `pt`**. `get_lang_cfg` cai no default
   inglês, então `set_lang("pt_BR")` seguido de `flesch_reading_ease()` aplica
   `206.835 / 1.015 / 84.6`: a fórmula inglesa. 42 pontos de erro só no intercepto.
2. **Sílabas subcontadas.** Não é heurística inglesa (usa `pyphen` com dicionário pt_BR),
   mas hifenização ≠ silabação, e `left=2/right=2` suprime sílabas de uma letra nas
   bordas. Medido: `água`→1, `ação`→1, `ações`→1, `ideia`→1, `ativo`→2. A subcontagem
   é sistemática justamente no vocabulário financeiro (ação, aplicação, ativo, ágio).

**Impacto medido** em texto financeiro de 45 palavras / 4 frases: silabador correto dá
Flesch-BR **34,4** (Ensino Médio); `pyphen` default dá **55,1** (6º–9º ano). São
**20,7 pontos e duas faixas de erro**.

Mitigação parcial, se houver insistência em pyphen: `Pyphen(lang='pt_BR', left=1, right=1)`
corrige a maioria (água→2, economia→5, ação→2) mas erra outros casos.

### Silabador correto

Extrair do NILC: `nilcmetrix/text_metrics/tools/syllable/` — algoritmo de Silva (2011),
implementação de Alessandro Bokan. ~1.200 linhas, **zero dependências além de `re`**,
offline puro. É isto que circula como "separasilabas"; **não existe no PyPI**, e
`nilc-nlp/coh-metrix-port` está morto desde 2014.

- **Licença GPL-3.0 — contamina.** Decisão de supply chain: manter em arquivo isolado e
  cumprir a GPL, ou reimplementar a partir do artigo. Precisa virar ADR.
- **Bug conhecido:** `ideia` → `i-dei--a` produz sílaba vazia; filtrar strings vazias ou
  conta 4 em vez de 3.
- Erros típicos do domínio: hiatos (`sa-ú-de` vs `sau-de`), ditongos decrescentes
  (`ideia`, `mãe`), e `-ia` final (`e-co-no-mi-a` vs `e-co-no-mia`). Fixar uma convenção
  e documentá-la.

NILC-Metrix como serviço só roda via Docker + PostgreSQL local ou web — **não há API
pública nem pacote PyPI**. Pesado demais para este caso.

---

## 3. Números e léxico financeiro

### Extração de números (alimenta o verificador de fidelidade factual)

spaCy `pt_core_news_*` está em v3.8.0 (CC BY-SA 4.0), sem release pt em 2026, e só
reconhece PER/LOC/ORG/MISC — **inútil para números financeiros**. Serve para
tokenização e POS. Para entidades: `marquesafonso/bertimbau-large-ner-selective`
(MIT, tem VALOR e TEMPO).

Caminho recomendado: regex própria + `Babel.parse_decimal(locale='pt_BR')` +
`text2num` (MIT, v3.1.0 de ago/2026, suporta pt) + `dateparser` travado em `languages=['pt']`.

Descartar `duckling` (exige runtime Haskell + servidor) e `quantulum3` (sem pt).

**Armadilhas semânticas críticas:** `p.p.` ≠ `%`, e `CDI+2%` ≠ `110% do CDI`. Formato
brasileiro: vírgula decimal, ponto de milhar, escalas por extenso (bilhão, trilhão).

### Léxico para o score de densidade de termos

- **Dicionário CVM** (gov.br) — licença **CC BY-ND 3.0** explícita. *ND = no derivatives*:
  atenção ao que isso permite.
- **Glossário ANBIMA** (PDF, out/2024) — download direto.
- **B3 / Bora Investir** (`borainvestir.b3.com.br/glossario/letra/a/`…) — raspagem,
  licença **NÃO VERIFICADA**.
- **Mortos:** glossário legado do BCB (HTTP 500) e `investidor.gov.br/glossario`
  (301/descontinuado).

Congelar tudo em arquivo versionado no repositório, mais ~150 termos manuais
(Selic, CDI, come-cotas, marcação a mercado).

---

## 4. LLM a custo zero

| Provedor | Limites reais | Contexto | Treina com seus dados |
|---|---|---|---|
| Gemini Flash (AI Studio) | instável — Google parou de publicar número fixo (ver abaixo) | 1M | **Sim** |
| Groq (`gpt-oss-120b`) | 30 RPM, 1.000 RPD, **200k TPD** (limite por organização, não por chave) | 131k | Não (contratual) |
| SambaNova Cloud (`gpt-oss-120b`) | 20 RPM / 20 RPD / 200k TPM, sem cartão | ~65k | **NÃO VERIFICADO** |
| ~~Cerebras~~ | **descontinuado como grátis em 17/08/2026** — ver abaixo | ~65k | Não |
| OpenRouter | 20 RPM, 50 RPD sem créditos | varia | Depende do provider |

**Cerebras deixou de ser tier gratuito.** Confirmado contra a documentação oficial
(`inference-docs.cerebras.ai/support/rate-limits`, consultada em 15/09/2026): contas novas
exigem cartão de crédito verificado para liberar US$5 em créditos que expiram em 30 dias;
sem cartão, a API fica inativa. **Substituída por SambaNova Cloud como reserva** — roda o
mesmo `gpt-oss-120b` da Groq, tier gratuito real sem cartão hoje
(`docs.sambanova.ai/docs/en/models/rate-limits`). Ver [ADR 0007](../adr/0007-roteador-de-provedores-distingue-tipo-de-429.md).

Google parou de publicar a tabela de limites do Gemini; vale só o painel em
`aistudio.google.com/rate-limit`, e a doc oficial hoje instrui explicitamente checar o
painel porque a cota "vai atualizar automaticamente". Isso é postura deliberada, não lacuna
de documentação: houve um corte não avisado de 50–92% no free tier no fim de semana de
6–7/12/2025 (confirmado publicamente pelo PM do Google AI Studio, Logan Kilpatrick — o limite
generoso "deveria ter durado só o fim de semana" e ficou por engano por meses). Gemini
**Pro saiu do free tier** em abr/2026.

**Groq: o limite é por organização, não por chave de API.** Rotação de múltiplas chaves
Groq na mesma conta não multiplica capacidade — confirmado cruzando documentação e relatos
de terceiros. Não vale a pena implementar essa estratégia para a Groq especificamente.

**Conta para uma demo com reflection loop** (~200 chamadas × ~8k tokens ≈ 1,6M tokens):
a reserva trava por RPM/TPD antes de aguentar sozinha; Groq estoura os 200k TPD em ~25
chamadas de documento longo; **só o Gemini Flash aguenta a geração com o documento
inteiro**. Daí a divisão: Gemini gera, Groq julga (prompts curtos), SambaNova de reserva.
Três chaves = três cotas independentes, com roteador tratando 429 — mas a cota do Gemini
deve ser tratada como valor volátil a confirmar no painel antes de qualquer bateria
importante, não como constante.

**Pedágio do free tier do Gemini:** os termos dizem que o conteúdo é usado para melhorar
os produtos e que revisores humanos podem ler entrada e saída. Os documentos-fonte são
públicos, mas os *prompts*, limiares e glossário são o ativo do projeto.

### Armadilhas de provedor — **NÃO VERIFICADO por nós**

Achados de código e documentação de dois projetos irmãos (Tractian, Nvidia), não
confirmados contra os provedores por requisição própria. Tratar como hipótese a testar
antes de confiar, não como fato — mas valem a pena verificar cedo porque, se
procederem, mudam o desenho do roteador ([ADR 0007](../adr/0007-roteador-de-provedores-distingue-tipo-de-429.md)):

- **Groq distingue cota por minuto de cota diária/total na mensagem de erro** (procurar
  `"per day"`, `"tpd"`, `"rpd"` no texto do 429). Um projeto irmão só troca de chave/conta
  no caso diário — cota por minuto "se resolve sozinha em segundos" e trocar por ela
  gastaria a cota diária da conta seguinte à toa.
- **`max_tokens` é um teto declarado na requisição, não estimado pelo servidor** — a Groq
  recusaria a chamada pelo número declarado, antes de gerar qualquer coisa.
  Instrução de brevidade no prompt não substitui declarar um teto por papel.
- **Em modelo de raciocínio, o "pensar" consomeria o mesmo orçamento de `max_tokens` que a
  resposta** — um papel com teto baixo seria cortado no meio da resposta porque gastou o
  teto pensando. Se confirmado, mitigação é reduzir `reasoning_effort` por papel quando o
  teto não pode subir, não aumentar o teto sem limite.
- **A lista de modelos gratuitos do OpenRouter muda sem aviso** — um modelo saiu do plano
  gratuito no meio do desenvolvimento de um projeto irmão. Consultar a lista ao vivo
  antes de cada bateria, nunca fixar nome de modelo em código.

**Fallback local:** em CPU, 3–7B Q4 roda a 3–5 tok/s — inviável como motor. Com GPU de
6 GB, um `Qwen3 8B Q4_K_M` cabe; **NÃO VERIFICADO** se a velocidade resultante serve.
`Tucano 2` (Apache-2.0, nativo em português) é ótimo para citar no relatório mas pequeno
demais para gerar análise. `Sabiá-3/4` (Maritaca) é o melhor em pt-BR e é **pago**.

---

## 5. Frameworks de avaliação

**Não adotar DeepEval nem Ragas como espinha dorsal:**

- **DeepEval** (v4.2.2, ativo): telemetria PostHog ligada por padrão, incluindo IP
  público — desligar com `DEEPEVAL_TELEMETRY_OPT_OUT=1`. Issue #2497 (fev/2026)
  documentou sequestro do `TracerProvider` global do OTel exportando spans da aplicação
  hospedeira para New Relic com chave hardcoded; o exporter foi removido em versão
  posterior, mas **NÃO VERIFICADO** se está 100% limpo na 4.2.x. Dashboard free
  inutilizável: 5 execuções/semana.
- **Ragas**: último release no PyPI em **jan/2026** (8 meses parado). A v0.4 removeu
  APIs centrais e o caminho de migração recomendado pela própria documentação está
  quebrado no PyPI. ~85% das métricas são específicas de RAG, não de qualidade de
  conteúdo — usaria-se 15% do framework herdando 100% do churn.

**Recomendado: `pydantic-evals`** (MIT, v2.43.0 de 12/09/2026). Sem SaaS, sem telemetria
(`logfire-api` é shim no-op), datasets em YAML versionáveis no git, `LLMJudge` embutido,
`Evaluator` custom para as métricas determinísticas, roda dentro do pytest. Dataset
versionado no git *é* a reprodutibilidade que o Entregável 6 pede.

Se quiserem dashboard sem escrever UI: **Langfuse** ou **Opik** self-hosted
(docker-compose, MIT/Apache-2.0, sem limite). Evitar **Phoenix** se houver qualquer
chance de o projeto virar serviço (Elastic License 2.0, não-OSI).

**LangGraph** (v1.2.11) é *só* orquestração: não tem hook de avaliação nem
observabilidade embutida. Tracing é OTel opt-in — dá para apontar para Langfuse/Opik
sem nunca depender do LangSmith.

---

## 6. Vídeo com avatar sintético (extensão além do escopo do case)

| Ferramenta | Situação | Licença | VRAM |
|---|---|---|---|
| SadTalker | **morto** (jun/2024, preso a torch 2.0.1) | Apache-2.0 | ~6 GB |
| Wav2Lip | vivo, baseline feio (256px) | **uso comercial proibido** | ~2 GB, roda em CPU |
| MuseTalk 1.5 | melhor custo/benefício | **MIT, pesos livres** | **~4 GB fp16** |
| LatentSync 1.5/1.6 | melhor qualidade viável | Apache-2.0 | 8 GB / 18 GB |
| EchoMimic v3 | o mais vivo (mar/2026) | Apache-2.0 | 12–24 GB |
| InfiniteTalk / Wan2.2-S2V | quebra em T4/P100 | Apache-2.0 | 16–40 GB |

**Compute grátis:** o ToS do **Colab veta explicitamente "criar deepfakes"** e veta usar
o notebook como backend de web UI. HF Spaces passou a exigir plano pago para criar Space,
com exceção de 2 Spaces ZeroGPU para conta com mais de 30 dias (5 min/dia). Kaggle dá
~30 h GPU/semana mas é notebook, não servidor.

**TTS pt-BR:** `edge-tts` está vivo (mar/2026) mas usa endpoint não documentado da
Microsoft, sem ToS. **Azure Speech F0** dá 500 mil caracteres/mês permanentes, mesma voz,
com contrato — melhor opção. XTTS-v2: Coqui fechou em jan/2024; fork mantido é
`idiap/coqui-ai-TTS`, pesos sob CPML **não-comercial**. `Piper` foi relicenciado para
**GPL-3.0**; robótico, mas é o fallback offline garantido. Kokoro pt-br e F5-TTS
(CC-BY-NC): descartar.

**Caminho recomendado pela pesquisa — não é talking-head:** Remotion (React → MP4,
Chrome headless, CPU, determinístico) + TTS neural + lip-sync 2D de apresentador
ilustrado via `rhubarb-lip-sync`. Argumento: ninguém julga um resumo do Copom pela boca
do avatar, julga pelo gráfico da Selic na tela. Remotion é livre para indivíduos e
organizações sem fins lucrativos — **estudante se qualifica; empresa com 4+ funcionários, não**.

Fallback nomeado: MuseTalk 1.5 pré-renderizado, com o MP4 cacheado no repositório,
nunca no caminho crítico da gravação.

---

## 7. Ferramentas mortas ou armadilhas (não confie em tutoriais)

- **GitHub Models** — desativado em 30/07/2026. Playground, API e BYOK fora do ar.
- **OpenAI Evals** — repo arquivado; plataforma read-only em 31/10/2026, desligada em 30/11/2026.
- **HF Inference Providers** — US$ 0,10/mês de crédito. Inservível.
- **SadTalker** — morto desde jun/2024, mas é o que todo tutorial recomenda.
- **coqui-ai/TTS** — morto desde ago/2024 (a empresa fechou em jan/2024).
- **textstat para português** — silenciosamente errado, ver seção 2.
- **Números que circulam em blogs e estão errados:** "14.400 req/dia" no Groq e
  "30 RPM" na Cerebras não batem com os docs oficiais de hoje.
- **MLflow `mlflow.genai.evaluate()`** — a suíte nova é Databricks-managed, "coming soon"
  ao OSS. Não contar com ela.

---

## 8. Imagens para o Pacote de publicação — **NÃO PESQUISADO**

O [ADR 0009](../adr/0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md) decide que
toda imagem do Carrossel é gerada pelo sistema, nunca raspada de terceiro — mas o mecanismo de
geração ainda não foi investigado. Duas direções possíveis, nenhuma verificada:

- **Template determinístico** (ex. Pillow, ou HTML/CSS renderizado para imagem): sem custo, sem
  dependência de rede, mas exige desenho gráfico prévio. Compatível com "demo roda sem rede".
- **Geração por modelo de imagem**: precisaria de um provedor de tier gratuito equivalente aos da
  seção 4 — não pesquisado se existe algum com cota utilizável para o volume da demo.

Pesquisar antes de decidir a implementação; não presumir viabilidade do caminho de geração por
modelo sem confirmar cota e licença de uso comercial.

## 9. Licenças que exigem decisão (supply chain)

| Item | Licença | Consequência |
|---|---|---|
| Silabador NILC | GPL-3.0 | **Contamina.** Isolar e cumprir, ou reimplementar. |
| Dicionário CVM | CC BY-ND 3.0 | *No derivatives* — cuidado com o que se deriva dele. |
| Wav2Lip | acadêmico, não-comercial | Inviabiliza virar produto. |
| XTTS-v2 (CPML) | não-comercial | Idem. |
| Piper | GPL-3.0 | Contamina se linkado. |
| Remotion | livre p/ indivíduo e ONG | Empresa com 4+ funcionários não se qualifica. |
| Phoenix (Arize) | Elastic License 2.0 | Proíbe oferecer como serviço gerenciado. |

Padrão: várias peças gratuitas **deixam de ser gratuitas se o projeto virar negócio**.
Isso precisa ser decisão consciente, não descoberta tardia.
