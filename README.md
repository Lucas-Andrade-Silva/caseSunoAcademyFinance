# Suno Content

Transforma uma Ata do Copom (o documento em que o Banco Central explica a decisão de juros) em
nove conteúdos: três públicos (Iniciante, Intermediário, Avançado) vezes três formatos (Texto
analítico, Carrossel e Roteiro de vídeo). Antes de liberar cada conteúdo, um avaliador sem
inteligência artificial confere a legibilidade, os termos técnicos, os números e se o texto
sugere investimento. O conteúdo que não passa é reescrito ou vai para revisão humana.

Case acadêmico feito por duas pessoas em duas semanas, com orçamento
R$ 0: todo modelo de linguagem usado roda em tier gratuito.

## O que você precisa

| Ferramenta | Para quê | Obrigatória? |
|---|---|---|
| [Python 3.12+](https://www.python.org/downloads/) | o sistema | sim |
| [uv](https://docs.astral.sh/uv/) | instala as dependências Python | sim |
| [Node.js](https://nodejs.org/) (testado com a versão 24) | a interface web e o render do Carrossel | só para a interface e o Carrossel em HTML |

Nenhuma chave de API é necessária para a demo e os testes.

## Instalar

```bash
# 1. Instale o uv (uma vez)
curl -LsSf https://astral.sh/uv/install.sh | sh     # Linux/macOS
winget install astral-sh.uv                         # Windows

# 2. Na pasta do projeto, prepare o ambiente
scripts/setup.sh                                    # Linux/macOS
scripts\setup.ps1                                   # Windows (PowerShell)
```

O `setup` instala as dependências (inclusive as do vídeo) e cria o `.env` a partir do
`.env.example`.

Opcional, para o Carrossel sair nos templates visuais da Suno em vez da versão simplificada:

```bash
cd render && npm install
```

## Rodar a demo (sem internet)

```bash
scripts/demo.sh        # Windows: scripts\demo.ps1
```

Gera as nove Células da Ata 280 com um modelo de linguagem simulado, avalia cada uma e monta o
Pacote de publicação das aprovadas. O resultado fica em `data/execucoes/demo-ao-vivo/`. No
terminal aparece `celulas=9 aprovadas=8 pendencias=1` e uma linha por Célula: a demo manda uma
Célula, de propósito, para a fila de revisão humana.

## Abrir a interface

```bash
cd web && npm install && npm run build && cd ..
uv run --offline python -m suno.cli servir
```

Abra <http://127.0.0.1:8000>. A interface tem seis guias: Ingestão, Texto analítico, Carrossel,
Vídeo, Histórico e Configurações. Para desenvolver a interface com recarga automática, veja
[web/README.md](web/README.md).

## Rodar os testes

```bash
scripts/test.sh        # Windows: scripts\test.ps1
```

A suíte roda sem internet e sem `.env`: um teste quebra se outro tentar acessar a rede. Os testes
da interface rodam com `cd web && npm test`.

## Usar modelos de linguagem reais

Preencha no `.env` as chaves que tiver: `GEMINI_API_KEY` (gera o conteúdo), `GROQ_API_KEY`
(confere a fidelidade à Ata e é a reserva) e `JEV_API_KEY` (nota de qualidade). Depois:

```bash
uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor roteador
```

Sem a chave necessária, o comando para com um erro que diz qual variável falta. Todas as
variáveis e comandos estão em [docs/FUNCIONAMENTO.md](docs/FUNCIONAMENTO.md).

## A regra que não se quebra

O sistema nunca recomenda compra ou venda de investimento: no Brasil, isso é atividade regulada.
Quem detecta é código com regra fixa (léxico e padrão sintático), nunca um modelo de linguagem,
e o conteúdo que cruza essa linha é reprovado sem correção parcial
([ADR 0012](docs/DECISOES.md)).

## Os seis entregáveis do case

| Entregável | Onde está | Como conferir |
|---|---|---|
| 1. Pipeline de adaptação | `src/suno/gerador/` | `scripts/demo.sh`; `tests/test_gerador.py`, `tests/test_execucao.py` |
| 2. Suíte de avaliação híbrida | `src/suno/avaliador/`, `evals/` | `uv run --offline pytest -q tests/test_laudo.py tests/test_evals.py` |
| 3. Ciclo de correção | `src/suno/gerador/ciclo.py` | `tests/test_ciclo.py` |
| 4. Interface web | `src/suno/api/`, `web/` | `suno.cli servir` depois do build; `tests/test_api.py`, `npm test` |
| 5. Vídeo demonstrativo | `src/suno/video/` | `uv run --offline python -m suno.cli video --execucao demo-copom-280 --audiencia iniciante`; `tests/test_video.py` |
| 6. Relatório experimental | [docs/relatorio-experimental.md](docs/relatorio-experimental.md) | `uv run --offline python scripts/relatorio.py --execucao demo-copom-280` |

## Estrutura do repositório

```
src/suno/
  gerador/       extração de Âncoras, Matriz 3×3 e Ciclo de correção
  avaliador/     as cinco medidas sem LLM, a Qualidade (Jev), a Fidelidade e o Laudo
  pacote/        Carrossel (famílias visuais, render), legenda, fotos e conferência visual
  video/         vídeo 9:16 e plano de edição, fora do fluxo principal
  imagens/       biblioteca local e busca de fotos dos slides
  ingestao/      leitura de PDF, busca no BCB e extração de números
  origens/       catálogo e coleta de notícias (Copom, CVM, BCB, B3)
  provedores/    interface única de LLM e o roteador entre provedores
  api/           FastAPI: lê e grava as execuções em disco
  dominio.py     os modelos do domínio: Ata, Âncora, Célula, Laudo, Pacote
  cli.py         a linha de comando (python -m suno.cli)
web/             interface React + Vite + Tailwind
render/          Puppeteer: transforma os slides HTML em PNG
netlify-jev/     ponte na Netlify que leva o pedido de Qualidade ao Jev
evals/           casos da suíte pydantic-evals
tests/           suíte pytest
scripts/         setup, testes, demo, cliente da API, relatório
data/            Atas, Léxico, canary, Calibração, fotos e a execução de demonstração
templates/       carrosséis reais da Suno e a bancada que recriou as famílias visuais
docs/            arquitetura, funcionamento, decisões (ADRs) e relatório experimental
```

## Documentação

- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): como as peças se encaixam e onde um humano decide.
- [docs/FUNCIONAMENTO.md](docs/FUNCIONAMENTO.md): comandos, configuração, arquivos gerados e API.
- [docs/DECISOES.md](docs/DECISOES.md): todas as decisões de arquitetura (ADRs), resumidas.
- [docs/relatorio-experimental.md](docs/relatorio-experimental.md): métricas, Limiares, custo e latência medidos.
