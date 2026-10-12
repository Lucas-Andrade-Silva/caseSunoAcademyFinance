# Front do Suno Content, Fase 5: acabamento

> **Para quem executar:** use superpowers:executing-plans (inline).

**Objetivo:** fechar o fluxo: montar o Pacote pela interface, estados de erro que se explicam e telas que
cabem no celular.

**Spec:** [2026-10-09-front-suno-design.md](../specs/2026-10-09-front-suno-design.md), seção 7 (Fase 5) e
risco 6.

## Decisões

1. **Montar Pacote é um job por Saída** (`api/pacotes.py`, `Montador`): `POST /api/execucoes/{id}/pacotes/montar`
   responde 202 e a tela consulta `.../pacotes/montagem`. Monta os Pacotes de **todas** as Células aprovadas da
   Saída, como `suno.cli pacote`.
2. **A rota recusa antes de chamar `montar_pacote`** (409, com o motivo) quando ele apagaria Pacote pronto: a
   Matriz que o ciclo transversal não aprovou (a função remove os Pacotes antigos nesse caso, ADR 0014) ou
   nenhuma Célula aprovada pelo Laudo.
3. **O vídeo do Roteiro continua no terminal** (ADR 0004): a tela mostra o comando.
4. **Erros**: `mensagemDeFalha` traduz o `TypeError` do `fetch` ("Sem conexão com o servidor…"); `MensagemErro`
   ganha **Tentar de novo**; um limite de erro de renderização evita a página em branco.
5. **Telas menores**: o menu lateral vira barra no topo abaixo de 768 px, e as Matrizes 3×3 estreitam a
   primeira coluna.

## Tarefas

- [x] **1.** Testes e `Montador` + rotas (`tests/test_api_pacotes.py`, 8 testes).
- [x] **2.** `lib/pacote.ts` (`motivoSemPacote`) com Vitest; `SecaoPacote` com o botão, a consulta e a instrução do
  vídeo; `CelulaAberta` passa o motivo.
- [x] **3.** `mensagemDeFalha`, **Tentar de novo**, `LimiteDeErro`.
- [x] **4.** Menu responsivo e Matrizes no celular.
- [x] **5.** Verificação no navegador.

## Registro da execução

Executado em 2026-10-10, inline, em `main`, sem commits. Ao fim: 1084 testes pytest e 74 Vitest, build verde,
`scripts/vocabulario.py` nos mesmos 16 achados da equipe.

Conferido no navegador (Edge): em desktop, montar os Pacotes de uma Saída com duas Células aprovadas (imagens
do carrossel, legenda, hashtags; o Roteiro sem vídeo mostra o comando do terminal); numa Saída com a Célula
teimosa, o botão não aparece e o motivo (ciclo transversal) está à vista. Em 390 px de largura: Saídas, Saída
aberta, Célula aberta, Fontes e Curadoria (passos 1 e 2) sem rolagem horizontal.

Não feito, de propósito: o Pacote **não considera a Decisão humana**. `montar_pacote` só monta Célula aprovada pelo
Laudo numa Matriz aprovada pelo ciclo transversal; aprovar à mão uma Célula que foi para a revisão humana não
libera Pacote. Mudar isso é decisão de domínio (ADR 0014) e fica para a equipe.
