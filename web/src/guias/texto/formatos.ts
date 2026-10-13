// Os quatro jeitos de mostrar o mesmo texto, e o que o Histórico guarda de um texto salvo.
import { pluralizar } from "../../texto/rotulos";
import { derivarEstrutura } from "./estrutura";

export type FormatoDoTexto = "email" | "newsletter" | "site" | "artigo";

export const FORMATOS_DO_TEXTO: readonly { valor: FormatoDoTexto; rotulo: string }[] = [
  { valor: "email", rotulo: "E-mail" },
  { valor: "newsletter", rotulo: "Newsletter" },
  { valor: "site", rotulo: "Site" },
  { valor: "artigo", rotulo: "Artigo" },
];

export function rotuloDoFormatoDoTexto(formato: FormatoDoTexto): string {
  return FORMATOS_DO_TEXTO.find((f) => f.valor === formato)?.rotulo ?? formato;
}

/** O `dados` de um texto salvo no Histórico. */
export interface DadosDoTexto {
  formato: FormatoDoTexto;
  html: string;
}

/** Lê o `dados` de um salvo sem confiar nele: o navegador pode ter guardado outra coisa. */
export function lerDados(bruto: unknown): DadosDoTexto | null {
  if (typeof bruto !== "object" || bruto === null) return null;
  const { formato, html } = bruto as Record<string, unknown>;
  const conhecido = FORMATOS_DO_TEXTO.some((f) => f.valor === formato);
  if (!conhecido || typeof html !== "string" || html.trim() === "") return null;
  return { formato: formato as FormatoDoTexto, html };
}

/** "E-mail · 320 palavras", a linha de apoio do salvo no Histórico. */
export function resumoDoTexto(formato: FormatoDoTexto, html: string): string {
  const { palavras } = derivarEstrutura(html);
  return `${rotuloDoFormatoDoTexto(formato)} · ${pluralizar(palavras, "palavra", "palavras")}`;
}
