# Suno Content — interface

React + Vite + Tailwind sobre FastAPI (ADR 0005), no padrão visual do editor do biosites
([ADR 0028](../docs/DECISOES.md)): barra lateral
arredondada, coluna de ajustes à esquerda e área de prévia à direita.

Seis guias, na ordem da barra:

- **Ingestão**: uma linha por origem de notícias (Atas do Copom, Fatos Relevantes da CVM, DFP/ITR e
  Formulários da CVM, Relatórios de Inflação e de Estabilidade, Resoluções do CMN e do BCB, Ofícios e
  comunicados da B3, Releases da B3 "em breve", documentos importados) e o botão **Importar documento**. À direita, as notícias da
  origem escolhida, **só as dos últimos 30 dias**; abrir uma mostra o texto estruturado. A pessoa marca
  até 3 e **ATUALIZAR** as guarda para gerar conteúdo (a seleção some quando a aba fecha). O ícone de
  atualizar, ao lado do título, consulta as origens ligadas (precisa de rede): com até 2 notícias novas
  baixa direto; com mais, mostra a quantidade e deixa escolher o período a baixar (ADR 0029).
- **Texto analítico**, **Carrossel** e **Vídeo**: abrem num popup que confirma as notícias e pergunta
  as audiências (Iniciante, Intermediário, Avançado; pode mais de uma). Confirmar pede uma Saída ao
  servidor com o Formato da guia; a geração continua se a pessoa trocar de guia.
- **Histórico**: o que foi salvo neste navegador e as Saídas do servidor; abrir leva o conteúdo de volta
  para a guia dele.
- **Configurações** (engrenagem): modo Demo ou Real, nome do avatar e limpeza dos dados locais.

A Demo só existe para uma Ata com respostas prontas (`data/respostas_prontas/`); o modo Real precisa de
chave e modelo de provedor no `.env`. Com mais de uma notícia só o Real gera (Visão unida).

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

O `vite.config.ts` faz proxy de `/api` para `http://127.0.0.1:8000` (ou para `SUNO_API`, se definida),
então a SPA em `http://localhost:5173` fala com a API sem configurar CORS à mão.

### A janela de 30 dias na demo

As Atas versionadas em `data/atas/` têm datas fixas. Quando passam de 30 dias a Ingestão não as mostra.
Para testar sem rede e sem sujar o que está versionado, copie `data/` para uma pasta de teste, ponha uma
`data_referencia` recente no `.json` da Ata e suba a API de lá (os caminhos são relativos ao diretório
atual):

```bash
mkdir -p /tmp/suno-teste && cp -r data /tmp/suno-teste/ && cd /tmp/suno-teste
# edite data/atas/copom-280-2026-08-05.json: "data_referencia": "<uma data de até 30 dias atrás>"
uv run --project <raiz-do-repositorio> python -m suno.cli servir --porta 8001
```

```bash
cd web && SUNO_API=http://127.0.0.1:8001 npm run dev
```

## Construir para o FastAPI servir

```bash
cd web
npm install
npm run build
```

Isso roda `tsc --noEmit` e depois `vite build`, gerando `web/dist/`. O `criar_app` do
`src/suno/api/app.py` serve essa pasta como estático em `/`, com fallback para `index.html` em
qualquer rota que não seja da API (atualizar a página em `/carrossel` funciona), quando
`web/dist/index.html` existe.

## Estrutura (`src/`)

| Pasta | O que tem |
|---|---|
| `nucleo/` | Estado e regras sem visual: cache e pré-carga (`dados.ts`, `precarga.ts`), janela de 30 dias, seleção, configurações, pedido ao servidor, sessões de geração, histórico, Laudo em barras. |
| `interface/` | O sistema visual: barra lateral, linha, botão, pílulas, divisão em duas áreas, janela dividida, barras, carregamento, estados vazios, ícones. |
| `guias/` | Uma pasta por guia. As de conteúdo têm também `PreviaSalva.tsx`, a prévia que o Histórico usa. |
| `lib/` | `ata.ts` (estrutura o texto de uma Ata) e `fontes.ts` (selos e nomes padrão). |
| `dados/cliente.ts` | Todo acesso à API; nenhum outro arquivo chama `fetch`. |
| `texto/rotulos.ts` | Valores do domínio em palavras de tela. |

## Testes

```bash
cd web
npm test
```

Vitest, só para lógica pura (janela de 30 dias, pedido ao servidor, Laudo em barras, estrutura de Ata e o
que cada guia tiver de lógica). Os componentes são conferidos por `tsc` e olhando o app rodando.

## Cliente da API

`npm run dev`/`npm run build` não regeram o cliente: `web/openapi.json` e
`web/src/api/schema.d.ts` são gerados a partir de `src/suno/api/app.py`. Para regerar, na raiz do
repositório:

```bash
bash scripts/gerar-cliente.sh
```

No Windows, `scripts\gerar-cliente.ps1`.

`tests/test_contrato_openapi.py` falha quando `web/openapi.json` diverge da API.
