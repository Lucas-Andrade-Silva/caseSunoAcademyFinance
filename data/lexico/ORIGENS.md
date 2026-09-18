# Origens do Léxico

`data/lexico/lexico.yaml` é uma **lista de elaboração própria** (Etapa 1, Agente 2). Nenhuma
definição de termo foi copiada de terceiro — o que este arquivo registra são as fontes
*consultadas como referência de que um termo existe e é de uso corrente no mercado financeiro
brasileiro*, não como origem de texto copiado. Distinto do glossário deste repositório
(`CONTEXT.md`), que define a linguagem do projeto — ver a entrada "Léxico" lá.

## Fontes consultadas

| Fonte | Licença | O que foi usado dela |
|---|---|---|
| Dicionário CVM (gov.br) | **CC BY-ND 3.0** — *No Derivatives* | Só a confirmação de que um termo existe no vocabulário regulatório do mercado (ex.: "covenants", "free float", "valuation"). Nenhuma definição foi lida e reescrita: copiar ou parafrasear de perto uma obra ND é o que a licença proíbe, então nenhuma definição da CVM entrou neste arquivo. |
| Glossário ANBIMA (PDF, out/2024) | Não verificada | Mesmo uso: existência do termo, não a definição. Citado em `docs/research/viabilidade-tecnica.md` §3 como fonte de referência da pesquisa; não foi baixado por este agente (proibido pelo brief). |
| B3 / Bora Investir (`borainvestir.b3.com.br/glossario/`) | **Não verificada** | **Não usada.** A pesquisa (`viabilidade-tecnica.md` §3) marca a licença como não verificada; por segurança, nenhum termo deste Léxico foi tirado de lá especificamente — os termos aqui presentes são vocabulário genérico do mercado (Selic, CDI, EBITDA...), não uma cópia de estrutura de glossário de terceiro. |
| Glossário legado do BCB | Morto (HTTP 500) | Não usada — fonte indisponível, registrada como morta em `viabilidade-tecnica.md` §7. |
| `investidor.gov.br/glossario` | Morto (301/descontinuado) | Não usada — mesma razão. |

## Como a lista foi montada

A seleção dos ~174 termos e a divisão em quatro áreas (política monetária, renda fixa, renda
variável, macro) mais uma área transversal (`geral`, para termos como "investidor" ou
"liquidez" que atravessam as quatro) vieram de três lugares, nesta ordem de peso:

1. **O enunciado do case** e o brief do Agente 2, que já citam nominalmente boa parte dos
   termos centrais (Selic, Copom, meta de inflação, IPCA, hiato do produto, forward guidance,
   CDI, marcação a mercado, EBITDA, dividendos, PIB, câmbio, fiscal primário...) e definem
   explicitamente quais são "núcleo" (o que o Intermediário já conhece: CDI, Selic, IPCA,
   dividendos, juros, inflação, Copom, Banco Central, PIB, câmbio, dólar, Tesouro Direto,
   ações, bolsa, renda fixa, renda variável, fundo, poupança, CDB — 19 termos exatos).
2. **A Ata do Copom versionada em `data/atas/copom-280-2026-08-05.txt`**, lida de ponta a
   ponta para confirmar que o vocabulário do Léxico cobre o que aparece de fato num documento
   real do Copom (taxa básica de juros, balanço de riscos, expectativas desancoradas, hiato do
   produto, choque de oferta, placar de votação, fiscal primário, dívida bruta...).
3. **Conhecimento de domínio geral** do mercado financeiro brasileiro (renda fixa — CDB, LCI,
   LCA, debênture, come-cotas, marcação na curva; renda variável — P/L, payout, free float,
   follow-on, ADR/BDR; macro — IGP-M, INCC, risco-país, formação bruta de capital fixo), para
   cobrir o que uma Ata cita de passagem ou o que um fato relevante / release de resultado usa
   sem estar na Ata do Copom especificamente.

Sinônimos e siglas correntes (ex. "BC"/"BCB" para Banco Central, "FGC" para Fundo Garantidor
de Créditos, "ROE" para retorno sobre patrimônio líquido) entram como `variantes` do termo
canônico, não como entradas novas — é o mesmo padrão descrito no brief.

## O que fica de fora, de propósito

Termos cuja licença de origem é ambígua ou cuja definição precisaria ser copiada de perto de
uma fonte ND não entraram. Onde havia dúvida sobre se um termo é "genérico o suficiente" para
não contar como derivado de uma fonte específica (ex. termos muito específicos de um glossário
em particular, com fraseado idiossincrático), a entrada foi descartada em vez de arriscada.

## Atualização

Léxico, Limiares e Calibração são conhecimento de domínio da pessoa dona do Avaliador (CLAUDE.md).
Este arquivo — e `lexico.yaml` — devem ser revistos por ela na Calibração (H2, ~30 Células
rotuladas à mão), quando termos que faltam ou termos que geram ruído (falsos positivos de
Densidade) aparecerem na prática.
