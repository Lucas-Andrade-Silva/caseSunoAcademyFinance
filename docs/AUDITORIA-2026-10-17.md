# Auditoria técnica e heurística — Suno Content

**Data:** 17/10/2026, America/Bahia. **Parecer da auditoria inicial: não pronto para encerramento.**

## Remediação executada no mesmo dia

Os achados A01–A16 foram corrigidos e receberam provas de regressão. A regra de liberação agora é
única: Recomendação sempre bloqueia, o veto humano prevalece, e Pacote, prévia, plano, vídeo, ZIP e
arquivos diretos precisam pertencer à revisão atualmente liberada. Editar ou reprovar invalida os
derivados; uma montagem em andamento não expõe manifesto nem arquivo parcial.

A Demo passou a abrir o acervo versionado com as datas originais e não instancia Jev, Fidelidade,
Diretor de Arte, juiz de visão ou busca de fotos a partir do ambiente. Também foram corrigidos a
reserva concorrente de identificadores na importação, a invalidação do cache por metadados/TXT, a
gravação atômica dos JSONs, a atualização do Histórico, o erro de acompanhamento visível, a
proveniência e o Laudo do Texto, a marcação dos cartões e o confinamento de foco nos modais.

O restante deste documento preserva a fotografia e as evidências da auditoria antes das correções.
A validação final da remediação está registrada ao fim do documento.

O fluxo principal funciona em condições controladas, mas há bloqueadores de compilação, de demonstração e de controle da publicação. O Avaliador detectou Recomendação corretamente nos casos adversariais; a interface permitiu retirar esse conteúdo do sistema mesmo assim. Aprovação, edição, decisão humana e artefatos derivados ainda não compartilham uma regra consistente de liberação.

## Escopo e estado auditado

- Base Git: `e824f4daa3a3950912b22f401b690e10828009f0`, incluindo as alterações locais preexistentes. Não é uma auditoria exclusiva do commit nem uma atribuição de causa à refatoração.
- Inspeção de ingestão, curadoria, geração, avaliação, revisão, persistência, exportação, interface, testes e documentação de entrega.
- Nenhum arquivo de implementação ou teste versionado foi corrigido. Este relatório e `.audit/2026-10-17/` são os materiais novos da auditoria.
- API de teste em `127.0.0.1:8765`, interface Vite em `127.0.0.1:5176`, dados separados em `.audit/2026-10-17/`. Sem carregar `.env`, sem modelos pagos e sem chamadas externas de LLM.
- O build atual não compila. A inspeção de navegador usou o servidor de desenvolvimento com o código atual; não certifica um pacote de produção compilado.
- Primeiro foi testada a demo com as datas originais. Após comprovar o bloqueio da janela, apenas a cópia de teste dos metadados do Copom 280 recebeu `data_referencia=2026-10-17`. Conteúdo e respostas prontas continuaram os mesmos. Isso permite testar os passos seguintes, mas **não resolve nem aprova a demo original**.
- Testes de navegação foram E2E exploratórios executados em navegador real, com API e disco reais e provedor falso. Não existe uma suíte de regressão E2E versionada no projeto; esta auditoria não a adicionou.

## Resultado dos testes

| Verificação | Resultado | Evidência |
|---|---|---|
| Python: unitários, integração, API e avaliação | **1.529 passaram, 7 falharam**, 0 pulados; 1.536 casos, 362,53 s | `.audit/2026-10-17/pytest.xml`, `pytest-unrestricted.log` |
| Frontend Vitest | **247 passaram**, 23 arquivos | `vitest.json`, `vitest.log` |
| Ponte Netlify/Jev | **11 passaram** | execução de `npm test` em `netlify-jev` |
| Build frontend | **Falhou: TS2741** | `build.log` |
| Código de saída do script Windows | **Incorreto: 0 após teste falhar** | `runner-exit.log` |
| Provas adicionais de pipeline | **3 defeitos reproduzidos** | `provas_pipeline.py`, `provas_pipeline_resultados.json` |
| Provas adicionais de avaliação/exportação | **5 defeitos reproduzidos** | `provas_avaliacao_exportacao.py`, `resultados_avaliacao_exportacao.json` |

Os grupos Python se sobrepõem e não devem ser somados: 124 casos em módulos de API (119 passaram, 5 falharam); 31 de `pydantic-evals`, 33 de calibração, 23 de Qualidade e 24 de Fidelidade passaram. Os 110 casos em módulos com “video” no nome passaram. Incluem renderização efetiva de um MP4 curto e medição de dimensão, duração e áudio. Isso não equivale a assistir a um vídeo final de apresentação com narração real.

Comandos principais: `scripts\test.ps1 --junitxml=.audit/2026-10-17/pytest.xml`; `npm test` e `npm run build` em `web`; `npm test` em `netlify-jev`.

As primeiras tentativas sofreram restrições do ambiente: cache do uv, temporários do Vitest e comunicação local de processos. O Vitest passou ao usar uma pasta temporária no workspace. A execução Python válida foi feita fora desse isolamento, preservando a trava de rede da própria suíte. Esses incidentes de infraestrutura não foram contados como defeitos do produto.

### As sete falhas Python, explicadas

1. `tests/test_api_fontes.py:69`: presume Copom 280 como primeiro item; hoje há Copom 281, mais recente.
2. `tests/test_api_fontes.py:223`: presume Copom 280 como Destaque único.
3. `tests/test_api_fontes.py:238`: ao desligar importados, presume novamente Copom 280.
4. `tests/test_api_fontes.py:499`: presume uma única Ata e nenhuma Visão unida, mas há duas Atas versionadas.
5. `tests/test_api_geracao.py:345`: espera exatamente uma Ata na lista; existe também Copom 281, sem respostas Demo.
6. `tests/test_imagens.py:662`: exige que toda imagem local seja aprovada por humano. As nove sementes do Git são humanas, mas a biblioteca desta máquina contém também entradas validadas por visão/texto, categorias aceitas pelo modelo.
7. `tests/test_origens.py:64`: compara o catálogo efetivo da máquina com os padrões. `data/fontes/preferencias.json`, ignorado pelo Git, liga CVM; `carregar_catalogo` aplica essa preferência corretamente. O catálogo versionado continua inalterado.

As cinco primeiras são expectativas/fixtures desatualizadas. As duas últimas dependem indevidamente do estado local. Elas deixam a verificação vermelha, mas não demonstram que a ordenação, a curadoria ou a leitura de preferências do produto estejam erradas. Isolar os insumos dos testes e atualizar o acervo esperado é necessário; silenciar as asserções não seria uma correção adequada.

## Situação de cada processo

| Processo | O que foi demonstrado | Pendências |
|---|---|---|
| Ingestão | Upload de TXT pela tela, persistência, resumo, leitura integral e selo não calibrado; testes de PDF, importação e coleta | Concorrência pode sobrescrever Atas; cache ignora arquivos auxiliares; disponibilidade atual de BCB/CVM/B3 não foi testada ao vivo |
| Curadoria | Seleção e confirmação de notícia alimentam as três guias; ranking e união cobertos por testes | Demo original não oferece Ata elegível; sugestões da API não estão integradas à interface atual |
| Geração | Texto, Carrossel e Roteiro gerados nas três Audiências, por UI → API → fila → pipeline → disco | Demo pode acionar Jev com configuração real; modo Real não foi certificado contra os provedores externos |
| Avaliação | Recomendação adversarial foi detectada em Carrossel e Roteiro; métricas, correção e contratos têm cobertura ampla | A saída pela interface ignora o veto em caminhos específicos; decisão humana e derivados divergem |
| Exportação | ZIP local com seis PNGs; família Notícia pelo servidor com seis PNGs e legenda; PNGs abertos e conferidos | ZIP local aceita Recomendação; pacote antigo permanece acessível; ZIP de Texto omite o próprio texto |
| Vídeo | Roteiro e plano no navegador; composição/MP4 curto testados pela suíte | Cópia de prompt reprovado; H4 não libera plano/MP4; prévia salva impede build; narração/serviços de avatar não verificados |

## Achados prioritários

P1 = corrigir antes de considerar a entrega pronta. P2 = falha relevante de integridade, fluxo ou operação. A prioridade é relativa ao case, não uma classificação de vulnerabilidade externa.

### A01 — P1 — Carrossel com Recomendação vira ZIP de publicação

**Local:** `web/src/guias/carrossel/Editor.tsx:367`, `:411`, `:568`, `:692`.

**Reprodução E2E:** gerar Carrossel → Suno escuro → editar corpo do primeiro quadro com “Compre estas ações agora.” → salvar e reavaliar → Compliance mostra Recomendação detectada → Gerar carrossel → Exportar carrossel.

**Resultado:** download real de seis PNGs. O primeiro PNG contém a frase reprovada. A geração/exportação local exige montagem, mas não valida o Laudo da versão exportada. Evidência: `carrossel-reprovado.zip`, `exportado/slide-01.png`, `04-carrossel-recomendacao-exportavel.png`.

**Correção mínima:** invalidar a liberação ao editar e exigir aprovação da mesma revisão antes de exportar por qualquer caminho. O caminho local precisa respeitar o mesmo veto de Compliance do servidor. Preservar rascunhos para edição é diferente de disponibilizá-los como publicação.

### A02 — P1 — Prompt reprovado continua disponível

**Local:** `web/src/guias/video/TelaDoVideo.tsx:111`, `:132`, `:247`.

**Reprodução E2E:** pedir prompt de Roteiro aprovado → inserir a mesma frase adversarial numa fala → salvar/reavaliar. “Quero o prompt” e “Salvar no histórico” ficam desativados, mas o cartão já aberto permanece e o botão Copiar confirma “Copiado”. O próprio texto do cartão contém a frase proibida.

**Limite da prova:** a API de leitura do clipboard do navegador devolveu vazio; o conteúdo do cartão, a ação permitida e o aviso de sucesso foram observados. Não se afirma validação independente do clipboard do sistema.

**Correção:** invalidar o prompt ao editar; ocultar ou bloquear o cartão quando a revisão estiver pendente/reprovada. Evidência: `03-prompt-reprovado-copiavel.png`.

### A03 — P1 — Frontend não compila

**Local:** `web/src/guias/video/PreviaSalva.tsx:31`.

`CenasDoRoteiro` exige `aoEditar`, mas a prévia salva só fornece `blocos`. `npm run build` retorna TS2741, antes do Vite. Pela inspeção, a prévia também expõe controles que chamariam callback inexistente ao editar.

**Correção:** definir explicitamente o contrato da prévia somente leitura, ou fornecer fluxo de edição válido. O teste de compilação deve ser um requisito de conclusão, além do Vitest.

### A04 — P1 — Veto humano não bloqueia Pacote

**Local:** `src/suno/dominio.py:1067`.

`celula_liberada` retorna `True` imediatamente para Laudo aprovado e não consulta uma decisão humana posterior de reprovação. Prova AE-01: decisão `reprovada`, liberação `true`, um Pacote realmente montado.

**Correção:** definir a precedência explícita do veto humano e aplicá-la a todos os consumidores, sem permitir aprovação humana de Recomendação.

### A05 — P1 — Demo original não pode começar pela interface

**Local:** `web/src/nucleo/janela.ts:36`, `web/src/nucleo/pedido.ts:40`.

Em 17/10/2026, Copom 280 (05/08) tem 73 dias e Copom 281 (16/09) tem 31. A janela exclui ambos. Além disso, só o Copom 280 possui respostas prontas. Navegador limpo, modo Demo, Copom: “Nada nos últimos 30 dias”.

**Correção:** oferecer um acervo demonstrativo explícito, preservando as datas reais, separado da janela de notícias recentes. Evidência: `01-demo-sem-noticias.png`. A geração controlada posterior não elimina este bloqueio.

### A06 — P1 — Demo pode depender de Jev real

**Local:** `src/suno/gerador/execucao.py:301` e configuração das camadas seguintes.

Trocar o Gerador para `falso` não desativa automaticamente Jev/Fidelidade. Prova com chave fictícia, rede bloqueada e cliente interceptado: `executar(..., 'falso')` chamou `ClienteJev.pontuar` uma vez. A suíte geral força essas camadas desligadas e não detecta esse cenário de máquina configurada.

**Correção:** tornar a política offline da Demo explícita em todas as camadas, inclusive montagem. A prova confirmou Jev; a participação de Fidelidade foi identificada por inspeção, sem chamada real.

### A07 — P1 — Script oficial de teste sinaliza sucesso após falha

**Local:** `scripts/test.ps1:4`.

Prova: executar `pwsh -NoProfile -File scripts/test.ps1 tests/test_api_geracao.py::test_a_ata_do_copom_280_diz_que_tem_demo`. O pytest imprime `1 failed`, mas o processo PowerShell termina com **0**. `$ErrorActionPreference='Stop'` não propaga por si só o erro do executável nativo.

**Correção:** propagar `$LASTEXITCODE`, como o próprio `scripts/setup.ps1` já faz. Evidência: `runner-exit.log`. Caso contrário, uma automação pode registrar sucesso falso.

### A08 — P2 — Edição não invalida o Pacote anterior

**Local:** `src/suno/api/app.py:1011`, `:1183`, `:1215`.

Prova AE-03: montar Pacote, editar para conteúdo com Recomendação, obter reprovação, baixar Pacote antigo com status 200 e aprová-lo em H5. A prova usa chamadas diretas dos endpoints, sem transporte HTTP.

**Impacto:** o arquivo baixado é antigo; não se afirma que a edição reprovada entrou nesse ZIP. O defeito é a divergência silenciosa entre conteúdo atual, Laudo e Pacote considerado publicável.

**Correção:** associar derivados à revisão/hash do conteúdo, invalidar H5 após edição e conferir a versão ao baixar/aprovar.

### A09 — P2 — Salvar edição de Visão unida pode falhar

**Local:** `src/suno/revisao.py:149`; modelo em `src/suno/dominio.py:278`.

Prova AE-02: Âncora textual em Visão unida causa `AttributeError: 'AncoraTextual' object has no attribute 'chave'`. A rotina itera Âncoras textuais e numéricas como se todas tivessem `chave`. A rota não trata essa exceção; o efeito previsto no transporte HTTP é 500.

**Correção:** usar identificadores apropriados a cada tipo e cobrir edição de união, além da geração da união.

### A10 — P2 — ZIP de Texto omite o Texto

**Local:** `src/suno/api/app.py:1186`.

Prova AE-04: `texto.md` existe no Pacote em disco, mas o ZIP contém somente `legenda.txt`. O filtro também exclui `plano.json` e `plano.md` de Roteiro; essa segunda exclusão foi identificada no código.

**Correção:** listar artefatos esperados por Formato e validar o conteúdo do ZIP final, não apenas os arquivos em disco.

### A11 — P2 — H4 libera Pacote, mas não plano/vídeo

**Local:** `src/suno/video/render.py:514`, `src/suno/api/app.py:1066`.

Prova AE-05: Roteiro reprovado por métrica, aprovado por humano e liberado por `celula_liberada`; vídeo lança `ValueError` e plano responde 409. Esses consumidores verificam apenas o destino automático original.

**Correção:** unificar a regra de liberação com a correção de A04, preservando o veto obrigatório de Recomendação.

### A12 — P2 — Histórico não acompanha as gerações iniciadas na sessão

**Local:** `web/src/guias/historico/index.tsx:58`, `web/src/nucleo/precarga.ts:29`.

**Prova E2E:** iniciar app sem execuções → gerar Texto, Roteiro e Carrossel → Histórico permanece vazio. Após F5, as três Saídas aparecem. O polling só começa se o cache já contiver uma execução em andamento; criar/concluir não invalida essa lista.

**Correção:** atualizar o cache nos eventos de criação/conclusão e/ou na entrada da guia. Evidência: `02-historico-desatualizado.png`.

### A13 — P2 — Importações simultâneas podem sobrescrever uma Ata

**Local:** `src/suno/origens/importacao.py:86`, `src/suno/api/app.py:669`.

Prova com intercalamento controlado: duas importações diferentes escolhem o mesmo título/data/identificador antes de gravar. Ambas retornam sucesso; sobra um único TXT com o segundo conteúdo. A escolha do nome e sua reserva não são indivisíveis; a API permite execução concorrente no threadpool.

**Correção:** reserva exclusiva do identificador ou trava cobrindo escolha e persistência. O teste atual cobre duplicatas sequenciais.

### A14 — P2 — Cache de Ata ignora alterações nos arquivos auxiliares

**Local:** `src/suno/origens/repositorio.py:104`.

Prova: carregar Ata, corrigir título no JSON e carregar novamente; a API interna devolve o título antigo. A chave de cache considera o arquivo principal, mas a leitura também depende do JSON e, para PDF, do TXT auxiliar.

**Correção:** incluir todos os arquivos relevantes na assinatura ou invalidar explicitamente após atualização/reextração. O cenário de JSON foi reproduzido; o de TXT foi identificado pelo mesmo mecanismo.

### A15 — P2 — Modal não contém o foco

**Local:** `web/src/interface/Modal.tsx:19`.

Prova E2E: abrir Importar documento, pressionar Shift+Tab; o foco vai ao checkbox de seleção da Ata atrás do modal. O fundo não está `inert`, e não há ciclo de foco. `aria-modal` não implementa esse comportamento sozinho.

**Correção:** conter Tab/Shift+Tab e tornar o fundo inerte durante abertura, mantendo restauração do foco ao fechar.

### A16 — P2 — Cartão de notícia contém botões aninhados

**Local:** `web/src/interface/CartaoDeNoticia.tsx:20`, `:74`, `:95`.

O cartão clicável é um `button` que contém outro `button` usado como checkbox. O navegador registrou os avisos React “button cannot be a descendant of button” e “button cannot contain a nested button” ao abrir a lista e importar. Isso é marcação interativa inválida e torna a semântica de navegação/seleção ambígua. Os cliques exercitados funcionaram; não se afirma que houve falha de hidratação, pois a interface atual é renderizada no cliente.

**Correção:** separar a ação de abrir e a ação de selecionar em controles irmãos. Evidência: `browser-console.json`. Esse arquivo também contém erros de MutationObserver cuja origem não foi estabelecida; eles não foram atribuídos ao produto.

## Outros pontos de atenção, sem reprodução E2E nesta rodada

- **Texto analítico não apresenta Laudo nem reavalia a edição local** (`web/src/guias/texto/index.tsx:89`). É uma lacuna de produto documentada em FUNCIONAMENTO, não uma regressão presumida. Distinguir rascunho de versão avaliada e dar acesso ao veredito antes de tratar o conteúdo como pronto.
- **Texto salvo pode receber a proveniência errada ao reabrir** (`web/src/guias/texto/index.tsx:47`, `:72`): usa `sessao.execucaoId` atual ao salvar HTML de outro item aberto. Confirmar com duas Saídas e proteger o vínculo entre conteúdo e Ata.
- **Falha de polling fica invisível** (`web/src/nucleo/sessao.tsx:202`): erros de acompanhamento são ignorados indefinidamente. Uma API indisponível pode deixar “Gerando…” sem orientação. Mostrar desconexão, preservar ID e oferecer recuperação.
- **Persistência de `execucao.json` sem troca atômica** (`src/suno/gerador/execucao.py:380`): risco de leitura parcial/perda após interrupção, identificado por código. Não foi injetada falha de disco. Reutilizar a estratégia de temporário + substituição já empregada no andamento.

## Avaliação heurística da interface

| Heurística | Observação | Consequência |
|---|---|---|
| Visibilidade do estado | Há andamento por Audiência e métricas visíveis em Carrossel/Vídeo; Histórico desatualizado e erros de polling silenciosos | Usuário não sabe se perdeu trabalho ou se o servidor parou |
| Prevenção de erro | Recomendação é detectada, mas exportação/cópia permanecem possíveis | A ação mais importante contradiz o veredito |
| Consistência | Texto, Carrossel local, família no servidor, plano e MP4 aplicam regras distintas | Mesmo conteúdo recebe permissões diferentes conforme a tela |
| Controle e recuperação | Seleção persiste na sessão e as guias preservam conteúdo; H4/H5 existem na API, mas não estão expostos como filas na UI atual | Revisão humana é tecnicamente disponível, mas o fluxo operacional fica incompleto |
| Reconhecimento | Barra lateral de desktop usa ícones sem rótulo permanente; há nomes acessíveis | Curva de descoberta para quem não conhece a ferramenta; validar com usuário iniciante |
| Acessibilidade | Guias ocultas usam `inert`; modal deixa foco escapar | Boa base de navegação, com falha objetiva no diálogo |
| Responsividade | Testado 390×844: navegação inferior, colunas empilhadas e prévia alcançável por rolagem | Fluxo básico utilizável; formulário longo exige bastante rolagem. Não foi certificada conformidade WCAG nem todos os dispositivos |
| Clareza de linguagem | “Gerar” inicia conteúdo e “Gerar carrossel” monta imagens; “Salvar” pode significar navegador ou servidor | Explicitar destino e estado do salvamento reduz interpretações erradas |

O aspecto visual é coerente, com tipografia e hierarquia consistentes. O problema central de finalização é a coerência dos estados e das permissões, não uma necessidade de redesenhar famílias visuais.

## Lacunas de cobertura e entrega

- Vitest roda em ambiente `node`, apenas `src/**/*.test.ts`: cobre lógica pura, mas não componentes, navegação, foco, salvamento nem download. Por isso 247 testes verdes convivem com build quebrado e falhas E2E.
- Não foi localizada suíte E2E versionada nem pipeline CI em `.github/`. A ausência não prova inexistência de automação externa ao repositório.
- Os testes de integração usam serviços simulados e rede bloqueada: não certificam disponibilidade, cotas, modelos e credenciais atuais de Gemini/Groq/Jev, busca de fotos, BCB/CVM/B3 ou narração.
- `docs/relatorio-experimental.md:3` declara medições de 19/09, anteriores às mudanças atuais. A documentação reconhece a defasagem; falta renová-las para defender o sistema atual.
- A mesma documentação registra Calibração humana pendente e ausência de Kappa real (`:169`–`:179`). Código/testes de cálculo não substituem os rótulos das duas pessoas. É pendência de validação de domínio, não tarefa a ser inventada pelo agente.
- H4/H5 aparecem em partes da arquitetura como filas de interface, mas o funcionamento atual e o código mostram que não estão expostos. Alinhar a narrativa da apresentação com o produto entregue.
- O ramo de vídeo passou nos testes, incluindo MP4 curto. A auditoria não certificou narração, avatar, sincronização de um vídeo final nem o material audiovisual da apresentação.
- Licença das fotos não verificada é limitação explícita do MVP/ADR; não foi reclassificada como regressão.

## Ordem recomendada para finalizar

1. **Fechar os bloqueios:** build (A03), propagação de falha nos testes (A07), veto consistente de Recomendação e decisão humana (A01/A02/A04). Acrescentar regressões sobre o arquivo/copiar final, não só sobre o Laudo.
2. **Vincular conteúdo e derivados:** revisão identificada, invalidação de Pacote/prompt/H5 após edição, mesma regra de liberação para ZIP/plano/MP4 (A08–A11).
3. **Garantir demonstração repetível:** Demo disponível sem falsificar datas e sem depender de chaves/rede (A05/A06); preparar MP4 final antes da apresentação.
4. **Resolver integridade e operação:** concorrência da importação, cache, Histórico, foco e semântica dos controles (A12–A16); testes isolados de dados locais; revisar os pontos de atenção de Texto/polling/persistência.
5. **Fechar evidência acadêmica:** rodar novamente build + todas as suítes + cenários E2E abaixo; atualizar relatório experimental; concluir calibração humana e conferir os seis entregáveis com o enunciado.

Critério de saída: compilação concluída, suíte determinística verde em ambiente limpo e em máquina com dados locais, erro propagado pelo runner, demo offline acessível, nenhum conteúdo reprovado exportável como publicação, derivados consistentes com a revisão atual e evidências atuais dos entregáveis. Até lá, a conclusão responsável é **funcional em parte, com bloqueadores comprovados**.

## Evidências E2E e reprodução

Todos os caminhos abaixo estão em `.audit/2026-10-17/`:

Os servidores temporários foram encerrados ao terminar a inspeção. Os arquivos com frases adversariais são evidências de teste, não materiais de publicação.

| Cenário | Resultado |
|---|---|
| Demo original, navegador limpo | Falhou: nenhuma Ata dentro da janela (`01-demo-sem-noticias.png`) |
| Importar TXT, consultar resumo e texto integral | Passou (`07-importacao.png`, `fontes/`) |
| Selecionar Ata controlada e gerar Texto para 3 Audiências | Passou (`execucoes/*134329/`) |
| Gerar Roteiro para 3 Audiências e obter plano/prompt | Passou no fluxo inicial (`execucoes/*134400/`) |
| Gerar Carrossel para 3 Audiências | Passou (`execucoes/*134507/`) |
| Reavaliar Roteiro adversarial e bloquear cópia | Falhou: cartão permanece e informa Copiado (`03-prompt-reprovado-copiavel.png`) |
| Reavaliar Carrossel adversarial e bloquear ZIP | Falhou: PNG contém Recomendação (`carrossel-reprovado.zip`, `exportado/slide-01.png`) |
| Renderizar família Notícia e baixar pacote | Passou: 6 PNGs + legenda (`carrossel-noticia.zip`, `05-familia-noticia.png`) |
| Mostrar novas Saídas no Histórico sem F5 | Falhou (`02-historico-desatualizado.png`) |
| Recarregar Histórico e consultar as 3 Saídas persistidas | Passou |
| Navegar entre as 6 guias e preservar estado na sessão | Passou no percurso exercitado |
| Tela de 390×844: navegação e acesso à prévia | Passou na amostra (`06-mobile-carrossel.png`) |
| Modal de importação conter Shift+Tab | Falhou: foco no checkbox da Ata atrás do modal |

As oito provas adicionais podem ser repetidas com o Python do ambiente, a partir da raiz:

```powershell
.venv/Scripts/python.exe .audit/2026-10-17/provas_pipeline.py
.venv/Scripts/python.exe .audit/2026-10-17/provas_avaliacao_exportacao.py
```

Elas usam temporários, chaves fictícias/interceptação e bloqueiam rede. Os status de AE-03/04/05 são de objetos de resposta/exceções dos endpoints chamados diretamente; não devem ser apresentados como testes HTTP. Os E2E de navegador, por sua vez, utilizaram transporte HTTP real local.

## Validação final da remediação

Esta seção substitui o parecer inicial para o código corrigido em 17/10/2026. Os achados A01–A16
foram encerrados com regressões automatizadas ou repetição do cenário E2E correspondente.

| Verificação final | Resultado | Evidência |
|---|---|---|
| Python: unitários, integração, API e avaliação | **1.565 passaram**, 0 falhas; 483,56 s | `correcoes-pytest-final.log`, `correcoes-pytest-final.xml` |
| Frontend Vitest | **264 passaram**, 0 falhas | `correcoes-vitest-conclusao.json` |
| Build frontend | **Concluído** | `correcoes-build-conclusao.log` |
| Ponte Netlify/Jev | **11 passaram**, 0 falhas | `correcoes-jev-final.log` |
| Propagação de falha pelo runner Windows | **Correta:** teste inexistente terminou com código 4 | `runner-exit-final.log` |
| Vocabulário novo da alteração | **0 nomes novos** da lista *Avoid* em relação ao `HEAD` auditado | `vocabulario-diferenca.log` |

No navegador real, com API e persistência locais, a Demo exibiu o acervo versionado mesmo com as
datas originais. Texto, Carrossel e Roteiro foram gerados; uma edição com Recomendação invalidou a
aprovação e bloqueou salvar, copiar, montar e exportar conforme o fluxo. O Histórico recebeu a nova
Saída sem recarregar a página. O modal conteve `Tab` e `Shift+Tab`, manteve o fundo inerte, e o fluxo
de ingestão permaneceu utilizável em 390×844. As capturas estão em `correcoes-e2e/`.

Também foi provada a coerência no servidor: a decisão humana prevalece, todo derivado carrega a
assinatura da revisão liberada, revisões antigas deixam de ser servidas, e uma montagem em andamento
não aparece como Pacote concluído nem entra no ZIP global. A importação concorrente preserva os dois
documentos, alterações em metadados e TXT invalidam o cache, e gravações críticas usam substituição
atômica.

### Limites que permanecem

- Os testes locais usam provedores simulados e rede bloqueada. Disponibilidade, cota e credenciais
  atuais de Gemini, Groq, Jev, fontes externas, busca de fotos e narração precisam de uma prova
  operacional separada quando houver ambiente autorizado.
- A calibração humana e o Kappa dependem dos rótulos das duas pessoas do projeto. Não foram
  fabricados nesta correção, e o relatório experimental de 19/09 continua identificado como histórico.
- Os cenários de navegador foram repetidos e documentados, mas ainda não há uma suíte E2E de
  navegador versionada para execução automática em CI.
- A compilação emite apenas o aviso de pacote JavaScript maior que 500 kB. Não bloqueia a entrega,
  mas merece divisão de código se o tempo de carregamento medido se tornar um problema.

**Parecer após a remediação:** o código e a Demo local satisfazem o critério técnico de saída da
auditoria: compilação verde, suíte determinística verde, falhas propagadas, conteúdo reprovado sem
saída de publicação e derivados vinculados à revisão vigente. O encerramento acadêmico ainda exige
a calibração humana, a atualização das medições experimentais e a conferência final dos seis
entregáveis; integrações externas só podem ser certificadas em execução real autorizada.
