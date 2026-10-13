# A interface vira uma ferramenta de produção em seis guias, no padrão do editor do biosites

A interface de três guias (Fontes, Curadoria, Saídas, em preto e vermelho) servia a quem **revisa** o
que o pipeline gera: aprovar, reprovar, exportar. A pessoa que usa o produto quer outra coisa: ver as
notícias do momento, escolher até três e transformá-las em texto analítico, carrossel e roteiro de
vídeo, para três audiências. A interface passa a ser essa ferramenta, e o visual segue o editor do
biosites, que a pessoa trouxe como referência.

Decidimos:

- **Seis guias**: Ingestão, Texto analítico, Carrossel, Vídeo, Histórico e Configurações, numa barra
  lateral arredondada. Cada guia de conteúdo pede **uma Saída** ao servidor, com o seu Formato e as
  Audiências marcadas num popup de confirmação (`POST /api/execucoes`, que já aceita qualquer
  subconjunto da Matriz: ADR 0017).
- **Só front** nesta decisão (as origens novas e a busca em duas etapas vieram depois, no
  [ADR 0029](0029-origens-de-noticias-e-busca-em-duas-etapas.md)). O que o servidor não tem (os quatro
  formatos do Texto analítico, o editor, a paleta e os ícones do Carrossel, a prévia no celular, os
  estilos e o prompt do Vídeo, o Histórico) roda no navegador e fica em `localStorage`. Cada peça
  pode ganhar rota depois sem trocar a tela.
- **Janela de 30 dias.** A Ingestão só mostra notícias com `data_referencia` de até 30 dias atrás
  (`web/src/nucleo/janela.ts`). É regra do produto, não detalhe de tela.
- **A seleção é de sessão.** O que a pessoa marca (até 3) vira *guardado* quando ela aperta ATUALIZAR e
  vale só enquanto a aba existir (`sessionStorage`). Quem sai sem gerar começa do zero.
- **Pré-carga.** Todas as vistas ficam montadas e os dados que elas leem são buscados na abertura
  (`web/src/nucleo/precarga.ts`); o único carregamento visível é a geração em si.
- **Contraste acima da referência.** Os cinzas de texto das capturas do biosites dão 2,4:1 sobre a
  superfície escura. Os tokens de texto secundário são mais claros para chegar a 4,5:1; o resto do
  visual segue as medidas e cores amostradas das capturas.

## O que sai da tela

A **Decisão humana** (aprovar e reprovar Célula), o **Pacote de publicação**, as **Âncoras** ao lado do
conteúdo e a lista de Saídas com filtros não têm tela nesta versão. As rotas continuam no servidor,
com os testes, e a Saída gerada continua gravada em disco como antes. O Laudo aparece em barras
horizontais, com os Limiares marcados; o detalhe por métrica e o motivo da reprovação ainda não.

## Consequências

- **A demo offline esvazia a Ingestão com o tempo.** A Ata do Copom de 05/08/2026 já passa de 30 dias e
  a de 16/09 sai da janela em 16/10. Sem rede, só **Importar documento** traz notícia recente; com
  rede, **Buscar notícias novas** traz as das origens. Se a banca precisar da demo sem rede, a janela é
  a constante `JANELA_EM_DIAS`, uma decisão de produto a rever.
- **Modo Demo e modo Real** passam a ser escolha de Configurações. Sem escolha, vale Real quando o
  servidor tem provedor configurado. Com mais de uma notícia só o Real gera (Visão unida: ADR 0019).
- **Compliance continua do Laudo.** Os formatos do texto e o prompt do vídeo só reorganizam o que o
  Avaliador já aprovou e nunca acrescentam chamada para compra ou venda.

## Alternativas recusadas

- **Rotas novas para cada peça** (formatos, prompt, histórico no servidor). Mais completo, mas mexe no
  contrato OpenAPI e em arquivos de `src/suno` que têm dona, e a tela precisava existir antes.
- **Manter a revisão humana como guia.** A pessoa descreveu o produto sem ela; o desenho não a
  impede, e a rota de decisão segue no ar.
