# 0024 — Diretor de Arte IA com fallback determinístico

## Status

Aceita.

## Contexto

As regras locais selecionam layouts com segurança e repetibilidade, mas não interpretam nuances
editoriais do carrossel inteiro. Uma decisão de IA pode melhorar coerência e adequação do estilo,
desde que não controle texto, números, identidade visual, CSS ou templates.

## Decisão

O Pacote faz uma única chamada estruturada ao Diretor de Arte IA por carrossel. A entrada contém
função e conteúdo dos slides, referências aprovadas e histórico recente. A saída escolhe, para
cada slide, composição, referência, intensidade visual e justificativa.

O código valida a resposta antes de renderizar:

- precisa haver exatamente uma escolha para cada slide, na ordem correta;
- a composição precisa ser compatível com o conteúdo;
- a referência precisa existir, estar aprovada e pertencer à composição;
- repetição consecutiva é recusada quando existe alternativa compatível.

Qualquer ausência de credencial, erro de provedor, resposta fora do schema ou violação dessas
regras aciona o seletor determinístico existente. O `pacote.json` registra se o plano veio da IA
ou das regras locais, o provedor usado, a intensidade de cada slide e o motivo do fallback.

## Consequências

A decisão editorial melhora sem transformar o renderizador num gerador livre. Há no máximo uma
chamada adicional por carrossel. O modo falso e ambientes sem credencial continuam plenamente
funcionais, e um problema externo nunca impede a montagem do Pacote.
