// Markdown do servidor → HTML do editor. O texto vem de um modelo de linguagem, então o HTML cru
// que ele escrever e os endereços dos links são descartados aqui: o resultado só tem parágrafos,
// títulos, listas, citações e ênfase, e entra na tela sem passar por outro filtro.
import { Marked } from "marked";
import { escaparHtml } from "./estrutura";

const conversor = new Marked({
  gfm: true,
  renderer: {
    html: ({ text }) => escaparHtml(text),
    link({ tokens }) {
      return this.parser.parseInline(tokens);
    },
    image: ({ text }) => escaparHtml(text),
  },
});

export function markdownParaHtml(markdown: string): string {
  return conversor.parse(markdown, { async: false }).trim();
}
