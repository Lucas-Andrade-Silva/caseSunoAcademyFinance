# Front do Suno Content, Fase 2: gerar sob demanda

> **Para quem executar:** use superpowers:executing-plans (execução inline, com checkpoints). Os passos
> usam caixas de seleção (`- [ ]`).

**Objetivo:** a pessoa marca quais Células quer na Matriz 3×3, escolhe Demo ou Real e gera pela
interface; a geração roda em segundo plano, um job por vez, e a tela mostra cada Célula ao vivo.

**Arquitetura:** `Execucao` ganha `pedido` (posições escolhidas). As funções que hoje usam a
constante `MATRIZ` recebem as posições por parâmetro (padrão: as nove). O pipeline avisa por
callback quando cada Célula muda de etapa. Um `Gerenciador` (uma thread, uma fila) chama `executar`,
grava `andamento.json` ao lado de `execucao.json` e a tela consulta por polling. A decisão está no
[ADR 0017](../../adr/0017-api-dispara-a-geracao-em-segundo-plano.md).

**Stack:** FastAPI + Pydantic v2 (backend), React 19 + Vite + Tailwind 4 + openapi-fetch (front),
pytest e Vitest.

**Spec:** [2026-10-09-front-suno-design.md](../specs/2026-10-09-front-suno-design.md), seções 4.2,
6.1 (achado 2), 6.2, 6.3, 6.4 e 8. Mockup: `mockups-2026-10-09/04-curadoria.html`.

## Restrições globais

- A suíte roda **offline**: nada novo abre rede. Os testes usam o provedor falso e funções injetadas.
- O Avaliador continua sem LLM e sem rede. Mudar `avaliar_matriz` só troca a constante `MATRIZ` por
  parâmetro com `MATRIZ` como padrão: nenhum teste existente muda de resultado.
- Vocabulário: nada de palavra da lista _Avoid_ do CONTEXT.md em nome de código
  (`scripts/vocabulario.py`, linha de base de 16 achados que não são nossos).
- Nenhuma execução antiga quebra: `pedido` ausente em `execucao.json` significa as nove.
- Sem commit: o usuário decide quando commitar.

## Decisões desta fase

1. **Posição.** `PosicaoDaMatriz(audiencia, formato)` é o modelo em JSON, na API e no `pedido`. O
   pipeline continua com tuplas `(Audiencia, Formato)` como `MATRIZ`; `Execucao.posicoes_pedidas()`
   converte.
2. **Ciclo transversal só com 2 ou mais Células.** Com uma, `executar` não roda a avaliação da Matriz
   nem o Judge, e `avaliacao_transversal` e `ciclo_transversal` ficam ausentes.
3. **Judge que cita Célula não pedida** é ignorado (a Célula não existe na Matriz pedida). Sem
   problema restante, a rodada termina sem regenerar nada.
4. **Fase do job** (`extraindo_ancoras`, `gerando_celulas`, `avaliando_matriz`, `gravando`) e **etapa da
   Célula** (`aguardando`, `gerando`, `corrigindo`, `aprovada`, `revisao_humana`) vão para o
   `andamento.json`. A barra de progresso conta Células terminadas.
5. **Demo** = provedor `falso`, só para Atas com `data/respostas_prontas/<id>.json`. **Real** =
   `roteador`, que precisa de ao menos uma chave no ambiente; a rota recusa antes de enfileirar.
6. **Resposta pronta do Judge** (`juiz_transversal:0` aprovando) entra no arquivo da demo. Com as nove
   Células ela nunca é consumida (a avaliação determinística reprova antes); com um subconjunto sem
   Intermediário × Roteiro ela deixa a Matriz parcial chegar a "aprovada".
7. **Passo 1 da Curadoria** nesta fase é só "escolher a Ata" entre as de `data/atas/`. A Fase 3 o
   troca pelo catálogo de Fontes e pelas sugestões.

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `src/suno/dominio.py` (acréscimo) | `PosicaoDaMatriz`, `EtapaDaCelula`, `FaseDaExecucao`, `EstadoDoAndamento`, `AndamentoDaCelula`, `Andamento`, `Execucao.pedido` |
| `src/suno/avaliador/transversal.py` | `avaliar_matriz(..., posicoes=MATRIZ)` |
| `src/suno/gerador/ciclo.py` | `rodar_ciclo(..., ao_andar=None)` |
| `src/suno/gerador/personas.py` | `gerar`/`gerar_formatos` passam `ao_andar` |
| `src/suno/gerador/matriz.py` | `gerar_matriz_do_dossie(..., posicoes=MATRIZ, ao_andar=None)` |
| `src/suno/gerador/orquestracao.py` | `rodar_ciclo_transversal(..., posicoes=MATRIZ, ao_andar=None)` |
| `src/suno/gerador/execucao.py` | `executar(..., pedido=None, nome=None, ao_mudar_fase=None, ao_andar=None)` |
| `src/suno/api/geracao.py` (novo) | `Gerenciador`: fila, thread, `andamento.json`, recuperação no boot |
| `src/suno/api/resumo.py` | `StatusSaida` ampliado, `PosicaoResumo.etapa`, resumo de Saída ainda sem `execucao.json` |
| `src/suno/api/app.py` | `POST /api/execucoes`, `GET /api/execucoes/{id}/andamento`, listagem com jobs |
| `web/src/lib/pedido.ts` (novo) | Seleção por Célula, linha e coluna |
| `web/src/lib/matriz.ts` | Estados `gerando`, `corrigindo`, `na_fila`, `interrompida`, `falhou` |
| `web/src/componentes/SeletorDeMatriz.tsx` (novo) | Matriz clicável |
| `web/src/componentes/MatrizAoVivo.tsx` (novo) | Andamento com polling e barra |
| `web/src/paginas/Curadoria.tsx` | Os três passos |
| `web/src/paginas/SaidaAberta.tsx`, `Saidas.tsx` | Saída em geração, interrompida ou que falhou |

---

### Tarefa 1: Domínio do pedido e do andamento

**Arquivos:** modificar `src/suno/dominio.py`; testes em `tests/test_pedido.py` (novo).

**Produz:**

```python
class PosicaoDaMatriz(BaseModel):          # frozen
    audiencia: Audiencia
    formato: Formato
    def como_tupla(self) -> tuple[Audiencia, Formato]: ...

class EtapaDaCelula(StrEnum):   # aguardando, gerando, corrigindo, aprovada, revisao_humana
class FaseDaExecucao(StrEnum):  # extraindo_ancoras, gerando_celulas, avaliando_matriz, gravando
class EstadoDoAndamento(StrEnum):  # na_fila, gerando, concluida, interrompida, falhou

class AndamentoDaCelula(BaseModel):  # audiencia, formato, etapa=aguardando, rodada=0
class Andamento(BaseModel):
    identificador, nome, ata, provedor: str
    comite: bool = False
    estado: EstadoDoAndamento
    fase: FaseDaExecucao | None
    celulas: list[AndamentoDaCelula]
    erro: str | None
    criado_em, atualizado_em: datetime
    concluido_em: datetime | None

# Execucao
pedido: list[PosicaoDaMatriz]   # vazio = as nove (execução antiga)
def posicoes_pedidas(self) -> tuple[tuple[Audiencia, Formato], ...]: ...
```

Validador de `Execucao.pedido`: sem repetição; ordena na ordem de `MATRIZ`.

- [ ] **1.1** Escrever `tests/test_pedido.py`: `pedido` vazio devolve as nove em `posicoes_pedidas()`; `pedido` fora de
  ordem sai na ordem de `MATRIZ`; repetição levanta `ValidationError`; `execucao.json` antigo (sem o campo) carrega;
  `Andamento` faz ida e volta em JSON.
- [ ] **1.2** Rodar e ver falhar (`ImportError`).
- [ ] **1.3** Implementar em `dominio.py`.
- [ ] **1.4** Rodar `uv run pytest tests/test_pedido.py tests/test_dominio.py -q`: verde.

### Tarefa 2: O pipeline recebe as posições

**Arquivos:** modificar `avaliador/transversal.py`, `gerador/ciclo.py`, `gerador/personas.py`,
`gerador/matriz.py`, `gerador/orquestracao.py`; testes em `tests/test_pedido_parcial.py` (novo).

**Produz:**

```python
# ciclo.py
Andou = Callable[[Audiencia, Formato, EtapaDaCelula, int], None]
def rodar_ciclo(..., ao_andar: Andou | None = None) -> HistoricoCelula
# etapas emitidas: gerando (rodada 0) → corrigindo (rodada ≥ 1) → aprovada | revisao_humana.
# Um erro dentro do callback é registrado no log e não derruba o Ciclo.

# transversal.py
def avaliar_matriz(celulas, ancoras, *, posicoes=MATRIZ) -> AvaliacaoTransversal   # total_esperado = len(posicoes)

# matriz.py
def gerar_matriz_do_dossie(dossie, provedor, *, comite=None, posicoes=MATRIZ, ao_andar=None)
# agrupa por Audiência, um trabalhador por Audiência, devolve na ordem de MATRIZ

# orquestracao.py
def rodar_ciclo_transversal(dossie, celulas, provedor, *, comite=None, posicoes=MATRIZ, ao_andar=None)
```

- [ ] **2.1** Testes: `avaliar_matriz` com 1, 5 e 9 posições (completude relativa ao pedido; posição fora do
  pedido é "inesperada" e reprova); `gerar_matriz_do_dossie` com 1, 5 e 9 posições devolve só as pedidas, na
  ordem de `MATRIZ`; `ao_andar` recebe `gerando` antes de `aprovada` e `corrigindo` na rodada 1; callback que
  levanta não derruba o Ciclo; Judge que cita posição não pedida é ignorado e não gera chamada extra.
- [ ] **2.2** Rodar e ver falhar.
- [ ] **2.3** Implementar. `avaliar_matriz` trata posição recebida fora de `posicoes` como `inesperadas`
  (nova lista em `AvaliacaoTransversal`, padrão vazio) e reprova.
- [ ] **2.4** Rodar `uv run pytest tests/test_orquestracao.py tests/test_gerador.py tests/test_pedido_parcial.py -q`:
  verde, sem mudar nenhum teste antigo.

### Tarefa 3: `executar` com pedido

**Arquivos:** modificar `gerador/execucao.py`, `data/respostas_prontas/copom-280-2026-08-05.json`;
testes em `tests/test_execucao_parcial.py` (novo) e ajuste em `tests/test_execucao.py`.

**Produz:**

```python
def executar(caminho_ata, provedor, pasta_execucoes, *, comite=False, identificador=None,
             pedido: Sequence[tuple[Audiencia, Formato]] | None = None,
             nome: str | None = None,
             ao_mudar_fase: Callable[[FaseDaExecucao], None] | None = None,
             ao_andar: Andou | None = None) -> Execucao
```

- [ ] **3.1** Testes com o provedor falso e a Ata do repositório: pedido de uma Célula (`iniciante×carrossel`)
  grava 1 Célula, `pedido` com 1 posição, `avaliacao_transversal is None` e `ciclo_transversal is None`;
  pedido de duas aprovadas (`iniciante×carrossel`, `iniciante×roteiro`) roda o Judge, que aprova
  (`ciclo_transversal.estado == aprovada`); pedido com `intermediario×roteiro` (a teimosa) deixa a H4 só
  para ela; `ao_mudar_fase` recebe as quatro fases na ordem; sem `pedido`, o comportamento é o de hoje
  (nove, `pedido` gravado com as nove).
- [ ] **3.2** Rodar e ver falhar.
- [ ] **3.3** Implementar. `_pendencias_transversais(ciclo, posicoes)` usa as posições pedidas. Acrescentar
  `"juiz_transversal:0": [{"estado": "aprovado", "problemas": []}]` ao arquivo da demo e ajustar o teste
  `test_o_arquivo_de_respostas_prontas_tem_todos_os_rotulos_do_cenario` para aceitar esse rótulo.
- [ ] **3.4** Rodar `uv run pytest tests/test_execucao.py tests/test_execucao_parcial.py -q`: verde.

### Tarefa 4: O `Gerenciador` e o `andamento.json`

**Arquivos:** criar `src/suno/api/geracao.py`; testes em `tests/test_geracao.py` (novo).

**Produz:**

```python
class Gerenciador:
    def __init__(self, pasta_execucoes: Path, *, pasta_atas: Path,
                 executar_fn: Callable[..., Execucao] = executar) -> None
    def pedir(self, *, ata: str, modo: ModoDeGeracao, pedido: list[PosicaoDaMatriz],
              nome: str | None, comite: bool) -> Andamento     # grava na_fila e enfileira
    def andamento(self, identificador: str) -> Andamento | None  # lê do disco
    def recuperar_interrompidos(self) -> list[str]               # no boot: na_fila/gerando → interrompida
    def aguardar_ocioso(self, timeout: float = 30) -> bool       # só para os testes
```

`ModoDeGeracao` (`demo`, `real`) mora em `geracao.py`. `andamento.json` é gravado com arquivo temporário
e `os.replace`, para o polling nunca ler metade. Escrita de Célula concorrente protegida por trava.

- [ ] **4.1** Testes com `executar_fn` falso e controlável: o job vai de `na_fila` a `gerando` a `concluida`;
  o segundo pedido fica `na_fila` enquanto o primeiro roda (um por vez); callback de Célula atualiza a etapa
  no arquivo; `executar_fn` que levanta vira `falhou` com mensagem sem credencial; `recuperar_interrompidos`
  marca `gerando` e `na_fila` como `interrompida` e não toca `concluida`; identificador não colide em
  dois pedidos no mesmo segundo.
- [ ] **4.2** Rodar e ver falhar.
- [ ] **4.3** Implementar (uma `threading.Thread` daemon iniciada no primeiro `pedir`, `queue.Queue`).
- [ ] **4.4** Rodar `uv run pytest tests/test_geracao.py -q`: verde.

### Tarefa 5: As rotas

**Arquivos:** modificar `api/app.py`, `api/resumo.py`; testes em `tests/test_api_geracao.py` (novo).

**Produz:**

```text
POST /api/execucoes            corpo NovaSaida{nome?, ata, modo, pedido[1..9], comite=false} → 202 Andamento
GET  /api/execucoes/{id}/andamento                                                          → Andamento (404 sem job)
GET  /api/execucoes                  inclui Saídas que só têm andamento.json
GET  /api/execucoes/{id}/resumo      funciona também sem execucao.json (posições a partir do andamento)
StatusSaida = na_fila | gerando | aguardando_revisao | concluida | interrompida | falhou
PosicaoResumo.etapa: EtapaDaCelula | None;  PosicaoResumo.destino: Destino | None
```

Recusas: Ata inexistente (404), pedido vazio ou repetido (422), `demo` sem
`data/respostas_prontas/<ata>.json` (422, com o motivo), `real` sem chave no ambiente (422).
`criar_app(pasta_execucoes, *, pasta_atas=PASTA_ATAS, executar_fn=None)` constrói o `Gerenciador` e chama
`recuperar_interrompidos()` no boot.

- [ ] **5.1** Testes com `TestClient`: 202 e andamento; demo de 2 Células ponta a ponta (provedor falso, a
  Ata do repositório) termina `concluida` e a Saída aparece como `aguardando_revisao` com 2 posições; segundo
  `POST` fica `na_fila`; as quatro recusas; reinício (novo `criar_app` sobre a mesma pasta) marca a
  `gerando` como `interrompida`; a lista mostra Saída em geração com `status: "gerando"`.
- [ ] **5.2** Rodar e ver falhar.
- [ ] **5.3** Implementar.
- [ ] **5.4** Regenerar o contrato (`web/openapi.json`, `web/src/api/schema.d.ts`) e rodar
  `uv run pytest -q` inteiro: verde, incluindo `test_contrato_openapi.py`.

### Tarefa 6: Lógica pura do front

**Arquivos:** criar `web/src/lib/pedido.ts` e `pedido.test.ts`; modificar `web/src/lib/matriz.ts` e `matriz.test.ts`.

**Produz:**

```ts
export type Posicao = { audiencia: string; formato: string };
alternarCelula(selecao: readonly Posicao[], p: Posicao): Posicao[]
alternarLinha(selecao, audiencia): Posicao[]     // linha cheia → limpa; senão completa
alternarColuna(selecao, formato): Posicao[]
selecionarTudo(): Posicao[]
estaSelecionada(selecao, p): boolean
resumirPedido(selecao): string                   // "5 Células" / "1 Célula" / "nenhuma"
// matriz.ts
EstadoPosicao ganha: "gerando" | "corrigindo" | "na_fila"
PosicaoParaTela ganha: etapa?: string | null; destino: string | null
progressoDoAndamento(celulas): { terminadas: number; total: number; percentual: number }
```

- [ ] **6.1** Testes (Vitest) para cada função acima, incluindo ordem estável (sempre a da Matriz) e `percentual`
  arredondado.
- [ ] **6.2** Implementar; `npm test` verde.

### Tarefa 7: Componentes e Curadoria

**Arquivos:** criar `SeletorDeMatriz.tsx`, `MatrizAoVivo.tsx`; modificar `MiniMatriz.tsx`, `CelulaDaMatriz.tsx`,
`CartaoSaida.tsx`, `Saidas.tsx`, `SaidaAberta.tsx`, `Curadoria.tsx`, `dados/cliente.ts`, `texto/rotulos.ts`.

- [ ] **7.1** `cliente.ts`: `criarSaida(corpo)` e `obterAndamento(id)`; tipos `Andamento`, `NovaSaida`,
  `EtapaDaCelula`, `EstadoDoAndamento`.
- [ ] **7.2** `SeletorDeMatriz`: Matriz 3×3 clicável; cabeçalho de linha e de coluna alterna a linha e a coluna.
- [ ] **7.3** `MatrizAoVivo`: polling a cada 1,5 s, barra de progresso, cada Célula com o estado da etapa, para
  de consultar em estado final; avisa quando termina (callback).
- [ ] **7.4** `Curadoria`: passo 1 (escolher a Ata), passo 2 (nome, Demo/Real com Demo desabilitado e motivo à
  vista, Matriz clicável, **Gerar**), passo 3 (`MatrizAoVivo` e o botão **Abrir Saída**). Erro do servidor
  aparece como frase.
- [ ] **7.5** `Saidas` e `SaidaAberta` tratam Saída em geração (contorno pulsando), na fila, interrompida e
  que falhou. Saída em geração abre `MatrizAoVivo`.
- [ ] **7.6** `npm run build` e `npm test` verdes.

### Tarefa 8: Registros e verificação

- [ ] **8.1** ADR 0017: acrescentar "Implementado" com o formato do `andamento.json`. `CONTEXT.md`: termo
  **Pedido**. `CLAUDE.md`: tirar a frase "a API não executa o pipeline" se existir. Docstring de `app.py`.
- [ ] **8.2** `uv run pytest -q`, `npm test`, `npm run build`, `uv run python scripts/vocabulario.py` (16 achados
  da equipe, nenhum novo).
- [ ] **8.3** Subir o servidor sobre uma pasta temporária, gerar uma Saída Demo de poucas Células pela tela, ver a
  Matriz ao vivo, abrir a Saída e aprovar uma Célula. Registrar no fim deste arquivo.

---

## Registro da execução

Executado em 2026-10-10, inline, em `main`, sem commits. Ao fim da fase: 952 testes pytest e 53 Vitest
passando, build verde, `scripts/vocabulario.py` nos mesmos 16 achados da equipe.

Divergências do plano:

- `AvaliacaoTransversal` ganhou `posicoes_inesperadas` (Célula que chega sem ter sido pedida reprova a
  Matriz): o plano só falava de completude relativa.
- `criar_app` ganhou `recuperar_ao_iniciar` (o gerador do schema OpenAPI não pode mexer em disco).
- Fora do plano e necessários para a Curadoria: `AtaResumo.demo_disponivel` e `Saude.real_disponivel`, para
  desabilitar Demo e Real com o motivo à vista.
- `usarRequisicao` ganhou `atualizarACada` (atualização silenciosa, sem piscar "Carregando…"), usada pela lista de
  Saídas e pelo contador do menu enquanto algo está sendo gerado.
- A resposta pronta `juiz_transversal:0` entrou no arquivo da demo, como previsto, e o teste que confere os
  rótulos do cenário aceita esse rótulo.
- Os testes de `lib/pedido.ts` foram escritos junto com a implementação, não antes.

Conferido no navegador (Edge, servidor sobre cópia): escolher Células na Matriz, gerar em Demo, ver a Matriz
ao vivo, sair da tela e voltar, Saída em geração e Saída interrompida na lista e abertas.

