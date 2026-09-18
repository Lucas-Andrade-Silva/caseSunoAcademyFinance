# Recomendação é detectada por padrão sintático, não só por lista de palavras

Recomendação é a linha que o sistema não cruza, e o CLAUDE.md já estabelece que ela é métrica do
Laudo, não instrução de prompt. Falta decidir **como** se mede.

O caminho óbvio é uma blocklist: "compre", "venda", "recomendamos". Ele falha, e a pesquisa diz
por quê: escorregar para Recomendação quase nunca é vocabulário óbvio — é **personalização**.
Referência implícita à situação do leitor mais direção de ação. "É hora de reduzir sua exposição"
não contém nenhuma palavra proibida e é exatamente o que a regulação impede. Um estudo com
profissionais de compliance financeiro mostra que a fronteira é ambígua até para humanos
treinados; uma lista de palavras não vai resolver o que um humano treinado hesita em classificar.

Decisão: a detecção soma duas camadas determinísticas.

1. **Léxico**, organizado por *pode* e *não pode* em vez de lista plana de banidos. Proibido é
   personalização e promessa de retorno; permitido é discussão neutra em terceira pessoa.
2. **Padrões sintáticos** sobre POS tagging (spaCy, modelo `pt_core_news_sm`): sujeito
   "você"/"investidor"/elidido de segunda pessoa + modal de obrigação ("deve", "precisa",
   "convém") + verbo de ação financeira. É o padrão que pega a paráfrase que a lista deixa passar.

Nada disso passa por LLM. Um paper de 2026 mostra LLM-juiz de compliance dando vereditos
diferentes para o mesmo input e alucinando evidência para justificar o veredito depois. Uma linha
que reprova não pode mudar de opinião entre duas execuções.

Um **canary set adversarial versionado** em `data/` guarda paráfrases sutis de Recomendação
("seria prudente considerar reduzir posição") e roda a cada mudança de Léxico, padrão ou Limiar.
É a suíte de regressão contra fuga por paráfrase.

## Consequências

O Avaliador ganha uma dependência de peso — o modelo `pt_core_news_sm` do spaCy, cerca de 15 MB.
Ele roda offline e é versionado como qualquer outro dado, então a propriedade que o
[ADR 0001](0001-gerador-e-avaliador-como-modulos-separados.md) defende — Avaliador sem LLM e sem
rede, testável em CI — se mantém. Mas é uma dependência a validar cedo, não na última semana: se
o modelo não carregar offline no ambiente de CI, a decisão precisa ser revista enquanto ainda há
tempo.

A **allowlist de moldes sintáticos aprovados** — definir positivamente as formas aceitas de
informar e reprovar tudo fora delas — foi considerada e recusada para este prazo. É mais estrita e
mais difícil de burlar por paráfrase, mas o risco de reprovar Célula boa é alto e o trabalho
linguístico não cabe em duas semanas. Fica registrada como o próximo passo natural se a taxa de
fuga medida pelo canary set não for aceitável.

Léxico, padrões sintáticos e canary set são conhecimento de domínio: pertencem à pessoa dona do
Avaliador, como o CLAUDE.md já estabelece para Léxico, Limiares e Calibração.
