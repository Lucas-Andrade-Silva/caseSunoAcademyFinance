# Suno Content — interface

React + Vite + Tailwind sobre FastAPI (ADR 0005). Mostra a Matriz 3×3, cada Célula com as
Âncoras ao lado, a reprovação como tela de primeira classe, e as filas H3, H4 e H5.

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

## Construir para o FastAPI servir

```bash
cd web
npm install
npm run build
```

Isso roda `tsc --noEmit` e depois `vite build`, gerando `web/dist/`. O `criar_app` do
`src/suno/api/app.py` serve essa pasta como estático em `/`, com fallback de SPA para
`index.html`, quando `web/dist/index.html` existe.

## Cliente da API

`npm run dev`/`npm run build` não regeram o cliente: `web/openapi.json` e
`web/src/api/*.ts` são gerados por `scripts/gerar-cliente.{ps1,sh}` (Agente 11, a partir de
`src/suno/api/app.py`). Todo acesso à API na SPA passa por `web/src/dados/cliente.ts`, que
envolve `criarCliente()` desse cliente gerado — nenhum outro arquivo chama `fetch`.

## PWA

`vite-plugin-pwa` gera o `manifest.webmanifest` e registra o service worker no build; o
ícone é `public/icone.svg`, desenhado para o projeto (nada baixado de rede).
