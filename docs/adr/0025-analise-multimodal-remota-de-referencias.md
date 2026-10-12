# 0025 — Análise multimodal remota de referências

## Status

Aceita.

## Contexto

A biblioteca já guarda metadados e padrões estruturais, mas ainda não observa os pixels de uma
referência autorizada. Um modelo local adicionaria instalação, consumo de hardware e operação que
não são necessários para o projeto. O Gemini já está integrado e aceita imagem no contrato comum
de provedores.

## Decisão

A análise multimodal usa o Gemini configurado no ambiente. Não há Ollama nem modelo local. Grok
não é adicionado nesta fase porque exigiria outro conector e o caminho existente já atende ao
aceite.

A interface aceita PNG, JPEG ou WebP de até 10 MB. O servidor valida dimensões, limita a 24 milhões
de pixels, corrige a orientação, reduz o maior lado para 1600 px, remove metadados e persiste apenas
um PNG normalizado em `data/execucoes/referencias-visuais/`.

O provedor recebe a imagem e devolve `AnaliseVisualReferencia` no schema já usado pela biblioteca:
posição e proeminência do título, densidade, uso de imagem, fundo, elementos visuais e estrutura do
conteúdo. Ele não transcreve texto, marcas ou números. Trocar a imagem revoga a aprovação anterior;
um humano precisa revisar e aprovar de novo.

## Migração e rollback

A tabela `referencias_visuais` recebe, por expansão idempotente, colunas opcionais para arquivo,
estado, provedor, mensagem e data da análise. Nenhuma coluna antiga é alterada ou removida. Um
binário anterior continua lendo e escrevendo seus campos conhecidos; o rollback consiste em voltar
o código, deixando as colunas extras inertes. Não há contração destrutiva implícita.

## Falhas

Sem credencial do Gemini, com resposta inválida ou falha de rede, a imagem permanece salva e a
referência continua editável e revisável manualmente. O estado registra o erro sem impedir geração,
direção de arte ou renderização.
