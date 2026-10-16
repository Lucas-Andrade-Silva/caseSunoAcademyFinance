# Front do Suno Content, Fase 3: Fontes

> **Para quem executar:** use superpowers:executing-plans (inline, com checkpoints). Passos com `- [ ]`.

**Objetivo:** a guia Fontes (trilhos horizontais de cartões, um por Ata), o passo 1 da Curadoria
(Destaque único e "Montar a minha") e a entrada de Atas de fora do Copom: catálogo, adaptador da CVM,
upload de PDF ou texto, resumo e sugestão determinísticos, e o selo **não calibrado**.

**Arquitetura:** o código novo mora em `src/suno/origens/`. Um item de qualquer Origem é uma `Ata`
(o CONTEXT.md já a define como "o comunicado financeiro público que entra no sistema"); o que muda
entre eles é a `categoria` da Ata, que escolhe o conjunto de Âncoras essenciais e liga o selo. O
Avaliador ganha um parâmetro opcional (`chaves_essenciais`), com o padrão do Copom, e a costura
`(Conteúdo, Âncora[], Audiência) → Laudo` não muda para quem não o usa.

**Spec:** [2026-10-09-front-suno-design.md](../specs/2026-10-09-front-suno-design.md), seções 4.1, 4.2
(passo 1), 6.1 (achado 1), 6.2, 6.3, 6.5 e 10 (riscos 1, 4 e 9).

## Restrições globais

- A suíte roda **offline**: CVM e BCB só com `httpx` simulado (`httpx.MockTransport`).
- Nenhuma execução antiga quebra: `Ata.categoria` ausente no `.json` vale Copom.
- O Avaliador continua sem LLM e sem rede.
- Vocabulário: ver "Nomes" abaixo. Linha de base do `scripts/vocabulario.py`: 16 achados da equipe.
- Sem commit: o usuário decide quando commitar.

## Nomes (resolve o risco 9 do spec)

`Fonte`, `ItemDeFonte` e `tipo` estão na lista _Avoid_ (de **Ata**, **Célula** e **Formato**). Decisão:

| Na tela | No código | Por quê |
|---|---|---|
| Fonte | `Origem` | CONTEXT.md ganha o termo **Origem**: de onde as Atas vêm |
| item | `Ata` (`ResumoDaAta` na lista) | um Fato Relevante é um comunicado financeiro público |
| tipo da fonte | `categoria` (`CategoriaDaAta`) | `tipo` é _Avoid_ de Formato |

"Fonte" e "item" seguem como texto de tela, como "Saída" já segue. O `CONTEXT.md` registra isso e a
definição de **Ata** deixa de dizer "por padrão, uma ata do Copom" como única possibilidade.

## Decisões desta fase

1. **Onde ficam os arquivos.** O Copom continua em `data/atas/` (versionado, a demo roda sem rede).
   Fato Relevante e Ata importada ficam em `data/fontes/<origem>/<identificador>.{txt,json,pdf}`, fora
   do git; só `data/fontes/catalogo.json` entra no repositório.
2. **Conjunto essencial genérico** (categorias que não são Copom): `data_do_documento` (uma data achada
   no texto) e `numero_principal` (o primeiro número com unidade que não seja data). As duas saem de
   regra fixa. A Saída leva o selo **não calibrado**: Limiares e Léxico foram medidos só com Atas do
   Copom. Quais chaves valem de fato é decisão da pessoa dona do Avaliador (risco 1 do spec).
3. **Resumo e Sugestão da curadoria são determinísticos**, sem LLM e sem cota. Resumo: título, data,
   primeiras frases, número de números e datas que a extração de regra fixa achou. Ranking:
   recência, número de Âncoras e peso da Origem (Copom 3, CVM 2, importada 1).
4. **Upload sem dependência nova:** `POST /api/fontes/importar` recebe o arquivo como corpo cru
   (`application/pdf` ou `text/plain`) e os metadados na query. Sem `python-multipart`.
5. **Atualizar fontes** é um job de uma thread só (`atualizacao.json` com o estado). Sem rede mostra o
   erro e mantém o que já está em disco. A CVM respeita `Crawl-Delay: 10` entre requisições, tenta o
   zip do ano atual e cai para o anterior (o de 2026 estava 404 na pesquisa) e detecta PDF por
   `%PDF`, nunca pelo `Content-Type`.
6. **Releases de Resultados (B3):** fora do MVP. A linha tracejada "em breve" fica na guia.
7. **Demo só para Ata com respostas prontas**, como na Fase 2: itens fora do Copom só geram em Real.
8. **Visão unida** só aparece na Fase 4: aqui o cartão fica "em breve".

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/suno/dominio.py` | `CategoriaDaAta`, `Ata.categoria` e `Ata.origem`, `chaves_essenciais_da`, `CHAVES_ESSENCIAIS_GENERICAS`, `Execucao.categoria` |
| `src/suno/avaliador/{integridade,laudo}.py` | `chaves_essenciais` opcional |
| `src/suno/gerador/{extracao,ciclo,moldes}.py` | extração genérica, Ciclo e molde por categoria |
| `src/suno/ingestao/pdf.py` | `carregar_ata` lê `categoria` e `origem` do `.json` |
| `src/suno/origens/catalogo.py` | `Origem`, `carregar_catalogo`, `alternar` |
| `src/suno/origens/repositorio.py` | `RepositorioDeAtas`: lista, acha o arquivo, resume |
| `src/suno/origens/resumo.py` | `ResumoDaAta`, resumo determinístico |
| `src/suno/origens/curadoria.py` | `sugerir`: Destaque único |
| `src/suno/origens/importacao.py` | `importar`: PDF ou texto vira Ata |
| `src/suno/origens/cvm.py` | adaptador dos Fatos Relevantes |
| `src/suno/origens/atualizacao.py` | job "Atualizar fontes" |
| `src/suno/api/{app,geracao}.py` | rotas novas; o `Gerenciador` acha a Ata no repositório |
| `web/src/paginas/{Fontes,Curadoria}.tsx` | trilhos e passo 1 |

---

### Tarefa 1: Categoria da Ata e conjunto essencial por categoria

**Arquivos:** `dominio.py`, `ingestao/pdf.py`, `avaliador/integridade.py`, `avaliador/laudo.py`,
`gerador/extracao.py`, `gerador/ciclo.py`, `gerador/moldes.py`, `gerador/execucao.py`; testes em
`tests/test_categoria_da_ata.py` (novo).

- [ ] **1.1** Testes: `Ata` sem `categoria` vale Copom; `carregar_ata` lê `categoria` e `origem` do `.json`;
  `medir_integridade` com o conjunto genérico aprova um documento com data e número e reprova sem número
  (`faltantes == ["numero_principal"]`); `avaliar(..., chaves_essenciais=...)` reprova por
  `FALHA_DE_EXTRACAO` só com o conjunto escolhido; `extrair_ancoras` de uma Ata de Fato Relevante gera
  `data_do_documento` e `numero_principal` por regra fixa e não pede chave do Copom ao LLM; a Ata do
  Copom segue pedindo as mesmas chaves (o pedido não muda).
- [ ] **1.2** Implementar. `rodar_ciclo` só passa `chaves_essenciais` ao `avaliar` quando a categoria não é
  Copom (os testes antigos trocam `avaliar` por fakes sem esse parâmetro). `executar` grava
  `Execucao.categoria`.
- [ ] **1.3** `uv run pytest -q` verde.

### Tarefa 2: Catálogo, repositório, resumo e sugestão

**Arquivos:** criar `src/suno/origens/{__init__,catalogo,repositorio,resumo,curadoria}.py` e
`data/fontes/catalogo.json`; `.gitignore`; testes em `tests/test_origens.py` (novo).

- [ ] **2.1** Testes: catálogo padrão tem Copom (ativa), CVM (desligada), Releases B3 (indisponível, "em
  breve") e Importadas (ativa); `alternar` grava e recusa Origem indisponível; o repositório lista a Ata do
  Copom 280 com resumo (título, data, ≥ 1 número, primeiras frases ≤ 280 caracteres); acha o arquivo por
  identificador em `data/atas/` e em `data/fontes/<origem>/`; recusa identificador com `..`; `sugerir` põe
  no topo o mais recente, desempata por mais números e depois pelo peso da Origem, ignora Origem
  desligada e responde `None` sem itens.
- [ ] **2.2** Implementar.
- [ ] **2.3** `uv run pytest tests/test_origens.py -q` verde.

### Tarefa 3: Importar, adaptador da CVM e "Atualizar fontes"

**Arquivos:** criar `origens/{importacao,cvm,atualizacao}.py`; testes em `tests/test_importacao.py` e
`tests/test_cvm.py` (novos).

- [ ] **3.1** Testes de importação: texto vira Ata `importada` com `.txt` e `.json`; PDF vira `.pdf` + `.txt`;
  arquivo que não é PDF nem texto UTF-8 é recusado; PDF falso (cabeçalho errado) é recusado; texto vazio é
  recusado; identificador gerado do título sem acento nem barra e sem colidir.
- [ ] **3.2** Testes da CVM com `httpx.MockTransport`: lê o CSV `;` em latin-1 de um zip, filtra a categoria
  "Fato Relevante", pega os mais recentes, baixa por `Link_Download`, detecta PDF por `%PDF` mesmo com
  `Content-Type: text/html`, espera 10 s entre requisições (relógio injetado), cai para o ano anterior
  quando o zip do ano atual dá 404, e falha de rede vira `ErroDeIngestao` sem apagar o que existia.
- [ ] **3.3** Implementar. `atualizacao.py` roda em uma thread, grava `atualizacao.json` (`rodando`, `ok`,
  `erro`, mensagem e horário) e nunca levanta para quem chama.
- [ ] **3.4** `uv run pytest tests/test_importacao.py tests/test_cvm.py -q` verde.

### Tarefa 4: Rotas e `Gerenciador`

**Arquivos:** `api/app.py`, `api/geracao.py`, `api/resumo.py`; testes em `tests/test_api_fontes.py` (novo).

**Produz:**

```text
GET   /api/fontes                       → origens com os itens (ResumoDaAta) e o estado da atualização
PATCH /api/fontes/{id}                  corpo {ativa} → Origem (404 desconhecida, 409 indisponível)
POST  /api/fontes/atualizar             → 202, estado da atualização
GET   /api/fontes/atualizacao           → estado
POST  /api/fontes/importar?titulo=&data_referencia=   corpo cru PDF ou texto → 201 ResumoDaAta
GET   /api/curadoria/sugestoes          → {destaque_unico: Sugestao | null, visao_unida: null}
ExecucaoResumo.categoria, Andamento.categoria, AtaResumo.categoria
```

- [ ] **4.1** Testes: a lista traz a Copom 280 com resumo e a Origem CVM desligada; liga e desliga persistem
  no disco; Releases B3 responde 409; importar texto aparece na lista e vira escolha válida no
  `POST /api/execucoes` (modo Real com chave de teste e executor falso); a Saída de Origem importada nasce
  com `categoria: "importada"`; Demo para Ata importada responde 422; sugestão devolve a Copom 280 com
  motivo; corpo cru enorme (> 15 MB) responde 413; atualizar sem rede devolve `erro` sem 500.
- [ ] **4.2** Implementar. `criar_app(..., pasta_fontes=PASTA_FONTES)`; o `Gerenciador` acha a Ata pelo
  repositório (Copom em `data/atas/`, resto em `data/fontes/`).
- [ ] **4.3** Regenerar contrato; `uv run pytest -q` verde.

### Tarefa 5: Front

**Arquivos:** `web/src/dados/cliente.ts`, `web/src/lib/` (nova `fontes.ts` + teste), componentes
`CartaoDeAta.tsx`, `TrilhoDeOrigem.tsx`, `ImportarDocumento.tsx`; páginas `Fontes.tsx`, `Curadoria.tsx`.

- [ ] **5.1** `lib/fontes.ts` + Vitest: seleção de itens por bolinha (alternar, contar por Origem, ordem estável),
  `selo` ("não calibrado" para categoria diferente de Copom).
- [ ] **5.2** Guia Fontes: um trilho por Origem (título, chip "ligada", **Ver tudo**), cartões com data, título,
  resumo de duas linhas, número de Âncoras, bolinha de seleção e selo; Releases como linha tracejada "em
  breve"; topo com **Importar documento** e **Atualizar fontes** (estado e erro).
- [ ] **5.3** Curadoria, passo 1: cartão **Destaque único** com o motivo e **Usar este destaque**; cartão **Visão
  unida** "em breve"; **Montar a minha** com a contagem e **Usar selecionados** (exatamente um item
  nesta fase). Selo "não calibrado" nos itens fora do Copom e no passo 2 (Demo desabilitada com o motivo).
- [ ] **5.4** `npm test`, `npm run build`.

### Tarefa 6: Registros e verificação

- [ ] **6.1** CONTEXT.md (Origem, Ata ampliada), ADR 0018 (origens e categoria da Ata), spec (decisões).
- [ ] **6.2** `uv run pytest -q`, `npm test`, `npm run build`, `scripts/vocabulario.py` (16 achados).
- [ ] **6.3** Navegador (Edge): importar um texto, ligar a CVM, escolher o item, gerar em Real é impossível sem
  chave, então verificar a recusa; Demo do Copom continua funcionando. Se houver rede, rodar o adaptador da
  CVM uma vez de verdade e registrar o resultado.

---

## Registro da execução

Executado em 2026-10-10, inline, em `main`, sem commits. Ao fim da fase: 1045 testes pytest e 69 Vitest,
build verde, `scripts/vocabulario.py` nos mesmos 16 achados da equipe.

Divergências do plano:

- **`comunicado_relevante` no lugar de `fato_relevante`** e `comunicado` no lugar de `documento` nos nomes: o
  verificador de vocabulário acusa `fato` (_Avoid_ de Âncora), `documento` e `pdf` (_Avoid_ de Ata), `item`,
  `corte` e `entrega`. O texto de tela continua "Fatos Relevantes" e "Importar documento".
- **As preferências (ligar e desligar) ficam em `data/fontes/preferencias.json`**, não no catálogo versionado:
  ligar a CVM não suja o repositório.
- **"Atualizar fontes" guarda o estado em memória**, não em `atualizacao.json`: um processo só.
- **`extracao_completa`** no resumo, a recusa da rota e o aviso na tela não estavam no plano. Vieram da primeira
  execução real do adaptador da CVM (abaixo).
- A regra de `numero_principal` prefere o primeiro valor em reais (o plano dizia "o primeiro número").

Execução real do adaptador da CVM (rede disponível, pasta temporária): os zips de 2025 e de 2026 responderam 200
(a pesquisa dizia que o de 2026 estava 404). Baixou o Fato Relevante mais recente (Porto Seguro, pedido de
cancelamento de registro, 02/10/2026) em 11 s, detectou o PDF e extraiu 2.746 caracteres. Esse comunicado
tem a data e **nenhum número com unidade**: pelo conjunto genérico toda Célula reprovaria. Registrado no ADR 0018.

Conferido no navegador: importar um texto pelo formulário, ligar a CVM, "Atualizar fontes" com erro simulado,
selecionar e levar à Curadoria, o selo "não calibrado" e o bloqueio de Demo e Real sem chave.

