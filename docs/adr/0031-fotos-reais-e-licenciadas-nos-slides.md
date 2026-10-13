# 0031 — Os slides usam fotos reais e licenciadas, buscadas fora da demo

## Status

Aceita. **Substitui a parte do [ADR 0009](0009-imagens-do-pacote-de-publicacao-sao-geradas-nunca-raspadas.md)
que proibia foto de terceiros.** O resto do 0009 continua: 1080×1350 em todo slide, e o sistema
não raspa foto de notícia nem reaproveita imagem de veículo de imprensa.

## Contexto

Os carrosséis reais da Suno têm foto do assunto (a sede do Banco Central, o pregão, uma nota de
real). O ADR 0009 recusou foto de terceiros por risco de direito autoral e escolheu gráfico
gerado. A decisão do projeto mudou: os slides devem ter **fotos reais, sobre o assunto**, vindas
da internet. O risco que o 0009 apontou não desapareceu; precisa ser tratado por construção.

## Decisão

1. **Uma única fonte: Wikimedia Commons**, pela API aberta e sem chave. Só licença que permite
   reuso: CC0, domínio público, CC BY, CC BY-SA. Fora tudo que for NC, ND, marcado `NonFree` ou com
   `Restrictions` (marca registrada, direito de personalidade). Nenhuma raspagem de site de
   notícias, de buscador ou de rede social. O ADR 0009 acertou nisso e continua valendo.
2. **A demo roda sem rede.** As fotos ficam versionadas em `data/imagens/` com um `indice.json`
   (tags em português, autor, licença, página de origem, aprovação), como as Atas em `data/atas/`.
   `python -m suno.cli imagens buscar "<assunto>" --rede` e `pacote --buscar-fotos` são os
   únicos caminhos que tocam a rede, e sempre explícitos.
3. **O Gerador sugere só o assunto**, em `Slide.imagem` (até quatro palavras de busca). Não é
   texto do post, não passa pelo Avaliador de texto e não entra em `texto_avaliavel`. O prompt
   restringe a lugares, instituições, objetos concretos e autoridades em exercício do cargo;
   nunca pessoa privada.
4. **Relevância verificada.** A busca por palavra erra em tema genérico: nos testes, 3 de 12 fotos
   vieram erradas ("dólar" trouxe nota dos Estados Confederados, "contas" trouxe uma foto de
   crianças britando pedra, "satélite" trouxe uma praça alemã). Foto vinda da rede só é usada se
   o juiz de visão (`PapelLLM.JUIZ_VISAO`) a aprova e não a marca como inadequada; sem juiz, a foto
   fica gravada como pendente e só entra depois da aprovação humana
   (`imagens aprovar <id>`).
5. **Crédito sempre.** O bloco `Foto: autor / licença / url` entra na legenda depois do aviso de
   não recomendação, e o `pacote.json` guarda cada foto usada (`FotoDoPacote`). CC BY exige o
   autor; CC0 e domínio público dispensam, mas o crédito sai igual.
6. **Foto sem acerto não quebra o slide.** O layout da família degrada sozinho (classe
   `sem-imagem`) e o planejador evita layout de foto quando não há foto. A mesma foto não repete
   no mesmo carrossel.

## Consequências

- A cobertura da biblioteca decide a qualidade: instituições e figuras públicas têm foto no
  Commons; assuntos genéricos têm pouco. Slide sem foto é o resultado normal, não um erro.
- **Risco aberto: CC BY-SA.** A cláusula de compartilhamento pela mesma licença pode alcançar uma
  imagem composta que incorpore a foto. Hoje o projeto aceita BY-SA e credita; a revisão jurídica
  deve decidir se BY-SA fica ou se o filtro passa a aceitar só CC0, domínio público e CC BY.
- **Pessoa na foto.** Só autoridade em exercício do cargo e em foto institucional (a biblioteca
  tem uma, da Agência Senado). O juiz de visão marca `inadequada` para pessoa privada.
- Imagem real não é determinística como o gráfico do ADR 0009: o teste de CI continua usando a
  reserva Pillow, sem foto, e o render com foto é coberto no teste com navegador.
