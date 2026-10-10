# Front do Suno Content: desenho

Data: 2026-10-09 · Estado: aguardando revisão do usuário · Mockups: [mockups-2026-10-09/](mockups-2026-10-09/)

## 1. Objetivo

Painel web interno para a equipe da Suno revisar o conteúdo que o pipeline gera. A pessoa
escolhe as fontes, recebe uma sugestão de pauta, gera só as Células que quer, lê o Laudo,
aprova ou reprova, importa documentos e exporta. Não é produto para o cliente final.

Visual: preto e vermelho da Suno, menu lateral e cartões escuros, como o site e o app deles.

## 2. Fora do escopo

| Item | Situação |
|---|---|
| API aberta `/v1` para puxar conteúdo aprovado | **Adiada** pelo usuário. Sem chaves, sem guia API. O desenho não a impede: a decisão humana por Célula e um id estável são o que ela serviria depois. |
| Releases de Resultados da B3 | Fora do MVP. O bloco aparece na tela como "em breve". A pesquisa ([viabilidade-tecnica.md](../../research/viabilidade-tecnica.md)) descartou raspar a B3. |
| Colar URL qualquer | Fora. Fontes extras são um catálogo fixo liga/desliga mais upload de PDF ou texto. |
| Login e perfis | Fora. A decisão registra um nome de revisor guardado no navegador. |
| Atualização automática de fontes | Fora. Só o botão **Atualizar fontes**, com a data da última. |
| Publicação nas redes | Fora, como no [CLAUDE.md](../../../CLAUDE.md): o sistema entrega o Pacote e um humano publica. |

## 3. Decisões

| Tema | Decisão |
|---|---|
| Arquitetura | Evoluir o que existe: React + Vite + Tailwind sobre FastAPI, estado em arquivos no disco ([ADR 0005](../../adr/0005-interface-em-react-vite-sobre-fastapi.md), [ADR 0006](../../adr/0006-atas-do-copom-como-documento-fonte-principal.md)). Sem banco de dados. |
| Guias | **Fontes**, **Curadoria**, **Saídas**. |
| Geração | Sob demanda: o usuário marca quaisquer Células da Matriz 3×3, de 1 a 9, inclusive combinações soltas. |
| Curadoria | Duas sugestões, **Destaque único** (`ModoSelecao.SEPARADA`) e **Visão unida** (`UNIDA`), ou "montar a minha" pelas bolinhas das Fontes. |
| Linguagem | "Sugestão da curadoria", nunca "Recomendação" (palavra proibida, [CONTEXT.md](../../../CONTEXT.md)). |
| Tema | Só escuro. Substitui o claro/escuro por sistema que o front tem hoje. |

## 4. Telas

Cada tela tem seu mockup. A opção marcada foi a escolhida; as outras foram descartadas.

### 4.1 Fontes ([01-fontes.html](mockups-2026-10-09/01-fontes.html)), opção B

Menu lateral e uma fileira horizontal de cartões por fonte ("trilhos"). Cada cartão é um item:
data, título, resumo de duas linhas, número de Âncoras e uma bolinha de seleção. A fileira tem
título, chip de status (ligada) e **Ver tudo**. Topo: **Importar documento** e **Atualizar fontes**.
Releases de Resultados é uma linha tracejada "em breve". Itens selecionados formam a seleção
manual da Curadoria. Descartadas: A (um bloco por fonte, só o último item) e C (abas no topo).

### 4.2 Curadoria ([04-curadoria.html](mockups-2026-10-09/04-curadoria.html))

Três passos: **Escolher**, **Configurar**, **Gerando**.

1. **Escolher.** Dois cartões, Destaque único e Visão unida, cada um com o motivo da
   sugestão. Abaixo, "Montar a minha" com a contagem de itens selecionados. Fixo no rodapé:
   a curadoria sugere pauta, nunca ativo para comprar ou vender. Itens de fonte não Copom
   mostram o chip **não calibrado**.
2. **Configurar.** Nome da Saída (vem preenchido, editável), **Demo** ou **Real**, e a Matriz
   3×3 clicável (célula, linha ou coluna). Uma lista de Audiências e outra de Formatos só
   montaria retângulos; a Matriz permite combinações soltas. Demo fica desabilitado, com o
   motivo, quando o item não tem `data/respostas_prontas/<id>.json`. Hoje só a Ata do Copom 280 tem.
3. **Gerando.** A Matriz mostra cada Célula ao vivo (gerando, corrigindo, aprovada, revisão
   humana) e uma barra de progresso. Dá para sair da tela, a geração continua.

### 4.3 Saídas ([05-saidas-lista.html](mockups-2026-10-09/05-saidas-lista.html))

Grade de cartões nomeados. Cada um traz fonte, modo, Demo ou Real, data e uma **mini-Matriz**
3×3 em que a posição do quadradinho é a posição da Célula. Cores: verde (você aprovou), cinza
(espera sua decisão), âmbar (revisão humana), vermelho (reprovada ou parou), contorno
vermelho pulsando (gerando), tracejado (não pedida). Filtros: busca por nome, status, fonte,
ordem. O número vermelho no menu conta as Saídas aguardando revisão. Uma Saída interrompida
(cota esgotada, servidor reiniciado) fica registrada com esse status. O menu **···** tem
renomear e exportar.

### 4.4 Saída aberta ([02-saida-aberta.html](mockups-2026-10-09/02-saida-aberta.html)), opção A

Cabeçalho com nome editável, fonte, modo, provedor e data, e o botão **Exportar**. Abaixo, a
Matriz 3×3 (Audiências nas linhas, Formatos nas colunas). Cada cartão mostra só o estado: chip
do Laudo e chip da decisão humana. Células não pedidas ficam tracejadas ("não pedida"). Clicar
numa Célula abre a Célula aberta. Descartadas: trilhos com prévia (B) e tabela de revisão (C).

### 4.5 Célula aberta ([03-celula-aberta.html](mockups-2026-10-09/03-celula-aberta.html)), opção B

Página inteira em duas colunas. Esquerda: o conteúdo (slides do carrossel, texto ou blocos do
roteiro; cada elemento mostra a chave da Âncora que cita) e o painel do **Pacote de
publicação**. Direita, sempre visível e sem abas: o **Laudo** (cinco métricas com valor, faixa e
barra) e as **Âncoras citadas** (valor, unidade e trecho literal). Rodapé fixo: chip de
Compliance, **Reprovar…** (pede motivo) e **Aprovar**. Navegação para a Célula vizinha no
topo. Descartada: gaveta lateral sobre a Matriz.

### 4.6 O que acontece com o front atual

| Hoje | Depois |
|---|---|
| `paginas/Execucoes.tsx` | Lista de Saídas (4.3) |
| `paginas/Matriz.tsx` | Saída aberta (4.4) |
| `paginas/CelulaVista.tsx` | Célula aberta (4.5) |
| `paginas/Filas.tsx` | Some como página. H3, H4 e H5 viram **estados da Célula** (chip "Revisão: Tom", "Revisão humana", Pacote aguardando aprovação) resolvidos pela decisão humana. |
| `paginas/Pacotes.tsx` | Painel do Pacote dentro da Célula aberta |
| `componentes/Layout.tsx` | Menu lateral e tema escuro (seção 5) |

## 5. Tokens visuais

Tailwind v4, declarados em `@theme` em `web/src/estilos/global.css`. **Os valores vieram dos
mockups e o vermelho foi estimado de uma captura de tela da Suno.** O hex oficial substitui
esses valores antes de ir para o ar.

| Token | Valor |
|---|---|
| fundo | `#0e0e0f` |
| menu lateral | `#141415` |
| cartão / cartão 2 | `#1c1c1e` / `#242427` |
| linha | `#2c2c30` |
| texto / texto suave | `#f3f3f4` / `#8d8d93` |
| vermelho Suno | `#ef4b3f` (tinta de fundo `rgba(239,75,63,.14)`) |
| ok / alerta | `#3ecf8e` / `#f5b042` |

Cartões com raio de 13 a 14 px. Botão primário em pílula vermelha, caixa alta, negrito.
Botão secundário com contorno. Chips pequenos com ponto de status. Fonte do sistema (a da Suno
não foi identificada). O logotipo é "( SUNO )" com os parênteses em vermelho.

## 6. Backend

### 6.1 Três achados que mudam o escopo

1. **Âncoras e Limiares são só do Copom.** `CHAVES_ESSENCIAIS` exige `selic_decidida`,
   `data_reuniao` e `placar_votacao` ([dominio.py](../../../src/suno/dominio.py)). Um Fato
   Relevante ou um PDF importado reprovaria todas as Células por `FALHA_DE_EXTRACAO`.
   **Proposta:** cada fonte declara um tipo. O Copom mantém as chaves atuais. Os outros tipos
   usam um conjunto genérico (uma data e ao menos um número com unidade). A Saída de outro tipo
   leva o selo **não calibrado**, porque Limiares e Léxico foram medidos só com Atas do Copom.
   Quais chaves são essenciais é decisão da pessoa dona do Avaliador.
2. **As nove posições estão cravadas.** `MATRIZ` é usada em
   [transversal.py](../../../src/suno/avaliador/transversal.py),
   [execucao.py](../../../src/suno/gerador/execucao.py) e
   [orquestracao.py](../../../src/suno/gerador/orquestracao.py). `Execucao` ganha `pedido` e essas
   funções recebem as posições em vez da constante. O ciclo transversal só roda com 2 ou mais
   Células. Esses arquivos têm alterações não commitadas da equipe: combinar antes de mexer.
3. **A Visão unida é a peça mais difícil.** `DossieCurado` tem uma `Ata` só
   ([curador.py](../../../src/suno/gerador/curador.py)) e as chaves de Âncora colidem entre
   fontes. **Proposta:** chaves prefixadas por item. Entregar `SEPARADA` primeiro e `UNIDA`
   depois. A validação da seleção já existe em [dominio.py](../../../src/suno/dominio.py).

### 6.2 Domínio novo

Em `src/suno/dominio.py`, sem renomear nada existente. No código continua `Execucao`; "Saída" é
rótulo de tela, em `web/src/texto/rotulos.ts`.

- `Execucao.nome: str`, texto livre. O `identificador` continua sendo gerado pelo sistema (nome de pasta, no padrão `<fonte>-<provedor>-<carimbo>`), porque `NOME_DE_PASTA` em `gerador/execucao.py` não aceita acento nem espaço. Execuções antigas usam o identificador como nome.
- `Execucao.pedido: list[tuple[Audiencia, Formato]]`. Ausente em execuções antigas significa as nove.
- `Execucao.decisoes: list[DecisaoHumana]`. `DecisaoHumana` tem `audiencia`, `formato`,
  `estado` (`aprovada` ou `reprovada`), `motivo`, `revisor` e `em`. Sem registro significa pendente.
- `Fonte` (`id`, `nome`, `tipo`, `ativa`, `disponivel`) e `ItemDeFonte` (`fonte`,
  `identificador`, `titulo`, `data_referencia`, `resumo`, `total_ancoras`). O texto do item fica no arquivo dele, não no registro.
- `Andamento`, em `andamento.json` ao lado de `execucao.json`: estado do job e estado por Célula.
  É arquivo à parte porque `execucao.json` só é gravado ao fim do pipeline.

### 6.3 Rotas novas

Os nomes `/api/execucoes` continuam. Nada que existe é quebrado.

| Rota | Faz |
|---|---|
| `GET /api/fontes` | Catálogo e itens com resumo |
| `PATCH /api/fontes/{id}` | Liga e desliga |
| `POST /api/fontes/atualizar` | Job que busca nas fontes ligadas. Precisa de rede e falha sem travar a tela |
| `POST /api/fontes/importar` | Upload de PDF ou texto |
| `GET /api/curadoria/sugestoes` | Destaque único e Visão unida |
| `POST /api/execucoes` | Cria a Saída e inicia o job. Responde 202 |
| `GET /api/execucoes/{id}/andamento` | Andamento por Célula |
| `PATCH /api/execucoes/{id}` | Renomear |
| `POST …/celulas/{aud}/{fmt}/decisao` | Aprovar ou reprovar |
| `GET …/exportar?formato=json\|md\|zip` | Exportar |

### 6.4 Geração em segundo plano

- Um job por vez. O tier gratuito tem cota, e jobs simultâneos disparam 429. Os demais ficam em fila.
- O pipeline avisa por callback quando cada Célula termina, e `andamento.json` é atualizado. A tela consulta por polling.
- No boot do servidor, job que ficou "gerando" vira "interrompida".
- Demo funciona com geração parcial: o provedor falso responde por rótulo (`celula:<aud>:<fmt>:<rodada>`), não por ordem.
- O comentário de [app.py](../../../src/suno/api/app.py) ("a API não executa o pipeline") passa a ser falso. Vira ADR.

### 6.5 Fontes e curadoria

- Catálogo em `data/fontes/catalogo.json`. As Atas do Copom continuam em `data/atas/`, versionadas, para a demo seguir sem rede.
- Adaptadores: `copom` (já existe em `ingestao/bcb.py`) e `cvm_fatos_relevantes` (novo, pelos dados abertos da CVM, ver pesquisa). `releases_b3` fica desligado.
- **Resumo do bloco e Sugestão da curadoria são determinísticos, sem LLM.** Resumo: título, data, primeiras frases, contagem de Âncoras. Ranking: recência, número de Âncoras e peso da fonte. Não gastam cota, funcionam offline e são testáveis.
- **Atualizar fontes** é a interface do comando `buscar-ata`. Sem rede, mostra o erro e mantém o que já está em disco.

### 6.6 Decisão humana: regras

- Só se decide uma Célula com `celula_final`. Sem conteúdo gerado, não há o que aprovar.
- **Compliance bloqueia.** Se o Laudo final contém `MotivoReprovacao.RECOMENDACAO`, a rota responde 409 e a tela desabilita **Aprovar** com o motivo. Isso é o Laudo falando, não regra de tela.
- Pode ser aprovada por humano a Célula com destino `aprovado` ou `reprovado_revisao_humana` (sem Recomendação). **Reprovar** exige motivo.
- Registrar uma decisão resolve a `Pendencia` H4 da Célula. A rota antiga `…/filas/h4/{i}/resolver` fica por compatibilidade.
- Aprovar o conteúdo e aprovar o Pacote (H5, `aprovado_por_humano`) são decisões separadas.

### 6.7 Exportar

- `json`: o `execucao.json` inteiro.
- `md`: os `celulas/*.md` que `gravar_execucao` já escreve.
- `zip`: os dois, mais a pasta `pacote/` quando existir.

## 7. Fases

Cada fase termina com algo funcionando ponta a ponta e verificado no app rodando. O pipeline
já existe, então a interface não depende de esperar o Gerador.

| Fase | Entrega | Resultado visível |
|---|---|---|
| **0. Preparação** | Combinar com a equipe sobre os arquivos com alterações não commitadas. ADR 0017. Tokens da seção 5, menu lateral e rotas das três guias. Regenerar o cliente TypeScript. | Casca nova no ar, guias vazias. |
| **1. Revisar o que já existe** | Lista de Saídas, Saída aberta e Célula aberta sobre as execuções em disco. Backend: `nome` e renomear, `decisoes`, rota de decisão com 409 de Compliance, exportar. | Revisar, aprovar e exportar o que já foi gerado, inclusive a demo sem rede. |
| **2. Gerar sob demanda** | `Execucao.pedido`, as funções sem a constante `MATRIZ`, job em segundo plano, `andamento.json`, `POST /api/execucoes`, Curadoria passos 2 e 3. Fonte única: as Atas de `data/atas/`. | Escolher Células na Matriz e gerar, em Demo e Real. |
| **3. Fontes** | Catálogo, adaptador CVM, upload, resumo, tipo de fonte com conjunto essencial genérico, selo **não calibrado**. Guia Fontes (trilhos) e passo 1 da Curadoria (Destaque único e "Montar a minha"). | As três guias completas. |
| **4. Visão unida** | Dossiê com várias fontes, chaves prefixadas por item. | O segundo cartão da Curadoria passa a funcionar. |
| **5. Acabamento** | **Montar Pacote** pela interface (outro tipo de job), estados vazios e de erro, ajuste de telas menores. | Fluxo completo. |

**Se atrasar, corte nesta ordem** (a mesma lógica do [CLAUDE.md](../../../CLAUDE.md)): Fase 5,
depois Fase 4 (o cartão "Visão unida" fica "em breve"), depois o adaptador CVM (fica só o
upload). As Fases 0 a 2 e o upload da 3 não caem.

## 8. Testes

O Avaliador continua sem LLM e sem rede. A suíte continua offline: a trava de rede de
[conftest.py](../../../tests/conftest.py) vale para tudo o que for novo, e fontes e cota usam
`httpx` simulado.

**Backend (pytest)**

- `avaliar_matriz` e o ciclo transversal parametrizados por posições: 1, 5 e 9 Células; completude relativa ao pedido; ciclo transversal pulado com menos de 2 Células.
- `Execucao`: `pedido` e `decisoes` nos validadores; execução antiga sem os campos continua carregando.
- API com `TestClient` e provedor falso: `POST /api/execucoes` responde 202; o andamento progride; o segundo job fica em fila; reinício marca a interrompida; renomear; decisão aprova e reprova; **decisão em Célula com Recomendação responde 409**; exportar `json`, `md` e `zip` com o conteúdo esperado.
- Fontes: liga/desliga; upload de PDF e de texto; arquivo inválido recusado; caminho com `..` recusado; atualizar sem rede falha sem derrubar a listagem.
- Fonte não Copom: conjunto essencial genérico aprova um item válido e reprova um sem número nem data.
- Contrato: um teste que falha se `web/openapi.json` não bate com o que a API gera hoje (hoje só o script [gerar-cliente](../../../scripts/gerar-cliente.ps1) o atualiza, nada confere).

**Front**

- `tsc --noEmit` (já faz parte do `build`) contra o cliente regenerado.
- Vitest para a lógica pura: seleção da Matriz por célula, linha e coluna; mapeamento estado → cor da mini-Matriz; contagens do cartão da Saída. O front hoje não tem nenhum teste, então isso inclui adicionar a ferramenta.
- Verificação manual com o app rodando ao fim de cada fase, nos fluxos reais (rodar a demo, abrir uma Célula, aprovar, exportar).

## 9. Registros a atualizar

- **ADR 0017**, "A API dispara a geração em segundo plano" (próximo número livre; hoje o 0016 é o último). Registra um job por vez por causa da cota e o fim de "a API só lê".
- **[CONTEXT.md](../../../CONTEXT.md)**: termos **Saída** (rótulo de tela de uma execução nomeada), **Sugestão da curadoria**, **Fonte**, **Item de fonte**, **Decisão humana** e **Pedido**.
- **[CLAUDE.md](../../../CLAUDE.md)**: o trecho "execuções gravam em disco e a interface lê do disco" segue valendo, e a nota de que a API não executa o pipeline sai.
- **[README.md](../../../README.md)** e [ARQUITETURA.md](../../ARQUITETURA.md): as três guias novas.

## 10. Riscos e pontos em aberto

1. **Calibração fora do Copom.** A pessoa dona do Avaliador valida o conjunto essencial genérico e se aceita o selo **não calibrado** no lugar de medir Limiares para Fatos Relevantes.
2. **Alterações não commitadas** em `matriz.py`, `execucao.py`, `dominio.py` e `avaliador/` (segundo o `git status` de 2026-10-09) bloqueiam a Fase 2 até serem combinadas.
3. **Cota gratuita.** O modo Real gasta cota de Gemini e Groq. Um job por vez reduz o 429, mas não o elimina.
4. **Adaptador CVM.** A pesquisa o descreve como fonte secundária. Testar de ponta a ponta na Fase 3, antes de prometer.
5. **Visão unida** (Fase 4) é a mais arriscada. Por isso é a primeira a cair.
6. **Montar Pacote pela interface** exige outro tipo de job. Hoje o Pacote só sai pelo terminal.
7. **Cores da marca.** O hex oficial da Suno e a fonte substituem os valores estimados.
8. **Quem decidiu.** Sem login, o revisor é um nome digitado e guardado no navegador. Aceitável para o case, a revisitar se a API aberta voltar.
9. **Vocabulário.** Os nomes `Fonte`, `ItemDeFonte` e o campo `tipo` da seção 6.2 colidem com a lista _Avoid_ do [CONTEXT.md](../../../CONTEXT.md) (`fonte`, `item`, `tipo`), que `scripts/vocabulario.py` confere em `src/`, `tests/` e `web/src/`. Antes de escrever código da Fase 3, decidir os nomes: ou CONTEXT.md ganha o termo **Fonte** e tira "fonte" do _Avoid_ da Ata, ou o código usa outro nome. Nas Fases 0 e 1 isso não aparece. Hoje a checagem já acusa 16 achados, todos do trabalho em andamento da equipe (`avaliacao`, `persona`, `evidencia`).
