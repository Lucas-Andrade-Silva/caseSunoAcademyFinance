# Relatório experimental — Suno Content (Entregável 6)

Todo número citado aqui vem de uma execução real, de um arquivo em disco, ou de um comando
colado com a saída completa. Onde uma medição não foi feita, este relatório diz que não foi
feita — nunca inventa o número. `scripts/relatorio.py --execucao <id>` gera
`docs/relatorio/<id>.json` a partir de `resumo_da_execucao` (`src/suno/avaliador/calibracao.py`),
e é dele que saem as tabelas de custo, rodadas e matriz de confusão abaixo.

## 1. Metodologia de avaliação

O Avaliador (`src/suno/avaliador/`) recebe `(Conteúdo, Âncora[], Audiência)` de uma Célula e
devolve um Laudo, sem LLM e sem rede — é o que o mantém testável em CI
([ADR 0001](adr/0001-gerador-e-avaliador-como-modulos-separados.md)). Cinco medidas:

### Flesch-BR

Fórmula do **Índice de Facilidade de Leitura de Flesch adaptado ao português**, de
**Martins, Ghiraldelo, Nunes & Oliveira Jr. (1996)**, NILC/ICMC-USP:

```
Flesch-BR = 248,835 − 1,015 × (palavras / frases) − 84,6 × (sílabas / palavras)
```

**O enunciado deste case pede "Flesch-Kincaid adaptado ao português", e isso está errado.**
Flesch-Kincaid é uma fórmula diferente — nível de escolaridade (*grade level*), não
facilidade de leitura: `0,39×(palavras/frases) + 11,8×(sílabas/palavras) − 15,59`. O nome
correto para o que o case pede é **Índice de Flesch, adaptado ao português por Martins et
al.** ([ADR 0002](adr/0002-flesch-br-implementado-no-projeto.md)).

`textstat`, a biblioteca sugerida pelo enunciado, calcula português errado e não avisa: ela
não tem `pt` na tabela de idiomas (`LANG_CONFIGS`, conferido no código-fonte do pacote), cai
silenciosamente nos coeficientes do inglês, e o silabador que usa (`pyphen`) é hifenizador,
não silabador — subconta sílabas em uma letra nas bordas (`água`→1, `ação`→1). O impacto
medido pela pesquisa em texto financeiro de 45 palavras / 4 frases foi de **20,7 pontos —
duas faixas inteiras de interpretação** (`docs/research/viabilidade-tecnica.md §2`).

**Esta medição não foi reproduzida nesta máquina**: nem `textstat` nem `pyphen` estão no
ambiente (`uv run --offline python -c "import pyphen"` e `"import textstat"` falham os dois
com `ModuleNotFoundError` — conferido em 19/09/2026). O número de 20,7 pontos é citado da
pesquisa, não remedido aqui; nenhuma das duas bibliotecas está em `pyproject.toml`, porque
o `CLAUDE.md` e o ADR 0002 proíbem `textstat` como base de métrica.

Implementamos o **Flesch-BR** do zero: um silabador reimplementado a partir do algoritmo de
Silva (2011) (`src/suno/avaliador/silabas.py`, sem copiar código do NILC — que é GPL-3.0 e
contaminaria o projeto) e a fórmula em `src/suno/avaliador/flesch_br.py`. O texto de
referência de `tests/test_flesch_br.py` (45 palavras, 4 frases, 108 sílabas contadas à mão,
palavra a palavra, e conferidas contra o separador) dá:

```
$ uv run --offline pytest -q tests/test_flesch_br.py::test_texto_de_referencia_da_34_4
```

resultado **34,4** — faixa "difícil" (Ensino Médio), a mesma ordem de grandeza citada na
pesquisa para um texto equivalente. As faixas por Audiência (seção 2) vêm da mesma fonte.

### Densidade

`src/suno/avaliador/densidade.py` mede a proporção de termos do Léxico presentes na Célula
e se cada termo apareceu com explicação quando a Audiência exigia. O Léxico
(`data/lexico/lexico.yaml`) tem **174 termos** (mínimo exigido: 150), dos quais **19** são
`núcleo` — os do enunciado (CDI, Selic, IPCA, dividendos, juros, inflação, Copom, Banco
Central, PIB, câmbio, dólar, Tesouro Direto, ação, bolsa, renda fixa, renda variável, fundo,
poupança, CDB) —, elaboração própria a partir do Dicionário CVM (CC BY-ND 3.0, nenhuma
definição copiada), do Glossário ANBIMA e de leitura da própria Ata
(`data/lexico/ORIGENS.md` documenta cada fonte). A exigência de explicação por Audiência
(`ExigenciaDeExplicacao`, `src/suno/dominio.py`) é `sempre` para o Iniciante, `fora_do_nucleo`
para o Intermediário, `nunca` para o Avançado.

### Aderência

`src/suno/avaliador/aderencia.py` confere cada número presente na Célula contra a tabela de
Âncoras numéricas por **igualdade exata de valor e unidade** — sem LLM, sem julgamento
([ADR 0011](adr/0011-ancoras-numericas-sao-citadas-nunca-reescritas.md)). O extrator de
números (`src/suno/ingestao/numeros.py`) tem uma fronteira documentada, e é onde alguém vai
supor cobertura que não existe: decimal solto sem unidade não entra (evitaria confundir
numeração de parágrafo com Âncora); moeda estrangeira (`US$`) não entra, só `R$`; número
relativo ("acima do projetado") não entra, como o ADR 0011 manda; `p.p.` e `%` nunca casam
entre si, nem `CDI+2%` com `110% do CDI` (a diferença semântica que a pesquisa §3 aponta
como armadilha crítica).

### Recomendação e o canary

Duas camadas determinísticas somam
([ADR 0012](adr/0012-recomendacao-detectada-por-padrao-sintatico-nao-por-lista-de-palavras.md)):
um **Léxico** organizado por `pode`/`não pode` e cinco **padrões sintáticos** sobre POS
tagging do `pt_core_news_sm` (spaCy) — sujeito dirigido + modal de obrigação, conveniência
impessoal, imperativo sobre patrimônio, voz editorial com ação, favorecimento de quem age.
Nada passa por LLM: um veredito que reprova sem chance de correção não pode mudar de opinião
entre duas execuções do mesmo texto.

O **canary set adversarial** (`data/canary/canary.yaml`) tem armadilhas de paráfrase sutil
("seria prudente considerar reduzir posição", sem nenhuma palavra de uma blocklist) e frases
neutras que citam o mesmo vocabulário sem recomendar. Medido nesta máquina em 19/09/2026:

```
$ uv run --offline python -c "
from suno.avaliador.recomendacao import casos_do_canary, detectar_recomendacao
casos = casos_do_canary()
armadilhas = [c for c in casos if c.deve_acusar]
neutras = [c for c in casos if not c.deve_acusar]
fuga = [c for c in armadilhas if not detectar_recomendacao(c.texto)]
falso_positivo = [c for c in neutras if detectar_recomendacao(c.texto)]
print(f'armadilhas={len(armadilhas)} neutras={len(neutras)}')
print(f'fuga={len(fuga)} ({100*len(fuga)/len(armadilhas):.1f}%)  falso_positivo={len(falso_positivo)} ({100*len(falso_positivo)/len(neutras):.1f}%)')
"
armadilhas=63 neutras=37
fuga=0 (0.0%)  falso_positivo=0 (0.0%)
```

Saída completa: `docs/relatorio/canary.json`. Das 63 armadilhas, **16 são pegas só pela
camada sintática** — o argumento medido de que uma blocklist sozinha (o caminho óbvio, que
o ADR 0012 recusou) deixaria passar um quarto do canary. **Aviso honesto**: o canary foi
escrito pela mesma pessoa que escreveu os padrões, no mesmo dia — mede regressão, não
generalização. O número que faltaria para uma medida de generalização é o da Calibração
(H2), com Células geradas de verdade e rotuladas à mão, e essa Calibração **ainda não tem
nenhum rótulo humano** (seção 2).

### Integridade da extração

`src/suno/avaliador/integridade.py` mede a fração de chaves essenciais de Âncora presente.
Ata sem `selic_decidida`, `placar_votacao` ou `data_reuniao` reprova com o motivo próprio
`falha_de_extracao`, que **não** aciona o Ciclo de correção — reescrever não conserta um
documento mal lido ([ADR 0013](adr/0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md)).
Vai direto para a fila de revisão humana (H4).

### O comitê de juízes-LLM — desligado na demo

O comitê (`src/suno/comite/`, [ADR 0008](adr/0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md))
julga tom, clareza e coerência com dois juízes-LLM em provedores diferentes, só em Texto
analítico e Carrossel. Está implementado e testado (`tests/test_comite.py`), mas **fica
desligado por padrão e na demo**: ligado, os três provedores gratuitos (Gemini gera, e dois
dos três — Groq e SambaNova — julgam) ficam todos ocupados na mesma execução, e não sobra
reserva para lidar com 429. Compliance e Aderência nunca passam por LLM, nem com o comitê
ligado — só dimensões subjetivas entram nele. Liga-se com `--comite` na linha de comando.

## 2. Limiares por Audiência

| Audiência | Flesch-BR | Exigência de explicação | Origem |
|---|---|---|---|
| Iniciante | ≥ 50 | sempre, na primeira ocorrência | NILC (Martins et al., 1996), faixa "fácil"/"muito fácil" |
| Intermediário | 25–50 | só termo fora do núcleo | NILC, faixa "difícil" |
| Avançado | < 25 | nunca | NILC, faixa "muito difícil" |

(`LIMIARES_PROVISORIOS`, `src/suno/dominio.py`.) Faixas completas do NILC, publicadas em
artigo revisado por pares (Língu@ Nostr@ v.10 n.2, 2022, UESB):

| Índice | Dificuldade | Escolaridade |
|---|---|---|
| 100–75 | muito fácil | 1º ao 5º ano |
| 75–50 | fácil | 6º ao 9º ano |
| 50–25 | difícil | Ensino Médio |
| 25–0 | muito difícil | Ensino Superior |

**Estado da Calibração (H2): 0 rótulos humanos hoje.** Os Limiares acima são as faixas
publicadas do NILC, não uma Calibração própria — todo Laudo e toda matriz deste relatório
carrega o carimbo `"NILC, aguardando Calibração"`
(`ORIGEM_AUTOMATICA`, `src/suno/avaliador/calibracao.py`). O formato da Calibração já está
pronto: `data/calibracao/FORMATO.md` descreve o protocolo (duas pessoas rotulam ~30 Células
à mão, às cegas uma da outra) e o CSV de colunas; `data/calibracao/rotulos.exemplo.csv` tem
só duas linhas de exemplo (`pessoa=exemplo`) e um teste
(`tests/test_calibracao.py::test_csv_de_exemplo_nao_e_calibracao`) recusa rótulo de verdade
nesse arquivo por engano. O Kappa de Cohen entre duas pessoas sai de
`kappa_do_arquivo(caminho, pessoa_a, pessoa_b)`, e o alvo é **0,6–0,8**
([ADR 0002](adr/0002-flesch-br-implementado-no-projeto.md)) — abaixo disso os Limiares não
estão sustentados por rótulo, acima de 0,8 em ~30 Células é sinal de rotulagem conjunta, não
de juízes bons. Como não há CSV preenchido, **nenhum Kappa é reportado neste relatório**:
`kappa_cohen` devolve `nan` (não `0.0`) quando não há base, por decisão do próprio código —
zero mentiria "discordam totalmente" onde o certo é "não há dado".

## 3. Matriz de confusão de Audiências (automática) e reprovações

Da execução versionada `data/execucoes/demo-copom-280/` — a mesma que o pytest lê e a API
expõe —, gerada com:

```
$ uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor falso --identificador demo-copom-280
$ uv run --offline python -m suno.cli pacote --execucao demo-copom-280
$ uv run --offline python scripts/relatorio.py --execucao demo-copom-280
```

Saída em `docs/relatorio/demo-copom-280.json`. **Matriz de confusão automática** — Audiência
pretendida × Audiência que o Flesch-BR medido colocaria pelas faixas do NILC
(`matriz_de_confusao_da_execucao`). É a matriz automática, **não** uma Calibração humana —
carimbada `"NILC, aguardando Calibração"` de propósito, para ninguém a citar como
concordância entre pessoas:

| pretendida \ percebida | iniciante | intermediário | avançado |
|---|---|---|---|
| **iniciante** | 3 | 0 | 0 |
| **intermediário** | 1 | 2 | 0 |
| **avançado** | 0 | 0 | 3 |

A célula fora da diagonal (`intermediário → percebida como iniciante`) é exatamente a
Célula que caiu na fila humana (ver abaixo): o Roteiro do Intermediário mediu Flesch-BR
muito acima da faixa 25–50 nas três rodadas, ou seja, "fácil demais" para o nível.

**Contagem de reprovação por motivo** (soma sobre todas as tentativas de todas as Células):

| Motivo | Ocorrências |
|---|---|
| flesch_br | 4 |
| densidade | 1 |
| aderência | 0 |
| recomendação | 0 |
| falha_de_extracao | 0 |

**Rodadas por Célula, destino final:**

| Audiência | Formato | Rodadas | Destino final |
|---|---|---|---|
| iniciante | texto_analitico | 2 | aprovado |
| iniciante | carrossel | 1 | aprovado |
| iniciante | roteiro | 1 | aprovado |
| intermediário | texto_analitico | 1 | aprovado |
| intermediário | carrossel | 1 | aprovado |
| intermediário | **roteiro** | **3** | **reprovado_revisao_humana** |
| avançado | texto_analitico | 1 | aprovado |
| avançado | carrossel | 1 | aprovado |
| avançado | roteiro | 1 | aprovado |

**A Célula que o Ciclo consertou** (Entregável 3, com os dois Flesch-BR): `iniciante ×
texto_analitico`. Rodada 0 reprovou por **dois** motivos simultâneos — `flesch_br` (12,98,
bem abaixo do Limiar ≥ 50: texto difícil demais para o Iniciante) e `densidade` (0,060,
termos de Léxico sem explicação). O Ciclo injetou os dois valores medidos na instrução de
correção (não uma instrução genérica: "Flesch-BR medido 13,0; o Limiar é ≥ 50"), e a rodada
1 saiu aprovada com **flesch_br = 92,55** e **densidade = 0,025** — dentro dos dois
Limiares, em uma única rodada de correção.

**A Célula que caiu na fila humana**: `intermediário × roteiro`. As três rodadas (original
mais as duas do teto) mediram Flesch-BR **90,77 → 91,09 → 89,58** — todas muito acima do
teto de 50 do Intermediário (fácil demais, não difícil demais), sem melhora entre rodadas.
Esgotado o teto de duas correções
([ADR 0013](adr/0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md)),
a Célula foi para a fila H4 com o motivo `flesch_br` e o histórico das três tentativas —
`execucao.pendencias[0]` no `execucao.json`. Nenhuma Célula da demo reprovou por Aderência,
Recomendação ou falha de extração: o preenchimento de número por Âncora (nunca reescrito
pelo LLM) fez a Aderência sair em 1,00 em todas as Células de primeira, e o canary não
acusou nada gerado.

## 4. Custo e latência

**Execução com `--provedor falso`** (LLM roteirizado, sem chamada de rede — é o que a demo
usa), de `data/execucoes/demo-copom-280/execucao.json`, campo `custo`:

| Métrica | Valor |
|---|---|
| Chamadas ao provedor | 13 |
| Tokens de entrada | 53.051 |
| Tokens de saída | 3.972 |
| Tempo de relógio | 4,80 s |
| Provedor | `falso` (13 chamadas) |

13 chamadas = 1 extração de Âncoras + 9 gerações originais + 3 correções do Ciclo (2 na
Célula `intermediário × roteiro`, 1 na Célula `iniciante × texto_analitico`). O pior caso
teórico do desenho é 1 + 9×3 = 28 chamadas por Ata
([ADR 0013](adr/0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md));
esta execução usou menos da metade disso porque a maioria das Células aprovou de primeira.

**Execução com `--provedor roteador` (LLM real): não medida nesta máquina.** Não há `.env`
neste ambiente (`ls .env` não encontra o arquivo — conferido em 19/09/2026), então nenhuma
chave de Gemini, Groq ou SambaNova está disponível para uma chamada real. O comando fica
pronto para quem tiver chave rodar e colar a saída aqui:

```sh
cp .env.example .env   # preencha GEMINI_API_KEY, GROQ_API_KEY, SAMBANOVA_API_KEY
uv run --offline python -m suno.cli executar --ata data/atas/copom-280-2026-08-05.pdf --provedor roteador --identificador demo-roteador
```

A saída de `cmd_executar` já imprime `custo: chamadas=N tokens=N segundos=N.N`, e o roteador
registra qual provedor respondeu cada chamada em `execucao.json` (`custo.por_provedor`) —
inclusive quantos 429 foram vistos e absorvidos por troca de provedor, porque o roteador
só troca depois de interpretar o tipo de 429
([ADR 0007](adr/0007-roteador-de-provedores-distingue-tipo-de-429.md)). Nenhum número desse
cenário é inventado aqui.

## 5. Suíte

```
$ uv run --offline pytest -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 62%]
........................................................................ [ 71%]
........................................................................ [ 80%]
........................................................................ [ 89%]
........................................................................ [ 98%]
.........                                                                [100%]
801 passed in 34.76s
```

Esta é a contagem final desta revisão do relatório, com os Agentes 11 (API, 21 testes) e 13
(vídeo, 6 testes) já entregues (`DONE` nos dois relatórios). `docs/relatorio/suite.json`
guarda também uma medição anterior da mesma sessão (774 passed, antes da Etapa 3 terminar) —
mantida ali como registro de como a contagem cresceu, não como o número que vale.

A suíte de `pydantic-evals` roda dentro do pytest, com casos em YAML
([ADR 0003](adr/0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md)):

```
$ uv run --offline pytest -q tests/test_evals.py tests/test_calibracao.py
................................................................         [100%]
64 passed in 8.56s
```

45 casos de avaliação em seis arquivos (`evals/casos/*.yaml`): `flesch_br` (8),
`densidade` (7), `aderencia` (7), `recomendacao` (7), `integridade` (7), `matriz` (9). O
quadro do `pydantic-evals`, com `-s` (trecho real, arquivo `integridade.yaml`):

```
$ uv run --offline pytest -s -q "tests/test_evals.py::test_suite_roda_contra_o_avaliador[integridade]"
                                                       Evaluation Summary: julgar
┌────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────┬──────────┐
│ Case ID                                    │ Assertions                                                                   │ Duration │
├────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼──────────┤
│ sem-data-da-reuniao-vai-a-revisao-humana   │ integridade_na_faixa: ✔                                                      │   25.6ms │
│                                            │   Reason: valor 0.6667; faixa [None, 1.0)                                    │          │
│                                            │                                                                              │          │
│                                            │ destino: ✔                                                                   │          │
│                                            │   Reason: esperado reprovado_revisao_humana, obtido reprovado_revisao_humana │          │
│                                            │                                                                              │          │
│                                            │ motivos: ✔                                                                   │          │
│                                            │   Reason: iguais                                                             │          │
│                                            │                                                                              │          │
├────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼──────────┤
│ chave-nao-essencial-nao-supre-a-essencial  │ integridade_na_faixa: ✔                                                      │   21.8ms │
│                                            │   Reason: valor 0.0000; faixa [0.0, 0.0001)                                  │          │
│                                            │                                                                              │          │
│                                            │ destino: ✔                                                                   │          │
│                                            │   Reason: esperado reprovado_revisao_humana, obtido reprovado_revisao_humana │          │
│                                            │                                                                              │          │
│                                            │ motivos: ✔                                                                   │          │
│                                            │   Reason: iguais                                                             │          │
│                                            │                                                                              │          │
├────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼──────────┤
│ ancora-textual-nao-supre-a-numerica        │ integridade_na_faixa: ✔                                                      │   24.6ms │
│                                            │   Reason: valor 0.0000; faixa [0.0, 0.0001)                                  │          │
│                                            │                                                                              │          │
│                                            │ destino: ✔                                                                   │          │
│                                            │   Reason: esperado reprovado_revisao_humana, obtido reprovado_revisao_humana │          │
│                                            │                                                                              │          │
│                                            │ motivos: ✔                                                                   │          │
│                                            │   Reason: iguais                                                             │          │
│                                            │                                                                              │          │
├────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼──────────┤
│ Averages                                   │ 100.0% ✔                                                                     │  314.6ms │
└────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────┴──────────┘
1 passed in 3.53s
```

```
$ uv run --offline python scripts/vocabulario.py
0 achado(s); 59 palavras a evitar
```

## 6. Decisões de engenharia

| ADR | Decisão | Cumprida em |
|---|---|---|
| [0001](adr/0001-gerador-e-avaliador-como-modulos-separados.md) | Gerador e Avaliador, módulos separados por `(Conteúdo, Âncora[], Audiência) → Laudo` | `src/suno/gerador/`, `src/suno/avaliador/` |
| [0002](adr/0002-flesch-br-implementado-no-projeto.md) | Flesch-BR reimplementado; `textstat` rejeitada | `src/suno/avaliador/silabas.py`, `flesch_br.py` |
| [0003](adr/0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md) | `pydantic-evals`, não DeepEval/Ragas | `evals/` |
| [0004](adr/0004-renderizacao-de-video-fora-do-grafo.md) | Vídeo fora do grafo, consome Roteiro aprovado | `src/suno/video/` |
| [0005](adr/0005-interface-em-react-vite-sobre-fastapi.md) | React + Vite + Tailwind sobre FastAPI | `src/suno/api/`, `web/` |
| [0006](adr/0006-atas-do-copom-como-documento-fonte-principal.md) | Atas do Copom, demo versionada sem rede | `data/atas/`, `src/suno/ingestao/` |
| [0007](adr/0007-roteador-de-provedores-distingue-tipo-de-429.md) | Roteador único, distingue 429 por minuto/dia | `src/suno/provedores/roteador.py` |
| [0008](adr/0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md) | Comitê de 2 juízes-LLM, opcional, desligado na demo | `src/suno/comite/` |
| [0009](adr/0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md) | Imagens geradas (matplotlib+Pillow), nunca raspadas | `src/suno/pacote/carrossel.py` |
| [0010](adr/0010-gerador-nao-e-agente-com-tools-nem-usa-mcp.md) | Gerador não é agente; sem tools, sem MCP | `src/suno/gerador/` (sequência fixa) |
| [0011](adr/0011-ancoras-numericas-sao-citadas-nunca-reescritas.md) | Âncoras numéricas citadas, nunca reescritas | `src/suno/ingestao/numeros.py`, `gerador/moldes.py` |
| [0012](adr/0012-recomendacao-detectada-por-padrao-sintatico-nao-por-lista-de-palavras.md) | Recomendação por Léxico + padrão sintático | `src/suno/avaliador/recomendacao.py` |
| [0013](adr/0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md) | Teto de 2 rodadas; falha de extração vai direto a H4 | `src/suno/gerador/ciclo.py` |
| [0014](adr/0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md) | Avaliação visual do Pacote, não reprova a Célula | `src/suno/pacote/visual.py` |

## 7. Reprodutibilidade

Passo a passo em máquina limpa — igual ao [README.md](../README.md), repetido aqui porque o
Entregável 6 pede reprodutibilidade no próprio relatório:

```sh
# 1. Instalar uv (uma vez por máquina)
curl -LsSf https://astral.sh/uv/install.sh | sh        # Unix
winget install astral-sh.uv                             # Windows

# 2. Preparar o ambiente
scripts/setup.sh          # ou scripts\setup.ps1 no Windows

# 3. Suíte inteira, offline
scripts/test.sh           # ou scripts\test.ps1

# 4. Demo ponta a ponta, sem rede
scripts/demo.sh           # ou scripts\demo.ps1

# 5. Relatório desta execução
uv run --offline python scripts/relatorio.py --execucao demo-copom-280
```

**O que uma pessoa precisa fazer antes da demo ao vivo**, que este repositório não
automatiza:

1. **Chaves de API**, se a demo quiser mostrar geração com LLM real em vez de
   `--provedor falso`: preencher `.env` com `GEMINI_API_KEY`/`GROQ_API_KEY`/`SAMBANOVA_API_KEY`
   antes, e testar a chamada uma vez fora do horário da apresentação — cota de tier
   gratuito é instável e pode já estar zerada (seção 4 e
   [ADR 0007](adr/0007-roteador-de-provedores-distingue-tipo-de-429.md)).
2. **`cd web && npm install && npm run build`** para a API servir a interface construída
   em `/`. Verificado nesta máquina em 19/09/2026: `npx tsc --noEmit` sem erro,
   `npm run build` grava `web/dist/index.html`, e `uv run --offline python -m suno.cli
   servir` + `curl http://127.0.0.1:8000/` devolve a SPA construída,
   `curl http://127.0.0.1:8000/api/execucoes/demo-copom-280` devolve o JSON da execução
   versionada. Os Agentes 11 (API + cliente TS) e 12 (interface) entregaram `DONE`; a
   interface mostra a Matriz 3×3, Âncoras ao lado da Célula, Reprovação como view própria
   e as filas H3/H4/H5, conforme os respectivos relatórios em
   `.superpowers/sdd/plano-de-execucao/reports/agente-11.md` e `agente-12.md`.
3. **Uma execução gravada** deve existir em `data/execucoes/` antes da apresentação — a
   versionada (`demo-copom-280`) já cobre isso e não depende de rede nem de geração ao
   vivo, que é o caminho recomendado para a demo.
4. **Vídeo pré-renderizado**: o vídeo do Roteiro é gerado fora do grafo
   ([ADR 0004](adr/0004-renderizacao-de-video-fora-do-grafo.md)) e deve ser renderizado
   antes da apresentação, não ao vivo — renderização de vídeo falha de formas demoradas.
   Verificado nesta máquina em 19/09/2026:

   ```
   $ uv run --offline python -m suno.cli video --execucao demo-copom-280 --audiencia iniciante
   video=data\execucoes\demo-copom-280\pacote\iniciante-roteiro\video.mp4
     duração 58.0s; a faixa aceita é 5–60s ok
     1080x1920; o vídeo precisa de 1080x1920 (9:16) ok
     sem trilha de áudio (sem narração) DEFEITO sem_audio
   ```

   O `SEM_AUDIO` é esperado e honesto: sem `--narracao` (não exposta na CLI hoje — ver
   relatório do Agente 13), o mp4 sai sem trilha de propósito, em vez de simular silêncio
   para enganar a medição. O binário de ffmpeg embutido é GPLv3 (ver "Licenças que
   importam" no README); chamado por `subprocess`, nunca linkado.

## 8. O que a pesquisa não cobria

Consolidado dos relatórios dos dez agentes das Etapas 0–2
(`.superpowers/sdd/plano-de-execucao/reports/agente-01.md` a `agente-10.md`), com a fonte
que cada um usou para descobrir o que a pesquisa de viabilidade não tinha.

- **A regra de ditongo crescente × hiato em `-ia` final não tem solução puramente
  ortográfica.** A pesquisa (§2) só listava o resultado esperado (`e-co-no-mi-a` mas
  `á-gio`); o Agente 1 derivou a regra de acentuação do Acordo Ortográfico da Língua
  Portuguesa (1990), Bases VIII–XI e XX (`portaldalinguaportuguesa.org`, Decreto nº
  6.583/2008), e validou contra ~40 palavras de controle.
- **`re.escape` do Python 3.14.5 escapa espaço** (`re.escape("ou seja")` →
  `'ou\\ seja'`), diferente do comportamento assumido por tutoriais mais antigos. O Agente
  2 descobriu isso rodando o interpretador direto, depois de um caso de teste falhar sem
  motivo aparente; não achou documentação oficial que marcasse a mudança de versão.
- **O `pt_core_news_sm` do spaCy praticamente não marca `Mood=Imp` em português** —
  treinado em corpus de jornal (UD Portuguese-Bosque), onde imperativo de segunda pessoa é
  raro. O Agente 3 mediu (`Compre/ADV`, `Venda/NOUN`) e mudou o desenho: imperativos ficaram
  na camada de Léxico, não na de morfologia (fontes:
  `universaldependencies.org/treebanks/pt_bosque/`, `spacy.io/models/pt`).
- **`text2num` não conhece "meio"/"meia"** e exige grafia acentuada
  (`github.com/allo-media/text2num`, README não promete fração por extenso) — o Agente 4
  tratou como caso especial e reacentua palavras comuns perdidas na extração de PDF.
- **A ordem de alternativa em regex é "primeiro que casa", não "mais longo"**
  (`docs.python.org/3/library/re.html`) — custou um `R$ 300 milhões` lido como 300 mil até
  o Agente 4 ordenar as alternativas da mais longa para a mais curta.
- **A forma real do JSON da API do BCB** (`DataReferencia` como datetime ISO com `Z`, campos
  extras não documentados como `ImagemCapa`) só apareceu numa requisição de pesquisa real
  contra `bcb.gov.br/api/servico/sitebcb/atascopom/ultimas`, feita pelo Agente 5 em
  18/09/2026 — a pesquisa de viabilidade só listava os nomes dos campos, não um payload.
- **O formato de 429 do Gemini, Groq e SambaNova não está publicado em nenhuma
  documentação oficial completa.** O Agente 6 cruzou páginas oficiais (`ai.google.dev`,
  `console.groq.com/docs`, `docs.sambanova.ai`) com relatos de comunidade para os campos que
  faltavam, e desenhou o parser para degradar com segurança (perde um provedor) quando não
  reconhece o padrão.
- **`round()` do Python é bancário** (`round(2.5) == 2`), o que muda o desempate de dois
  juízes com notas 2 e 3 no comitê — o Agente 7 documentou o efeito em vez de escondê-lo
  (fonte: `docs.python.org/3/library/functions.html#round`).
- **`ThreadPoolExecutor`, não `asyncio`, é o caminho certo para paralelizar as nove
  Células** — os provedores usam `httpx` síncrono (ADR 0007) e a documentação oficial do
  `concurrent.futures` recomenda `ThreadPoolExecutor` para I/O-bound tasks. Decisão do
  Agente 8.
- **Não há biblioteca permitida para medir contraste WCAG** — o Agente 9 implementou a
  fórmula de luminância relativa à mão a partir do texto normativo
  (`w3.org/TR/WCAG22/#dfn-contrast-ratio`), dez linhas, sem dependência nova.
- **A API do `pydantic-evals` 2.45.0 não está documentada em nível de assinatura** — o
  Agente 10 leu o código-fonte instalado (`.venv/Lib/site-packages/pydantic_evals/`) para
  descobrir que avaliadores customizados precisam ser `@dataclass` e que
  `Dataset._params` exige parametrização genérica explícita para não cair em `Any`.

Um achado transversal, fora dos dez relatórios: **`uv run` sem `--offline` revalida contra a
rede o wheel do `pt_core_news_sm` do spaCy antes de rodar qualquer comando**, o que falha ou
trava numa máquina sem internet mesmo que o pytest em si seja 100% offline. Por isso todo
comando deste relatório e do README usa `uv run --offline`.
