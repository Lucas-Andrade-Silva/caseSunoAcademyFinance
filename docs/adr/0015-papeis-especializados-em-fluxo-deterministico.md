# Papéis especializados em fluxo determinístico

O produto passou a exigir cinco responsabilidades explícitas: um curador, três geradores de
persona e um avaliador transversal. Esses papéis não alteram a conclusão do
[ADR 0010](0010-gerador-nao-e-agente-com-tools-nem-usa-mcp.md): o sistema não precisa de loop
ReAct, descoberta de ferramentas, LangGraph ou MCP.

Adotamos:

1. `AgenteCurador` prepara um `DossieCurado` com a fonte e as Âncoras conferidas.
2. Três `AgenteGeradorPersona` recebem o mesmo dossiê. Cada um fica preso a uma Audiência.
3. Código determina os três Formatos, as nove posições, a ordem e o armazenamento.
4. `avaliar_matriz` confere completude, unicidade, destinos e referências depois dos ciclos.
5. `SelecaoCuradoria` aceita vários itens no modo `unida` e exatamente um no modo `separada`.

"Agente" aqui nomeia responsabilidade e prompt especializado. Nenhum papel escolhe a próxima
etapa, cria novas ações ou acessa ferramentas livremente.

## Consequências

Todas as personas partem do mesmo núcleo factual. Mudam linguagem e profundidade, não os fatos.
O custo permanece previsível. O provedor falso continua cobrindo o fluxo sem rede. Um framework
agêntico só será reconsiderado quando existir uma decisão dinâmica que o código fixo não modele.
