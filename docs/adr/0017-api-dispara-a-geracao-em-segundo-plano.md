# A API dispara a geração em segundo plano, um job por vez

Até aqui a API só lia do disco. O docstring de `src/suno/api/app.py` diz que `executar` e
`montar_pacote` são comando de terminal e nunca uma rota. O painel novo (spec em
`legacy/docs/superpowers/specs/2026-10-09-front-suno-design.md`) muda isso: a pessoa marca quais
Células quer e a interface precisa iniciar a geração, acompanhar e registrar o resultado.

Decidimos que a API **inicia o pipeline em segundo plano** por `POST /api/execucoes`, grava o
andamento em `andamento.json` ao lado de `execucao.json` e roda **um job por vez**. Os demais
ficam em fila. No boot do servidor, um job que ficou "gerando" vira "interrompida".

O disco continua sendo a única fonte de verdade: a interface lê o mesmo `execucao.json` que o
pytest lê e o relatório cita ([ADR 0006](0006-atas-do-copom-como-documento-fonte-principal.md)).

## Por que um job por vez

O tier gratuito dos provedores tem cota ([ADR 0007](0007-roteador-de-provedores-distingue-tipo-de-429.md)).
Dois jobs juntos multiplicam os 429 sem ganho: as Células de uma Saída já geram em paralelo
dentro do job.

## Alternativas recusadas

- **Fila externa (Celery, Redis).** Infraestrutura demais para um case de 2 pessoas em 2 semanas.
- **Subprocesso do CLI por geração.** Duplicaria o estado e dificultaria o andamento por Célula.
- **Manter só o terminal.** Não atende a quem precisa escolher e gerar pela interface.

## Consequências

A demo continua sem rede: o provedor falso responde por rótulo (`celula:<aud>:<fmt>:<rodada>`) e
só existe para as Atas que têm `data/respostas_prontas/<id>.json`, hoje só o Copom 280. O modo
Real gasta cota gratuita. A suíte de testes cobre a fila e o andamento sem rede.

## Como ficou (Fase 2)

- `POST /api/execucoes` valida o pedido (Ata existente, de 1 a 9 posições sem repetição, nome de até
  120 caracteres, Demo só com `data/respostas_prontas/<ata>.json`, Real só com chave e modelo no
  ambiente), grava `andamento.json` em `na_fila` e responde 202. Quem decide recusar é o
  `Gerenciador` (`src/suno/api/geracao.py`), não a rota.
- O `Gerenciador` tem uma fila e uma thread que sobe quando há trabalho e some quando a fila
  esvazia. Cada job chama `executar` com os avisos de andamento: a **fase** (`extraindo_ancoras`,
  `gerando_celulas`, `avaliando_matriz`, `gravando`) e a **etapa de cada Célula** (`aguardando`,
  `gerando`, `corrigindo`, `aprovada`, `revisao_humana`, com a rodada).
- `andamento.json` é gravado por arquivo temporário e troca. Enquanto o job é desta vida do servidor,
  a leitura vem da memória: nenhuma leitura vê metade do arquivo.
- Estados do job: `na_fila`, `gerando`, `concluida`, `interrompida` (o servidor reiniciou) e `falhou`
  (a exceção, já sem credencial, fica em `erro`). Falha de um job não trava a fila.
- `GET /api/execucoes` e `.../resumo` enxergam também a Saída que ainda não tem `execucao.json`.
- A Matriz deixa de ser sempre de nove: `Execucao.pedido` guarda as posições. O ciclo transversal
  (avaliação da Matriz e Judge) só roda com duas ou mais Células, e uma Célula citada pelo Judge fora do
  pedido é ignorada.
- O **Pacote de publicação** também sai por rota (`POST .../pacotes/montar`), em outra thread e uma montagem
  por Saída por vez. A rota confere antes o que `montar_pacote` apagaria (Matriz sem aprovação do ciclo
  transversal) e recusa com 409; o vídeo do Roteiro continua no terminal ([ADR 0004](0004-renderizacao-de-video-fora-do-grafo.md)).
