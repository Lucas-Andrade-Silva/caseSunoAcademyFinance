# Gerador e Avaliador são módulos separados, ligados por um contrato

O sistema tem dois módulos profundos. O **Gerador** ingere a ata, extrai âncoras
factuais, adapta por audiência e sintetiza por formato. O **Avaliador** recebe uma
célula pronta mais as âncoras do documento-fonte e devolve um laudo. O contrato entre
eles é `(Conteúdo, Âncora[], Audiência) → Laudo`, e nada mais atravessa essa costura:
o Avaliador não sabe como o texto foi produzido, o Gerador não sabe como será julgado.
O ciclo de correção é o Gerador consumindo o laudo.

Escolhemos esta costura, e não uma divisão por etapa do pipeline, por três razões.
O Avaliador é o diferencial avaliado do case, e o teste da deleção confirma: apagá-lo
não move complexidade para outro lugar, apaga o projeto. Ele é muito comportamento
atrás de uma interface minúscula, que é a forma que o pytest testa direto e que um
agente navega sem precisar ler o resto do sistema. E ele **não depende de LLM nem de
rede**, o que o torna construível e testável desde a primeira hora, com texto colado à
mão, sem esperar o Gerador existir.

## Consequências

O time de duas pessoas se divide nessa costura: a pessoa com conhecimento de mercado é
dona do Avaliador, porque o que torna esse módulo profundo é conhecimento de domínio
codificado — léxico, limiares, o que conta como afirmação factual, o que é linguagem
de recomendação. As duas pessoas ficam desbloqueadas no dia 1 em vez de uma esperar
a outra.

A independência de rede do Avaliador é uma propriedade a defender, não um acidente. No
momento em que ele precisar de uma chamada de API para decidir, a suíte de testes deixa
de rodar offline e em CI, e o custo dessa perda é maior que o de qualquer métrica que
se ganhe com isso. O juiz estruturado por LLM é a exceção deliberada, e fica isolado
atrás da sua própria interface, com as métricas determinísticas rodando sem ele.
