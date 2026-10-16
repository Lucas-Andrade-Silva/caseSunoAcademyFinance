# Ponte do Jev (Netlify Function)

O Suno Content (Python) não chama o Jev direto: a Netlify só injeta a chave e o endereço do Jev
(`TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`) dentro de uma Function publicada. Esta Function recebe o
mesmo corpo que o `systemone` da TypeSafe aceita, repassa e devolve a resposta. [ADR 0035](../docs/DECISOES.md).

Cada chamada gasta **créditos da sua conta Netlify**. Por isso a Function recusa tudo que não traga
`Authorization: Bearer <JEV_PROXY_SECRET>`, e recusa de vez se o segredo não estiver configurado.

## Publicar (uma vez)

Precisa de uma conta Netlify em plano com créditos (o Free serve; o limite é de 90 créditos por minuto)
e do Netlify CLI. Dentro desta pasta:

```bash
npm install -g netlify-cli
netlify login
netlify sites:create --name suno-jev-<algo-unico>
```

Gere um segredo e guarde-o no site (ele **não** é a chave do Jev, é a senha desta ponte):

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
netlify env:set JEV_PROXY_SECRET <o valor gerado>
```

Publique em produção. O AI Gateway só liga depois do primeiro deploy de produção:

```bash
netlify deploy --prod
```

## Ligar ao Suno Content

No `.env` da raiz do repositório:

```
SUNO_JEV=1
JEV_URL=https://<seu-site>.netlify.app/.netlify/functions/jev
JEV_API_KEY=<o mesmo valor de JEV_PROXY_SECRET>
```

Atenção: `JEV_API_KEY` passa a ser o **segredo da ponte**, não a chave da Netlify nem da TypeSafe.

## Conferir

O diagnóstico mostra o que a Function enxerga, sem nenhum valor secreto:

```bash
curl -H "Authorization: Bearer <o segredo>" https://<seu-site>.netlify.app/.netlify/functions/jev
```

Esperado: `TYPESAFE_API_KEY: "definida"`. Se vier `"ausente"`, o AI Gateway não ligou: confira o deploy de
produção e o plano. Depois, uma chamada de verdade, na raiz do repositório:

```bash
uv run python scripts/testar_llm_de_avaliacao.py jev
```

## O que não foi verificado

- O formato de `TYPESAFE_BASE_URL` não está na documentação da Netlify. A Function aceita a base com ou
  sem `/v1`. O diagnóstico (`endereco_usado`) mostra o endereço que ela montou.
- Se o AI Gateway do plano Free cobre o Jev e quantos créditos cada chamada gasta.

## Testes

```bash
node --test testes/jev.test.mjs
```
