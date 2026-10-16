# Arquitetura — Suno Content

Este documento descreve o fluxo ponta a ponta do sistema e referencia o ADR que justifica cada
decisão. Não repete o *porquê* — isso já está nos ADRs — só mostra como as peças se encaixam.

## Como funciona, em palavras simples

Antes do diagrama, a versão que se explica numa conversa.

O Banco Central publica, a cada reunião, um documento denso sobre a decisão de juros. Quase
ninguém fora do mercado lê até o fim. Este sistema pega esse documento e escreve nove versões
dele — uma para cada combinação de três tipos de leitor (quem está começando, quem já acompanha,
quem trabalha com isso) e três formatos (um texto para ler, um carrossel de imagens, um roteiro de
vídeo curto). O que ele tem de diferente é que nada sai antes de passar por uma prova.

Começa com uma pessoa escolhendo de qual reunião o conteúdo vai falar. O documento fica guardado
no próprio projeto, então a demonstração funciona sem internet.

O sistema então lê o documento e faz uma coisa parecida com um fichamento: anota à parte todos os
números e datas importantes — o juro que ficou valendo, quanto subiu ou caiu, o resultado da
votação, quando é a próxima reunião — e junto de cada anotação guarda o trecho exato de onde ela
saiu. Daí para frente, nenhum número é escrito de novo pela inteligência artificial: ele é
**copiado** dessa lista. É a diferença entre citar e lembrar de cabeça, e é o que impede o sistema
de inventar um número que soa plausível.

Com o fichamento pronto, a inteligência artificial escreve as nove versões, todas ao mesmo tempo.
Fazer uma depois da outra levaria minutos demais para uma apresentação ao vivo.

Aí entra a parte que é o coração do projeto: um corretor. Ele não usa inteligência artificial —
são contas e regras, o que significa que ele dá sempre a mesma resposta para o mesmo texto e pode
ser testado sozinho, sem depender de nada. Ele faz quatro perguntas a cada versão. O texto está
fácil de ler no ponto certo para aquele leitor — nem difícil demais para quem está começando, nem
raso demais para quem é do ramo? Os termos de mercado aparecem explicados quando precisavam
aparecer explicados? Cada número confere com o fichamento? E a pergunta que não tem margem: o
texto sugere comprar, vender ou promete retorno? Sugerir investimento é atividade regulada no
Brasil, e este sistema informa, não aconselha. Quem cruza essa linha é reprovado, ponto.

O corretor devolve um boletim com as medidas e o resultado. Reprovado volta para ser reescrito,
levando na mão o número exato que faltou — "faltaram três pontos para o texto ficar fácil o
bastante" em vez de "melhore o texto". Isso acontece um número limitado de vezes (quatro, por padrão,
ajustável nas configurações); a partir daí, insistir custa mais do que rende. A versão que continua reprovando não é jogada fora nem publicada: vai
para uma fila que uma pessoa abre e resolve, escrevendo à mão, mudando a régua, ou aceitando que
aquele assunto não rende naquele formato.

O que passa vira um pacote pronto para publicar: as imagens do carrossel, desenhadas pelo próprio
sistema a partir dos números do fichamento, o vídeo, a legenda. Aí tem uma segunda conferência, de
outra natureza: até aqui só o texto foi avaliado, e um desenho pode sair torto mesmo com o texto
certo — palavra cortada na borda, letra em cima do gráfico, cor que não dá para ler. Então o
sistema mede o que é mensurável e, quando ligado, mostra as imagens do carrossel a uma
inteligência artificial que sabe olhar figura, só para responder "isso parece quebrado?". Isso não
reprova o texto, que já passou; serve para avisar que vale refazer o desenho. O vídeo não passa por
essa conferência automática — dele se mede o tamanho e o som, e quem assiste é uma pessoa, que para
um vídeo de um minuto vê tudo e não uma amostra. Depois uma pessoa confere se
está apresentável e publica ela mesma no Instagram, no TikTok ou no Drive. Não existe publicação
automática, de propósito — a última assinatura é sempre humana.

A razão de tudo estar partido em duas metades, quem escreve e quem corrige, é simples: se a mesma
inteligência artificial escrevesse e se avaliasse, ela se daria boas notas. Há registro disso
acontecendo, inclusive de modelo inventando a nota que alega ter tirado. Separar as duas coisas, e
deixar a correção sem depender de inteligência artificial nenhuma, é o que torna o resultado
verificável por outra pessoa.

## Diagrama

Os nós em destaque (`H1`–`H6`) são os pontos onde um humano age. Não são exceções ou fallbacks:
são parte do desenho. O sistema informa e prepara; quem decide publicar é uma pessoa.

```mermaid
flowchart TD
    BCB["BCB · API de Atas"]
    H1{{"H1 · Curadoria da Ata<br/>humano escolhe a reunião<br/>e roda o fetch, antes da demo"}}
    ATAS[("data/atas/<br/>versionado no repo")]
    BCB --> H1 --> ATAS

    ATAS --> EXT

    subgraph G["Gerador · Gemini Flash pelo roteador"]
        direction TB
        EXT["1 · Extração<br/>Âncoras textuais +<br/>tabela de Âncoras numéricas<br/>roda 1× por Ata · ADR 0011"]
        MATRIZ["2 · Matriz 3×3<br/>Audiência × Formato"]
        TXT["Texto analítico<br/>prosa · 3 Audiências"]
        CAR["Carrossel<br/>roteiro de slides · 3 Audiências"]
        ROT["Roteiro<br/>fala cronometrada · 3 Audiências"]
        EXT --> MATRIZ
        MATRIZ --> TXT
        MATRIZ --> CAR
        MATRIZ --> ROT
    end

    ROUTER["Roteador de provedores<br/>Gemini → Groq<br/>ADR 0007"]
    G -. usa .-> ROUTER

    TXT --> A
    CAR --> A
    ROT --> A

    H2{{"H2 · Calibração e Léxico<br/>~30 Células rotuladas à mão,<br/>Kappa 0,6–0,8 · define os Limiares"}}
    H2 -.->|"parametriza, fora de runtime"| A

    subgraph A["Avaliador · sem LLM e sem rede por padrão"]
        direction TB
        DET["Métricas determinísticas<br/>Flesch-BR · Densidade · Aderência<br/>Recomendação · Extração"]
        JUIZ["Qualidade (Jev) → Fidelidade (LLM)<br/>depois do determinístico, por Célula<br/>ADR 0035 e 0036"]
        DET --> JUIZ
    end

    ROUTER -.->|"Groq, depois Gemini<br/>(só a Fidelidade)"| JUIZ

    A --> LAUDO{"Laudo<br/>três destinos"}

    LAUDO -->|"reprovado,<br/>correção possível"| CICLO["Ciclo de correção<br/>teto configurável, padrão 4<br/>feedback = valor medido · ADR 0013"]
    CICLO --> MATRIZ

    LAUDO -->|"reprovado 2×<br/>ou falha de extração"| H4
    H4{{"H4 · Fila de revisão humana<br/>reescrever à mão · ajustar Limiar ·<br/>ou descartar a Célula"}}
    H4 -->|"reescrita aprovada"| P

    LAUDO -->|"aprovado"| P

    subgraph P["Pacote de publicação · só de Célula aprovada"]
        direction TB
        IMG["Imagens do Carrossel<br/>famílias visuais + fotos licenciadas<br/>PNG 1080×1350 · ADR 0030 e 0031"]
        VIDEO["Vídeo<br/>fora do grafo, consome<br/>Roteiro aprovado · 9:16 · ADR 0004"]
        LEG["Legenda + hashtags"]
    end

    VIS["Avaliação visual<br/>medições em tudo · juiz de visão só no<br/>Carrossel · não reprova a Célula · ADR 0014"]
    P --> VIS
    VIS -->|"defeito de render"| P
    H5{{"H5 · Aprovação do Pacote<br/>humano confere com a lista<br/>do que o sistema achou suspeito"}}
    VIS --> H5
    H5 --> H6{{"H6 · Publicação<br/>humano publica<br/>Instagram · TikTok · Drive"}}

    UI["Interface React + Vite sobre FastAPI<br/>cliente TS gerado do OpenAPI · ADR 0005"]
    ATAS -. lê .-> UI
    LAUDO -. lê .-> UI
    H4 -. exibida em .-> UI
    H5 -. exibida em .-> UI

    classDef humano fill:#fff4d6,stroke:#b8860b,stroke-width:2px,color:#000
    class H1,H2,H4,H5,H6 humano
```

## Os seis pontos de interferência humana

| | Momento | Quem | O que decide |
|---|---|---|---|
| **H1** | Antes da execução | Qualquer um do time | Qual Ata entra. O fetch no BCB é comando separado; a demo roda sem rede ([ADR 0006](adr/0006-atas-do-copom-como-documento-fonte-principal.md)) |
| **H2** | Fora de runtime | Dona do Avaliador | Os Limiares, o Léxico e os padrões sintáticos. Deriva de ~30 Células rotuladas pelas duas pessoas, com Kappa reportado. Parametriza o Avaliador; não roda durante a execução |
| **H3** | — | — | Removido junto com o Comitê, que era quem gerava o desempate ([ADR 0037](adr/0037-judge-transversal-removido-jev-sempre-ligado-sem-sambanova.md)) |
| **H4** | Depois do teto de correções | Qualquer um do time | O que fazer com a Célula que o Gerador não conseguiu consertar, ou com a Ata que o extrator não conseguiu ler ([ADR 0013](adr/0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md)) |
| **H5** | Antes de publicar | Qualquer um do time | Se o Pacote está apresentável. Aprovação do Laudo é sobre conteúdo; aqui se confere render, corte e legenda, com a lista da avaliação visual em mão ([ADR 0014](adr/0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md)) |
| **H6** | Publicação | Qualquer um do time | Publica. Não há integração de API com Instagram, TikTok ou Drive, por decisão |

H4 e H5 aparecem na interface como filas. H1 e H2 são trabalho de linha de comando e de
planilha, feitos antes.

## Os dois módulos

**Geração** usa um curador para preparar o dossiê factual e três geradores especializados:
Iniciante, Intermediário e Avançado. Cada gerador produz Texto analítico, Carrossel e Roteiro;
o código garante as nove posições e a ordem. Cada Célula passa pelas regras determinísticas e
volta ao seu gerador quando falha em integridade, Flesch-BR, Léxico/Densidade, Aderência ou
Recomendação. Depois do determinístico vêm duas camadas de LLM, por Célula: a **Qualidade** (o Jev nota
desenvolvimento, completude, clareza e tom, sempre ligado) e a **Fidelidade** (um LLM confere a Célula contra
a Ata, ligada por padrão). Abaixo do Limiar, ou diante de contradição provada com a Ata, a Célula volta ao Gerador,
dentro do mesmo teto de rodadas (padrão 4, de 0 a 10). Na correção o Gerador recebe a frase exata de cada problema, raciocina
(`raciocinio`) e muda o mínimo. Depois das Células, uma conferência **determinística** da Matriz (quantidade,
unicidade, aprovação e referências) vai para o JSON de auditoria. O Judge transversal foi removido
([ADR 0015](adr/0015-papeis-especializados-em-fluxo-deterministico.md),
[ADR 0035](adr/0035-qualidade-pelo-jev-depois-do-deterministico.md),
[ADR 0036](adr/0036-fidelidade-a-ata-por-llm-que-cita-e-o-codigo-confere.md),
[ADR 0037](adr/0037-judge-transversal-removido-jev-sempre-ligado-sem-sambanova.md)).

"Agente" significa papel especializado com contrato fixo, não loop ReAct ou tool calling. O fluxo
continua sem LangGraph ou MCP.

**Avaliador individual** recebe `(Conteúdo, Âncora[], Audiência)` de uma Célula e devolve um
Laudo. As cinco medidas rodam sem LLM e sem rede. O LLM (Jev e checador de fidelidade) aparece
somente depois dessa aprovação. O contrato entre geração e regras individuais continua sendo essa assinatura
([ADR 0001](adr/0001-gerador-e-avaliador-como-modulos-separados.md)).

## O estágio de extração

Roda uma vez por Ata, antes da Matriz, e produz duas coisas:

- **Âncoras textuais** — afirmações factuais em prosa, contra as quais a Aderência é medida.
- **Tabela de Âncoras numéricas** — Selic, variação em pontos base, IPCA, placar da votação,
  datas. Cada registro guarda valor, unidade e o trecho literal da Ata de onde veio.

A tabela é o insumo **único** de número no sistema. O Gerador substitui em molde em vez de
reescrever o número em prosa, e o Avaliador confere por igualdade exata — sem LLM, sem julgamento
([ADR 0011](adr/0011-ancoras-numericas-sao-citadas-nunca-reescritas.md)). O texto da Célula, a
legenda do Pacote e o gráfico do Carrossel leem todos da mesma tabela.

Extração degradada é motivo de reprovação próprio, e vai direto para H4 sem passar pelo Ciclo de
correção: reescrever não conserta um documento mal lido.

## Os quatro produtores

Os três primeiros são Formatos e vivem dentro do Gerador. O quarto vive fora do grafo.

### Texto analítico

O resumo analítico em prosa. Estrutura fixa em três partes: **o que foi decidido** (a Âncora
numérica principal, citada), **por que** (o argumento da Ata, parafraseado), **o que observar
adiante** (sem projeção própria, só o que a Ata sinaliza).

| | Iniciante | Intermediário | Avançado |
|---|---|---|---|
| Flesch-BR | ≥ 50 | 25–50 | < 25 |
| Termo do Léxico | sempre com explicação na primeira ocorrência | explicação só para termo fora do núcleo | sem explicação |

Saída em Markdown, para a interface e para o relatório. É o Formato mais barato de gerar e o mais
fácil de avaliar, e por isso é o primeiro a ser implementado ponta a ponta.

### Carrossel

O Gerador produz o **roteiro de slides** — texto estruturado, um registro por slide com título,
corpo e o campo opcional de dado a plotar. O Avaliador julga esse texto, não a imagem.

A renderização é etapa posterior e roda sem rede: templates HTML/CSS renderizados pelo Puppeteer,
saída **PNG 1080×1350 (4:5) em todos os slides de todas as nove Células**. Proporção variando entre
Células faz o Instagram cortar o carrossel inteiro para igualar a primeira imagem — é requisito
técnico, não estética. O visual vem de **famílias visuais** recriadas dos carrosséis reais da Suno
(Notícia, Explicativo, Jornal, Dados e Asset, além do layout escuro antigo): um carrossel usa uma
família, e os slides variam de layout dentro dela
([ADR 0030](adr/0030-familias-visuais-do-carrossel.md)). O texto de tamanho variável encolhe até
caber; o número do slide sai da Âncora, nunca do template.

**Fotos.** O Gerador sugere só o assunto da foto (`Slide.imagem`). A foto é real, vem da biblioteca local
`data/imagens/` (a demo roda sem rede) ou da busca de imagens na web (Bing) com relevância
verificada por um juiz de visão, e o crédito vai na legenda; no MVP a licença não é verificada
([ADR 0031](adr/0031-fotos-reais-e-licenciadas-nos-slides.md), [ADR 0032](adr/0032-fotos-da-web-pelo-bing-imagens-sem-verificar-licenca.md)). Sem foto, o layout degrada sozinho.
Geração de imagem por modelo continua fora do caminho crítico.

A reserva **Pillow + matplotlib** ([ADR 0009](adr/0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md),
[ADR 0020](adr/0020-carrossel-em-templates-html-renderizados-pelo-puppeteer.md)) é o que o `pytest` exercita:
determinística, sem navegador, com o layout escuro e sem foto.

### Roteiro

Fala cronometrada para vídeo vertical. O Gerador produz blocos de fala, cada um uma cena, com a
indicação do que aparece na tela e a **direção de cena**: layout, ícone, transição de entrada,
animação e momento do texto, efeito e sons, todos escolhidos de um catálogo fechado
([ADR 0021](adr/0021-direcao-de-cena-do-roteiro-em-catalogo-fechado.md)). O primeiro bloco é o
gancho; os Limiares de Flesch-BR valem sobre o texto falado, não sobre a rubrica de cena.

A pessoa escolhe a **duração** antes de gerar: 40 s, 1 min, 1 min 30, 2 min ou 3 min (padrão: 1
min). O pedido informa o orçamento de palavras e de cenas dessa duração, e o tempo de cada cena é
recalculado pelo código a partir da fala.

O Roteiro passa pelas mesmas camadas que os outros Formatos (as cinco medidas, a Qualidade e a
Fidelidade). Só o vídeo pronto não vai a juiz de visão
— o ramo do vídeo é o primeiro a cair sob atraso, e não se gasta cota avaliando o que pode não ser
entregue.

O Gerador **termina aqui**. Narração, composição, legenda e lip-sync vivem depois, atrás de outra
interface ([ADR 0004](adr/0004-renderizacao-de-video-fora-do-grafo.md)).

### Vídeo

Job **fora de banda** que consome Roteiros já aprovados pelo Avaliador. Nunca é nó do grafo: o
vídeo é critério eliminatório do case e renderização falha de formas criativas e demoradas — se
quebrar na véspera, os seis entregáveis continuam de pé e a demo usa um mp4 já renderizado.

Caminho principal é composição determinística em CPU. Avatar falante é alternativa, e é o item 3
da ordem de corte do CLAUDE.md — o primeiro a virar "vídeo sem rosto" quando o prazo apertar.

Nenhum LLM olha o mp4. Duração, proporção e presença de áudio são medidas; o resto é uma pessoa
assistindo no H5, que para sessenta segundos de vídeo é revisão completa, não amostra.

Do Roteiro aprovado sai também o **plano de edição**: um JSON versionado, autocontido, para colar
num gerador de vídeo com avatar sintético, e a tabela legível da mesma edição
([ADR 0021](adr/0021-direcao-de-cena-do-roteiro-em-catalogo-fechado.md)).

Um único mp4, 9:16, com dois destinos: a galeria da aplicação e o Pacote de publicação. Gerar um
vídeo "para o app" e outro "para as redes" é o erro a evitar.

## A avaliação visual do Pacote

O Avaliador julga texto, e julga antes de qualquer imagem existir. Isso deixa um vão: o render
determinístico sai sempre igual, mas não sai necessariamente certo — texto estoura a caixa, rótulo
se sobrepõe no gráfico, contraste fica ilegível, legenda dessincroniza do áudio.

Duas camadas cobrem esse vão, no mesmo padrão do resto do projeto
([ADR 0014](adr/0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md)).

**Medições, sempre ligadas e sem rede.** Estouro de caixa medido pelo Pillow, razão de contraste,
dimensão exata, número no gráfico conferido contra a tabela de Âncoras numéricas, duração e áudio
do vídeo. Falha aqui é defeito de render: refaz o render.

**Juiz de visão, opcional e só no Carrossel.** Olha a imagem pronta e responde o que não se mede —
isto parece quebrado, o layout está equilibrado, o gráfico comunica o que a legenda promete. É o
único lugar do sistema onde um juiz holístico é aceitável, porque aqui não existe número a atingir.
O Carrossel é julgado em folha de contato, todos os slides de uma Célula numa imagem só: três
chamadas de visão por Ata em vez de dezoito, e inconsistência entre slides é justamente o defeito
que se vê melhor em conjunto.

**O vídeo não vai a juiz nenhum**, nem antes nem depois de renderizar: o Roteiro passa só pelas
métricas determinísticas, e o mp4 só pelas medições de duração, proporção e áudio. Quadro
amostrado não mostra movimento nem sincronia, que é onde vídeo falha, e o vídeo já tem o revisor
que a imagem não tem — uma pessoa assiste antes de publicar. O ramo do vídeo é determinístico de
ponta a ponta.

Duas fronteiras importam. O juiz visual **nunca julga Recomendação** — isso é verificado no texto,
antes do render, sem LLM. E a avaliação visual **não entra no Laudo e não reprova a Célula**: o
texto já foi aprovado, e reescrevê-lo não conserta um rótulo sobreposto. O resultado vai anexado
ao Pacote para o H5, que deixa de ser inspeção humana cega e passa a ser inspeção humana com uma
lista.

A restrição de autopreferência do checador de fidelidade não vale aqui: a imagem não foi gerada por LLM, então não há
autopreferência a evitar, e o juiz visual pode rodar em qualquer provedor.

## O roteador de provedores

Uma única interface por trás da qual vivem Gemini (gera) e Groq (julga e é a reserva) — o
resto do pipeline não sabe qual provedor está ativo. Distingue cota por minuto de cota diária
antes de decidir entre esperar e trocar, e reaplica bindings de saída estruturada ao trocar de
cliente, para não perder a capacidade de produzir o schema da Célula no meio de uma troca
silenciosa ([ADR 0007](adr/0007-roteador-de-provedores-distingue-tipo-de-429.md)).

## O Avaliador e o Laudo

Cinco medidas determinísticas: **Flesch-BR** (fórmula própria, não `textstat` —
[ADR 0002](adr/0002-flesch-br-implementado-no-projeto.md)), **Densidade** contra o Léxico,
**Aderência** contra as Âncoras, **Recomendação** por Léxico mais padrão sintático em POS tagging
([ADR 0012](adr/0012-recomendacao-detectada-por-padrao-sintatico-nao-por-lista-de-palavras.md)) e
**integridade da extração**.

Sobre elas, nos três Formatos, vêm duas camadas de LLM: a **Qualidade** (o Jev nota
desenvolvimento, completude, clareza e tom) e a **Fidelidade** (um LLM confere a Célula contra a Ata
e o código confere as citações). Compliance e Aderência nunca passam por LLM, nem como segunda
opinião ([ADR 0035](adr/0035-qualidade-pelo-jev-depois-do-deterministico.md),
[ADR 0036](adr/0036-fidelidade-a-ata-por-llm-que-cita-e-o-codigo-confere.md),
[ADR 0037](adr/0037-judge-transversal-removido-jev-sempre-ligado-sem-sambanova.md)).

O Laudo tem três destinos, não dois: aprovado, reprovado com correção possível, e reprovado para
revisão humana. O motivo de reprovação é valor enumerado, não texto livre — é o que permite contar
reprovação por tipo no relatório final.

## A interface

React + Vite + Tailwind sobre FastAPI, com cliente TypeScript gerado do OpenAPI
([ADR 0005](adr/0005-interface-em-react-vite-sobre-fastapi.md)), lendo do disco — o mesmo arquivo
que o pytest lê e que o relatório cita. Desde o [ADR 0028](adr/0028-interface-em-seis-guias-no-padrao-do-biosites.md)
ela é uma ferramenta de produção de conteúdo, no padrão visual do editor do biosites, em seis guias:

- **Ingestão**: as notícias (Atas) de cada origem, só as dos últimos 30 dias; a pessoa marca até 3 e
  confirma com ATUALIZAR. Importar documento e buscar notícias novas ficam aqui. A busca consulta
  Copom, CVM, BCB (relatórios e resoluções) e B3 e, com mais de 2 documentos novos, pede o período a
  baixar ([ADR 0029](adr/0029-origens-de-noticias-e-busca-em-duas-etapas.md)).
- **Texto analítico**, **Carrossel** e **Vídeo**: cada uma confirma as notícias, pergunta as
  audiências e pede ao servidor uma Saída com o seu Formato. O texto ganha quatro formatos de
  apresentação (e-mail, newsletter, site, artigo) e um editor; o carrossel, a escolha de composição,
  paleta e ícones, a prévia num celular de feed e a exportação em PNG; o vídeo, os estilos de
  narração e o prompt para a ferramenta de avatar. Em todas o Laudo aparece em barras horizontais
  com os Limiares marcados.
- **Histórico** e **Configurações** (modo Demo ou Real, nome do avatar e o que o sistema liga e
  desliga: Jev, checador de fidelidade, limite de requisições, rodadas de correção, modelos).

A geração roda em segundo plano na API, um job por vez
([ADR 0017](adr/0017-api-dispara-a-geracao-em-segundo-plano.md)); fora do Copom a Saída é "não
calibrada" ([ADR 0018](adr/0018-origens-e-categoria-da-ata.md)); a Visão unida junta de duas a
cinco Atas com as Âncoras prefixadas por parte
([ADR 0019](adr/0019-visao-unida-com-chaves-de-ancora-prefixadas.md)) e, na tela, é o que acontece
quando a pessoa guarda mais de uma notícia.

O que o servidor já faz e a tela deixou de mostrar nesta versão: a Decisão humana (aprovar ou
reprovar Célula, com a regra de que a Célula com Recomendação não pode ser aprovada), o Pacote de
publicação, as Âncoras ao lado do conteúdo e o detalhe do Laudo por métrica. As rotas e os testes
continuam; o Compliance segue sendo métrica do Laudo, não da tela.

## Parâmetros ainda não fixados

Número de slides do Carrossel e comprimento do Texto analítico por Audiência não estão decididos
aqui (a duração do Roteiro é escolha da pessoa: ADR 0021). São conhecimento de domínio da dona do Avaliador e saem da
Calibração (H2), junto com os Limiares.

## O que este diagrama não mostra

Prioridade de corte sob atraso e a divisão de dono por módulo estão no CLAUDE.md. Cada ideia de
inovação que entrou ou ficou de fora já virou ou atualizou um ADR — não há registro de triagem
separado dos ADRs.
