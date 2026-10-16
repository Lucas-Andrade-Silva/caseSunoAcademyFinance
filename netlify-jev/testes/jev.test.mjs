// node --test netlify-jev/testes/jev.test.mjs
import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";

import jev, { enderecoDoSystemone } from "../functions/jev.mjs";

const SEGREDO = "segredo-de-teste";
const original = { fetch: globalThis.fetch, env: { ...process.env } };
let chamadas;

beforeEach(() => {
  chamadas = [];
  process.env.JEV_PROXY_SECRET = SEGREDO;
  process.env.TYPESAFE_API_KEY = "chave-da-netlify";
  delete process.env.TYPESAFE_BASE_URL;
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push({ url, opcoes });
    return new Response(JSON.stringify({ answers: { tom: { type: "score", score: 2 } } }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };
});

afterEach(() => {
  globalThis.fetch = original.fetch;
  process.env = { ...original.env };
});

const pedido = (corpo, { metodo = "POST", segredo = SEGREDO } = {}) =>
  new Request("https://site.test/.netlify/functions/jev", {
    method: metodo,
    headers: { authorization: `Bearer ${segredo}`, "content-type": "application/json" },
    ...(metodo === "POST" ? { body: typeof corpo === "string" ? corpo : JSON.stringify(corpo) } : {}),
  });

const VALIDO = { state: { conteudo: "texto" }, questions: { tom: { type: "score", instructions: "?", criteria: ["a", "b"] } } };

test("sem o segredo certo, recusa e não chama o Jev", async () => {
  const resposta = await jev(pedido(VALIDO, { segredo: "errado" }));
  assert.equal(resposta.status, 401);
  assert.equal(chamadas.length, 0);
});

test("sem JEV_PROXY_SECRET configurado, recusa tudo (falha fechada)", async () => {
  delete process.env.JEV_PROXY_SECRET;
  const resposta = await jev(pedido(VALIDO));
  assert.equal(resposta.status, 500);
  assert.equal(chamadas.length, 0);
});

test("repassa state, model e questions ao systemone com a chave da Netlify", async () => {
  const resposta = await jev(pedido(VALIDO));
  assert.equal(resposta.status, 200);
  assert.equal(chamadas.length, 1);
  const { url, opcoes } = chamadas[0];
  assert.equal(url, "https://api.typesafe.ai/v1/systemone");
  assert.equal(opcoes.headers.authorization, "Bearer chave-da-netlify");
  const enviado = JSON.parse(opcoes.body);
  assert.deepEqual(Object.keys(enviado).sort(), ["model", "questions", "state"]);
  assert.equal(enviado.model, "jev-latest");
  assert.deepEqual((await resposta.json()).answers.tom.score, 2);
});

test("campos desconhecidos do corpo não são repassados", async () => {
  await jev(pedido({ ...VALIDO, intruso: "x" }));
  assert.equal("intruso" in JSON.parse(chamadas[0].opcoes.body), false);
});

test("usa TYPESAFE_BASE_URL quando a Netlify a define", async () => {
  process.env.TYPESAFE_BASE_URL = "https://gateway.exemplo.test/typesafe/";
  await jev(pedido(VALIDO));
  assert.equal(chamadas[0].url, "https://gateway.exemplo.test/typesafe/v1/systemone");
});

test("monta o endereço com ou sem /v1", () => {
  assert.equal(enderecoDoSystemone(undefined), "https://api.typesafe.ai/v1/systemone");
  assert.equal(enderecoDoSystemone("https://g.test/v1"), "https://g.test/v1/systemone");
  assert.equal(enderecoDoSystemone("https://g.test/v1/systemone"), "https://g.test/v1/systemone");
});

test("corpo que não é JSON ou sem questions dá 400", async () => {
  assert.equal((await jev(pedido("isto não é json"))).status, 400);
  assert.equal((await jev(pedido({ state: "x" }))).status, 400);
  assert.equal(chamadas.length, 0);
});

test("corpo grande demais dá 413", async () => {
  const grande = { ...VALIDO, state: "x".repeat(300 * 1024) };
  assert.equal((await jev(pedido(grande))).status, 413);
});

test("método diferente de POST e GET dá 405", async () => {
  assert.equal((await jev(pedido(null, { metodo: "DELETE" }))).status, 405);
});

test("GET devolve o diagnóstico sem nenhum valor secreto", async () => {
  const resposta = await jev(pedido(null, { metodo: "GET" }));
  const texto = await resposta.text();
  assert.equal(resposta.status, 200);
  assert.ok(texto.includes("https://api.typesafe.ai/v1/systemone"));
  assert.ok(!texto.includes("chave-da-netlify") && !texto.includes(SEGREDO));
});

test("erro do Jev volta com o mesmo status, e falha de rede vira 504 sem vazar a chave", async () => {
  globalThis.fetch = async () => new Response('{"detail":"quota"}', { status: 429 });
  assert.equal((await jev(pedido(VALIDO))).status, 429);

  globalThis.fetch = async () => {
    throw new Error("ECONNRESET com chave-da-netlify");
  };
  const resposta = await jev(pedido(VALIDO));
  assert.equal(resposta.status, 504);
  assert.ok(!(await resposta.text()).includes("chave-da-netlify"));
});
