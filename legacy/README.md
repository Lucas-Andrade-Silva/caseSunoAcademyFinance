# legacy/

O que já cumpriu o seu papel e não descreve mais o sistema atual. Nada aqui é lido pelo código,
pelos testes ou pelos scripts, e nada foi apagado: os arquivos foram movidos com `git mv`, então
o histórico de cada um continua no `git log --follow`.

Os links relativos dentro destes arquivos foram escritos para o lugar antigo (`docs/`) e não
foram corrigidos de propósito: são registro histórico.

| Arquivo | O que era | Por que saiu |
|---|---|---|
| `docs/prompt-de-execucao.md` | O prompt que iniciou a construção do projeto (17/09/2026) | Já executado; fala em "catorze ADRs" e em etapas concluídas |
| `docs/plano-de-execucao.md` | O plano das etapas 0–3, com o dono de cada arquivo (18–19/09/2026) | Já executado; cita módulos que não existem mais (`comite/`, `sambanova.py`) |
| `docs/superpowers/` | Planos e especificações da interface e da inteligência visual (09–13/10/2026), com mockups | Já implementados; a interface atual está em `web/README.md` e no ADR 0028 |
| `docs/prompt-carrossel-suno-gemini.md` | Prompt para gerar carrosséis à mão no Gemini | Não é usado pelo pipeline; o visual vem das famílias (ADR 0030) |
| `docs/exemplos/carrossel-rubix-copom-281.json` | Exemplo de carrossel num formato externo | Esquema diferente do `Celula` do domínio; nada o lê |
| `docs/Guia completo do projeto Suno Content.docx`, `docs/Guia_resumido_Suno_Content.docx` | Guias em Word de 09/10/2026 | Anteriores ao Jev, à Fidelidade e às famílias visuais; o `README.md` e `docs/` os substituem |
