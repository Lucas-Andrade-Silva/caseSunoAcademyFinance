# ADR 0026 — coleta pública opcional de referências

## Decisão

A descoberta de referências usa um adaptador isolado de Instaloader, sem login e sem download
de mídia. Perfis monitorados, resultados e falhas ficam no mesmo SQLite da biblioteca visual. A
interface aceita somente janelas de 30, 60 ou 90 dias, limita a coleta a 20 carrosséis por perfil
e filtra os resultados por setor financeiro. A classificação de setor é determinística, baseada
no título e na legenda; não chama LLM.

O adaptador é uma dependência opcional (`uv sync --extra coleta`). Se ele estiver ausente ou o
Instagram recusar a consulta, a falha é registrada por perfil e a importação manual continua
disponível. Não há tentativa de contornar autenticação, bloqueio ou perfil privado.

Um resultado coletado contém somente URL, URL pública da capa, legenda resumida, data e métricas públicas que o
provedor realmente retornou. A taxa aproximada só existe quando curtidas, comentários e número
de seguidores estão disponíveis; nenhum valor ausente é inventado.

A tela ranqueia somente os perfis monitorados, pela soma de curtidas e comentários dos carrosséis
que passaram pelos filtros, e mostra a taxa de engajamento média quando ela existe. Descoberta
global de perfis exigiria busca autenticada ou outro provedor e não faz parte deste adaptador.

O candidato não orienta o Diretor de Arte e a Descoberta não o promove automaticamente para a
biblioteca. Se quiser usar aquele exemplo, um humano abre a origem e o cadastra explicitamente na
Configuração visual, onde escolhe uma das seis composições. Imagem e análise estrutural continuam
sendo enviadas e revisadas pelo fluxo multimodal já existente.

## Consequências

- A geração permanece determinística e independente do Instagram.
- Consultas repetidas são idempotentes pelo identificador público do post.
- Nenhuma imagem de terceiro é armazenada automaticamente.
- A descoberta pode deixar de funcionar quando o Instagram mudar ou limitar o acesso público;
  isso não degrada as demais funções do produto.
