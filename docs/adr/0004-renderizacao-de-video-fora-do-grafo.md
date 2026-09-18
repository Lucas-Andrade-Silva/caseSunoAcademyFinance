# A renderização de vídeo roda fora do grafo

O enunciado deixa a geração de vídeo com avatar fora do escopo; nós decidimos entregá-la
como extensão. Ela roda como **job fora de banda** que consome roteiros já aprovados
pelo Avaliador, nunca como nó do grafo.

A razão é assimetria de risco. O vídeo demonstrativo é critério eliminatório do case, e
renderização de vídeo falha de formas criativas e demoradas. Dentro do grafo, cada falha
de render vira falha do entregável que vale nota. Fora dele, o vídeo é um *consumidor*
do pipeline: se quebrar na véspera, os seis entregáveis continuam de pé e a demo usa um
mp4 já renderizado.

## Consequências

O Gerador termina no roteiro. O que existe depois disso — narração, composição, legenda,
lip-sync — vive atrás da sua própria interface e pode ser trocado inteiro sem tocar no
grafo. Isso importa porque o caminho de render ainda não está fechado: a pesquisa aponta
composição determinística em CPU como caminho principal e talking-head com GPU como
alternativa, e a escolha entre os dois não deve custar uma refatoração do pipeline.

Nenhum LLM olha o mp4. O Avaliador julgou o roteiro, em texto, antes de qualquer render existir; o
vídeo pronto passa só por checagem determinística de duração, proporção e presença de áudio, e
quem assiste antes de publicar é uma pessoa. Juiz de visão por amostragem de quadros foi
considerado e recusado ([ADR 0014](0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md)):
quadro amostrado não mostra movimento nem sincronia, que é onde vídeo falha.

O mp4 gerado é um artefato só, em 9:16, com dois destinos: a galeria da aplicação web e
o pacote de publicação que um humano sobe nas redes. Gerar um vídeo "para o app" e outro
"para as redes" é o erro a evitar.
