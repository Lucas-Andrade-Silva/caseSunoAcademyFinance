// A ponte entre o Suno Content e o Jev (TypeSafe) pelo AI Gateway da Netlify (ADR 0035).
//
// O Python não chama o Jev direto: a Netlify só injeta o endereço (TYPESAFE_BASE_URL) e a chave
// (TYPESAFE_API_KEY) dentro de uma Function publicada. Esta Function recebe o mesmo corpo que o
// `systemone` da TypeSafe aceita ({ state, model, questions }), repassa e devolve a resposta.
//
// Quem pode chamar: só quem manda `Authorization: Bearer <JEV_PROXY_SECRET>`. Cada chamada gasta
// créditos da sua conta Netlify, então a Function recusa tudo sem o segredo, e recusa de vez se o
// segredo não estiver configurado.

import { timingSafeEqual } from "node:crypto";

const URL_PADRAO = "https://api.typesafe.ai";
const TAMANHO_MAXIMO_BYTES = 256 * 1024;
const TEMPO_LIMITE_MS = 20_000;
const CAMPOS_REPASSADOS = ["state", "model", "questions"];

const json = (corpo, status = 200) =>
  new Response(JSON.stringify(corpo), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });

/** O endereço completo do systemone, a partir de uma base com ou sem /v1 (a Netlify não documenta o formato). */
export function enderecoDoSystemone(base) {
  const limpa = (base || URL_PADRAO).replace(/\/+$/, "");
  if (limpa.endsWith("/v1/systemone")) return limpa;
  if (limpa.endsWith("/v1")) return `${limpa}/systemone`;
  return `${limpa}/v1/systemone`;
}

function segredoConfere(cabecalho, segredo) {
  const recebido = Buffer.from((cabecalho || "").replace(/^Bearer\s+/i, ""));
  const esperado = Buffer.from(segredo);
  return recebido.length === esperado.length && timingSafeEqual(recebido, esperado);
}

export default async (req) => {
  const segredo = process.env.JEV_PROXY_SECRET;
  if (!segredo) {
    return json({ erro: "JEV_PROXY_SECRET não está configurado nesta Function." }, 500);
  }
  if (!segredoConfere(req.headers.get("authorization"), segredo)) {
    return json({ erro: "não autorizado" }, 401);
  }

  const endereco = enderecoDoSystemone(process.env.TYPESAFE_BASE_URL);
  const chave = process.env.TYPESAFE_API_KEY;

  // GET devolve o diagnóstico: o que a Function enxerga, sem nenhum valor secreto.
  if (req.method === "GET") {
    return json({
      endereco_usado: endereco,
      TYPESAFE_API_KEY: chave ? "definida" : "ausente",
      TYPESAFE_BASE_URL: process.env.TYPESAFE_BASE_URL ? "definida" : "ausente (vale o padrão da TypeSafe)",
    });
  }
  if (req.method !== "POST") {
    return json({ erro: "use POST" }, 405);
  }
  if (!chave) {
    return json({ erro: "TYPESAFE_API_KEY ausente: publique o site (o AI Gateway só liga depois do primeiro deploy de produção)." }, 500);
  }

  const bruto = await req.text();
  if (Buffer.byteLength(bruto) > TAMANHO_MAXIMO_BYTES) {
    return json({ erro: "corpo grande demais" }, 413);
  }
  let corpo;
  try {
    corpo = JSON.parse(bruto);
  } catch {
    return json({ erro: "o corpo não é JSON" }, 400);
  }
  if (corpo === null || typeof corpo !== "object" || corpo.state === undefined || typeof corpo.questions !== "object") {
    return json({ erro: "faltam state e questions" }, 400);
  }
  const repassado = Object.fromEntries(CAMPOS_REPASSADOS.filter((c) => c in corpo).map((c) => [c, corpo[c]]));
  repassado.model ??= "jev-latest";

  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), TEMPO_LIMITE_MS);
  try {
    const resposta = await fetch(endereco, {
      method: "POST",
      headers: { authorization: `Bearer ${chave}`, "content-type": "application/json" },
      body: JSON.stringify(repassado),
      signal: controle.signal,
    });
    return new Response(await resposta.text(), {
      status: resposta.status,
      headers: { "content-type": resposta.headers.get("content-type") || "application/json" },
    });
  } catch (erro) {
    const tempo = erro?.name === "AbortError";
    return json({ erro: tempo ? "o Jev não respondeu a tempo" : "a chamada ao Jev não chegou" }, 504);
  } finally {
    clearTimeout(relogio);
  }
};
