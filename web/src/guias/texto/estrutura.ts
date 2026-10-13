// Lê o HTML do texto (o que o `marked` gera ou o Tiptap devolve) e tira dele a estrutura que os
// quatro formatos usam: título, lide, seções, tempo de leitura. Sem DOM: o HTML das duas origens é
// bem formado, e assim a leitura roda no Vitest, no servidor e na tela do mesmo jeito.
import type { CSSProperties } from "react";

export interface Bloco {
  /** "p", "h2", "ul", "blockquote"... em minúsculas. */
  etiqueta: string;
  /** O que vem depois do nome na abertura, ex.: ` style="text-align: center"`. */
  atributos: string;
  /** O HTML de dentro do bloco. */
  interno: string;
  /** O bloco inteiro, abertura e fechamento. */
  html: string;
}

export interface SecaoDoTexto {
  /** `null` na abertura do texto que vem antes do primeiro `##`. */
  titulo: string | null;
  tituloHtml: string;
  atributosDoTitulo: string;
  blocos: Bloco[];
}

export interface EstruturaDoTexto {
  titulo: string;
  tituloHtml: string;
  atributosDoTitulo: string;
  /** O primeiro parágrafo, quando ele vem antes do primeiro `##`. */
  lide: Bloco | null;
  secoes: SecaoDoTexto[];
  palavras: number;
  minutos: number;
  /** Uma frase do próprio texto, escolhida para o destaque do artigo. */
  citacao: string | null;
}

const VAZIAS = new Set(["br", "hr", "img", "input", "wbr"]);
const MARCA = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)((?:"[^"]*"|'[^']*'|[^'">])*)>/g;
const PALAVRAS_POR_MINUTO = 200;
const LIMITE_DO_TITULO = 160;

/** Divide o HTML nos blocos de primeiro nível, respeitando o aninhamento (listas, citações). */
export function dividirEmBlocos(html: string): Bloco[] {
  const blocos: Bloco[] = [];
  let profundidade = 0;
  let abertura: { etiqueta: string; atributos: string; inicio: number; fim: number } | null = null;

  for (const achado of html.matchAll(MARCA)) {
    const [marca, barra, nome, atributos] = achado;
    const etiqueta = nome.toLowerCase();
    const fimDaMarca = achado.index + marca.length;
    const vazia = VAZIAS.has(etiqueta) || atributos.trimEnd().endsWith("/");

    if (barra) {
      if (profundidade === 0) continue;
      profundidade -= 1;
      if (profundidade === 0 && abertura) {
        blocos.push({
          etiqueta: abertura.etiqueta,
          atributos: abertura.atributos,
          interno: html.slice(abertura.fim, achado.index),
          html: html.slice(abertura.inicio, fimDaMarca),
        });
        abertura = null;
      }
    } else if (vazia) {
      if (profundidade === 0) blocos.push({ etiqueta, atributos, interno: "", html: marca });
    } else {
      if (profundidade === 0) abertura = { etiqueta, atributos, inicio: achado.index, fim: fimDaMarca };
      profundidade += 1;
    }
  }
  return blocos;
}

const ENTIDADES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };

export function decodificar(texto: string): string {
  return texto.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (inteira, nome: string) => {
    if (nome.startsWith("#")) {
      const hexa = nome[1] === "x" || nome[1] === "X";
      const codigo = hexa ? Number.parseInt(nome.slice(2), 16) : Number.parseInt(nome.slice(1), 10);
      return Number.isFinite(codigo) && codigo > 0 && codigo <= 0x10ffff ? String.fromCodePoint(codigo) : inteira;
    }
    return ENTIDADES[nome.toLowerCase()] ?? inteira;
  });
}

export function escaparHtml(texto: string): string {
  return texto.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function textoPlano(html: string): string {
  const semMarcas = html
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<\/(?:p|li|h[1-6]|blockquote|ul|ol)>/gi, " ")
    .replace(/<[^>]*>/g, "");
  return decodificar(semMarcas).replace(/\s+/g, " ").trim();
}

export function contarPalavras(texto: string): number {
  return (texto.match(/\S+/g) ?? []).filter((pedaco) => /[\p{L}\p{N}]/u.test(pedaco)).length;
}

export function minutosDeLeitura(palavras: number): number {
  return Math.max(1, Math.ceil(palavras / PALAVRAS_POR_MINUTO));
}

/** Corta em frases sem quebrar siglas ("a.a.") nem iniciais: só quebra se a próxima começa em maiúscula ou dígito. */
export function dividirFrases(texto: string): string[] {
  const frases: string[] = [];
  let inicio = 0;
  for (const achado of texto.matchAll(/[.!?]+(?=\s+["“(]?[\p{Lu}\d])/gu)) {
    const fim = achado.index + achado[0].length;
    const antes = texto.slice(inicio, achado.index);
    const sigla = /(?:^|[\s(])\p{L}(?:\.\p{L})*$/u.test(antes) && achado[0] === ".";
    if (sigla) continue;
    frases.push(texto.slice(inicio, fim).trim());
    inicio = fim;
  }
  const resto = texto.slice(inicio).trim();
  if (resto) frases.push(resto);
  return frases;
}

export function primeiraFrase(texto: string): string {
  return dividirFrases(texto)[0] ?? "";
}

const PROPRIEDADES_PERMITIDAS = new Set(["text-align", "line-height", "font-family", "font-size", "color"]);

/** O `style` de uma abertura de bloco como objeto do React, só com o que o editor produz. */
export function aparenciaDosAtributos(atributos: string): CSSProperties {
  const achado = /\sstyle\s*=\s*(?:"([^"]*)"|'([^']*)')/i.exec(atributos);
  const css = decodificar(achado?.[1] ?? achado?.[2] ?? "");
  const resultado: Record<string, string> = {};
  for (const declaracao of css.split(";")) {
    const separador = declaracao.indexOf(":");
    if (separador < 1) continue;
    const nome = declaracao.slice(0, separador).trim().toLowerCase();
    const valor = declaracao.slice(separador + 1).trim();
    if (!valor || !PROPRIEDADES_PERMITIDAS.has(nome)) continue;
    resultado[nome.replace(/-([a-z])/g, (_inteira, letra: string) => letra.toUpperCase())] = valor;
  }
  return resultado;
}

/** A data de hoje por extenso: "12 de outubro de 2026". */
export function dataDeHoje(agora: Date = new Date()): string {
  return agora.toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
}

/** A primeira frase de cada seção, na ordem: o bloco "Em resumo" da newsletter. */
export function resumoDasSecoes(estrutura: EstruturaDoTexto): string[] {
  const topicos: string[] = [];
  for (const secao of estrutura.secoes) {
    const bloco = secao.blocos.find((b) => b.etiqueta === "p") ?? secao.blocos[0];
    const frase = bloco ? primeiraFrase(textoPlano(bloco.interno)) : "";
    if (frase) topicos.push(frase);
  }
  return topicos;
}

const SEM_TITULO = "Sem título";

function escolherCitacao(blocos: Bloco[]): string | null {
  const citada = blocos.find((b) => b.etiqueta === "blockquote");
  if (citada) {
    const texto = textoPlano(citada.interno);
    if (texto) return texto;
  }
  const frases = blocos
    .filter((b) => b.etiqueta === "p")
    .flatMap((b) => dividirFrases(textoPlano(b.interno)))
    .filter((frase) => frase.length >= 60 && frase.length <= 260);
  return frases.find((frase) => /\d/.test(frase)) ?? frases[0] ?? null;
}

/** O título é o primeiro `#`; sem ele, a primeira linha do texto, se couber num título. */
function separarTitulo(blocos: Bloco[]): { titulo: Bloco | null; restante: Bloco[]; texto: string } {
  const posicao = blocos.findIndex((b) => b.etiqueta === "h1");
  if (posicao >= 0) {
    return {
      titulo: blocos[posicao],
      restante: blocos.filter((_b, i) => i !== posicao),
      texto: textoPlano(blocos[posicao].interno),
    };
  }
  const primeiro = blocos[0];
  if (!primeiro) return { titulo: null, restante: [], texto: SEM_TITULO };
  const texto = textoPlano(primeiro.interno);
  if (/^(?:p|h[2-6])$/.test(primeiro.etiqueta) && texto.length <= LIMITE_DO_TITULO) {
    return { titulo: primeiro, restante: blocos.slice(1), texto: texto || SEM_TITULO };
  }
  const frase = primeiraFrase(texto);
  return { titulo: null, restante: blocos, texto: frase.length > 120 ? `${frase.slice(0, 117)}…` : frase || SEM_TITULO };
}

export function derivarEstrutura(html: string): EstruturaDoTexto {
  const blocos = dividirEmBlocos(html);
  const { titulo, restante, texto: textoDoTitulo } = separarTitulo(blocos);

  const secoes: SecaoDoTexto[] = [];
  let abertura: Bloco[] = [];
  let atual: SecaoDoTexto | null = null;
  for (const bloco of restante) {
    if (bloco.etiqueta === "h2" || bloco.etiqueta === "h1") {
      atual = {
        titulo: textoPlano(bloco.interno) || null,
        tituloHtml: bloco.interno,
        atributosDoTitulo: bloco.atributos,
        blocos: [],
      };
      secoes.push(atual);
    } else if (atual) {
      atual.blocos.push(bloco);
    } else {
      abertura.push(bloco);
    }
  }

  let lide: Bloco | null = null;
  if (abertura[0]?.etiqueta === "p") {
    lide = abertura[0];
    abertura = abertura.slice(1);
  }
  if (abertura.length > 0) {
    secoes.unshift({ titulo: null, tituloHtml: "", atributosDoTitulo: "", blocos: abertura });
  }

  const palavras = contarPalavras(textoPlano(html));
  return {
    titulo: textoDoTitulo,
    tituloHtml: titulo ? titulo.interno : escaparHtml(textoDoTitulo),
    atributosDoTitulo: titulo?.atributos ?? "",
    lide,
    secoes,
    palavras,
    minutos: minutosDeLeitura(palavras),
    citacao: escolherCitacao(restante),
  };
}
