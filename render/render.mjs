// Uso: node render.mjs <trabalho.json>
// O trabalho lista {html, png, json}: abre cada HTML, tira a captura 1080x1350 e grava o manifesto
// com as caixas de texto medidas no próprio navegador (retângulo reservado x espaço usado).
import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import puppeteer from "puppeteer";

const trabalho = JSON.parse(readFileSync(process.argv[2], "utf-8"));

const paraHex = (rgb) =>
  "#" +
  (rgb.match(/\d+/g) ?? [0, 0, 0])
    .slice(0, 3)
    .map((n) => Number(n).toString(16).padStart(2, "0"))
    .join("");

const navegador = await puppeteer.launch({ args: ["--no-sandbox", "--font-render-hinting=none"] });
try {
  const pagina = await navegador.newPage();
  await pagina.setViewport({ width: trabalho.largura, height: trabalho.altura, deviceScaleFactor: 1 });
  for (const item of trabalho.slides) {
    await pagina.goto(pathToFileURL(item.html).href, { waitUntil: "load" });
    await pagina.evaluate(() => document.fonts.ready);
    const caixas = await pagina.evaluate(() =>
      [...document.querySelectorAll("[data-caixa]")].map((el) => {
        const r = el.getBoundingClientRect();
        const faixa = document.createRange();
        faixa.selectNodeContents(el);
        const conteudo = faixa.getBoundingClientRect();
        const estilo = getComputedStyle(el);
        const fundo = el.closest("[data-fundo]") ?? document.body;
        return {
          nome: el.dataset.caixa,
          retangulo: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)],
          texto: el.innerText,
          fonte: estilo.fontFamily,
          tamanho: parseFloat(estilo.fontSize),
          cor: estilo.color,
          cor_fundo: getComputedStyle(fundo).backgroundColor,
          usado: [
            el.scrollWidth,
            Math.max(el.scrollHeight, Math.ceil(conteudo.height)),
          ],
        };
      }),
    );
    for (const c of caixas) {
      c.cor = paraHex(c.cor);
      c.cor_fundo = paraHex(c.cor_fundo);
    }
    await pagina.screenshot({ path: item.png, type: "png" });
    writeFileSync(item.json, JSON.stringify({ caixas }));
  }
} finally {
  await navegador.close();
}
