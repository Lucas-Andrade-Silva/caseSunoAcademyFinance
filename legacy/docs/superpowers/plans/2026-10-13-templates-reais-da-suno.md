# Templates reais da Suno no catálogo de composições

**Origem:** o usuário colocou 5 carrosséis reais da Suno em `templates/suno/` e pediu que a IA gere
dentro daquele padrão. `templates/recriados/` guarda as 20 recriações em HTML, as comparações
original × recriado e as ferramentas de render. Este plano integra 17 delas ao pipeline.

**Estado de partida:** suíte com 1240 testes passando e 7 falhando por motivo anterior
(`test_api_fontes` ×4, `test_api_geracao::test_a_ata_do_copom_280_diz_que_tem_demo`,
`test_origens` ×2: esperam a Ata 280 como padrão e o catálogo aponta para a 281). Nenhuma
falha nova é aceitável.

## Decisões de desenho

1. **Família visual** é o conjunto coerente de layouts de uma conta da Suno: `noticia`,
   `explicativo`, `jornal` (Suno Notícias), `dados`, `asset`, mais `suno_escuro` (os seis
   layouts escuros que já existem). Um carrossel usa **uma** família; os slides variam de
   layout dentro dela. Os posts reais fazem assim.
2. **O layout continua sendo `ComposicaoCarrossel`**: cada layout novo vira um valor do enum,
   prefixado pela família. Histórico, referências e API seguem funcionando sem migração.
3. **Cada família é autodescritiva**: `src/suno/pacote/templates/familias/<familia>/familia.json`
   declara, por layout, papéis compatíveis, se usa imagem, se exige dado e quais slots tem e de
   onde vêm. O HTML marca os slots com `data-slot`, e o motor troca o conteúdo sem mexer no resto.
   Os HTMLs continuam renderizáveis sozinhos com o texto de exemplo.
4. **Nenhum campo de texto novo no `Slide`.** O Avaliador julga `titulo + corpo`
   (`dominio.py`, `Conteudo.texto_avaliavel`); texto extra seria brecha de Compliance. A frase em
   vermelho vem do último parágrafo do `corpo`. O único campo novo é `imagem`, o assunto da foto:
   termo de busca que não aparece no post.
5. **Texto de tamanho variável** é tratado por encolhimento até caber: cada slot de texto tem
   altura máxima no manifesto e o script de ajuste já existente reduz a letra de 2 em 2 px.
6. **Foto sem acerto não quebra o slide**: o layout degrada com a classe `sem-imagem`.
7. **Fotos**: biblioteca local versionada em `data/imagens/` primeiro; rede (Wikimedia Commons)
   só em comando separado, com validação de relevância por visão e crédito obrigatório na
   legenda. A demo roda sem rede.
8. **Fora desta etapa (exigem dado estruturado que o sistema não produz)**: `jornal_painel`
   (série de rentabilidade), `dados_linha_do_tempo` (3 colunas), `asset_tabela` (fundos).
   Ficam documentados como pendência.
9. **Famílias `jornal` e `asset` têm marca própria** (Suno Notícias, Suno Asset): só entram por
   escolha explícita; a escolha automática usa `noticia`, `explicativo`, `jornal` e `dados`.
   `asset` carrega aviso legal de fundos e não serve para conteúdo educativo sem revisão.

## Fatias (cada uma termina com a suíte sem falha nova)

1. **Infraestrutura + família Explicativo.** `FamiliaVisual`, manifesto, motor de slots,
   planejador por família, fundo explícito para contraste, render dos 4 layouts com o texto real
   da execução `copom-281-...-052631`.
2. **Famílias Notícia, Jornal, Dados e Asset** sobre a mesma infraestrutura.
3. **Imagens**: `src/suno/imagens/` (biblioteca, Commons, validação, créditos), `Slide.imagem`,
   resolução no render e crédito na legenda.
4. **Banco e direção de arte**: sementes de `referencias_visuais` para cada layout novo (com
   miniatura), Diretor de Arte IA recebendo o catálogo da família, escolha automática de família
   em `montar_pacote`.
5. **API, OpenAPI, cliente TypeScript, interface** (seletor de família) e **documentação**:
   ADR de famílias visuais e de imagens licenciadas (substitui a parte do 0009 sobre foto de
   terceiro), `CONTEXT.md`, `ARQUITETURA.md`.

## Riscos conhecidos

- Os layouts foram calibrados no texto de exemplo; o encolhimento até caber resolve estouro,
  mas texto muito curto deixa vazio. Mede-se com o texto real do Gerador.
- Busca de foto por palavra erra em tema genérico (3 de 12 nos testes): a validação de
  relevância é obrigatória para foto vinda da rede.
- O reserva Pillow não conhece as famílias; renderiza como antes.
