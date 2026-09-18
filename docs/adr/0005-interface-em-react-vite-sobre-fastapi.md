# A interface é React + Vite sobre FastAPI; Streamlit e Next.js foram rejeitados

O enunciado sugere Streamlit, Gradio ou FastAPI + React. Escolhemos **FastAPI servindo
uma SPA em React + Vite + Tailwind**, entregue como PWA para instalar no celular.

**Streamlit foi rejeitado por posicionamento**, não por capacidade: ele entrega o
Entregável 4 sem esforço, mas tem cara de protótipo, e este projeto é apresentado como
produto. **Next.js foi rejeitado por custo conceitual**: o FastAPI já é o servidor —
obrigatório, porque o pipeline é Python — e o Next.js traria um segundo servidor, em
outra linguagem, com a distinção entre componente de servidor e de cliente que é
justamente onde um time aprendendo trava. O benefício principal dele, renderização no
servidor para indexação, não vale nada num painel que a banca abre localmente.

Aplicativo nativo foi considerado e descartado: custaria dias que o time não tem, exigiria
gravar tela de celular na demo, e **não cumpriria o Entregável 4, que pede literalmente
"aplicação web"**. O PWA entrega a sensação de app pelo preço da web.

## Consequências

O contrato entre back-end e front-end é **gerado do OpenAPI do FastAPI**, e não escrito à
mão nos dois lados. Com duas pessoas sem domínio forte de nenhuma das linguagens, a
divergência silenciosa entre cliente e servidor é a classe de bug que mais consumiria
tempo, e geração elimina a classe inteira.

A interface é construída **por último**. O contrato é definido cedo; a tela vem depois do
Gerador e do Avaliador estarem de pé. O esqueleto ponta a ponta do dia 4 pode cuspir JSON
no terminal sem prejuízo nenhum.

Esta escolha custa 2 a 3 dias-pessoa a mais que a alternativa em Python puro, e esses dias
saem da extensão de vídeo, conforme a ordem de sacrifício registrada no `CLAUDE.md`.
