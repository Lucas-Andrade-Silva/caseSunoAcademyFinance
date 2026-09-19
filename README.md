# Suno Content

Adapta uma Ata do Copom em nove Células — três Audiências (Iniciante, Intermediário,
Avançado) vezes três Formatos (Texto analítico, Carrossel, Roteiro) — e reprova, sem LLM
e sem rede, a Célula que não atinge o Limiar da sua Audiência ou que cruza a linha de
Recomendação. Dois módulos: o **Gerador** produz, o **Avaliador** julga, e entre eles
passa só `(Conteúdo, Âncora[], Audiência) → Laudo`. O diagrama completo, com os seis
pontos onde um humano decide (H1–H6), está em [docs/ARQUITETURA.md](docs/ARQUITETURA.md).

Caso acadêmico de duas semanas, duas pessoas. Orçamento R$ 0: todo LLM do pipeline roda
em tier gratuito, atrás de um roteador único que troca de provedor no 429
([ADR 0007](docs/adr/0007-roteador-de-provedores-distingue-tipo-de-429.md)).

## Os seis entregáveis

| Entregável | Onde está | Comando | Teste que prova |
|---|---|---|---|
| 1 — Pipeline de adaptação | `src/suno/gerador/` | `uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor falso` | `tests/test_gerador.py`, `tests/test_execucao.py` |
| 2 — Suíte de avaliação híbrida | `src/suno/avaliador/`, `evals/` | `uv run --offline pytest -q tests/test_laudo.py tests/test_evals.py` | `tests/test_laudo.py`, `tests/test_evals.py` (pydantic-evals, [ADR 0003](docs/adr/0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md)) |
| 3 — Ciclo de correção | `src/suno/gerador/ciclo.py` | mesmo comando do Entregável 1 — a demo tem uma Célula corrigida e uma na fila humana | `tests/test_ciclo.py` |
| 4 — Interface web | `src/suno/api/`, `web/` | `uv run --offline python -m suno.cli servir` + `cd web && npm run build` | `tests/test_api.py` (21 testes) + `npx tsc --noEmit` sem erro |
| 5 — Vídeo demonstrativo | `src/suno/video/`, gravado fora do repositório a partir da aplicação rodando | `uv run --offline python -m suno.cli video --execucao demo-copom-280 --audiencia iniciante` | `tests/test_video.py` (6 testes) |
| 6 — Relatório experimental | [docs/relatorio-experimental.md](docs/relatorio-experimental.md) | `uv run --offline python scripts/relatorio.py --execucao demo-copom-280` | `docs/relatorio/*.json` |

## Rodar numa máquina limpa

Precisa só de Python 3.12+ e [`uv`](https://docs.astral.sh/uv/). Nenhum comando abaixo
toca a rede, exceto onde está escrito.

| Passo | Unix (`sh`) | Windows (PowerShell) | Saída esperada |
|---|---|---|---|
| 1. Instalar `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `winget install astral-sh.uv` | binário `uv` no PATH |
| 2. Preparar o ambiente | `scripts/setup.sh` | `scripts\setup.ps1` | `uv sync` termina; `.env` copiado de `.env.example` |
| 3. Rodar a suíte | `scripts/test.sh` | `scripts\test.ps1` | `N passed`, 0 falhas (número exato da última medição — 801 — em `docs/relatorio/suite.json`) |
| 4. Rodar a demo | `scripts/demo.sh` | `scripts\demo.ps1` | `celulas=9 aprovadas=8 pendencias=1`, seguido do Pacote das Células aprovadas |
| 5. Construir a interface | `cd web && npm install && npm run build` | idem | `tsc --noEmit` sem erro, depois `vite build` grava `web/dist/index.html` |
| 6. Servir a API + interface | `uv run --offline python -m suno.cli servir` | idem | `Uvicorn running on http://127.0.0.1:8000`; `/` serve a SPA construída, `/api/saude` devolve `{"ok": true, "execucoes": 1}` |

Os seis passos acima foram executados nesta máquina em 19/09/2026, na ordem acima, com a
saída batendo com a coluna "esperada" — inclusive um teste manual de ponta a ponta
(`curl http://127.0.0.1:8000/api/execucoes/demo-copom-280` com o servidor de pé, depois do
build) devolvendo o JSON da execução versionada.

Os scripts usam `uv run --offline`: sem `--offline`, o `uv` tenta revalidar contra a rede
o wheel do modelo `pt_core_news_sm` do spaCy antes de rodar, e isso falha ou trava numa
máquina sem internet (achado do Agente 1, registrado na seção 8 abaixo).

A demo não baixa nada: as Atas ficam versionadas em `data/atas/`, e a execução gravada
de referência está em `data/execucoes/demo-copom-280/` — o mesmo arquivo que o pytest lê,
que a API expõe e que este relatório cita
([ADR 0006](docs/adr/0006-atas-do-copom-como-documento-fonte-principal.md)).

## Rodar com LLM real

`--provedor falso` (usado acima) não faz nenhuma chamada de rede — é um LLM roteirizado,
com respostas fixas por rótulo. Para gerar com um provedor de verdade:

```sh
cp .env.example .env        # preencha GEMINI_API_KEY / GROQ_API_KEY / SAMBANOVA_API_KEY
uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor roteador
```

Nenhuma chave é obrigatória — sem elas, `--provedor roteador` falha com um erro que diz
qual variável falta. Orçamento é **R$ 0**: os três provedores usados (Gemini gera, Groq
julga, SambaNova é reserva) rodam em tier gratuito. Nenhuma chamada paga entra no
pipeline, inclusive a API da Anthropic. Cotas medidas na pesquisa (podem mudar sem
aviso — os provedores não fixam número na documentação oficial):

| Provedor | Papel | Cota (tier gratuito, medida em set/2026) |
|---|---|---|
| Gemini Flash | Gerador | instável; painel em `aistudio.google.com/rate-limit`, sem número fixo publicado |
| Groq (`gpt-oss-120b`) | Juiz do comitê | 30 RPM, 1.000 RPD, 200k TPD (por organização, não por chave) |
| SambaNova Cloud (`gpt-oss-120b`) | Reserva | 20 RPM, 20 RPD, 200k TPM, sem cartão |

Detalhe completo, incluindo a Cerebras descartada como reserva (exige cartão desde
17/08/2026) em [docs/research/viabilidade-tecnica.md §4](docs/research/viabilidade-tecnica.md#4-llm-a-custo-zero)
e [ADR 0007](docs/adr/0007-roteador-de-provedores-distingue-tipo-de-429.md).

O comitê de juízes-LLM ([ADR 0008](docs/adr/0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md))
nasce desligado — liga com `--comite` — porque, ligado, os três provedores ficam ocupados
numa mesma execução e não sobra reserva para 429.

## H1 e H2: os dois pontos que rodam antes da demo

**H1 — curadoria da Ata.** Buscar uma Ata nova é um comando separado, com rede, rodado
antes da apresentação — nunca durante:

```sh
uv run --offline python -m suno.cli buscar-ata --reuniao 280
```

Grava `data/atas/<identificador>.{pdf,txt,json}`. A API não documentada do BCB pode mudar
sem aviso ([ADR 0006](docs/adr/0006-atas-do-copom-como-documento-fonte-principal.md)); se
quebrar, a demo continua com as Atas já versionadas no repositório.

**H2 — Calibração e Léxico.** Os Limiares publicados hoje (Flesch-BR ≥ 50 Iniciante,
25–50 Intermediário, < 25 Avançado) vêm das faixas do NILC, marcadas
`"NILC, aguardando Calibração"` em todo relatório — ainda não há rótulo humano. Para
preencher a Calibração: as duas pessoas do time rotulam ~30 Células à mão, às cegas uma
da outra, no formato descrito em `data/calibracao/FORMATO.md`, e gravam em
`data/calibracao/rotulos.csv` (o arquivo versionado, `rotulos.exemplo.csv`, tem só linhas
de exemplo — um teste próprio recusa rótulo de verdade nele). O Kappa de Cohen entre as
duas pessoas sai de `src/suno/avaliador/calibracao.kappa_do_arquivo`; o alvo é 0,6–0,8
([ADR 0002](docs/adr/0002-flesch-br-implementado-no-projeto.md)).

## A linha que não se cruza

O conteúdo nunca produz **Recomendação** — sugestão de compra, venda ou promessa de
retorno é atividade regulada no Brasil; este sistema informa e educa. A detecção é
100% determinística, em duas camadas (Léxico + padrão sintático sobre POS tagging,
[ADR 0012](docs/adr/0012-recomendacao-detectada-por-padrao-sintatico-nao-por-lista-de-palavras.md)),
nunca um LLM, e reprova a Célula sem chance de correção parcial. O canary set adversarial
(`data/canary/canary.yaml`, 63 armadilhas e 37 frases neutras) mede 0% de fuga hoje — ver
seção 1 do [relatório experimental](docs/relatorio-experimental.md) para o número medido e
o aviso sobre o que ele não prova.

## Decisões e onde estão

O enunciado sugere um caminho para cinco pontos que a pesquisa mostrou errado ou
inviável; o `CLAUDE.md` resume os cinco, e cada um tem um ADR:

| Decisão | O enunciado sugere | Adotamos | ADR |
|---|---|---|---|
| Legibilidade | `textstat` / "Flesch-Kincaid adaptado" | Flesch-BR reimplementado (Martins et al., 1996); o enunciado erra o nome da fórmula | [0002](docs/adr/0002-flesch-br-implementado-no-projeto.md) |
| Avaliação | DeepEval ou Ragas | `pydantic-evals` | [0003](docs/adr/0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md) |
| Vídeo | avatar sintético (fora do escopo) | composição determinística em CPU, fora do grafo | [0004](docs/adr/0004-renderizacao-de-video-fora-do-grafo.md) |
| Interface | Streamlit, FastAPI+React ou Gradio | React + Vite + Tailwind sobre FastAPI, cliente TS gerado do OpenAPI | [0005](docs/adr/0005-interface-em-react-vite-sobre-fastapi.md) |
| Orquestração | LangGraph ou Pydantic AI, multiagente | sequência fixa de chamadas, sem agente, sem MCP | [0010](docs/adr/0010-gerador-nao-e-agente-com-tools-nem-usa-mcp.md) |

As catorze decisões estruturais completas estão em [docs/adr/](docs/adr/); o porquê de
cada uma nunca é repetido fora de lá. O que foi verificado contra fonte primária antes de
qualquer decisão — cotas, licenças, URLs testadas, ferramentas mortas — está em
[docs/research/viabilidade-tecnica.md](docs/research/viabilidade-tecnica.md).

## Licenças que importam

Resumo de [viabilidade-tecnica.md §9](docs/research/viabilidade-tecnica.md#9-licenças-que-exigem-decisão-supply-chain):
o silabador do Flesch-BR foi **reimplementado** a partir do artigo de Silva (2011), não
copiado do NILC (GPL-3.0 — contaminaria o projeto); o Dicionário CVM, usado como uma das
fontes de pesquisa do Léxico, é CC BY-ND 3.0 (*no derivatives*) e nenhuma definição dele
foi copiada (`data/lexico/ORIGENS.md`); e várias peças do ramo de vídeo (Piper, XTTS-v2,
Remotion para empresa) deixam de ser gratuitas se o projeto virar produto — não é o caso
deste case, mas fica registrado.

O wrapper Python `imageio-ffmpeg` (usado pelo ramo de vídeo) é BSD-2-Clause, mas o
**binário de ffmpeg que ele embute é GPLv3** (build "essentials" do gyan.dev, confirmado
rodando `ffmpeg -version` nesta máquina: `--enable-gpl --enable-version3 --enable-libx264`).
O projeto só chama esse binário por `subprocess`, nunca linka a biblioteca, o que não cria
obra derivada sob a GPL — mas é uma licença GPLv3 de verdade, não permissiva, e vale
revalidar esse raciocínio se o projeto crescer além do case (achado do Agente 13, não
estava em `viabilidade-tecnica.md`).

## O que ficou de fora

Ordem de corte sob atraso, do `CLAUDE.md`: (1) teste de retenção nas redes, (2) publicação
automática — um humano publica sempre, por decisão, não só por prazo — (3) avatar falante
no vídeo. O juiz de visão do Pacote ([ADR 0014](docs/adr/0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md))
está implementado e desligado por padrão, abaixo da linha dos seis entregáveis. O comitê de
juízes-LLM ([ADR 0008](docs/adr/0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md))
está implementado e desligado na demo, para não disputar cota com o roteador. Nenhum dos
seis entregáveis do enunciado caiu.

## Estrutura do repositório

```
src/suno/avaliador/   as cinco medidas determinísticas + Laudo — sem LLM, sem rede
src/suno/gerador/     extração de Âncoras, Matriz 3×3, Ciclo de correção
src/suno/comite/      juízes-LLM opcionais (ADR 0008)
src/suno/pacote/      Carrossel (matplotlib+Pillow), legenda, conferência visual (ADR 0009, 0014)
src/suno/video/       vídeo fora do grafo, composição determinística em CPU (ADR 0004)
src/suno/provedores/  interface única de LLM + roteador (ADR 0007)
src/suno/ingestao/    BCB, PDF, extração de números
src/suno/api/         FastAPI, lê execucao.json do disco (ADR 0005)
web/                  React + Vite + Tailwind, PWA instalável (ADR 0005)
evals/                casos pydantic-evals (ADR 0003)
data/                 Atas, Léxico, canary, Calibração, execuções gravadas
docs/adr/             as catorze decisões estruturais
docs/relatorio-experimental.md   Entregável 6
```
