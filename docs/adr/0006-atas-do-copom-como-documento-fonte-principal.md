# As atas do Copom são o documento-fonte principal; a B3 foi descartada

O enunciado cita atas do Copom, fatos relevantes da CVM e releases de resultados da B3.
Testamos os três caminhos e elegemos as **atas do Copom** como fonte principal, com a
CVM como secundária.

As atas atendem todos os critérios ao mesmo tempo: são densas e macroeconômicas —
o material certo para exercitar três audiências —, totalmente públicas, em português
com par oficial em inglês, publicadas oito vezes por ano, com histórico de mais de
quinhentos documentos, e disponíveis por uma API do site do BCB sem autenticação, com
PDFs que têm camada de texto real. A demo inteira cabe em duas chamadas HTTP.

A **CVM** fica como fonte secundária, pela variedade de emissores e gêneros textuais,
sabendo que exige dois saltos — o CSV de dados abertos traz só metadados, e o texto vem
de um segundo download — e que o arquivo de 2026 estava indisponível na investigação.

A **B3 foi descartada como origem de documentos**: está atrás de proteção anti-bot e,
mais decisivo, ela apenas indexa. Os documentos que ela lista moram nos sistemas da CVM
de qualquer forma, então raspá-la seria trabalho extra para chegar ao mesmo lugar por um
caminho pior.

## Consequências

O endpoint do BCB que usamos **não é documentado** e pode mudar sem aviso. Duas defesas:
a ingestão inteira fica atrás de uma interface única, de modo que trocar a origem não
vaze para o resto do sistema; e os documentos usados na demo ficam **versionados no
repositório**, com a busca no BCB sendo um comando separado rodado antes. A apresentação
nunca depende de rede.

O par português–inglês oficial das atas, traduzido por humanos pelo próprio Banco
Central, é um corpus paralelo que ganhamos de graça. Não está no escopo, mas é a base
óbvia de uma métrica de fidelidade adicional se sobrar tempo.

Requisições automatizadas usam User-Agent identificado com contato institucional, e
respeitam o atraso declarado no `robots.txt` de cada domínio.
