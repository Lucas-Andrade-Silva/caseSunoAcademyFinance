# A direção de cena do Roteiro sai de um catálogo fechado, e a duração é escolhida

O Roteiro era fala e uma rubrica de texto. Para virar vídeo bom, e para alimentar um gerador de
vídeo com avatar sintético, ele precisa dizer também **como a cena é editada**: o ícone, o texto
na tela e quando ele aparece, a transição, o efeito e os sons. E a pessoa precisa escolher
quanto o vídeo dura: 40 s, 1 min, 1 min 30, 2 min ou 3 min.

## A direção é escolha entre nomes, nunca texto livre

Cada bloco do Roteiro ganha campos de direção (`cena`, `icone`, `entrada`, `texto_anima`,
`texto_entra_em_s`, `efeito`, `som_de_entrada`, `som_de_efeito`). Todos são enumerados em
`suno.dominio`, descritos em `suno.video.design` e escolhidos pelo LLM **por nome**, a partir do
catálogo que o pedido lista. O design system (cores, tipografia, área segura, tempos) é código.

Três consumidores leem o mesmo catálogo: o prompt, o JSON do plano de edição e o render local.
Texto livre de direção foi recusado: não daria para validar, e o JSON para o gerador de avatar
só serve se cada nome significar uma coisa só.

A direção **não cria texto novo**. O único texto que aparece escrito continua sendo `tela`, que
já passa por Aderência e Recomendação (ADR 0011, `texto_de_conferencia`). Ícone, transição,
efeito e som são nomes de catálogo: não há número nem frase para o Avaliador julgar, e o
contrato `(Conteúdo, Âncora[], Audiência) → Laudo` não muda (ADR 0001).

## O tempo é conta, não escolha do LLM

O LLM erra a conta de tempo, e sempre para o mesmo lado: escreve mais do que cabe. Por isso
`cronometrar` recalcula `inicio_s` e `fim_s` pelo número de palavras de cada fala (2,5 palavras
por segundo), em sequência e sem buraco, e higieniza a direção (a primeira cena entra em corte;
contagem só em `dado_grande`). A duração escolhida fixa o **orçamento** que o pedido informa
(palavras e cenas) e a **faixa** que `medir_video` aceita (75% a 125% do alvo).

A duração viaja como parâmetro: `POST /api/execucoes` → `Gerenciador` → `executar` → dossiê →
persona → `rodar_ciclo` → `gerar_celula` → `montar_pedido`. O Roteiro guarda o alvo em
`Conteudo.duracao_alvo_s`; os outros Formatos não a leem.

## O plano de edição

`suno.video.plano` deriva do Roteiro aprovado dois arquivos: `plano.json` (autocontido, versionado
em `esquema` e `versao`, com tempos absolutos, posição do avatar por cena e os tokens do design
system) e `plano.md` (a tabela para uma pessoa conferir). Saem no Pacote de publicação e pela rota
`GET /api/execucoes/{id}/celulas/{audiencia}/roteiro/plano`, que a interface usa no botão "Copiar
JSON para avatar". Só Roteiro aprovado tem plano (ADR 0004).

## O render local acompanha, em versão simples

O mp4 em CPU aplica layout por cena, ícones desenhados em Pillow, animação do texto, os cinco
efeitos e as quatro transições. Os sons são sintetizados em código (sem arquivo, sem rede, sem
licença). **Eles só entram com narração**: um mp4 sem voz continua sem trilha de áudio, para
`medir_video` não ser enganado por um som solto (ADR 0014).

## Consequências

- Execuções gravadas antes continuam abrindo: todo campo novo tem padrão.
- `suno.video.__init__` resolve o render sob demanda; o Gerador importa `suno.video.design` e o
  render importa o Gerador de volta, e carregá-lo junto fecharia um ciclo.
- Nada aqui mede se o Roteiro respeitou o orçamento de palavras. Isso seria uma métrica do
  Laudo, e o Laudo é da dona do Avaliador: fica como proposta, não como código.
