# Inteligência visual — plano técnico de integração

## Diagnóstico do repositório

O pipeline existente já contém os encaixes necessários para o MVP:

- Python e Pydantic modelam o conteúdo e o fluxo de geração.
- O Carrossel é um roteiro estruturado de 5 a 7 slides (`Slide`).
- HTML/CSS + Puppeteer já são o renderizador principal; Pillow permanece como reserva.
- A identidade visual está centralizada em `src/suno/pacote/templates/base.css`.
- O manifesto de cada slide e `suno.pacote.visual` já verificam dimensão, contraste,
  estouro de texto e fidelidade das Âncoras numéricas.
- O projeto usa catálogos fechados para direção de cena. A direção de arte reutiliza o
  mesmo princípio, sem criar um agente com tools ou uma nova chamada de LLM.

O problema arquitetural era que `TipoSlide` acumulava duas responsabilidades: função
narrativa (`hook`, `ponto`, `citacao`, `cta`) e escolha do template. A integração separa essas
responsabilidades sem alterar o contrato do Gerador nem o JSON das execuções existentes.

## Aceite do primeiro incremento

1. Existir um catálogo fechado com seis composições: editorial, minimalista, infográfico,
   comparativo, estatístico e narrativo.
2. Selecionar uma composição pela função narrativa, presença de Âncora numérica, indícios de
   comparação e densidade textual.
3. Penalizar layouts já usados no Carrossel e layouts recebidos no histórico recente.
4. Manter a decisão determinística para a mesma entrada.
5. Renderizar as seis composições com a identidade atual e registrar a decisão no manifesto.
6. Preservar o pipeline sem referências externas, Instagram, banco novo ou modelo multimodal.

## Não objetivos deste incremento

- Coleta automática do Instagram.
- Supabase ou outra persistência remota.
- Importação e curadoria de referências.
- Ollama ou análise multimodal.
- Geração de fotografia/ilustração por IA.
- Persistência global do histórico entre execuções distintas.
- Reescrita do Gerador, do Avaliador ou da interface administrativa.

## Tarefas e arquivos

### 1. Catálogo e direção de arte — concluído

- Criar `src/suno/pacote/direcao_de_arte.py`.
- Definir compatibilidade e pontuação das seis composições.
- Tornar a seleção determinística e aplicar penalidade de repetição.
- Aceitar histórico recente por interface, sem exigir persistência.

### 2. Biblioteca de layouts — concluído

- Criar seis estruturas HTML reutilizáveis em `src/suno/pacote/templates/`.
- Reutilizar paleta, tipografia, margens, selo e navegação de `base.css`.
- Manter números derivados exclusivamente das Âncoras existentes.

### 3. Integração ao renderizador — concluído

- Modificar `src/suno/pacote/carrossel_html.py` para planejar antes de renderizar.
- Registrar `layout`, pontuação e motivos em cada `slide-<nn>.json`.
- Modificar `src/suno/pacote/carrossel.py` para aceitar histórico opcional.
- Modificar `src/suno/pacote/__init__.py` para compartilhar o histórico entre os
  carrosséis montados no mesmo Pacote.
- Melhorar `render/render.mjs` para medir o conteúdo real no limite mínimo da fonte.

### 4. Prova focada — concluído

- Criar `tests/test_direcao_de_arte.py`.
- Provar presença das seis composições e dos seis templates.
- Provar seleção por conteúdo e mudança diante de histórico repetido.
- Renderizar as seis composições e passar pela conferência visual existente.
- Reexecutar os testes do Gerador e do Pacote para provar compatibilidade.

## Evolução por fases

### Fase 2 — histórico persistente e observabilidade — concluída

- Persistir a sequência de layouts no SQLite local `data/execucoes/suno.sqlite3`.
- Substituir atomicamente os registros de uma execução quando ela for remontada, sem duplicar
  histórico.
- Excluir a execução atual da consulta ao histórico, preservando o resultado determinístico de
  uma remontagem.
- Expor no pacote e na interface a composição escolhida, sua justificativa, a distribuição de
  uso e as repetições consecutivas.
- Usar somente `sqlite3` da biblioteca padrão; Supabase e persistência remota ficam fora da
  arquitetura.

### Fase 3 — referências e curadoria manual — concluída

- Criar o domínio `ReferenciaVisual` separado da geração.
- Persistir a futura biblioteca de referências no mesmo SQLite local.
- Semear seis referências internas e aprovadas sobre finanças e investimentos, uma por
  composição do catálogo.
- Registrar em cada escolha qual referência aprovada orientou a composição.
- Expor a biblioteca em uma API e numa tela própria com miniaturas estruturais.
- Importar manualmente metadados e URLs/origens autorizadas; nenhuma imagem remota é baixada.
- Aprovar ou rejeitar referências pela interface. Só as aprovadas orientam a direção de arte.
- O Gerador continua operando se essa biblioteca estiver vazia.

### Diretor de Arte IA — camada híbrida concluída

- Fazer uma chamada estruturada por carrossel, nunca uma por slide.
- Limitar a decisão às seis composições e às referências aprovadas.
- Validar no código quantidade de escolhas, compatibilidade, correspondência da referência e
  repetição consecutiva.
- Usar automaticamente o seletor determinístico quando o provedor estiver ausente, falhar ou
  devolver um plano inválido.
- Registrar origem do plano, provedor, intensidade visual e motivo do fallback no Pacote.

### Fase 4 — coleta opcional — concluída

- Instaloader é um extra opcional, isolado e falível; nenhuma mídia é baixada.
- Perfis, janela de 30/60/90 dias, candidatos, métricas disponíveis e falhas persistem no SQLite.
- Candidatos entram na curadoria somente após escolha humana da composição e sempre não aprovados.
- Nunca contornar autenticação ou bloqueios; manter importação manual como caminho garantido.

### Fase 5 — análise multimodal remota — concluída antes da coleta

- Receber PNG, JPEG ou WebP autorizado pela interface e normalizar para PNG local sem metadados.
- Usar o Gemini já integrado como provedor principal; nenhum modelo local ou Ollama é adotado.
- Extrair somente análise estrutural em schema fechado, sempre sujeita a nova aprovação humana.
- Manter imagem e análise manual utilizáveis quando o Gemini estiver ausente ou falhar.
- Migrar o SQLite de forma expansiva e idempotente, preservando todas as referências existentes.

### Fase 6 — Eval visual e ciclo de aprovação humana — concluída

- Reutilizar o Eval existente para legibilidade, coerência visual e aderência à marca.
- Executar uma chamada pela folha de contato, com falha aberta e sem decisão automática.
- Registrar a aprovação H5 como sinal positivo idempotente no SQLite.
- Entregar ao Diretor apenas contagens agregadas, tratadas como preferência fraca.

## Condição de parada da fase 2

A fase termina quando o histórico sobrevive entre execuções, uma remontagem não duplica dados,
o pacote expõe a direção de arte realmente renderizada, a interface apresenta decisão e
distribuição, e os testes focados de Python e da interface passam. Nenhuma infraestrutura
externa é adicionada.
