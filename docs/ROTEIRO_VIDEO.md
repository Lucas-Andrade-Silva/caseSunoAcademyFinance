# Roteiro do vídeo — Suno Content (alvo: 6 min 30 s, teto 7 min)

Duas vozes: **A** (dona do Avaliador, mercado) e **B** (pipeline, front). Troque os papéis se preferir.
Fala a ~150 palavras/min. Tudo roda em modo **Demo** (sem rede, execução `demo-copom-280`), então
nada quebra ao vivo.

## Antes de gravar (checklist)

- `uv run --offline python -m suno.cli servir` rodando; navegador em `http://127.0.0.1:8000`, modo Demo.
- Segundo terminal aberto na raiz, fonte grande (≥ 18 pt), vazio.
- Abas prontas: diagrama do [ARQUITETURA.md](ARQUITETURA.md) (renderizado), app, terminal.
- `scripts\test.ps1` já rodado uma vez (cache quente). Relatório: `uv run --offline python scripts/relatorio.py --execucao demo-copom-280`.
- Plano B se algo falhar: a execução `demo-copom-280` está versionada, então a Interface abre sem gerar nada.

---

## 1. Abertura e problema — 0:00–0:40 (A)

**Tela:** logo/título, depois a Ata do Copom em PDF rolando.

> "O Banco Central publica a Ata do Copom a cada reunião. É densa, e quase ninguém fora do mercado
> lê até o fim. Nosso sistema pega essa Ata e escreve **nove conteúdos**: três Audiências — iniciante,
> intermediário e avançado — vezes três Formatos — texto analítico, carrossel e roteiro de vídeo.
> A diferença é que **nada sai sem passar por uma prova**, e o conteúdo nunca recomenda compra ou
> venda, porque isso é atividade regulada no Brasil."

## 2. Arquitetura — 0:40–2:10 (B)

**Tela:** diagrama mermaid de [ARQUITETURA.md](ARQUITETURA.md). Apontar com o cursor na ordem abaixo.

> "Fluxo em cinco passos. **Um**: a Ata fica versionada em `data/atas`, então a demo roda sem rede.
> **Dois**: uma extração, uma vez por Ata, gera as **Âncoras** — a tabela de números com o trecho
> literal de onde cada um veio. Daí em diante o modelo **copia** número dessa tabela, nunca reescreve.
> **Três**: Gemini gera as nove Células **em paralelo**; em sequência a demo morreria esperando.
> **Quatro**: o Avaliador devolve um Laudo. **Cinco**: reprovou, volta ao Gerador com o número exato
> que faltou, até quatro rodadas; se não resolver, vai para a fila de revisão humana. Aprovou, vira
> Pacote de publicação, e **uma pessoa publica** — não há integração com Instagram nem TikTok, de propósito."

> "A costura central: Gerador e Avaliador só se falam por `(Conteúdo, Âncoras, Audiência) → Laudo`.
> Isso divide o trabalho da dupla e deixa o Avaliador testável em CI."

Apontar os **pontos humanos H1–H6** (caixas amarelas) por 5 s.

## 3. Demo da aplicação ao vivo — 2:10–4:00 (B conduz, A comenta)

**Tela:** navegador, modo Demo.

1. **Ingestão** (15 s): "Aqui estão as notícias dos últimos 30 dias. Marco a Ata do Copom."
2. **Texto analítico** (25 s): marcar as 3 Audiências → gerar → barra de andamento (`extraindo_ancoras`,
   `gerando_celulas`). Mostrar os três textos lado a lado: "mesma decisão, três linguagens".
3. **Laudo** (25 s): barras horizontais com os Limiares marcados. Mostrar Flesch-BR iniciante ≥ 50,
   avançado < 25. "Repare: o texto do iniciante é mais fácil porque o Limiar da Audiência obriga."
4. **Carrossel** (25 s): escolher uma família visual → prévia no celular de feed → exportar PNG.
   "Visual recriado dos posts reais da Suno; número do slide vem da Âncora, não do template."
5. **Vídeo** (20 s): mostrar Roteiro com cenas e o plano para a ferramenta de avatar.
   "O vídeo renderiza fora do grafo, consumindo Roteiro já aprovado; se quebrar, os outros entregáveis seguem."

Frase de transição: "Tudo isso lê do disco — o mesmo arquivo que o pytest lê e o relatório cita."

## 4. Suíte de avaliação em ação — 4:00–5:30 (A)

**Tela:** terminal.

```powershell
scripts\test.ps1
```

> "Esta é a suíte. Roda sem rede e sem `.env` — o `conftest` derruba qualquer socket. Usa
> **pydantic-evals**, com casos em YAML versionados."

Enquanto roda, explicar as **cinco medidas determinísticas** (30 s):

> "**Flesch-BR**: fórmula própria, porque a `textstat` calcula português errado e não avisa — cai nos
> coeficientes do inglês, 20 pontos de erro. **Densidade** de termos do Léxico. **Aderência** de
> números às Âncoras, por igualdade exata. **Recomendação**, por Léxico mais padrão sintático em POS
> tagging, com um canary set adversarial. E **integridade da extração**. Nenhuma usa LLM, então o
> veredito não muda entre duas execuções."

Depois o relatório (30 s):

```powershell
uv run --offline python scripts/relatorio.py --execucao demo-copom-280
```

> "Aqui o relatório: aprovadas, reprovadas por motivo — o motivo é valor enumerado, então dá para contar
> por tipo — e as que foram para revisão humana. Por cima das cinco medidas ficam duas camadas de LLM:
> **Qualidade**, pelo Jev, e **Fidelidade** à Ata, em que o código confere se a citação existe mesmo."

Se quiser um momento de impacto: editar um texto na interface inserindo "compre Selic agora" e mostrar a
reprovação por **Recomendação** com o trecho apontado.

## 5. Decisões de engenharia — 5:30–6:30 (A e B alternando, ~15 s cada)

**Tela:** [DECISOES.md](DECISOES.md), tabela "Onde o enunciado sugere outro caminho".

- **B — ADR 0003:** "O enunciado sugere DeepEval e Ragas. Recusamos: telemetria ligada por padrão num, oito meses sem release e foco em RAG no outro. `pydantic-evals` roda local, com casos versionados."
- **A — ADR 0002:** "Flesch-BR próprio, pelo motivo que mostrei."
- **B — ADR 0005:** "React + Vite sobre FastAPI com cliente gerado do OpenAPI: o contrato elimina divergência silenciosa entre front e back. Streamlit parecia protótipo."
- **A — ADR 0007 e 0037:** "Orçamento R$ 0: Gemini gera, Groq julga e é reserva, e o roteador distingue limite por minuto — espera — de limite diário — troca de provedor. Cerebras e SambaNova caíram quando encerraram o tier gratuito."
- **B — ADR 0010:** "Sem LangGraph, sem tool calling, sem MCP: as nove Células são independentes, não há dúvida sobre o próximo passo. 'Agente' aqui é papel com contrato fixo."

## 6. Fechamento — 6:30–7:00 (A)

> "Resumo: nove conteúdos, cada um medido antes de existir, com números rastreáveis até a Ata e uma
> linha que o sistema não cruza — nunca recomenda. O que fica como limite: o Jev e a Fidelidade ainda
> não foram calibrados com Kappa, e fora do Copom a Saída vai marcada como 'não calibrada'. Obrigado."

---

## Dicas de gravação

- **Corte primeiro o que for ao vivo e lento:** a geração real leva minutos; em Demo é instantânea. Diga
  "em modo Demo, com respostas prontas" uma vez, para ser honesto com a banca.
- Se passar de 7 min, corte nesta ordem: aba Vídeo (§3.5), dois dos cinco ADRs (§5), exemplo de Recomendação (§4).
- Não leia o roteiro: use só as frases em negrito como âncora de cada trecho.
- Grave a tela em 1080p, zoom do navegador em 125%, terminal em fonte grande.
