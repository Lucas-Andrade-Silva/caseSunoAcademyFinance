# Seis origens de notícias e a busca em duas etapas (consultar, depois baixar)

A Ingestão tinha o Copom e os Fatos Relevantes da CVM. O produto precisa de mais fontes, de
gêneros diferentes: o fato relevante (curto, narrativo), as demonstrações financeiras e os
formulários (longos, tabulares), os relatórios do BCB (longos, analíticos), as resoluções
(artigos e incisos) e os ofícios e comunicados da B3. A janela passou de 20 para **30 dias**.

Decidimos:

- **Um coletor por origem** (`src/suno/origens/coleta.py`), cada um com duas operações: `listar`
  (só metadados, uma ou poucas requisições) e `baixar` (um documento). Fontes, todas testadas ao
  vivo em 2026-10-12:
  - **Copom, Relatório de Inflação e Relatório de Estabilidade Financeira**: a API não documentada
    do site do BCB (`api/servico/sitebcb/{atascopom,ri,ref}/ultimas`), PDF no `Url`.
  - **Resoluções do CMN e do BCB**: a busca de normas do BCB (`api/search/app/normativos/buscanormativos`),
    que também lista comunicados (filtramos `Resolução*` no cliente: o filtro por tipo na consulta
    devolve zero linhas). O texto vem de `api/conteudo/app/normativos/exibeversao` em HTML e é gravado
    como `.txt`.
  - **CVM** (Fatos Relevantes e "DFP, ITR e Formulários"): o IPE dos dados abertos, o mesmo zip, lido
    uma vez por consulta. DFP e ITR são as "Demonstrações Financeiras Anuais e Intermediárias" e os
    formulários são as categorias que começam em "Formulário".
  - **Ofícios e comunicados da B3**: a página pública de regulação, que lista no HTML e aceita
    `dataIni`, `dataFim` e `pagination` na URL; o PDF é o link "Download do Documento". Nada de API
    paga ou chave. O ADR de pesquisa (§1) descartava a B3 como origem de *documentos* por causa do
    Cloudflare; os ofícios são outro caso, porque a página responde ao cliente HTTP comum.
- **A busca é em duas etapas.** `POST /api/fontes/atualizar` consulta cada origem ligada e lista o que
  saiu nos últimos 30 dias e ainda não está em disco. Com até 2 documentos o job baixa tudo. Com mais,
  o estado vira `aguardando_filtro` e a tela mostra a quantidade e deixa escolher um período dentro da
  janela; `POST /api/fontes/atualizar/baixar` baixa só esse período e
  `POST /api/fontes/atualizar/cancelar` descarta a consulta. O teto é de 40 documentos por download,
  porque a CVM pede 10 s entre requisições (`Crawl-Delay`).
- **Categorias.** As origens novas reaproveitam `CategoriaDaAta` (`release` para DFP e ITR,
  `comunicado_relevante` para as demais) e se distinguem pelo campo `origem`; todas são "não
  calibradas". Não criamos categoria nova porque ela mexe em `dominio.py`, nos Limiares e no contrato.

## Consequências

- **Nem todo documento gera conteúdo.** A regra do conjunto essencial exige uma data e um número com
  unidade no texto; a maioria dos ofícios, resoluções e fatos relevantes curtos não tem, e a geração
  recusa antes de gastar cota. A tela marca esses cartões com "sem número".
- **Documentos longos.** Uma DFP tem centenas de milhares de caracteres (a da Oi passou de 300 mil). O
  prompt de geração e o tier gratuito não foram dimensionados para isso; é um limite aberto.
- **Rede.** As consultas falham sem derrubar a tela e cada origem que cai entra na mensagem. A B3
  oscilou durante os testes (tempo esgotado), por isso há uma segunda tentativa nos tempos esgotados.
- **Endpoints não documentados** (BCB) podem mudar sem aviso: o risco já estava no ADR 0006.
- A `Origem` "Releases de Resultados (B3)" continua "em breve": ofícios e comunicados não são
  releases de resultados.
