# Funcionamento — Suno Content

O que o sistema faz hoje, do ponto de vista de quem o opera: comandos, configuração, onde cada
coisa grava e o que a API expõe. O desenho e o porquê estão em [ARQUITETURA.md](ARQUITETURA.md)
e em [DECISOES.md](DECISOES.md) (texto completo em [adr/](adr/)). Todos os comandos rodam na raiz do repositório.

## Componentes

| Pasta | O que é | Linguagem |
|---|---|---|
| `src/suno/` | O pacote Python: Gerador, Avaliador, Pacote, vídeo, provedores de LLM, API | Python 3.12+ |
| `web/` | A interface (seis guias), servida pela API depois do build | React + Vite + Tailwind |
| `render/` | Captura os slides HTML do Carrossel em PNG (ADR 0020) | Node + Puppeteer |
| `netlify-jev/` | Ponte que leva o pedido de Qualidade ao Jev (ADR 0035) | Netlify Function |
| `evals/` | Casos da suíte `pydantic-evals` (ADR 0003) | Python + YAML |
| `tests/` | A suíte `pytest`: roda sem rede e sem `.env` | Python |
| `scripts/` | Preparar, testar, rodar a demo, regerar o cliente, gerar o relatório | sh, PowerShell, Python |
| `data/` | Atas, Léxico, canary, Calibração, fotos e execuções gravadas | JSON, YAML, PDF |
| `templates/` | Carrosséis reais da Suno (`suno/`) e a bancada que recriou as famílias (`recriados/`) | HTML, imagens |

Os templates que o código usa de fato ficam dentro do pacote, em `src/suno/pacote/templates/`
(famílias visuais e layouts) e `src/suno/pacote/fontes/`. Nada lê `templates/` da raiz em tempo
de execução.

## Fluxo de uma execução

1. **Ata** — um `.pdf` ou `.txt` em `data/atas/` (versionado) ou importado pela interface.
2. **Extração** — Âncoras textuais e a tabela de Âncoras numéricas, uma vez por Ata (ADR 0011).
3. **Matriz 3×3** — um curador prepara o dossiê; três geradores (um por Audiência) escrevem
   Texto analítico, Carrossel e Roteiro, em paralelo (ADR 0015).
4. **Avaliador** — cinco medidas sem LLM: Flesch-BR, Densidade, Aderência, Recomendação e
   integridade da extração. Depois, a Qualidade (Jev) e a Fidelidade à Ata (ADR 0035, 0036).
5. **Ciclo de correção** — a Célula reprovada volta ao seu gerador com o valor medido que faltou.
   O teto de rodadas é configurável: padrão **4**, de 0 a 10 (`SUNO_RODADAS` ou a aba
   Configurações). O ADR 0013 fixava 2. Falha de extração vai direto à fila humana (H4).
6. **Pacote de publicação** — só das Células aprovadas: PNGs do Carrossel, legenda, créditos
   das fotos e conferência visual (ADR 0014, 0030).
7. **Vídeo** — comando separado, fora do grafo, a partir de um Roteiro aprovado (ADR 0004).
8. **Publicação** — manual. Nenhuma integração com Instagram, TikTok ou Drive.

## Linha de comando

`uv run --offline python -m suno.cli <comando>` (o pacote também instala o atalho `suno`).
O `--offline` evita que o `uv` tente revalidar na rede o wheel do modelo do spaCy.

| Comando | O que faz | Rede |
|---|---|---|
| `executar --ata <arquivo> [--provedor falso\|gemini\|groq\|roteador] [--duracao 40\|60\|90\|120\|180] [--identificador <id>] [--sem-jev] [--sem-fidelidade]` | Gera e avalia as nove Células e grava a execução | só com provedor real |
| `pacote --execucao <id> [--familia suno_escuro\|noticia\|explicativo\|jornal\|dados\|asset] [--buscar-fotos]` | Monta o Pacote das Células aprovadas | só com `--buscar-fotos` |
| `video --execucao <id> --audiencia <audiencia> [--narracao]` | Renderiza o `video.mp4` 9:16 do Roteiro aprovado | só com `--narracao` (edge-tts) |
| `plano --execucao <id> --audiencia <audiencia> [--provedor ...]` | Grava `plano.json` e `plano.md`, o plano de edição para ferramenta de avatar | só com provedor real |
| `buscar-ata [--reuniao N] [--destino data/atas]` | H1: baixa uma Ata do Copom do BCB | sim |
| `servir [--host 127.0.0.1] [--porta 8000] [--sem-fotos-da-web]` | Sobe a API e, se houver `web/dist/`, a interface | só ao buscar notícias novas, gerar com provedor real ou buscar fotos (com `SERPER_API_KEY`, desligável por `--sem-fotos-da-web`) |
| `imagens listar \| buscar "<assunto>" [--rede] \| aprovar <id>` | Biblioteca local de fotos dos slides | só com `--rede` |

`--provedor falso` é um LLM roteirizado, sem rede, com respostas fixas em
`data/respostas_prontas/`. É o que a demo, os testes e o modo Demo da interface usam.
`--execucoes <pasta>` muda a pasta de saída em todos os comandos.

## Configuração (`.env`)

Copie `.env.example` para `.env`. Nenhuma variável é obrigatória para a demo e o `pytest`.

| Variável | Para quê | Padrão |
|---|---|---|
| `GEMINI_API_KEY`, `GEMINI_MODELO` | Gerador | modelo `gemini-2.5-flash` |
| `GROQ_API_KEY`, `GROQ_MODELO` | Fidelidade e reserva do Gemini | modelo `openai/gpt-oss-120b` |
| `JEV_API_KEY` (ou `TYPESAFE_API_KEY`), `JEV_URL` | Qualidade pelo Jev | `https://api.typesafe.ai/v1/systemone` |
| `SUNO_JEV` | `0` desliga a Qualidade | ligada (`1`); sem chave, não roda |
| `SUNO_JEV_LIMIAR` | Nota mínima por dimensão, de 0 a 1 | `0,6` |
| `SUNO_FIDELIDADE` | `0` desliga a Fidelidade à Ata | ligada (`1`) |
| `SUNO_RODADAS` | Teto do Ciclo de correção, de 0 a 10 | `4` |
| `SUNO_RPM` | Teto de requisições por minuto aos LLMs, somados; `0` desliga | `8` |
| `SUNO_JUIZ_VISAO` | `1` liga o juiz de visão do Carrossel | desligado |
| `SERPER_API_KEY` | Busca de fotos no Google Imagens; sem ela, cai no Bing | — |
| `SUNO_RENDER` | `pillow` força o render de reserva, sem Node | `auto` |
| `SUNO_CONTATO` | User-Agent das requisições ao BCB | texto do case |
| `SUNO_EXECUCOES` | Pasta das execuções | `data/execucoes` |
| `SUNO_CONFIGURACOES` | Arquivo da aba Configurações | `data/configuracoes.json` |

A aba Configurações da interface grava em `data/configuracoes.json` (não versionado), e esse
arquivo tem precedência sobre o `.env` para Jev, Fidelidade, RPM, rodadas, modelos e `JEV_URL`.

## Render do Carrossel

Com Node e `render/node_modules/puppeteer` instalados (`cd render && npm install`), os slides
saem dos templates HTML das famílias visuais. Sem isso, ou com `SUNO_RENDER=pillow`, entra a
reserva em Pillow + matplotlib: determinística, sem navegador, com o layout escuro e sem foto.

## Onde cada coisa grava

```
data/
  atas/                      Atas versionadas da demo (.pdf, .txt e .json de metadados)
  fontes/catalogo.json       catálogo de Origens; o resto de fontes/ é cópia local, não versionada
  respostas_prontas/         respostas do provedor falso, por Ata
  lexico/                    Léxico e a origem/licença de cada fonte
  canary/                    armadilhas de Recomendação e padrões sintáticos
  calibracao/                formato e exemplo dos rótulos humanos (H2)
  imagens/                   biblioteca local de fotos e indice.json
  configuracoes.json         o que a aba Configurações salvou (não versionado)
  execucoes/
    suno.sqlite3             histórico de layouts, referências visuais e feedback (não versionado)
    <id>/execucao.json       o estado inteiro de uma execução: Âncoras, Células, Laudos, filas, custo
    <id>/celulas/*.md        cada Célula em Markdown
    <id>/pacote/<audiencia>-<formato>/
                             pacote.json, legenda.txt; no Carrossel, slide-NN.png/.json e a folha
                             de contato; no Roteiro, video.mp4, plano.json e plano.md
```

Só `data/execucoes/demo-copom-280/` é versionada (sem mp4 nem áudio). A API, o `pytest` e o
relatório leem o mesmo `execucao.json`.

## API

FastAPI em `src/suno/api/app.py`. Contrato em `web/openapi.json`; o cliente TypeScript
(`web/src/api/schema.d.ts`) é gerado dele por `scripts/gerar-cliente.sh` (ou `.ps1`), e
`tests/test_contrato_openapi.py` falha se os dois divergirem.

| Grupo | Rotas |
|---|---|
| Saúde | `GET /api/saude` |
| Atas e Origens | `/api/atas`, `/api/fontes` (listar, ligar/desligar, atualizar em duas etapas, importar) |
| Execuções | `GET/POST /api/execucoes`, andamento, resumo, renomear, apagar, exportar, Âncoras |
| Células | leitura, Âncoras por Célula, edição de texto, decisão humana, plano do Roteiro |
| Filas humanas | `GET .../filas`, `POST .../filas/h4/{indice}/resolver` |
| Pacotes | montar em segundo plano, andamento, listar, baixar, aprovar (H5), arquivos |
| Visual | `/api/familias-visuais`, `/api/referencias-visuais` (cadastro, coleta, descoberta, prévia) |
| Curadoria | `GET /api/curadoria/sugestoes` |
| Configurações | `GET/PUT/DELETE /api/configuracoes` |

A geração disparada pela API roda em segundo plano, um job por vez (ADR 0017).

## Interface

Seis guias: Ingestão, Texto analítico, Carrossel, Vídeo, Histórico e Configurações (ADR 0028).
Detalhe de cada guia, desenvolvimento e testes em [web/README.md](../web/README.md).

## Testes e avaliação

| O quê | Comando |
|---|---|
| Suíte Python (inclui `pydantic-evals`) | `scripts/test.sh` ou `scripts\test.ps1` |
| Interface | `cd web && npm test` (Vitest) e `npm run build` (inclui `tsc`) |
| Ponte do Jev | `cd netlify-jev && npm test` |
| Vocabulário do código (lista nomes com palavras _Avoid_; precisa do `CONTEXT.md` local, que não é versionado) | `uv run --offline python scripts/vocabulario.py` |
| Relatório de uma execução | `uv run --offline python scripts/relatorio.py --execucao demo-copom-280` |

`tests/conftest.py` derruba qualquer socket: um teste que tente usar a rede falha. Dois scripts
de conferência manual usam rede e chaves reais, e ficam fora da suíte:
`scripts/testar_llm_de_avaliacao.py` (Jev e Fidelidade) e `scripts/testar_busca_de_imagens.py`.
