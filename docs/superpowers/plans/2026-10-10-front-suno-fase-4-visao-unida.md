# Front do Suno Content, Fase 4: Visão unida

> **Para quem executar:** use superpowers:executing-plans (inline). Passos com `- [ ]`.

**Objetivo:** o segundo cartão da Curadoria passa a funcionar: um só conteúdo que junta de 2 a 5
Atas, com cada número citando a sua origem.

**Arquitetura:** a Visão unida é uma `Ata` composta (`categoria: unida`, `partes` com os
identificadores) cujo texto traz cada comunicado sob um cabeçalho `[a1]`, `[a2]`… A extração roda por
parte e as chaves de Âncora ganham o prefixo da parte (`a1_selic_decidida`, `a2_numero_principal`),
então nada colide. O conjunto essencial é o genérico, **por parte**: se uma parte não tem data e número
com unidade, a Matriz inteira reprova por falha de extração. O resto do pipeline (Ciclo, Avaliador,
Judge) não muda: recebe uma `Ata` e uma tabela de Âncoras.

**Spec:** [2026-10-09-front-suno-design.md](../specs/2026-10-09-front-suno-design.md), seções 6.1
(achado 3), 4.2 e 10 (risco 5).

## Restrições globais

- Suíte offline. O Demo não existe para a Visão unida (não há respostas prontas): só Real.
- Vocabulário: nada de `fonte`, `item`, `documento`, `fato`, `pdf` em identificador.
- Execuções antigas e a Saída de Ata única não mudam. Sem commit.

## Decisões

1. **Prefixo `a<N>`** (N de 1 a 5, na ordem da seleção). O rótulo de cada Âncora vira
   `[aN] <título curto>: <rótulo>`, e é isso que a Célula aberta mostra ao lado do conteúdo.
2. **Cada parte entra com as chaves genéricas**, inclusive a do Copom (que ainda recebe as próprias chaves
   do Copom, prefixadas). O LLM rotula por parte: uma chamada de extração por Ata.
3. **O molde ganha uma instrução** só para a categoria `unida`: dizer de qual comunicado vem cada número e
   não misturar números de comunicados diferentes como se fossem do mesmo.
4. **Limite de 5 Atas** por Visão unida: o prompt carrega o texto de todas, e a cota é gratuita.
5. **A sugestão** é as 3 Atas mais bem colocadas pelo mesmo ranking do Destaque único, só entre as que
   conseguem gerar, e só existe com 2 ou mais.
6. **`NovaSaida`** passa a aceitar `itens` (2 a 5 identificadores) no lugar de `ata`: exatamente um dos dois.

## Arquivos

| Arquivo | Mudança |
|---|---|
| `dominio.py` | `CategoriaDaAta.UNIDA`, `Ata.partes`, `chaves_essenciais_da_ata` |
| `gerador/curador.py` | `compor_uniao`, `AgenteCurador.preparar_uniao` |
| `gerador/extracao.py` | `extrair_ancoras(..., com_chaves_genericas)`, `extrair_ancoras_da_uniao` |
| `gerador/moldes.py` | descrição e instrução da `unida` |
| `gerador/ciclo.py`, `execucao.py` | essenciais pela Ata; `executar` aceita uma lista de caminhos |
| `origens/catalogo.py`, `curadoria.py` | peso da `unida`; `sugerir_visao_unida` |
| `api/geracao.py`, `api/app.py` | `itens`, 404/422, `visao_unida` nas sugestões |
| `web/...` | cartão **Visão unida**, **Usar selecionados**, passo 2 com vários itens |

---

### Tarefa 1: Dossiê com várias Atas

- [ ] **1.1** Testes (`tests/test_visao_unida.py`): `compor_uniao` (id estável e curto, título, texto com
  cabeçalhos `[a1]`, data mais recente, `partes`, categoria `unida`, ordem preservada, recusa de 0, 1 ou 6
  Atas, recusa de repetida); extração por parte com provedor falso (chaves prefixadas, sem colisão quando duas
  partes têm `numero_principal`, rótulo com o título, textuais prefixadas); integridade da `unida`
  (falta `a2_numero_principal` quando a segunda parte não tem número); molde da `unida` com a instrução;
  `executar` com duas Atas e provedor falso grava `selecao.modo == unida`, os itens, a categoria e as
  Âncoras prefixadas.
- [ ] **1.2** Implementar.
- [ ] **1.3** `uv run pytest -q` verde.

### Tarefa 2: Sugestão, `Gerenciador` e rotas

- [ ] **2.1** Testes: sugestão da Visão unida (3 melhores, só as que geram, `None` com menos de 2); `POST
  /api/execucoes` com `itens` responde 202 e `categoria: unida`; Demo é 422; item inexistente é 404; um só
  item em `itens` é 422; `ata` e `itens` juntos ou nenhum é 422; item com extração incompleta é 422;
  mais de 5 é 422.
- [ ] **2.2** Implementar; regenerar contrato.
- [ ] **2.3** `uv run pytest -q` verde.

### Tarefa 3: Front

- [ ] **3.1** `lib/fontes.ts`: `podeUsarSelecao` aceita de 1 a 5 (1 = Destaque único, 2+ = Visão unida) + testes.
- [ ] **3.2** Curadoria: cartão **Visão unida** com os itens e o motivo; **Usar selecionados**; passo 2 com a
  lista de itens, Demo desabilitada com o motivo e `criarSaida({itens})`.
- [ ] **3.3** `npm test`, `npm run build`.

### Tarefa 4: Registros e verificação

- [ ] **4.1** ADR 0019, CONTEXT.md (Visão unida, Destaque único), registro deste plano.
- [ ] **4.2** Suites, vocabulário, navegador.

---

## Registro da execução

Executado em 2026-10-10, inline, em `main`, sem commits. Ao fim da fase: 1076 testes pytest e 69 Vitest,
build verde, `scripts/vocabulario.py` nos mesmos 16 achados da equipe.

Divergências do plano:

- `Andamento.atas` e `ExecucaoResumo.atas` (as Atas usadas) não estavam no plano: a lista e o cabeçalho mostram
  "3 Atas" em vez do identificador `uniao-…`.
- `INSTRUCAO_DA_VISAO_UNIDA` chega ao molde por um parâmetro novo, `instrucoes_do_conjunto`.
- O `Gerenciador` valida a união (de 2 a 5, sem repetição, sem Demo, cada Ata com extração completa) antes de
  enfileirar, na mesma ordem em que valida o Destaque único.

Conferido no navegador, com o pipeline de verdade e o provedor falso (respostas prontas montadas na hora): o
cartão Visão unida com 3 itens, o passo 2 com Demo desabilitada, a geração, a Saída "3 Atas · Visão unida ·
não calibrado" e a Célula aberta com a Âncora `[a2] Empresa Exemplo…: Número principal` e o trecho literal.
Nenhuma chamada de LLM real foi feita: o modo Real da Visão unida **não foi exercitado com provedor de
verdade** (sem chave no ambiente).

