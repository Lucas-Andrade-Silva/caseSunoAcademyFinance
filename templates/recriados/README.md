# Templates recriados a partir dos carrosséis reais da Suno

Referências originais: `../suno/carrossel1..5/`. Aqui estão as recriações em HTML/CSS (1080×1350),
uma pasta por família, um `.html` por *layout* (não por slide).

| Pasta | Referência | Layouts |
|---|---|---|
| `familia-1-noticia` | carrossel1 | capa escura, notícia com foto |
| `familia-2-explicativo` | carrossel2 | capa com foto, texto com imagem, texto puro, texto com ilustração |
| `familia-3-suno-noticias` | carrossel3 | capa papel rasgado, item numerado com foto, texto serifado, painel de rentabilidade |
| `familia-4-dados` | carrossel4 | linha do tempo, texto+foto (3 variantes), número gigante, texto grande, CTA |
| `familia-5-suno-asset` | carrossel5 | capa vermelha, aviso legal, tabela de fundos |

## Contrato
- 1ª linha `<!-- ref: arquivo -->` aponta o slide original que o layout reproduz.
- Todo conteúdo variável tem `data-slot="nome"`; `slots.json` de cada pasta descreve tipo, tamanho máximo e obrigatoriedade.
- `{{FONTES}}` injeta as fontes (Anton, Poppins 300–700, Inter, Newsreader — `src/suno/pacote/fontes/`, todas OFL).
- `{{IMG:nome}}` resolve para `_imagens/nome.jpg`. As fotos são slots: vêm de fonte licenciada, nunca das referências.

## Ferramentas
- `_ferramentas/renderizar.py <pasta> --ref ../suno/carrosselN` gera `png/` e `comparacao/` (original | recriado).
- `_imagens/buscar_commons.py` busca foto no Wikimedia Commons (só CC0, domínio público, CC BY, CC BY-SA) e grava o crédito em `creditos.json`.
  A busca por palavra erra tema genérico; exige validação de relevância antes do uso.
- `_galeria/` tem uma folha por família com as comparações.

## Pendências conhecidas
- Fotos de exemplo não casam com o assunto dos textos (só existem 9 em `_imagens`).
- Ainda não integrado ao catálogo de composições nem ao Gerador/Diretor de Arte.
- Slots com `<br>` ou largura calibrada para o texto de exemplo: texto de outro tamanho pode quebrar diferente.
