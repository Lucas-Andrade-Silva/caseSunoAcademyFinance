# O Gerador é um pipeline direto de chamadas estruturadas, não um agente com tools — e não usa MCP

Três projetos irmãos analisados como referência de arquitetura (Tractian, BTG, Nvidia) usam
LangGraph com agentes que decidem, via tool calling, quais ações tomar a cada passo — um deles em
ciclo ReAct explícito. É o caminho óbvio para "sistema que usa LLM para produzir algo a partir de
um documento", e foi deliberadamente não seguido aqui.

Um agente com tools existe para resolver incerteza sobre *o que fazer a seguir*: buscar mais dado,
decidir se investiga mais ou já responde, escolher entre ações concorrentes. Nenhuma dessas
perguntas existe no Gerador. A Ata inteira já está disponível antes da primeira chamada
([ADR 0006](0006-atas-do-copom-como-documento-fonte-principal.md) — o fetch é um comando separado,
rodado antes); as Âncoras são extraídas do próprio texto, não buscadas em outro lugar; e as nove
Células são independentes entre si — não há sequência a decidir, e sim nove transformações que
rodam em paralelo. Um loop ReAct é sequencial por natureza, cada ação depende do resultado da
anterior; "as nove Células geram em paralelo" já é incompatível com isso.

O Tractian — o mais maduro dos projetos irmãos nesse ponto — documenta a própria arquitetura
multiagente como decisão nunca validada contra a alternativa mais simples, e chama isso de maior
lacuna do projeto. Não repetimos a complexidade sem repetir a validação que faltou.

Por consequência direta, também não há uso de **MCP**: MCP resolve a exposição de ferramentas para
um agente descobrir e chamar dinamicamente, e sem agente não há o que expor. Adotá-lo aqui seria
infraestrutura — processo de servidor, handshake de protocolo — sem problema real por trás, e
tensiona o "demo roda sem rede" do ADR 0006.

Adotamos: o Gerador é uma sequência fixa de chamadas estruturadas ao provedor de LLM ativo — extrai
Âncoras → adapta por Audiência → sintetiza por Formato, por Célula —, atrás do roteador do
[ADR 0007](0007-roteador-de-provedores-distingue-tipo-de-429.md). Nenhum tool calling, nenhum
framework de orquestração de agente, nenhum MCP.

## Consequências

Se uma etapa futura precisar mesmo de decisão dinâmica sobre ação — não é o caso hoje —, ela entra
como uma exceção isolada e justificada por escrito, não como reescrita silenciosa do Gerador
inteiro para um framework de agente.

O Avaliador já era não-agente pelo [ADR 0001](0001-gerador-e-avaliador-como-modulos-separados.md);
este ADR estende o mesmo princípio ao Gerador, fechando a arquitetura do pipeline inteiro como
não-agêntica por padrão.
