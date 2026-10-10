# Suno Content — interface

React + Vite + Tailwind sobre FastAPI (ADR 0005). Painel escuro, em preto e vermelho da Suno,
com três guias: **Fontes**, **Curadoria** e **Saídas**. Fontes e Curadoria ainda são páginas
"em breve"; a guia Saídas já lista as execuções, abre a Matriz 3×3, mostra cada Célula com o
Laudo e as Âncoras ao lado, e deixa aprovar, reprovar, renomear e exportar.

O desenho completo está em `docs/superpowers/specs/2026-10-09-front-suno-design.md`, com os
mockups em `docs/superpowers/specs/mockups-2026-10-09/`.

## Rodar em dev

Em dois terminais, na raiz do repositório:

```bash
uv run python -m suno.cli servir
```

```bash
cd web
npm install
npm run dev
```

O `vite.config.ts` faz proxy de `/api` para `http://127.0.0.1:8000`, então a SPA em
`http://localhost:5173` fala com a API sem configurar CORS à mão.

Aprovar e reprovar **gravam** no `execucao.json` da execução. Para testar sem sujar a demo
versionada, copie a pasta e aponte a API para a cópia:

```bash
mkdir -p /tmp/suno-execucoes && cp -r data/execucoes/demo-copom-280 /tmp/suno-execucoes/
SUNO_EXECUCOES=/tmp/suno-execucoes uv run python -m suno.cli servir
```

## Construir para o FastAPI servir

```bash
cd web
npm install
npm run build
```

Isso roda `tsc --noEmit` e depois `vite build`, gerando `web/dist/`. O `criar_app` do
`src/suno/api/app.py` serve essa pasta como estático em `/`, com fallback para `index.html` em
qualquer rota que não seja da API (atualizar a página em `/saidas/abc` funciona), quando
`web/dist/index.html` existe.

## Testes

```bash
cd web
npm test
```

Vitest, só para a lógica pura em `src/lib/` (estado e cor de cada posição da Matriz, contagens,
filtro). Os componentes são conferidos por `tsc` e olhando o app rodando.

## Cliente da API

`npm run dev`/`npm run build` não regeram o cliente: `web/openapi.json` e
`web/src/api/schema.d.ts` são gerados a partir de `src/suno/api/app.py`. Para regerar sem rede:

```bash
uv run python -c "import json, pathlib; from suno.api.openapi import gerar_schema; pathlib.Path('web/openapi.json').write_text(json.dumps(gerar_schema(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')"
cd web && npx openapi-typescript openapi.json -o src/api/schema.d.ts
```

`tests/test_contrato_openapi.py` falha quando `web/openapi.json` diverge da API. Todo acesso à
API na SPA passa por `web/src/dados/cliente.ts`; nenhum outro arquivo chama `fetch`.
