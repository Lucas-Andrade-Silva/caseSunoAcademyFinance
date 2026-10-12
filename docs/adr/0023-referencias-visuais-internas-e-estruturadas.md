# 0023 — Referências visuais internas e estruturadas

## Status

Aceita.

## Contexto

A direção de arte precisa de ao menos uma referência para cada uma das seis composições iniciais.
Usar publicações de terceiros como sementes exigiria verificar licença e permissão para persistir
as imagens. Também não existe análise multimodal nesta fase, e a geração não pode depender de
Instagram, rede ou Ollama.

## Decisão

A biblioteca nasce com seis referências originais da própria Suno, focadas em finanças e
investimentos: editorial, minimalista, infográfico, comparativo, estatístico e narrativo.

Cada referência contém tema, descrição, instrução de design e uma análise estrutural explícita:
posição e proeminência do título, densidade textual, uso de imagem, tipo de fundo, elementos
visuais e estrutura do conteúdo. Os registros são aprovados por padrão e persistidos na tabela
`referencias_visuais` do mesmo `data/execucoes/suno.sqlite3` usado pelo histórico de layouts.

A semeadura usa `INSERT OR IGNORE`, portanto não desfaz uma curadoria local posterior. A biblioteca
é configuração: depois de escolher a fonte, a pessoa seleciona na Curadoria uma das seis
composições e uma referência aprovada daquela família. Essa escolha fica na Saída e prevalece na
montagem do Carrossel sempre que o layout é compatível com o slide. A direção de arte grava o
identificador usado no manifesto e no `pacote.json`. A interface mostra miniaturas estruturais
feitas com os elementos visuais do próprio produto; nenhuma imagem externa é copiada.

Referências manuais podem ser cadastradas pela interface com metadados e uma URL ou descrição de
origem autorizada. Elas nascem não aprovadas. Aprovar inclui a referência no conjunto consultado
pela direção de arte; rejeitar a retira. A aplicação não baixa nem processa a imagem remota nesta
fase.

## Consequências

O sistema já possui uma base auditável e utilizável sem rede. As referências orientam o mecanismo
determinístico ou ao Diretor de Arte IA; nunca são enviadas ao Gerador de texto. Coleta do Instagram
e análise multimodal ficam para incrementos separados.
