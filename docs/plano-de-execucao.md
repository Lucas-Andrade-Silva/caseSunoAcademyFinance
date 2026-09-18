# Plano de execução — Suno Content

Escrito depois de ler, inteiros e nesta ordem, `CLAUDE.md`, `CONTEXT.md`, `docs/ARQUITETURA.md`,
os catorze ADRs, `docs/research/viabilidade-tecnica.md` e o enunciado do case. É a lista dos
arquivos que serão criados, com o ADR que justifica cada um. Os agentes das etapas 1 a 3 leem
este arquivo, o `CONTEXT.md` e os ADRs que lhes cabem — nunca o repositório inteiro.

## O que foi verificado antes de fixar versões (18/09/2026)

| Verificação | Resultado |
|---|---|
| Python da máquina | 3.14.5; `uv` 0.11.26; Node 24.13.0 / npm 11.6.2 |
| `spacy==3.8.16` | tem wheel `cp314-win_amd64`; carrega `pt_core_news_sm` 3.8.0 offline |
| `pydantic-evals==2.45.0` | instala em 3.14; traz `pydantic-ai-slim` e `logfire-api` (shim no-op) |
| `pypdf==6.19.0` | BSD-3, puro Python; extraiu a Ata 280 (5 páginas, 14.502 caracteres, camada de texto real). Não estava na pesquisa; conferido na documentação oficial. PyMuPDF foi descartado por ser AGPL. |
| `text2num==3.1.0` | importa como `text_to_num`; `text2num("quinze","pt") == 15` |
| API do BCB | `atascopom/ultimas?quantidade=5&filtro=` respondeu; Ata 280 (4–5/08/2026) baixada, magic bytes `%PDF-1.7` |
| ffmpeg | **não existe** na máquina; o ramo de vídeo usa o binário embutido do `imageio-ffmpeg` (a verificar na doc oficial pelo agente 13) |

## Regras transversais que valem para todo arquivo

1. Nomes saem do `CONTEXT.md`. Palavras da lista _Avoid_ não aparecem em nome de classe, função,
   campo, rota, arquivo ou tabela. Exceções mandadas pelo prompt: `ingestao/pdf.py` (é o formato de
   arquivo, não a Ata) e `docs/relatorio-experimental.md` (Entregável 6).
2. Nenhum módulo importa SDK de LLM. Só `provedores/` fala com a rede, via `httpx` ([ADR 0007]).
3. `pytest -q` passa sem `.env` e sem internet; `tests/conftest.py` derruba qualquer socket.
4. Cada arquivo tem um dono. Quem precisa mudar arquivo alheio avisa no relatório, não edita.

## Etapa 0 — feita pelo coordenador, antes de qualquer agente

| Arquivo | ADR / motivo |
|---|---|
| `pyproject.toml` | versões fixas; nenhuma dependência fora da pesquisa de viabilidade (0002, 0003, 0007, 0012) |
| `.env.example` | chaves e nomes de modelo por provedor, nunca fixados em código (0007) |
| `.gitignore` | `.venv`, `.env`, `__pycache__`, `web/node_modules`, `web/dist` |
| `scripts/setup.{ps1,sh}`, `scripts/test.{ps1,sh}`, `scripts/demo.{ps1,sh}` | rodam em PowerShell e sh; a demo roda sem rede (0006) |
| `src/suno/dominio.py` | todos os modelos Pydantic fechados: Ata, Âncoras, Célula, Laudo com três destinos e motivos enumerados, Pacote, filas humanas, contratos de provedor (0001, 0008, 0011, 0013, 0014) |
| `src/suno/provedores/base.py` | a porta de entrada única para qualquer LLM (0007) |
| `src/suno/provedores/falso.py` | LLM de mentira com fila de respostas por rótulo, sem rede; torna o Gerador e o roteador testáveis (0007) |
| `src/suno/avaliador/__init__.py` | a assinatura `avaliar(conteudo, ancoras, audiencia) -> Laudo` (0001) |
| `src/suno/cli.py` | `python -m suno.cli executar|pacote|buscar-ata|video|servir`, delegando aos módulos das etapas |
| esqueletos com `raise NotImplementedError` e o ADR que manda em cada um | ver tabela das etapas 1–3 |
| `data/atas/copom-280-2026-08-05.{pdf,txt,json}` | uma Ata de verdade, versionada, com texto já extraído ao lado (0006) |
| `tests/conftest.py`, `tests/test_trava_rede.py` | a trava de rede: teste que quebra se outro teste tentar acessar a rede (0001) |
| `tests/test_dominio.py`, `tests/test_provedor_falso.py` | modelos e LLM falso verdes |
| `docs/adr/0002-…md` (atualização) | registro da escolha: silabador reimplementado a partir de Silva (2011), não copiado do NILC (GPL) |
| `docs/plano-de-execucao.md` | este arquivo |

## Etapa 1 — seis agentes em paralelo, nada depende de LLM

| # | Dono de | ADR | Termina quando |
|---|---|---|---|
| 1 | `src/suno/avaliador/silabas.py`, `src/suno/avaliador/flesch_br.py`, `tests/test_silabas.py`, `tests/test_flesch_br.py` | 0002 | dá 34,4 no texto de 45 palavras / 4 frases / 108 sílabas (a pesquisa cita o número, não o texto: o agente escreve o texto e conta à mão); acerta `ideia`, hiatos, ditongos decrescentes, `-ia` final e palavras de finanças |
| 2 | `src/suno/avaliador/densidade.py`, `data/lexico/lexico.yaml`, `data/lexico/ORIGENS.md`, `tests/test_densidade.py` | 0012; pesquisa §3 | Léxico em arquivo com origem e licença por fonte; termo sem explicação na primeira ocorrência é detectado |
| 3 | `src/suno/avaliador/recomendacao.py`, `data/canary/canary.yaml`, `tests/test_recomendacao.py` | 0012 | pega todas as armadilhas do canary; `pt_core_news_sm` carrega sem internet |
| 4 | `src/suno/avaliador/aderencia.py`, `src/suno/avaliador/integridade.py`, `src/suno/ingestao/numeros.py`, `tests/test_numeros.py`, `tests/test_aderencia.py`, `tests/test_integridade.py` | 0011, 0013 | distingue `p.p.` de `%` e `CDI+2%` de `110% do CDI`; entende vírgula decimal e número por extenso |
| 5 | `src/suno/ingestao/bcb.py`, `src/suno/ingestao/pdf.py`, `tests/test_ingestao.py` | 0006 | busca no BCB é comando à parte; PDF reconhecido pelos primeiros bytes; teste usa o PDF do repositório |
| 6 | `src/suno/provedores/roteador.py`, `gemini.py`, `groq.py`, `sambanova.py`, `tests/test_roteador.py` | 0007 | lê a mensagem do 429 para distinguir minuto (espera) de dia (troca); o schema de saída viaja com o pedido e sobrevive à troca |

## Etapa 2 — quatro agentes, dependem da etapa 1

| # | Dono de | ADR | Termina quando |
|---|---|---|---|
| 7 | `src/suno/avaliador/laudo.py`, `src/suno/comite/*.py`, `tests/test_laudo.py`, `tests/test_comite.py` | 0001, 0008, 0013 | cinco medidas viram Laudo com três destinos; métrica sem base sai `ausente`; comitê nasce desligado, dois juízes, provedor ≠ Gerador |
| 8 | `src/suno/gerador/*.py`, `data/respostas_prontas/copom-280.json`, `tests/test_gerador.py`, `tests/test_ciclo.py` | 0010, 0011, 0013 | nove Células em paralelo com o LLM falso; número entra por preenchimento; teste prova que o Ciclo para na segunda tentativa e que falha de extração vai direto à fila humana |
| 9 | `src/suno/pacote/carrossel.py`, `legenda.py`, `visual.py`, `tests/test_pacote.py` | 0009, 0014 | PNG 1080×1350 exatos; Pillow mede estouro de caixa e contraste; número do gráfico bate com as Âncoras |
| 10 | `evals/*.py`, `evals/casos/*.yaml`, `src/suno/avaliador/calibracao.py`, `data/calibracao/FORMATO.md`, `tests/test_evals.py`, `tests/test_calibracao.py` | 0003 | `pydantic-evals` roda dentro do pytest com casos em YAML; Kappa e matriz de confusão saem de arquivo |

## Etapa 3 — quatro agentes, a parte de fora

| # | Dono de | ADR | Termina quando |
|---|---|---|---|
| 11 | `src/suno/api/*.py`, `web/src/api/` (cliente TS gerado), `tests/test_api.py` | 0005 | lê do disco o mesmo arquivo que o pytest lê; expõe filas H3, H4 e H5 |
| 12 | `web/*` (exceto `web/src/api/`) | 0005 | `npm run build` passa; Âncoras ao lado da Célula; reprovação com tela própria; veredito em palavras com número ao lado |
| 13 | `src/suno/video/*.py`, `tests/test_video.py` | 0004, 0014 | comando separado; consome Roteiro aprovado; um mp4 em 9:16; mede duração, proporção e áudio |
| 14 | `README.md`, `docs/relatorio-experimental.md` | Entregável 6 | metodologia das métricas, matriz de confusão, custo e latência medidos, passo a passo em máquina limpa |

## Onde a execução grava

`data/execucoes/<id>/execucao.json` é o único arquivo de estado de uma execução: Âncoras, as
nove Células com o histórico de tentativas e Laudos, filas humanas e custo. O Pacote grava em
`data/execucoes/<id>/pacote/`. A API lê daí, o pytest lê daí, o relatório cita daí.
