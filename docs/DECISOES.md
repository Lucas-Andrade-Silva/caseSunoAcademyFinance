# Decisões de arquitetura

Este arquivo resume as 38 decisões de arquitetura do projeto, uma entrada por ADR, com o que foi decidido e por quê. Os textos completos de cada ADR saíram do repositório e seguem no histórico do Git (`git show 24a5b3b:docs/adr/`).

## Onde o enunciado sugere outro caminho

| Ponto | O enunciado sugere | Adotado | ADR |
|---|---|---|---|
| Legibilidade | "Flesch-Kincaid adaptado ao português", que é outra fórmula, de nível de escolaridade | Flesch-BR (Martins et al., 1996) implementado no projeto; `textstat` rejeitada por calcular português com os coeficientes do inglês | 0002 |
| Avaliação | DeepEval ou Ragas | `pydantic-evals`, sem serviço externo nem telemetria, com casos em YAML versionados e execução no pytest | 0003 |
| Vídeo | Vídeo com avatar fora do escopo | Entregue como extensão, num job fora do grafo que consome Roteiros já aprovados | 0004 |
| Interface | Streamlit, Gradio ou FastAPI + React | FastAPI servindo SPA em React + Vite + Tailwind, como PWA, com cliente gerado do OpenAPI | 0005 |
| Orquestração | Pipeline multiagente / workflow com estado (LangGraph ou Pydantic AI) | Pipeline fixo de chamadas estruturadas, sem tool calling, LangGraph nem MCP; os papéis são prompts especializados num fluxo que o código orquestra | 0010, 0015 |

## Decisões

### 0001 — Gerador e Avaliador como módulos separados · Em vigor
Dois módulos ligados só pelo contrato `(Conteúdo, Âncora[], Audiência) → Laudo`; o Ciclo de correção é o Gerador consumindo o Laudo. O Avaliador não depende de LLM nem de rede, e o juiz por LLM é a exceção deliberada, isolada atrás de interface própria. Por quê: o Avaliador é o diferencial do case, testável no pytest e em CI desde o primeiro dia, e a costura divide o trabalho da dupla (a pessoa de mercado é dona do Avaliador). Os ADRs 0035 e 0036 usam essa exceção: Qualidade e Fidelidade rodam por LLM depois das medidas determinísticas.

### 0002 — Flesch-BR implementado no projeto · Em vigor, com mudanças
`textstat` rejeitada: sem `pt`, cai em silêncio no inglês (206.835 no lugar de 248.835) e subconta sílabas, com erro de 20,7 pontos no teste. Fórmula de Martins et al. (1996), `248.835 − 1.015×(palavras/frases) − 84.6×(sílabas/palavras)`, com Limiares iniciante ≥ 50, intermediário 25–50 e avançado < 25, confirmados contra a Calibração (~30 Células, Kappa alvo 0,6–0,8); o Gerador pede um alvo interno com overshoot calibrado. Por quê: a ferramenta padrão erra sem avisar. Notas no próprio ADR: em 18/09/2026 o silabador de Silva (2011) foi reimplementado em `src/suno/avaliador/silabas.py` para não herdar a GPL-3.0; em 16/10/2026 o título do slide virou frase própria e todo número passou a contar como palavra de duas sílabas, sem mudar os Limiares.

### 0003 — pydantic-evals no lugar de DeepEval e Ragas · Em vigor
DeepEval recusado por telemetria ligada por padrão (com IP público), histórico de sequestrar o `TracerProvider` do OpenTelemetry e painel grátis de 5 execuções por semana. Ragas recusado por oito meses sem release, APIs removidas na 0.4 e métricas voltadas a RAG. Adotado `pydantic-evals`: sem serviço externo, casos em YAML no repositório, execução no pytest. Por quê: o conjunto de casos versionado é a reprodutibilidade que o Entregável 6 pede, e o schema do resultado fica sob controle do projeto. Métrica útil dos outros entra só como biblioteca, dentro de um avaliador nosso.

### 0004 — Renderização de vídeo fora do grafo · Em vigor
O vídeo roda como job fora de banda que consome Roteiros aprovados; o Gerador termina no Roteiro. O mp4 é um só, em 9:16, para a galeria e para o Pacote de publicação. Nenhum LLM olha o mp4: só checagem determinística de duração, proporção e áudio, e uma pessoa assiste antes de publicar. Por quê: o vídeo demonstrativo é eliminatório e render falha de formas demoradas; fora do grafo, uma falha não derruba os seis entregáveis.

### 0005 — Interface em React + Vite sobre FastAPI · Em vigor
FastAPI serve uma SPA em React + Vite + Tailwind, entregue como PWA, com o cliente gerado do OpenAPI. Streamlit recusado por ter cara de protótipo; Next.js por trazer um segundo servidor em outra linguagem; app nativo por não cumprir a "aplicação web" do Entregável 4. A interface é construída por último. Por quê: gerar o contrato elimina a divergência silenciosa entre cliente e servidor. Custa 2 a 3 dias-pessoa, tirados da extensão de vídeo. O ADR 0028 redesenhou a tela em seis guias sobre a mesma pilha.

### 0006 — Atas do Copom como documento-fonte principal · Em vigor
Atas do Copom pela API não documentada do site do BCB; CVM como fonte secundária; B3 descartada como origem de documentos (anti-bot, e ela só indexa o que está na CVM). As Atas da demo ficam versionadas no repositório e buscar no BCB é um comando separado. Por quê: são densas, públicas, oito por ano, em PDF com texto e com par oficial em inglês, e a apresentação nunca depende de rede. Os ADRs 0018 e 0029 ampliaram as origens; os ofícios da B3 entraram no 0029 porque a página responde a cliente HTTP comum.

### 0007 — Roteador de provedores distingue o tipo de 429 · Em vigor, com mudanças
Interface única de provedor (nenhum módulo importa SDK direto), fila ordenada de fallback, leitura do erro de cada provedor para decidir entre esperar (cota por minuto, com a espera sugerida) e trocar (cota diária), e reaplicação de schema e tools ao trocar de cliente. A lista de modelos gratuitos é configuração; um LLM falso roteirizado cobre a troca em teste. Por quê: o orçamento é R$ 0, em tiers gratuitos com cotas e recusas diferentes. Mudanças: a reserva Cerebras foi trocada pelo SambaNova em 15/09/2026 (tier gratuito encerrado em 17/08/2026), e o SambaNova saiu pelo ADR 0037 (HTTP 402 em 14/10/2026); hoje a fila é Gemini → Groq.

### 0008 — Comitê de juízes-LLM como camada opcional · Removida
Um juiz por dimensão subjetiva (tom, clareza, coerência), dois juízes em provedores diferentes do Gerador, cegos ao modelo, só para Texto analítico e Carrossel, só informativo e desligado na demo; discordância virava `revisão humana`. Compliance e Aderência nunca passavam por LLM. Por quê: nota única esconde qual dimensão falhou, e juiz no mesmo provedor do gerador tem autopreferência. Removido pelo ADR 0037 em 15/10/2026: sem o SambaNova não havia dois juízes fora do gerador, e a Qualidade (0035) e a Fidelidade (0036) ocuparam o lugar.

### 0009 — Imagens geradas pelo sistema, nunca raspadas · Em vigor, com mudanças
Toda imagem do Pacote seria gerada pelo sistema a partir das Âncoras, em template determinístico (matplotlib para o gráfico, Pillow para a composição, PNG), com 1080×1350 (4:5) em todo slide e geração por IA fora do caminho crítico; WeasyPrint recusada. Por quê: reusar foto de imprensa em rede social é a maior exposição a direito autoral, e o Instagram corta o carrossel pela proporção da primeira imagem. Mudanças: o render passou a HTML/CSS + Puppeteer no ADR 0020 (Pillow como reserva), e a proibição de foto de terceiros foi substituída pelo ADR 0031; continuam o 1080×1350 e a regra de não raspar notícia.

### 0010 — Gerador sem agente, sem tools e sem MCP · Em vigor
O Gerador é uma sequência fixa de chamadas estruturadas (extrai Âncoras → adapta por Audiência → sintetiza por Formato) atrás do roteador do ADR 0007, sem tool calling, framework de agente ou MCP. Por quê: não há dúvida sobre o próximo passo (a Ata já está toda disponível e as nove Células são independentes e rodam em paralelo), e um loop ReAct é sequencial por natureza. Uma etapa que precise de decisão dinâmica entra como exceção isolada e justificada por escrito.

### 0011 — Âncoras numéricas citadas, nunca reescritas · Em vigor
Antes da Matriz, uma vez por Ata, o sistema extrai uma tabela de Âncoras numéricas (Selic, variação em pontos base, IPCA, placar, data da reunião e da próxima), cada uma com valor, unidade e trecho literal. O Gerador preenche moldes e o Avaliador confere cada número por igualdade exata; número fora da tabela reprova. A tabela é a única entrada de número para texto, legenda e gráfico. Por quê: grounding por citação é a correção mais citada para alucinação numérica. Números por extenso ou relativos ficam fora da tabela.

### 0012 — Recomendação detectada por padrão sintático · Em vigor
Duas camadas determinísticas: Léxico organizado em pode e não pode, e padrões sintáticos sobre o POS do spaCy `pt_core_news_sm` (sujeito de segunda pessoa + modal de obrigação + verbo de ação financeira). Nada passa por LLM. Um canary set adversarial versionado em `data/` roda a cada mudança de Léxico, padrão ou Limiar; a allowlist de moldes foi recusada para o prazo. Por quê: Recomendação escorrega por personalização, não por vocabulário, e um veredito que reprova não pode mudar entre duas execuções.

### 0013 — Teto no Ciclo de correção e fila de revisão humana · Em vigor, com mudanças
Teto de duas rodadas; o feedback é o valor medido ("Flesch-BR medido 47,2; o Limiar da Audiência Iniciante é 50"), não instrução genérica; o que ainda reprova vai à fila de revisão humana com Laudo e histórico. Falha de extração é motivo próprio, não aciona o Ciclo e vai direto à fila; o motivo de reprovação é enumerado. Por quê: sem teto, uma Célula teimosa consome a cota, e o ganho se concentra na primeira rodada. Mudança (nota de 16/10/2026): o teto agora vem de `rodadas_de_correcao`, padrão 4, de 0 a 10, editável na aba Configurações ou por `SUNO_RODADAS`.

### 0014 — Avaliação visual própria do Pacote de publicação · Em vigor
Duas camadas: a determinística, sempre ligada (estouro de caixa, contraste, 1080×1350 e 9:16, número da imagem contra as Âncoras, duração e áudio do vídeo), cuja falha pede refazer o render; e um Eval multimodal holístico só para o Carrossel, em folha de contato (três chamadas por Ata), que nunca julga compliance. O resultado vai ao humano no H5, não entra no Laudo nem reprova a Célula; o vídeo não vai a juiz de visão. Por quê: texto aprovado não garante imagem legível, e reescrever texto não conserta render.

### 0015 — Papéis especializados em fluxo determinístico · Em vigor, com mudanças
`AgenteCurador` monta o `DossieCurado`; três `AgenteGeradorPersona`, um por Audiência, recebem o mesmo dossiê; o código decide Formatos, posições, ordem e armazenamento; `avaliar_matriz` confere a Matriz; `SelecaoCuradoria` opera em modo `unida` ou `separada`. "Agente" nomeia papel e prompt, sem escolher etapa nem usar ferramentas. Por quê: as personas partem do mesmo núcleo factual e o custo fica previsível, sem contrariar o ADR 0010. Mudança: o avaliador transversal (LLM Judge) foi removido pelo ADR 0037.

### 0016 — LLM Judge transversal com retorno seletivo · Revogada
Um Judge rodava depois da aprovação determinística das nove Células, com schema `aprovado`, `corrigivel` ou `grave`, regenerava só as Células afetadas, tinha teto de duas correções transversais e mandava para H4 no esgotamento; o Pacote só nascia com o ciclo aprovado. Por quê: repetição e contradição entre Células não cabem em métrica de uma Célula só. Revogado pelo ADR 0037 em 15/10/2026: o Judge quase nunca chegava a rodar.

### 0017 — API dispara a geração em segundo plano · Em vigor
`POST /api/execucoes` valida o pedido (1 a 9 posições, nome de até 120 caracteres, Demo só com respostas prontas, Real só com chave e modelo), grava `andamento.json` e responde 202; o `Gerenciador` roda um job por vez, em fila, com estados `na_fila`, `gerando`, `concluida`, `interrompida` e `falhou`. O Pacote também sai por rota; o disco continua a fonte de verdade. Por quê: dois jobs juntos multiplicam os 429, e Celery/Redis ou subprocesso do CLI seriam demais para o case. O texto ainda cita o Judge e o ciclo transversal, removidos depois pelo ADR 0037.

### 0018 — Origens e categoria da Ata · Em vigor, com mudanças
Toda Ata tem `categoria` (`copom`, `comunicado_relevante`, `release`, `importada`), que escolhe as Âncoras essenciais: o Copom mantém `selic_decidida`, `data_reuniao` e `placar_votacao`; as demais usam `data_do_comunicado` e `numero_principal`, por regra fixa. Fora do Copom a Saída leva o selo "não calibrado", e Limiares e Léxico continuam os do Copom; `avaliar` ganhou `chaves_essenciais` opcional. Por quê: o Avaliador só foi calibrado com Atas do Copom. Mudança: no ADR 0034, uma afirmação central conferida contra o texto pode substituir o `numero_principal`.

### 0019 — Visão unida com chaves de Âncora prefixadas · Em vigor
A Visão unida é uma Ata composta de categoria `unida` (de 2 a 5 Atas, identificador `uniao-<hash>`), com extração por parte e chaves prefixadas (`a1_selic_decidida`, `a2_numero_principal`). O conjunto essencial genérico vale por parte; roda só no modo Real e é sempre não calibrada. Por quê: evita colisão de chaves sem mudar Avaliador, Ciclo de correção nem extração. O ADR atribui ao Judge transversal apontar números de duas Atas misturados numa frase; o Judge saiu no ADR 0037.

### 0020 — Carrossel em templates HTML renderizados pelo Puppeteer · Em vigor
O Gemini gera só estrutura e texto de cada Slide (`tipo` hook, ponto, citacao ou cta; `titulo`, `corpo`, `destaque`, `dado`); a direção de arte escolhe uma de seis composições, e o Puppeteer (`render/render.mjs`) captura o template em PNG. Imagem por IA não desenha slide. Paleta do anexo do case: `#FF0000`, `#AF0404`, `#414141`, `#252525` e `#FFFFFF`. O Pillow fica como reserva (`SUNO_RENDER=pillow`) e é o que o pytest usa. Por quê: consistência pixel a pixel é difícil com imagem pura. Ampliado pelo ADR 0030 (famílias visuais), com fotos pelo ADR 0031.

### 0021 — Direção de cena do Roteiro em catálogo fechado · Em vigor
Cada bloco do Roteiro ganha campos de direção (`cena`, `icone`, `entrada`, `efeito`, sons e outros) escolhidos por nome de um catálogo em `suno.dominio`; nenhum texto novo além de `tela`. A duração é escolhida entre 40 s, 1 min, 1 min 30, 2 min e 3 min; `cronometrar` recalcula os tempos a 2,5 palavras por segundo e `medir_video` aceita de 75% a 125% do alvo. Do Roteiro aprovado saem `plano.json` e `plano.md` para o gerador de avatar. Por quê: texto livre não dá para validar, e o LLM erra a conta de tempo sempre para mais.

### 0022 — Histórico de layouts em SQLite · Em vigor
O histórico fica em `data/execucoes/suno.sqlite3`, com o `sqlite3` da biblioteca padrão: um registro por slide (execução, audiência e índice únicos), remontagem substitui os registros numa transação, e a seleção ignora a própria execução para continuar determinística. Supabase foi recusado. Por quê: sem serviço externo, credencial nem rede, num projeto que roda local.

### 0023 — Referências visuais internas e estruturadas · Em vigor
A biblioteca nasce com seis referências originais da Suno, uma por composição, com análise estrutural explícita, na tabela `referencias_visuais` do mesmo SQLite, semeadas com `INSERT OR IGNORE`. Referência manual nasce não aprovada, e nenhuma imagem externa é copiada ou baixada; as referências nunca vão ao Gerador de texto. Por quê: usar post de terceiro como semente exigiria verificar licença, e a geração não pode depender de Instagram, rede ou Ollama.

### 0024 — Diretor de Arte IA com fallback determinístico · Em vigor
Uma chamada estruturada por carrossel escolhe, por slide, composição, referência, intensidade e justificativa; o código valida (uma escolha por slide, composição compatível, referência aprovada da composição, sem repetição consecutiva quando há alternativa). Qualquer falha cai no seletor determinístico, e o `pacote.json` registra de onde veio o plano. Por quê: melhora a coerência editorial sem deixar a IA mexer em texto, números, CSS ou templates. O ADR 0030 restringe o Diretor à família escolhida.

### 0025 — Análise multimodal remota de referências · Em vigor
A análise usa o Gemini do ambiente, sem Ollama ou modelo local, e sem Grok nesta fase. A interface aceita PNG, JPEG ou WebP de até 10 MB; o servidor limita a 24 milhões de pixels, reduz o maior lado a 1600 px, remove metadados e grava um PNG normalizado. O provedor devolve `AnaliseVisualReferencia` sem transcrever texto, marca ou número, e trocar a imagem revoga a aprovação. A migração só acrescenta colunas opcionais, e falha não impede a geração. Por quê: um modelo local traria instalação e hardware sem necessidade.

### 0026 — Coleta pública opcional de referências · Em vigor
Adaptador isolado de Instaloader, sem login nem download de mídia, como dependência opcional (`uv sync --extra coleta`); janelas de 30, 60 ou 90 dias, até 20 carrosséis por perfil e filtro de setor financeiro determinístico, sem LLM. Guarda só URL, capa, legenda resumida, data e as métricas que o provedor retornou. O candidato não orienta o Diretor de Arte nem entra sozinho na biblioteca: um humano o cadastra. Por quê: a geração fica independente do Instagram, sem contornar autenticação nem bloqueio.

### 0027 — Eval visual auxilia o H5 e aprovação humana fecha o ciclo · Em vigor
Com provedor multimodal configurado, o Eval avalia a folha de contato do Carrossel numa chamada (legibilidade, coerência visual, aderência à marca, se parece quebrado); o parecer é consultivo e nunca aprova nem reprova. A aprovação humana grava uma linha idempotente na tabela nova `feedback_visual_pacotes`, e o Diretor de Arte recebe só contagens agregadas, como preferência fraca. Por quê: separar o parecer da máquina da aprovação humana, com aprendizado contextual e sem ajuste de pesos do modelo.

### 0028 — Interface em seis guias no padrão do biosites · Em vigor
Seis guias (Ingestão, Texto analítico, Carrossel, Vídeo, Histórico e Configurações); cada guia de conteúdo pede uma Saída por `POST /api/execucoes`. Só front: o que o servidor não tem roda no navegador, em `localStorage`. Janela de 30 dias, seleção de até 3 notícias por sessão, pré-carga e texto secundário a 4,5:1. Decisão humana, Pacote e Âncoras saem da tela, mas as rotas ficam. Por quê: quem usa o produto quer produzir conteúdo, não revisar. Sem rede, a Ingestão esvazia com o tempo (`JANELA_EM_DIAS`).

### 0029 — Seis origens de notícias e busca em duas etapas · Em vigor
Um coletor por origem, com `listar` e `baixar`: Copom, Relatório de Inflação e de Estabilidade Financeira (API do BCB), Resoluções do CMN e do BCB, CVM (Fatos Relevantes, DFP, ITR e Formulários) e ofícios e comunicados da B3. `POST /api/fontes/atualizar` lista os últimos 30 dias; acima de 2 documentos pede um período, com teto de 40 por download por causa do `Crawl-Delay` de 10 s da CVM. As origens novas reaproveitam `CategoriaDaAta` e são não calibradas. Por quê: o produto precisa de gêneros diferentes de documento. Limite aberto: DFP com mais de 300 mil caracteres.

### 0030 — Famílias visuais do Carrossel · Em vigor
Família visual é o conjunto de layouts de uma conta (`noticia`, `explicativo`, `jornal`, `dados`, `asset`, `suno_escuro`), e um carrossel usa uma só. Cada família se descreve em `familia.json` e marca o conteúdo com `data-slot`; a escolha automática usa `noticia`, `explicativo`, `jornal` e `dados` (`asset` só por pedido; seu miolo `asset_texto` foi recriado no estilo da capa, já que o post real só tem capa e aviso), e o texto encolhe de 2 em 2 px até 26 px. Só no motor de navegador, sem campo de texto novo além de `Slide.imagem`; 17 de 20 layouts recriados. Por quê: os cinco carrosséis reais da Suno têm outro visual que os seis layouts inventados. Ampliado pelo ADR 0038.

### 0031 — Fotos reais e licenciadas nos slides · Em vigor, com mudanças
Os slides ganham foto real do assunto: fonte única Wikimedia Commons, só CC0, domínio público, CC BY e CC BY-SA; fotos versionadas em `data/imagens/` com `indice.json` e rede só por comando explícito; o Gerador sugere só o assunto em `Slide.imagem`; o juiz de visão confere a relevância; crédito na legenda; slide sem foto degrada (`sem-imagem`). Substitui a proibição de foto de terceiros do ADR 0009. Por quê: os carrosséis reais da Suno têm foto do assunto. Mudanças: fonte e licença (itens 1 e 5) substituídas pelo ADR 0032, e o ADR 0033 faz o juiz de visão decidir só a dúvida.

### 0032 — Fotos da web pelo Bing, sem verificar licença (MVP) · Em vigor, com mudanças
Fonte Bing Imagens por HTTP, sem chave (`ClienteWeb`), pedindo imagem grande e tirando bancos pagos; nenhuma licença verificada, e o crédito diz `licença não verificada (MVP)`; o juiz de visão rejeita marca d'água, banner, captura de tela e homônimo; largura mínima de 800 px; até quatro novas tentativas; o Commons sai do código. Por quê: o Commons cobria mal finanças, e o dono do projeto assumiu o risco autoral (13/10/2026) num MVP que não vai para produção; para publicar de verdade, este ADR tem de ser revertido. Mudança: fonte (item 1) e papel do juiz (item 3) seguem o ADR 0033.

### 0033 — Busca de imagens própria do mercado, juiz só na dúvida · Em vigor
Catálogo de assuntos visuais em `src/suno/imagens/assuntos.json` (cerca de 75 assuntos, com consultas, `exigir` e `proibidas`; sede e depois logo para empresa e instituição), mantido pela pessoa de mercado. Pontuação por texto sem LLM: 5 pontos ou mais aprova direto (`validada_por = "texto"`), palavra proibida descarta, o resto é dúvida, que o juiz de visão decide até três vezes por assunto. Serper (Google Imagens, `SERPER_API_KEY`) é a fonte, com o Bing de reserva; foto sem acerto não ocupa slide, e foto achada é realocada ou descartada junto com o crédito. Por quê: "B3" trazia a vitamina B3, o juiz gastava cota à toa e o Bing serve imagens sem relação a robôs.

### 0034 — Ata sem número gera conteúdo qualitativo · Em vigor
Fora do Copom, a data sai dos metadados quando falta no texto, e o `numero_principal` pode ser satisfeito por uma Âncora textual com trecho: o LLM devolve de 1 a 5 afirmações centrais e o código descarta as que não têm trecho literal na Ata. O Gerador recebe `INSTRUCAO_SEM_NUMERO`, e a API só recusa texto com menos de 200 caracteres e sem número. No Copom nada muda. Por quê: comunicados reais (ofícios, resoluções, fatos relevantes) não têm número e eram recusados. É uma proposta para a dona do Avaliador validar.

### 0035 — Qualidade pelo Jev depois do determinístico · Em vigor, com mudanças
Depois que as cinco medidas aprovam, uma chamada ao Jev (TypeSafe AI) faz quatro perguntas (desenvolvimento, completude, clareza e tom) nos três Formatos; a Medida é a menor nota, de 0 a 1, e abaixo do Limiar (60%, não calibrado) a Célula volta ao Gerador com motivo `qualidade`. Falha do Jev nunca reprova; o endereço vem de `JEV_URL` e `JEV_API_KEY`. Por quê: as medidas determinísticas não pegam ideia jogada em fatos soltos, texto cortado ou frase que não se lê de primeira. Mudança: pelo ADR 0037, o Jev fica sempre ligado (só `SUNO_JEV=0` ou `--sem-jev` desligam), e o Comitê que ele complementava foi removido.

### 0036 — Fidelidade à Ata por LLM que cita, conferida pelo código · Em vigor, com mudanças
Um LLM por Célula, com a Ata inteira, aponta `sem_suporte`, `distorce` ou `contradiz` copiando o trecho literal; o código confere a citação e descarta a que não existe ou tem menos de 15 caracteres. Só `distorce` e `contradiz` reprovam (motivo `fidelidade`); `sem_suporte` só avisa. Roda por último, no Groq e depois no Gemini, e nunca reprova por falha. O ADR a fazia nascer desligada; hoje o código a liga por padrão (`SUNO_FIDELIDADE=0` ou `--sem-fidelidade` desligam). Por quê: o enunciado pede um "Factuality & Grounding Checker", e afirmação em prosa sem número escapa da Aderência. Na medição com 6 Células da Ata 281, nenhuma foi bloqueada.

### 0037 — Judge e Comitê removidos, Jev sempre ligado, sem SambaNova · Em vigor
Saem o LLM Judge transversal (revoga o ADR 0016) e o Comitê de dois juízes (ADR 0008); fica `avaliar_matriz`, sem LLM. O Jev vale ligado quando `SUNO_JEV` não está no ambiente, desde que haja `JEV_API_KEY`. O SambaNova sai de todas as filas, e o Groq vira a reserva do Gemini na geração. Por quê: o Judge julgou 4 vezes em 15 execuções com ciclo, o SambaNova voltou HTTP 402 em 14/10/2026, e Qualidade e Fidelidade cobrem por Célula o que o Judge prometia. Fica aberta a lacuna de contradição entre Células, e o Jev gasta créditos do plano Free da Netlify (300).

### 0038 — Paleta do editor recolore as famílias visuais · Em vigor
`suno.pacote.recolorir` troca as cores do CSS pelo papel de cada uma: as neutras deslizam entre `fundo` e `texto` conforme o fundo do Layout (`data-fundo-cor`), as vivas viram `destaque` e as escuras `apoio`; texto e foto não mudam. A paleta Suno mantém o original; as outras vão como `paleta=fundo,texto,destaque,apoio` e ficam em `Execucao.paleta_visual`, com prévias recoloridas servidas por duas rotas em `iframe`. Por quê: reescrever os 17 templates com variáveis ou mapear cada hexadecimal à mão não escala. A regra não garante contraste em todo par.
