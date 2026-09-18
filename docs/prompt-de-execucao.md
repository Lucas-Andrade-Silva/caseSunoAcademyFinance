# Prompt de execução — Suno Content

Cole tudo abaixo da linha na primeira mensagem de uma sessão nova do Claude Code, na raiz
do repositório.

---

Construa o **Suno Content** inteiro, do zero aos seis entregáveis. A arquitetura já foi
decidida e está escrita nos documentos: sua tarefa é implementar o que está decidido, não
decidir de novo. Não peça permissão para começar nem proponha outro plano. Só pare se
descobrir que um ADR está factualmente errado — aí me diga qual, com a prova.

## 1. Leia primeiro, inteiros, nesta ordem

`CLAUDE.md` → `CONTEXT.md` → `docs/ARQUITETURA.md` → os catorze ADRs em `docs/adr/` →
`docs/research/viabilidade-tecnica.md` → `docs/Case Suno __ Academy __ Finance.pdf`.

Nenhuma biblioteca, modelo ou fonte de dado entra no projeto sem estar na pesquisa de
viabilidade — ou sem você conferir na documentação oficial antes. Os nomes que o código usa
saem do `CONTEXT.md`, e as palavras da lista `_Avoid_` não podem aparecer em nome de
classe, função, campo, rota, arquivo ou tabela.

Terminada a leitura, escreva `docs/plano-de-execucao.md`: a lista dos arquivos que você vai
criar, com o ADR que justifica cada um. É o combinado que os agentes vão ler depois.

## 2. As sete regras que você vai esquecer no meio do caminho

Releia este bloco antes de cada etapa.

1. O sistema nunca produz Recomendação. Quem detecta é código, com regra fixa, nunca um
   LLM (0008, 0012).
2. O Avaliador funciona sem LLM e sem internet (0001). O `pytest` passa offline e sem
   `.env`. Escreva um teste que quebra se algum outro teste tentar acessar a rede.
3. Custo zero. Nada de chamada paga, nem da Anthropic. Provedor de LLM só é acessado por
   uma única porta de entrada, nunca importado direto (0007).
4. `textstat` está proibida. DeepEval e Ragas não podem ser a base da suíte (0002, 0003).
5. O Gerador não é um agente: ele não escolhe o que fazer a seguir, não usa ferramentas,
   não usa LangGraph nem MCP. É uma sequência fixa de chamadas (0010).
6. Número nenhum é reescrito pelo LLM. Ele é copiado da tabela de Âncoras numéricas, que é
   a única origem de número no sistema (0011).
7. O Ciclo de correção tenta no máximo duas vezes. Se a leitura da Ata falhou, ele nem
   tenta — vai direto para a fila humana (0013).

Se o prazo apertar, corte na ordem que está no `CLAUDE.md`, sem mudar nada.

## 3. Etapa 0 — você sozinho, antes de chamar qualquer agente

Sem isso, cada agente inventa um formato diferente de Laudo e nada encaixa depois.

- Estrutura do pacote, `pyproject.toml` com versões fixas, `.env.example`, e scripts que
  rodem tanto no PowerShell quanto no sh.
- `src/suno/dominio.py` com **todos** os modelos Pydantic fechados — inclusive a lista dos
  motivos de reprovação e os três destinos possíveis do Laudo.
- `provedores/base.py`, a porta de entrada única para qualquer LLM, e `provedores/falso.py`,
  um LLM de mentira que devolve respostas prontas de uma fila, sem tocar na rede. É ele que
  deixa tudo testável.
- A assinatura que o ADR 0001 exige: `avaliar(conteudo, ancoras, audiencia) -> Laudo`.
- Um arquivo vazio para cada módulo da etapa 1, com `raise NotImplementedError` e um
  comentário dizendo qual ADR manda nele.
- Uma Ata de verdade em `data/atas/`, com o texto já extraído guardado ao lado.
- `pytest` verde nos testes dos modelos, com a trava de rede funcionando.

Faça um commit. É esse commit que os agentes vão ler.

## 4. As três etapas com agentes em paralelo

Chame **todos os agentes de uma etapa na mesma mensagem**. Só comece a etapa seguinte
quando a anterior terminar. **Cada arquivo tem um dono só**: se um agente precisa mexer em
arquivo de outro, ele te avisa em vez de editar, e você resolve entre as etapas.

As instruções de cada agente sempre têm estas seis partes:

```
LEIA:      CONTEXT.md, docs/adr/<os seus>, viabilidade-tecnica.md §<a sua>
TAREFA:    <uma frase>
ESCREVE:   <lista fechada de arquivos — nenhum outro>
SÓ LÊ:     src/suno/dominio.py, provedores/base.py, <outros>
TERMINOU:  quando <comando de teste> passa sem internet, cobrindo <casos>
NÃO PODE:  acessar a rede em teste · renomear modelo do dominio.py · usar palavra da lista
           _Avoid_ · instalar dependência que não está na pesquisa · tocar em arquivo alheio
ME CONTE:  o que ficou de fora · o que você mudaria em arquivo de outro · o que a pesquisa
           não cobria e você teve que descobrir sozinho
```

**Etapa 1** — seis agentes ao mesmo tempo. Nada aqui depende de LLM.

1. `avaliador/silabas.py` + `flesch_br.py` — ADR 0002. Termina quando dá 34,4 no texto de
   45 palavras e 4 frases que está na pesquisa, e acerta as palavras difíceis de separar.
2. `avaliador/densidade.py` + `data/lexico/` — ADR 0012 e pesquisa §3. Termina quando o
   Léxico está num arquivo, com a origem e a licença de cada fonte anotadas, e o código
   percebe termo usado sem explicação na primeira vez que aparece.
3. `avaliador/recomendacao.py` + `data/canary/` — ADR 0012. O canary é a lista de frases
   armadilha que disfarçam uma Recomendação. Termina quando pega todas, e quando o modelo
   `pt_core_news_sm` do spaCy carrega sem internet.
4. `avaliador/aderencia.py` + `integridade.py` + `ingestao/numeros.py` — ADR 0011 e 0013.
   Termina quando distingue `p.p.` de `%` e `CDI+2%` de `110% do CDI`, e entende vírgula
   decimal e número escrito por extenso.
5. `ingestao/bcb.py` + `pdf.py` + o comando de busca — ADR 0006. Buscar no BCB é um comando
   à parte, nunca no meio da execução. O teste usa o PDF guardado no repositório. Reconheça
   PDF pelos primeiros bytes do arquivo, nunca pelo cabeçalho HTTP, que mente.
6. `provedores/*.py` — ADR 0007. Termina quando o código lê a mensagem de erro para saber
   se a cota estourou por minuto (espera) ou no dia (troca de provedor), e quando não perde
   o formato de saída exigido ao trocar de provedor.

**Etapa 2** — quatro agentes, dependem da etapa 1.

7. `avaliador/laudo.py` + `comite/` — ADR 0001, 0008, 0013. Termina quando as cinco medidas
   viram um Laudo com três destinos, quando métrica sem base sai como **ausente** em vez de
   zero, e quando o comitê de juízes nasce desligado.
8. `gerador/` inteiro — ADR 0010, 0011, 0013. Termina quando as nove Células saem ao mesmo
   tempo usando o LLM de mentira, quando o número entra por preenchimento e não por escrita
   livre, e quando existe teste provando que o Ciclo para na segunda tentativa.
9. `pacote/carrossel.py` + `legenda.py` + `visual.py` — ADR 0009, 0014. Termina quando o PNG
   sai em 1080×1350 exatos, quando o Pillow mede texto estourando a caixa e o contraste, e
   quando o número do gráfico bate com o da tabela.
10. `evals/` + `avaliador/calibracao.py` — ADR 0003. Termina quando o `pydantic-evals` roda
    dentro do pytest, com os casos em YAML no repositório, e o Kappa e a matriz de confusão
    saem de arquivo, não escritos à mão.

**Etapa 3** — quatro agentes, a parte de fora.

11. `api/` e o cliente TypeScript gerado a partir do OpenAPI — ADR 0005. Lê do disco, do
    mesmo arquivo que o pytest lê. Mostra as filas humanas H3, H4 e H5.
12. `web/` — ADR 0005. Termina quando `npm run build` passa, as Âncoras aparecem ao lado da
    Célula, a reprovação tem tela própria, e o veredito aparece em palavras com o número ao
    lado.
13. `video/` — ADR 0004. Roda por fora, num comando separado, a partir de um Roteiro já
    aprovado. Um mp4 só, em 9:16.
14. `README.md` + `docs/relatorio-experimental.md` — Entregável 6. Como as métricas foram
    definidas, a matriz de confusão, quanto custou e quanto demorou de verdade, e o passo a
    passo para alguém rodar numa máquina limpa.

## 5. Revisão

Quatro revisores ao mesmo tempo, nenhum deles pode escrever código:

- **ADR por ADR**: para cada uma das catorze decisões, aponte o arquivo e a linha que
  cumpre — ou que desobedece. Decisão sem código correspondente também é achado.
- **Vocabulário**: procure as palavras da lista `_Avoid_` do CONTEXT.md no código todo.
- **Erros**: procure o bug que passou pelos testes.
- **Reprodutibilidade**: clone limpo, sem `.env`, sem internet. O que o README manda fazer
  funciona exatamente como está escrito?

Cada achado vem com arquivo, linha e um exemplo concreto de como quebra. **Confira cada um
antes de mexer** — revisor também erra, e consertar um problema que não existe é pior do
que ignorá-lo. Diga quais você confirmou e quais você recusou.

## 6. Prova de que está funcionando

Rode e cole a saída. Não escreva "funciona".

```
pytest -q                                              # verde, sem internet, sem .env
python -m suno.cli executar --ata data/atas/<ata>.pdf --provedor falso
python -m suno.cli pacote --execucao <id>
cd web && npm run build
```

Confira uma por uma: nove Células gravadas em disco · uma reprovação de verdade que o Ciclo
consertou (isso é o Entregável 3) · uma Célula que tentou duas vezes, não passou, e caiu na
fila humana · o canary pegando todas as armadilhas · PNG em 1080×1350 com o número igual ao
da tabela · a tela lendo o mesmo arquivo que o pytest leu · tudo de novo com a internet
desligada.

Se quebrar, cole o erro, conserte e rode outra vez. Dizer que está verde com teste vermelho
é o único erro que não tem volta aqui.

## 7. Duas escolhas já feitas — siga sem perguntar

- **Separador de sílabas (ADR 0002):** escreva o seu, a partir do algoritmo de Silva (2011),
  num arquivo isolado. Não copie o código do NILC, que é GPL e contamina o projeto inteiro.
  Teste `ideia`, hiatos, ditongos decrescentes, `-ia` no fim e as palavras de finanças.
  Registre a escolha como atualização do ADR 0002.
- **Calibração (H2):** rotular umas 30 Células à mão é trabalho de gente, não seu. Entregue
  o formato do arquivo e a conta do Kappa, e use as faixas publicadas pelo NILC como Limiar
  provisório, marcado `origem: NILC, aguardando Calibração`. Não invente rótulo humano.

## 8. No fim, me conte

O que está de pé, com o comando que prova · o que ficou de fora e por quê · onde você
discordou de um ADR · o que a pesquisa não cobria e você teve que descobrir, com a fonte ·
o que uma pessoa precisa fazer antes da demo.
