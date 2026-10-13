# Front do Suno Content: refatoração no padrão do editor do biosites

Data: 2026-10-12 · Estado: em execução · Substitui o desenho de 2026-10-09 (`2026-10-09-front-suno-design.md`) na parte visual e de guias.

## 1. O que muda

O painel interno de três guias (Fontes, Curadoria, Saídas, preto e vermelho) vira uma interface de
seis guias no padrão visual do editor do biosites: barra lateral arredondada à esquerda, coluna de
ajustes e uma área de prévia mais escura à direita. Só front: as rotas da API são as que já existem.
O que não tem rota (formatos do texto, paleta, ícones, estilo do vídeo, prompt, histórico) roda no
navegador e fica guardado nele.

| Guia | O que faz |
|---|---|
| **Ingestão** | Origens de notícias à esquerda; as notícias da origem (só as dos últimos **30 dias**) à direita; abrir uma mostra o texto estruturado. Marca até **3** e **ATUALIZAR** as guarda. |
| **Texto analítico** | Popup de confirmação → geração → texto no formato escolhido (e-mail, newsletter, site, artigo) → **Editar** abre o editor ao lado. |
| **Carrossel** | Quadros com a direção da imagem, configurações visuais, prévia num celular de feed, avaliação em barras. |
| **Vídeo** | Roteiro, estilos, avaliação em barras, **Quero o prompt**. |
| **Histórico** | O que foi salvo neste navegador e as Saídas do servidor. |
| **Configurações** (engrenagem, embaixo) | Modo Demo ou Real, nome do avatar, limpeza dos dados locais. |

## 2. Decisões

| Tema | Decisão |
|---|---|
| Referência visual | Seis capturas do editor do biosites que o usuário enviou. Tokens por amostra de pixel: fundo `#1b1b1b`, superfícies e barra `#2a2a2a`, prévia `#141414`, pílula escura `#0e0e0e`, destaque branco `#e4e4e4`/`#fff`. Fonte Hanken Grotesk (a do biosites é proprietária; esta é a mais próxima das livres). |
| Contraste | Os cinzas de texto das capturas (`#6a6a6a`, `#67696b`) dão 2,4:1 sobre `#2a2a2a`. Os tokens `etiqueta` (`#969696`) e `apagado` (`#8d8f91`) são mais claros para chegar a 4,5:1. |
| Janela de notícias | 30 dias, regra do produto ("nunca acima disso"), em `nucleo/janela.ts`. Consequência hoje: as Atas versionadas do Copom (05/08 e 16/09) ficam fora; é preciso **Buscar notícias novas** (rede) ou **Importar documento**. |
| Seleção | `rascunho` (marcado na tela) e `guardada` (ATUALIZAR confirma). A guardada vive no `sessionStorage`: fechar a aba larga. |
| Geração | Cada guia de conteúdo pede **uma Saída** com o seu Formato e as Audiências marcadas no popup (`POST /api/execucoes`, `pedido` de 1 a 3 posições). Uma Ata vai em `ata` (Destaque único); de 2 a 3 vão em `itens` (Visão unida, só modo Real). O servidor gera um job por vez. |
| Pré-carga | Todas as vistas ficam montadas; origens, execuções, saúde, referências visuais e o texto de cada notícia recente são buscados na abertura (`nucleo/precarga.ts`). O único carregamento visível é o "Gerando…". |
| Modo | Configurações guarda Demo ou Real. Sem escolha: Real se o servidor tem provedor (`/api/saude`), senão Demo. |
| Fora do front | Aprovar e reprovar Célula, Pacote de publicação, Laudo detalhado e a API pública `/v1` não têm tela nesta versão. As rotas continuam no servidor. |

## 3. Arquitetura (`web/src`)

```
nucleo/        estado e regras, sem visual
  dados.ts       cache + `usarDados(chave, buscar)`; `precarregar`
  precarga.ts    o que se busca ao abrir; `CHAVES`
  janela.ts      a janela de 30 dias (Vitest)
  selecao.tsx    rascunho / guardada (até 3) / `atasGuardadas`
  configuracoes.tsx  modo Demo|Real, nome
  pedido.ts      monta o `POST /api/execucoes` (Vitest)
  sessao.tsx     uma sessão por Formato: iniciar, acompanhar, abrir, limpar
  historico.tsx  salvos no navegador (localStorage, até 60)
  laudo.ts       Laudo → barras horizontais (Vitest)
  guias.ts       as 6 guias e a ordem da barra
interface/     o sistema visual (ver seção 4)
guias/         uma pasta por guia: `index.tsx` (default) e, nas de conteúdo, `PreviaSalva.tsx`
```

A troca de guia é um deslize com desvanecer: `.vista` em `global.css`, posição `antes | ativa | depois`
conforme o índice na barra. O indicador branco da barra lateral desliza entre os ícones.

### Contrato das guias de conteúdo (Texto, Carrossel, Vídeo)

```tsx
<FluxoDaGuia formato="texto_analitico" rotuloGerando="Gerando o texto…">
  {(sessao) => /* só roda com sessao.fase === "pronta" */}
</FluxoDaGuia>
```

`FluxoDaGuia` cuida do popup (vazia), do "Gerando…" e da falha. `sessao` traz `audiencias`,
`celulas[audiencia].conteudo` (`texto`, `slides` ou `blocos`) e `.laudo`, `execucaoId`, `nome`, `limpar()`
(volta ao popup) e `abrir(id)`.

Salvar no Histórico: `usarHistorico().salvar({ especie, titulo, resumo, audiencia, execucaoId, dados })`.
Cada guia define o formato do próprio `dados` e o `PreviaSalva` que o mostra. Reabrir: o Histórico chama
`pedirAbertura(salvo)`; a guia lê `paraAbrir` quando `especie` é a dela, restaura e chama `consumirAbertura()`.

## 4. Sistema visual (`interface/`)

| Peça | Medidas da referência |
|---|---|
| `BarraLateral` | 70 px, raio 35, `#2a2a2a`, a 20 px da borda; avatar de 40 px; ícones de 24 px em traço 1,5; ativo `#e4e4e4`, inativo `#747474`; barrinha branca de 3×40 na borda. |
| `Divisao` | Coluna de 469 px centrada entre a barra e a metade da tela; metade direita `#141414`; topo da direita com `Ilha` (pílula `#0e0e0e`, 50 px) e `Botao`. |
| `Linha` | 70 px, raio 8, `#2a2a2a`, quadrado de 40 px colorido com ícone, título de 17 px, seta ou mais; 10 px entre linhas. |
| `Botao` | `claro` (branco, texto escuro, caixa alta; 70 px ou 50 px) e `escuro` (`#2a2a2a`, texto branco). |
| `Pilulas` | Altura 36, raio total; a ativa é branca com texto escuro (ALL · 1D · 7D). |
| `Modal` | Janela dividida a 12 px da borda, metade esquerda `#1b1b1b`, direita livre. |
| `Barras` | Laudo em barras horizontais; branco atingiu, coral não atingiu, marcas do Limiar. |
| Tipografia | Título de página 32 px leve; seção 24 px; linha 17 px; rótulo 12 px em caixa alta. |

Texto de tela: curto, em português, sem explicar o que a tela faz. Estado vazio é uma frase e, se houver, a saída.

## 5. Vocabulário

O `scripts/vocabulario.py` confere nomes declarados em `web/src` (função, constante, tipo, arquivo) contra a
lista _Avoid_ do `CONTEXT.md`. Evitar em identificadores: fonte, item, tipo, documento, painel, estilo,
perfil, versão, avaliação, feedback, post, export, entrega, input, meta, score, canal, corte, variante.
Usar: origem, cartão/linha, espécie, arquivo, vista, jeito, laudo, barras, salvo.

## 6. Verificação

`npx tsc --noEmit -p tsconfig.app.json`, `npx vitest run` e `npm run build` em `web/`. Visual: o app rodando
contra uma cópia dos dados com Atas recentes (ver `web/README.md`).
