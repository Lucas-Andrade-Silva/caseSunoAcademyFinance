"""Suíte `pydantic-evals` (ADR 0003). Casos em `evals/casos/*.yaml`, versionados; roda dentro do pytest.

Três peças, e a ordem importa para entender o arquivo YAML:

- `evals/casos/*.yaml` — um arquivo por métrica (`flesch_br`, `densidade`, `aderencia`,
  `recomendacao`, `integridade`) e um `matriz.yaml` de ponta a ponta. Cada caso tem
  `inputs`, `expected_output`, `metadata` (por que o caso existe) e, quando precisa,
  `evaluators` próprios.
- `evals/tarefas.py` — `Entrada`/`SaidaLaudo` (os tipos que o YAML valida) e `julgar`, a
  função que monta a Célula e chama `avaliar`.
- `evals/avaliadores.py` — os `Evaluator` próprios. Nenhum chama LLM.

Rodar: `uv run pytest tests/test_evals.py -s` — o `-s` deixa o relatório do `pydantic-evals`
aparecer. Conjunto de casos versionado no git *é* a reprodutibilidade que o Entregável 6
pede; nada aqui depende de serviço externo, telemetria ou cota.
"""
