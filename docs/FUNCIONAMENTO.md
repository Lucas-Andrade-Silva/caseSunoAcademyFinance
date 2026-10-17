# Funcionamento — Suno Content

Como o sistema roda hoje, conferido contra o código: o que acontece no back quando uma geração é
pedida, o que a interface faz no navegador e o que ela pede ao servidor, comandos, configuração e
arquivos gravados. O desenho e o porquê estão em [ARQUITETURA.md](ARQUITETURA.md) e
[DECISOES.md](DECISOES.md). Todos os comandos rodam na raiz do repositório.

## Componentes

| Pasta | O que é |
|---|---|
| `src/suno/` | Pacote Python: Gerador, Avaliador, Pacote, vídeo, provedores de LLM, API (FastAPI) e CLI |
| `web/` | Interface React + Vite + Tailwind; depois do build, a API a serve em `/` |
| `render/` | Puppeteer: captura os slides HTML das famílias visuais em PNG |
| `netlify-jev/` | Ponte na Netlify que leva o pedido de Qualidade ao Jev |
| `evals/`, `tests/` | Suíte `pydantic-evals` e `pytest`, sem rede e sem `.env` |
| `scripts/` | Preparar, testar, demo, regerar o cliente da API, relatório |
| `data/` | Atas, Léxico, canary, Calibração, fotos e a execução de demonstração |
| `templates/` | Carrosséis reais da Suno e a bancada de recriação; nada lê esta pasta em execução |

Os templates usados de fato ficam em `src/suno/pacote/templates/` e as fontes em
`src/suno/pacote/fontes/`.

## Back: o que acontece numa geração

### 1. O pedido (`POST /api/execucoes`)

Corpo: `nome`, `ata` **ou** `itens` (Visão unida), `modo` (`demo` ou `real`), `pedido` (lista de
posições `{audiencia, formato}`), `duracao` (40, 60, 90, 120 ou 180; padrão 60) e, só para
Carrossel, `composicao_visual` + `referencia_visual` (os dois juntos; a referência precisa existir,
estar aprovada e casar com a composição).

O servidor (`src/suno/api/geracao.py`) valida e recusa com 404/422:

- a Ata precisa existir e ter extração completa;
- `demo` usa o provedor `falso` e só existe para Ata com `data/respostas_prontas/<ata>.json`;
- `real` usa o `roteador` e exige chave e modelo de provedor;
- Visão unida: de 2 a 5 Atas distintas, só no modo `real`.

Passou: o identificador é `<ata>-<falso|roteador>-<AAAAMMDD-HHMMSS>`, o servidor grava
`andamento.json` como `na_fila` e responde **202**. Um único worker (thread `geracao-suno`) roda um
job por vez, em fila.

### 2. O job

Estados em `andamento.json`: `na_fila` → `gerando` → `concluida`, ou `falhou` (com o erro, até 500
caracteres) ou `interrompida`. Ao subir, a API marca como `interrompida` o que tinha ficado em
`na_fila` ou `gerando`.

`executar` (`src/suno/gerador/execucao.py`) segue estas fases, cada uma registrada no andamento:

1. **`extraindo_ancoras`**: o curador extrai, uma vez, as Âncoras textuais e a tabela de Âncoras
   numéricas (com LLM; no modo `demo`, das respostas prontas).
2. **`gerando_celulas`**: três geradores, um por Audiência, em threads paralelas; cada um abre uma
   thread por Formato pedido. Até nove Ciclos de correção correm ao mesmo tempo.
3. **`avaliando_matriz`**: conferência determinística da Matriz, só quando há 2 posições ou mais.
4. **`gravando`**: grava `execucao.json` e `celulas/<audiencia>-<formato>.md`. Nada da execução
   vai para o disco antes desta fase, só o andamento.

### 3. O Ciclo de cada Célula

Cada rodada gera a Célula e a avalia em camadas, cada uma só se a anterior aprovou:

1. **Determinístico**, nesta ordem: integridade da extração, Flesch-BR, Densidade, Aderência e
   Recomendação.
2. **Qualidade (Jev)**: obrigatória com provedor real (sem chave, a execução falha); no `falso`,
   fica sempre de fora para a Demo permanecer offline.
3. **Fidelidade à Ata** (LLM): ligada por padrão no modo Real e sempre fora no `falso`.

Reprovada, a Célula volta ao seu gerador com as correções medidas e o texto anterior, até o teto de
rodadas (padrão 4, de 0 a 10). Ela para quando aprova, quando reprova por falha de extração (que
vai direto à revisão humana, H4) ou quando o teto acaba. Erro de provedor também manda a Célula
para H4, com o motivo registrado.

Uma correção permanece no pedido enquanto a sua própria métrica não for medida e aprovada. Isso
evita alternar entre duas reprovações quando uma camada posterior, como Fidelidade, não chega a
rodar na rodada seguinte. O trecho da Ata citado pela Fidelidade é evidência da divergência, mas
seus números só podem entrar na Célula quando também existem como Âncoras; caso contrário, o
Gerador remove o número e preserva apenas o fato qualitativo.

### 4. Depois da geração

- **Pacote** (`POST .../pacotes/montar`, thread própria; andamento em `GET .../pacotes/montagem`):
  monta PNGs, legenda e conferência visual das Células aprovadas. Quando há chave, o Diretor de
  Arte e o juiz de visão (folha de contato) rodam sozinhos pelo roteador; falha deles não impede o
  Pacote. Com `SERPER_API_KEY`, `servir` liga a busca de fotos na web (`--sem-fotos-da-web`
  desliga). A Demo não descobre esses serviços no ambiente: permanece offline mesmo que a máquina
  tenha chaves configuradas.
- **Editar texto** (`PUT .../celulas/{aud}/{formato}/texto`): o servidor grava o texto novo e
  reavalia sem LLM. A edição invalida decisão anterior e derivados daquela Célula; Pacote, plano,
  vídeo, prévia e ZIP só voltam a ser entregues se corresponderem à revisão liberada.
- **Plano do vídeo** (`GET .../celulas/{aud}/roteiro/plano`): só para Roteiro aprovado (senão 409).
- **Vídeo mp4**: só pela CLI (`suno.cli video`), nunca pela API.

## Front: o que a interface faz

Todo acesso à API passa por `web/src/dados/cliente.ts`. Ao abrir, a interface pré-carrega
fontes, execuções, saúde, referências e famílias visuais.

**Modo Demo ou Real.** Fica no navegador (`localStorage`, chave `suno.configuracoes`). Sem escolha
salva, é Real se `GET /api/saude` diz que há provedor real disponível. Demo envia `modo: demo`
(provedor falso), Real envia `modo: real` (roteador). Na Ingestão, Demo mostra o acervo marcado
como `demo_disponivel` com suas datas originais; a janela de 30 dias vale para o modo Real.

**Como uma geração é pedida.** Cada guia de conteúdo pede **um Formato** para as Audiências
marcadas: `POST /api/execucoes`, depois `GET .../andamento` a cada 1,5 s. Em `concluida`, lê
`GET /api/execucoes/{id}` e mostra a última tentativa de cada Audiência, com o Laudo. A geração
em curso fica em `sessionStorage` e é retomada se a página recarregar. A interface sempre envia
`duracao: 60`; outra duração, só pela CLI.

| Guia | No servidor | Só no navegador |
|---|---|---|
| **Ingestão** | `GET /api/fontes`, ligar/desligar origem, atualizar em duas etapas (consultar, depois baixar um período), cancelar, importar documento, ler Ata | Seleção de até 3 notícias (`sessionStorage`) |
| **Texto analítico** | Geração; salvar texto (reavalia sem LLM) | Editor (TipTap), Laudo aberto na reprovação com o trecho apontado e ação para editar; quatro apresentações; versão não avaliada é salva como Rascunho |
| **Carrossel** | Geração; salvar texto (reavalia); prévias em HTML; Âncoras; render e zip das famílias visuais pelo servidor | A reprovação abre e marca o quadro e o campo afetados; gerar, salvar e exportar só liberam após a reavaliação aprovar |
| **Vídeo** | Geração; salvar falas e telas (reavalia); plano de atuação | A reprovação abre e marca a cena afetada; prompt e salvo ficam bloqueados até o Laudo aprovar a versão exibida |
| **Histórico** | Últimas 30 gerações (`GET /api/execucoes`, renovada ao criar, concluir ou falhar e a cada 3 s enquanto alguma roda) | Até 60 conteúdos salvos (`localStorage`) |
| **Configurações** | `GET/PUT/DELETE /api/configuracoes`: Jev, URL e Limiar do Jev, Fidelidade, rodadas, requisições por minuto, modelos e fila de provedor por papel; chaves aparecem só como presentes ou ausentes | Modo Demo/Real e nome exibido |

**O render do Carrossel tem dois caminhos.** O layout escuro antigo é desenhado e exportado no
navegador. Qualquer família visual (notícia, explicativo, jornal, dados, asset) é renderizada pelo
servidor: a interface chama `pacotes/montar`, acompanha a montagem (até 240 s) e baixa o zip de
`GET .../pacotes/{aud}/carrossel/baixar`. O manifesto identifica a revisão do conteúdo; durante
uma montagem a listagem fica vazia e os ZIPs são recusados, evitando arquivos parciais ou antigos.

**O que a API tem e a interface não usa:** decisão humana por Célula, aprovação do Pacote (H5),
filas humanas, resumo, renomear, apagar e exportar execução, sugestões de curadoria, cadastro e
coleta de referências visuais. Ficam disponíveis pela API.

## Linha de comando

`uv run --offline python -m suno.cli <comando>` (ou o atalho `suno`). O `.env` é lido sem
sobrescrever o ambiente.

| Comando | Opções |
|---|---|
| `executar` | `--ata <arquivo>` (obrigatória), `--provedor falso\|gemini\|groq\|roteador` (padrão `falso`), `--duracao 40\|60\|90\|120\|180` (padrão 60), `--identificador`, `--sem-jev`, `--fidelidade`, `--sem-fidelidade`, `--execucoes` |
| `pacote` | `--execucao <id>`, `--familia suno_escuro\|noticia\|explicativo\|jornal\|dados\|asset`, `--buscar-fotos`, `--execucoes` |
| `video` | `--execucao <id>`, `--audiencia`, `--narracao` (edge-tts, precisa de rede), `--execucoes` |
| `plano` | `--execucao <id>`, `--audiencia`, `--provedor` (padrão `falso`), `--execucoes` |
| `buscar-ata` | `--reuniao N`, `--destino` (padrão `data/atas`); precisa de rede |
| `servir` | `--host` (127.0.0.1), `--porta` (8000), `--execucoes`, `--sem-fotos-da-web` |
| `imagens` | `--pasta` (padrão `data/imagens`) e `listar`, `buscar "<assunto>" [--contexto] [--rede]` ou `aprovar <id>` |

## Configuração (`.env`)

Nenhuma variável é necessária para a demo e os testes. Valores padrão do código:

| Variável | Padrão |
|---|---|
| `GEMINI_API_KEY`, `GROQ_API_KEY` | — |
| `GEMINI_MODELO`, `GROQ_MODELO` | **vazio**: sem modelo, o provedor não sobe (o `.env.example` sugere `gemini-2.5-flash` e `openai/gpt-oss-120b`) |
| `JEV_API_KEY` (ou `TYPESAFE_API_KEY`) | — |
| `JEV_URL` | `https://api.typesafe.ai/v1/systemone`; só aceita https |
| `SUNO_JEV` | ligado; só `0` desliga |
| `SUNO_JEV_LIMIAR` | 0,6 |
| `SUNO_FIDELIDADE` | ligada; só `0` desliga |
| `SUNO_RODADAS` | 4 (de 0 a 10) |
| `SUNO_RPM` | 8 (de 0 a 600; 0 desliga) |
| `SERPER_API_KEY` | —; sem ela a busca de fotos usa o Bing |
| `SUNO_RENDER` | `auto`; `pillow` força o render sem Node |
| `SUNO_CONTATO` | User-Agent padrão do case, para o BCB |
| `SUNO_EXECUCOES` | `data/execucoes` (só a CLI) |
| `SUNO_CONFIGURACOES` | `data/configuracoes.json` |

`SUNO_JUIZ_VISAO`, que ainda aparece no `.env.example`, não é lido pelo código.

A aba Configurações grava `data/configuracoes.json` (não versionado), que vale por cima do `.env`
campo a campo e é relido quando muda: Jev, URL e Limiar do Jev, Fidelidade, rodadas, RPM, modelos e
a fila de provedores de cada papel (gerador, checador, vídeo, juiz de visão, diretor de arte,
analista visual). Chaves de API, `SUNO_RENDER`, `SERPER_API_KEY` e pastas ficam só no `.env`.

## Render do Carrossel no servidor

Com Node e `render/node_modules/puppeteer` (`cd render && npm install`), os slides saem dos
templates HTML das famílias. Sem isso, ou com `SUNO_RENDER=pillow`, entra a reserva em Pillow +
matplotlib, sem navegador e sem foto; é a que o `pytest` exercita.

## Onde cada coisa grava

```
data/
  atas/                         Atas versionadas (.pdf, .txt, .json)
  fontes/catalogo.json          catálogo de Origens; o resto de fontes/ é local
  respostas_prontas/            respostas do provedor falso (modo Demo)
  lexico/, canary/, calibracao/ Léxico, armadilhas de Recomendação, rótulos de Calibração
  imagens/                      biblioteca local de fotos e indice.json
  configuracoes.json            aba Configurações (não versionado)
  execucoes/
    suno.sqlite3                histórico de layouts, referências visuais, coleta e feedback
    referencias-visuais/        imagens das referências cadastradas
    <id>/andamento.json         estado do job, reescrito a cada fase
    <id>/execucao.json          Âncoras, Células com tentativas e Laudos, pendências, custo
    <id>/celulas/*.md           cada Célula em Markdown
    <id>/pacote/<aud>-<formato>/
                                pacote.json, legenda.txt; no Carrossel, slide-NN.png/.json/.html
                                e a folha de contato; no Roteiro, video.mp4, plano.json e plano.md
```

Só `data/execucoes/demo-copom-280/` é versionada (sem mp4 nem áudio).

## Testes

| O quê | Comando |
|---|---|
| Suíte Python (inclui `pydantic-evals`) | `scripts/test.sh` ou `scripts\test.ps1` |
| Interface | `cd web && npm test` e `npm run build` |
| Ponte do Jev | `cd netlify-jev && npm test` |
| Contrato da API | `tests/test_contrato_openapi.py`; regere o cliente com `scripts/gerar-cliente.sh` |
| Relatório de uma execução | `uv run --offline python scripts/relatorio.py --execucao demo-copom-280` |

`tests/conftest.py` derruba qualquer socket. `scripts/testar_llm_de_avaliacao.py` e
`scripts/testar_busca_de_imagens.py` usam rede e chaves reais e ficam fora da suíte.
