# O Avaliador ganha uma camada opcional de comitê de juízes-LLM, isolada atrás de sua própria interface

O [ADR 0001](0001-gerador-e-avaliador-como-modulos-separados.md) já reserva essa exceção: "o juiz
estruturado por LLM é a exceção deliberada, e fica isolado atrás da sua própria interface, com as
métricas determinísticas rodando sem ele." Este ADR decide a forma dessa camada, para quando ela
existir.

Decisão: um comitê de **um juiz por dimensão**, não um juiz único e holístico. Cada dimensão
recebe uma rubrica própria e uma nota isolada, nunca uma média. Um projeto irmão testou a
alternativa (juiz único multitarefa) e documentou o problema: misturar dimensões distintas numa
nota só esconde se o problema foi decisão errada, texto ruim, ou outra coisa — e correções
diferentes pedem diagnósticos diferentes. E o juiz nunca roda no mesmo provedor que gerou o
Conteúdo sendo avaliado, para não incorrer em autopreferência — a tendência conhecida de um modelo
avaliar melhor o que ele mesmo teria produzido.

Essa camada é opcional e roda depois das métricas determinísticas, nunca antes: a suíte
determinística continua sendo o que garante a testabilidade em CI do ADR 0001; o juiz-LLM é
aditivo, ligado sob demanda, e sua ausência não invalida um Laudo.

## O escopo do comitê (decidido em 17/09/2026)

O ADR original deixou as dimensões em aberto. Esta atualização as fecha:

**O comitê julga apenas dimensões subjetivas** — tom, clareza e coerência. Compliance e Aderência
ficam 100% determinísticos e **nunca** passam por LLM, nem como segunda opinião. A razão é
medida: vereditos de LLM-juiz sobre compliance são não-determinísticos no mesmo input, e há
registro de juiz alucinando evidência para justificar retroativamente um veredito
consistente-mas-errado. Uma linha que reprova não pode depender de um julgamento que muda entre
duas execuções do mesmo texto.

A dimensão de coerência existe para pegar um caso específico que a métrica não pega: o texto
degenerado de frases curtas e desconexas, que pontua bem no Flesch-BR e lê mal. A rubrica pergunta
se o texto está natural ou parece cortado artificialmente.

**São dois juízes, em provedores diferentes, não três.** O quórum de 2-de-3 foi considerado e
recusado: triplicaria as chamadas de juiz por Ata — 27 numa Matriz completa — e o tier gratuito
não comporta. Quando os dois juízes discordam, o Laudo marca `revisão humana` naquela dimensão em
vez de gastar uma terceira chamada para desempatar. Discordância é informação, não um impasse a
resolver automaticamente.

**O juiz é cego quanto ao modelo gerador.** Trocar de provedor evita autopreferência direta, mas
não o viés de reputação: o prompt do juiz nunca menciona qual modelo ou provedor produziu o texto.

**O comitê julga só dois dos três Formatos: Texto analítico e Carrossel.** O Roteiro passa apenas
pelas métricas determinísticas. O Roteiro é a entrada do vídeo, e vídeo é o item 3 da ordem de
corte do CLAUDE.md — gastar cota de juiz no Formato que pode não ser entregue é a troca errada. A
mesma linha vale do outro lado da renderização: o vídeo pronto também não vai a juiz de visão
([ADR 0014](0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md)). O ramo do vídeo é
determinístico de ponta a ponta, e quem o revisa é uma pessoa.

Este ADR trata do julgamento do **texto** da Célula. O julgamento visual do artefato renderizado
— imagem do Carrossel e vídeo — é outra coisa, com outras regras, e vive no
[ADR 0014](0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md). Notavelmente, a restrição
de provedor acima não se aplica lá: a imagem não é gerada por LLM, então não há autopreferência a
evitar.

## Consequências

Tom, clareza e coerência viram termos do CONTEXT.md quando a camada for implementada. Nenhuma
delas é um Limiar de aprovação sozinha — o veredito de aprovação continua saindo das métricas
determinísticas; a nota do comitê entra no Laudo como informação.

Um Laudo produzido sem essa camada ativa precisa deixar isso explícito — campo ausente, nunca nota
zero — seguindo a mesma disciplina que o resto do Laudo já aplica a qualquer métrica sem base
suficiente para ser calculada. `revisão humana` é um terceiro estado ao lado de ausente e medido,
e a interface o exibe como tal.

Calibrar o comitê contra a pessoa dona do Avaliador tem alvo de Kappa 0,6–0,8. Kappa acima de 0,95
é sinal de juízes redundantes ou de viés compartilhado, não de juízes bons.

O provedor do juiz está sujeito ao mesmo roteador do [ADR 0007](0007-roteador-de-provedores-distingue-tipo-de-429.md),
mas nunca pode resolver para o mesmo provedor usado pelo Gerador na mesma execução — essa restrição
é adicional à lógica de fallback por 429. Com dois juízes em provedores distintos e o Gerador num
terceiro, os três provedores do roteador ficam ocupados numa execução com o comitê ligado: não há
reserva sobrando para 429, e é por isso que o comitê é opcional e fica desligado na demo.

Com o comitê restrito a dois Formatos, o custo por Ata é de 6 Células vezes 2 juízes — 12 chamadas
de juiz, não 18.
