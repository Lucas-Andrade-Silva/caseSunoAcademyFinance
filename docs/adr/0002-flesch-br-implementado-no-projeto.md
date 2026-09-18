# Implementamos o Flesch-BR no projeto; `textstat` foi rejeitada

A métrica de legibilidade é o coração do Avaliador, e a biblioteca óbvia calcula
português errado. A `textstat` não tem `pt` na sua tabela de configurações de idioma:
ao receber `pt_BR` ela cai silenciosamente no default inglês e aplica os coeficientes
de Flesch para o inglês (`206.835`) no lugar dos brasileiros (`248.835`). Some a isso
uma subcontagem sistemática de sílabas — ela usa dicionário de *hifenização*, não de
silabação, e suprime sílabas de uma letra nas bordas, então `ação` conta 1 e `água`
conta 1. Em texto financeiro de teste, o erro combinado foi de **20,7 pontos: duas
faixas inteiras de interpretação**, reportando um texto de Ensino Médio como 6º ano.
Nada nisso levanta exceção; o número sai errado e parece certo.

Implementamos então o **Flesch-BR** no próprio projeto, com a fórmula de Martins,
Ghiraldelo, Nunes & Oliveira Jr. (1996), confirmada no código oficial do NILC/USP:
`248.835 − 1.015×(palavras/frases) − 84.6×(sílabas/palavras)`. As faixas publicadas
dessa mesma fonte definem os limiares por audiência — iniciante ≥ 50, intermediário
25–50, avançado < 25 — o que troca calibragem por chute com casas decimais por um
número citável na banca.

Registramos também que **o enunciado do case erra o nome**: ele pede "Flesch-Kincaid
adaptado ao português", mas Flesch-Kincaid é outra fórmula, de nível de escolaridade.
O relatório final usa o nome correto e explica a diferença.

## Consequências

A silabação correta exige o silabador do NILC (algoritmo de Silva, 2011), que é
**GPL-3.0 e contamina**. Duas saídas: manter o arquivo isolado e cumprir a GPL, ou
reimplementar a partir do artigo. A decisão fica pendente e precisa ser tomada antes
de qualquer conversa sobre o projeto virar produto.

O silabador tem um bug conhecido — `ideia` produz uma sílaba vazia — e erra de forma
previsível em hiatos, ditongos decrescentes e `-ia` final. A convenção adotada para
esses casos é documentada junto do código e coberta por teste, porque é exatamente o
tipo de detalhe que alguém "corrige" meses depois sem saber que era deliberado.

Esta investigação vira conteúdo do Entregável 6: medimos que a ferramenta padrão está
errada para português e temos a evidência numérica.

## Validação externa e calibração de overshoot (17/09/2026)

Uma pesquisa dedicada buscou ativamente um argumento contra esta decisão e não achou. A literatura
recente de controle de nível de leitura (TSAR 2025
shared task, ACL) converge na mesma arquitetura que adotamos: fórmula determinística verificando
por fora, separada do gerador. Dois achados pontuais reforçam:

- Um relato de campo documenta o LLM **inventando o score de Flesch que alega ter atingido** —
  validação direta de por que a medição não pode viver dentro do Gerador.
- Medições de Jakob Nielsen mostram que LLMs **erram sistematicamente para cima**: pedir nível 6
  produz nível 8 real. O paper "Right at My Level" (ACL 2026) mostra o efeito pior em idiomas não
  ingleses e nos níveis mais fáceis — exatamente PT-BR e a Audiência Iniciante.

Disso decorre o **overshoot calibrado**: o Gerador pede internamente um alvo mais folgado que o
Limiar real, um valor por Audiência, medido empiricamente contra a Calibração e não chutado. O
Limiar publicado no Laudo continua sendo o do NILC; o alvo interno é detalhe de prompt do Gerador,
e o Avaliador não sabe que ele existe.

Os Limiares desta decisão deixam de ser só as faixas publicadas do NILC e passam a ser
confirmados contra a Calibração — ~30 Células rotuladas pelas duas pessoas do time, com
concordância reportada (alvo Kappa 0,6–0,8). Onde o rótulo humano divergir da faixa publicada,
o relatório mostra os dois números.

## Atualização (18/09/2026): o silabador é reimplementado, não copiado

A decisão pendente sobre o silabador do NILC (GPL-3.0) foi tomada: **reimplementamos o
algoritmo de Silva (2011) a partir do artigo, num arquivo isolado
(`src/suno/avaliador/silabas.py`), sem copiar uma linha do código do NILC**. Copiar o
arquivo contaminaria o projeto inteiro com a GPL e fecharia a porta para qualquer conversa
sobre produto; a reimplementação custa um dia de trabalho e testes, e mantém a licença do
projeto limpa.

Convenções fixadas, cobertas por teste em `tests/test_silabas.py`:

- `ideia` → `i-dei-a` (3 sílabas; o bug de sílaba vazia do NILC não existe aqui).
- Hiato com vogal tônica marcada ou `i`/`u` tônicos separa: `sa-ú-de`, `pa-ís`, `ba-ú`.
- Ditongo decrescente não separa: `mãe`, `pau`, `lei`, `cau-sa`.
- `-ia` átono final é hiato: `e-co-no-mi-a`, `Se-lic` fica `Se-lic`, `ta-xa`, `ju-ros`,
  `in-fla-ção`, `a-ção`, `a-ções`, `a-ti-vo`, `á-gio`, `á-gua`.

O texto de referência de 45 palavras e 4 frases citado na pesquisa (Flesch-BR 34,4 com o
silabador correto) não foi preservado; o teste usa um texto próprio de 45 palavras, 4 frases
e 108 sílabas contadas à mão, que resulta no mesmo 34,4 pela fórmula.
