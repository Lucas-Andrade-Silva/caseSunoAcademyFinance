# A API dispara a geração em segundo plano, um job por vez

Até aqui a API só lia do disco. O docstring de `src/suno/api/app.py` diz que `executar` e
`montar_pacote` são comando de terminal e nunca uma rota. O painel novo (spec em
`docs/superpowers/specs/2026-10-09-front-suno-design.md`) muda isso: a pessoa marca quais
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

Este ADR registra a decisão. A implementação do job entra na Fase 2 do plano do front; as
Fases 0 e 1 só acrescentam rotas de leitura e de decisão humana.
