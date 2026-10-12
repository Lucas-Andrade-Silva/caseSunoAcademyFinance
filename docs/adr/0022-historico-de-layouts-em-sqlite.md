# 0022 — Histórico de layouts em SQLite

## Status

Aceita.

## Contexto

A direção de arte precisa considerar layouts usados em execuções anteriores, explicar a decisão
na interface e medir a distribuição das composições. O projeto é executado localmente e não
precisa de sincronização entre máquinas nesta fase. Adotar Supabase adicionaria serviço externo,
credenciais, rede e uma nova operação de infraestrutura sem benefício necessário para o recorte.

## Decisão

O histórico de layouts é persistido no banco local `data/execucoes/suno.sqlite3`, usando o módulo
`sqlite3` da biblioteca padrão do Python.

- Cada slide renderizado gera um registro com execução, audiência, índice, composição, pontuação,
  motivos e data de registro.
- A combinação execução, audiência e índice é única.
- Remontar uma execução substitui seus registros em uma única transação.
- A seleção consulta os usos recentes, mas exclui a própria execução para que uma remontagem com
  a mesma entrada continue determinística.
- O `pacote.json` recebe um resumo da direção de arte realmente renderizada. A API apenas expõe
  esse contrato, e a interface mostra escolhas, motivos, distribuição e repetições consecutivas.
- A futura curadoria de referências visuais deverá reutilizar o mesmo banco local, em tabelas
  separadas.

## Consequências

Não há dependência nova, conta externa, credencial nem indisponibilidade de rede. O histórico fica
restrito à instalação local; sincronização multiusuário e acesso remoto não fazem parte desta
fase. Caso isso se torne necessário, a migração deverá preservar o contrato do domínio e manter o
SQLite como opção local.
