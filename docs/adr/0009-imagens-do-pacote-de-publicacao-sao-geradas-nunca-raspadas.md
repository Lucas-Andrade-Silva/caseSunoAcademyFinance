# As imagens do Pacote de publicação são geradas pelo sistema, nunca raspadas de terceiros

O Formato Carrossel precisa de imagem. O caminho óbvio — buscar a foto de uma notícia ou uma
ilustração de mercado e reaproveitar no post — foi considerado e descartado.

Reusar foto e texto de um veículo de imprensa num carrossel destinado a redes sociais é uso
editorial, não indexação interna: é a categoria de reuso com maior exposição a direito autoral de
imagem, diferente de citar um link ou indexar um resumo para busca. Nenhum dos projetos irmãos
investigados como referência de arquitetura verifica licença de uso para esse cenário antes de
reaproveitar imagem de terceiro, e um deles documenta essa ausência como risco conhecido e não
tratado.

Adotamos: toda imagem do Pacote de publicação é gerada pelo próprio sistema — template com dado
extraído da Ata (por exemplo, o valor da Selic ou o gráfico da decisão) ou geração própria —, nunca
uma foto de terceiro copiada ou re-hospedada. Isso mantém a mesma linha que o CLAUDE.md já traça
para o conteúdo textual ("A linha que não se cruza"): o sistema não reproduz material de terceiro
sobre o qual não tem controle.

## O mecanismo (decidido em 17/09/2026)

A pesquisa que faltava foi feita e o resultado é claro: **nenhuma opção de geração de imagem por
IA gratuita é ao mesmo tempo estável, offline e sem risco de licença** — todas violam pelo menos
um dos três. A cota gratuita de imagem do Gemini mudou entre 2025 e 2026; Pollinations.ai não tem
SLA nem licença de modelo única.

Adotamos **template determinístico: matplotlib para o gráfico, Pillow para a composição com a
identidade visual, saída PNG**. Zero custo, zero rede, determinístico e testável em CI — a mesma
propriedade que o ADR 0001 defende para o Avaliador, agora valendo também para a imagem. O mesmo
padrão existe em projetos reais de automação de carrossel, não é caminho inventado aqui.

**Todas as imagens saem em 1080×1350 (4:5), em todas as nove Células.** Isso não é escolha
estética: o Instagram corta todo o carrossel para igualar a proporção da primeira imagem, então
variar entre Células degrada o post inteiro.

Geração por modelo fica **fora do caminho crítico**. Se algum dia entrar, entra como acessório
opcional de uma Célula específica, nunca como dependência da demo.

## Consequências

O Carrossel deixa de ter uma lacuna de pesquisa e passa a ter um alvo de implementação concreto,
com o mesmo perfil de teste do Avaliador: imagem gerada em CI, comparada byte a byte ou por
tolerância de pixel, sem rede.

Ser determinístico garante que a imagem saia sempre igual, não que saia certa: texto estoura
caixa, rótulo se sobrepõe, contraste fica ilegível. O render passa por avaliação própria antes de
chegar ao humano ([ADR 0014](0014-o-pacote-de-publicacao-tem-avaliacao-visual-propria.md)), que
mede o que é mensurável e opcionalmente mostra o resultado a um juiz de visão.

WeasyPrint (HTML/CSS → imagem) foi considerada como opção intermediária para layout mais rico e
recusada por redundância: matplotlib + Pillow já cobre o que o Carrossel precisa, e uma segunda
via de renderização é dependência sem ganho no prazo.

Esta decisão não afeta o texto da Célula nem depende de qualquer fonte de dado nova: usa só o que
já sai do Gerador para a Ata em questão, mais a tabela de Âncoras numéricas do
[ADR 0011](0011-ancoras-numericas-sao-citadas-nunca-reescritas.md), que é de onde o gráfico tira
os valores.
