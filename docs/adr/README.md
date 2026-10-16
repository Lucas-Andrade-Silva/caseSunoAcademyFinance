# Decisões de arquitetura (ADRs)

Cada arquivo registra uma decisão estrutural e o seu porquê. Um ADR não é apagado quando a
decisão muda: ganha uma nota no topo apontando o ADR que o substituiu, e fica como histórico.
Antes de propor mudar uma decisão, leia o ADR dela.

## Onde o enunciado sugere outro caminho

| Ponto | O enunciado sugere | Adotado | ADR |
|---|---|---|---|
| Legibilidade | `textstat` / "Flesch-Kincaid adaptado" | Flesch-BR implementado no projeto | [0002](0002-flesch-br-implementado-no-projeto.md) |
| Avaliação | DeepEval ou Ragas | `pydantic-evals` | [0003](0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md) |
| Vídeo | avatar sintético | composição determinística em CPU, fora do grafo | [0004](0004-renderizacao-de-video-fora-do-grafo.md) |
| Interface | Streamlit, FastAPI+React ou Gradio | React + Vite + Tailwind sobre FastAPI | [0005](0005-interface-em-react-vite-sobre-fastapi.md) |
| Orquestração | LangGraph ou Pydantic AI, multiagente | papéis fixos em fluxo determinístico, sem MCP | [0010](0010-gerador-nao-e-agente-com-tools-nem-usa-mcp.md), [0015](0015-papeis-especializados-em-fluxo-deterministico.md) |

## Índice

| ADR | Decisão | Estado |
|---|---|---|
| [0001](0001-gerador-e-avaliador-como-modulos-separados.md) | Gerador e Avaliador são módulos separados, ligados por um contrato | Em vigor |
| [0002](0002-flesch-br-implementado-no-projeto.md) | Flesch-BR implementado no projeto; `textstat` rejeitada | Em vigor |
| [0003](0003-pydantic-evals-no-lugar-de-deepeval-e-ragas.md) | `pydantic-evals`, não DeepEval nem Ragas | Em vigor |
| [0004](0004-renderizacao-de-video-fora-do-grafo.md) | Vídeo renderizado fora do grafo | Em vigor |
| [0005](0005-interface-em-react-vite-sobre-fastapi.md) | Interface em React + Vite sobre FastAPI | Em vigor |
| [0006](0006-atas-do-copom-como-documento-fonte-principal.md) | Atas do Copom como documento-fonte principal | Em vigor; ampliado por 0018 e 0029 |
| [0007](0007-roteador-de-provedores-distingue-tipo-de-429.md) | Roteador de provedores distingue o tipo de 429 | Em vigor; SambaNova removido por 0037 |
| [0008](0008-comite-de-juizes-llm-como-camada-opcional-do-avaliador.md) | Comitê de juízes-LLM opcional | **Removido** por 0037 |
| [0009](0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md) | Imagens do Pacote geradas pelo sistema | Render substituído por 0020; fotos, por 0031 |
| [0010](0010-gerador-nao-e-agente-com-tools-nem-usa-mcp.md) | Gerador é pipeline direto, não agente com tools nem MCP | Em vigor |
| [0011](0011-ancoras-numericas-sao-citadas-nunca-reescritas.md) | Âncoras numéricas citadas, nunca reescritas | Em vigor; Ata sem número em 0034 |
| [0012](0012-recomendacao-detectada-por-padrao-sintatico-nao-por-lista-de-palavras.md) | Recomendação detectada por padrão sintático | Em vigor |
| [0013](0013-teto-de-duas-rodadas-no-ciclo-de-correcao-e-fila-de-revisao-humana.md) | Teto no Ciclo de correção e fila de revisão humana | Em vigor; o teto virou configurável (padrão 4) |
| [0014](0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md) | Avaliação visual própria do Pacote, que não reprova a Célula | Em vigor |
| [0015](0015-papeis-especializados-em-fluxo-deterministico.md) | Papéis especializados em fluxo determinístico | Em vigor; o Judge saiu por 0037 |
| [0016](0016-llm-judge-transversal-com-retorno-seletivo.md) | LLM Judge transversal | **Revogado** por 0037 |
| [0017](0017-api-dispara-a-geracao-em-segundo-plano.md) | API dispara a geração em segundo plano, um job por vez | Em vigor |
| [0018](0018-origens-e-categoria-da-ata.md) | Origens e categoria da Ata; só o Copom é calibrado | Em vigor |
| [0019](0019-visao-unida-com-chaves-de-ancora-prefixadas.md) | Visão unida com chaves de Âncora prefixadas | Em vigor |
| [0020](0020-carrossel-em-templates-html-renderizados-pelo-puppeteer.md) | Carrossel em templates HTML renderizados pelo Puppeteer | Em vigor |
| [0021](0021-direcao-de-cena-do-roteiro-em-catalogo-fechado.md) | Direção de cena do Roteiro em catálogo fechado; duração escolhida | Em vigor |
| [0022](0022-historico-de-layouts-em-sqlite.md) | Histórico de layouts em SQLite | Em vigor |
| [0023](0023-referencias-visuais-internas-e-estruturadas.md) | Referências visuais internas e estruturadas | Em vigor |
| [0024](0024-diretor-de-arte-ia-com-fallback-deterministico.md) | Diretor de Arte IA com fallback determinístico | Em vigor |
| [0025](0025-analise-multimodal-remota-de-referencias.md) | Análise multimodal remota de referências | Em vigor |
| [0026](0026-coleta-publica-opcional-de-referencias.md) | Coleta pública opcional de referências | Em vigor |
| [0027](0027-eval-visual-e-feedback-humano.md) | Eval visual auxilia o H5; aprovação humana fecha o ciclo | Em vigor |
| [0028](0028-interface-em-seis-guias-no-padrao-do-biosites.md) | Interface em seis guias, no padrão do biosites | Em vigor |
| [0029](0029-origens-de-noticias-e-busca-em-duas-etapas.md) | Seis origens de notícias e busca em duas etapas | Em vigor |
| [0030](0030-familias-visuais-do-carrossel.md) | Famílias visuais recriadas dos posts reais da Suno | Em vigor; ampliado por 0038 |
| [0031](0031-fotos-reais-e-licenciadas-nos-slides.md) | Fotos reais nos slides | Fonte e licença substituídas por 0032 e 0033 |
| [0032](0032-fotos-da-web-pelo-bing-imagens-sem-verificar-licenca.md) | Fotos da web sem verificar licença (MVP) | Em vigor; fonte substituída por 0033 |
| [0033](0033-busca-de-imagens-propria-do-mercado-e-juiz-so-na-duvida.md) | Busca de imagens própria do mercado; juiz só na dúvida | Em vigor |
| [0034](0034-ata-sem-numero-gera-conteudo-qualitativo.md) | Ata sem número gera conteúdo qualitativo | Em vigor |
| [0035](0035-qualidade-pelo-jev-depois-do-deterministico.md) | Qualidade pelo Jev, depois do determinístico | Em vigor; sempre ligado por 0037 |
| [0036](0036-fidelidade-a-ata-por-llm-que-cita-e-o-codigo-confere.md) | Fidelidade à Ata: LLM cita, o código confere | Em vigor |
| [0037](0037-judge-transversal-removido-jev-sempre-ligado-sem-sambanova.md) | Judge e Comitê removidos; Jev sempre ligado; sem SambaNova | Em vigor |
| [0038](0038-paleta-recolore-as-familias-visuais.md) | Paleta do editor recolore as famílias visuais | Em vigor |
