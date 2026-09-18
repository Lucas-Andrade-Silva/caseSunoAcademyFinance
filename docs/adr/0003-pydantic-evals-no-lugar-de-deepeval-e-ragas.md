# A suíte de avaliação usa `pydantic-evals`, não DeepEval nem Ragas

O enunciado do case sugere DeepEval ou Ragas. Investigamos os dois e rejeitamos ambos
como espinha dorsal da suíte.

**DeepEval** liga telemetria por padrão, incluindo IP público, e tem histórico ruim
nesse terreno: uma issue de fevereiro de 2026 documentou a biblioteca sequestrando o
`TracerProvider` global do OpenTelemetry e exportando spans *da aplicação hospedeira*
para um serviço de terceiro com chave embutida no código. O exportador foi removido
numa versão seguinte, mas não confirmamos que o comportamento sumiu por completo. O
painel gratuito permite 5 execuções por semana, o que não sustenta um ciclo de
calibração.

**Ragas** está há oito meses sem release no PyPI, a versão 0.4 removeu APIs centrais, e
o caminho de migração que a própria documentação recomenda está quebrado no pacote
publicado. Além disso, a maior parte das métricas dele é específica de RAG — fidelidade
ao contexto recuperado, precisão de recuperação — e não de qualidade de conteúdo
gerado. Usaríamos uma fração pequena do framework herdando todo o seu churn.

Adotamos **`pydantic-evals`**: sem serviço externo, sem telemetria, conjuntos de casos
em YAML versionados no repositório, juiz por LLM embutido, avaliadores próprios para as
métricas determinísticas, e execução dentro do pytest. Conjunto de casos versionado no
git *é* a reprodutibilidade que o Entregável 6 exige, e o schema do resultado fica sob
nosso controle — que é o que permite o mesmo arquivo alimentar os testes, a interface e
o relatório.

## Consequências

Divergimos de uma sugestão explícita do enunciado, então o relatório final precisa
justificar a escolha. Isso é ganho, não risco: o Entregável 6 pede exatamente que o
time explique suas decisões de engenharia, e "avaliamos as duas ferramentas sugeridas e
recusamos as duas por estes motivos" é uma resposta mais forte que adotá-las sem
examinar.

Se alguma métrica pontual do DeepEval ou do Ragas for útil, ela entra chamada de dentro
de um avaliador nosso — como biblioteca, nunca como orquestrador.
