// As opções da barra de ferramentas do editor: famílias de letra, tamanhos, distância entre linhas
// e cores. Só dados e contas pequenas, sem Tiptap nem React.

export type IdDaFamilia = "hanken" | "lora" | "inter" | "space";

export interface Familia {
  id: IdDaFamilia;
  nome: string;
  /** O valor que vai no `font-family` do HTML guardado. */
  css: string;
}

export const FAMILIAS: readonly Familia[] = [
  { id: "hanken", nome: "Hanken Grotesk", css: "Hanken Grotesk Variable, system-ui, sans-serif" },
  { id: "lora", nome: "Lora", css: "Lora Variable, Georgia, serif" },
  { id: "inter", nome: "Inter", css: "Inter Variable, system-ui, sans-serif" },
  { id: "space", nome: "Space Mono", css: "Space Mono, ui-monospace, monospace" },
];

export const FAMILIA_PADRAO: IdDaFamilia = "hanken";

function primeiroNome(css: string): string {
  return (css.split(",")[0] ?? "").replace(/["']/g, "").trim().toLowerCase();
}

/** Qual família um `font-family` guardado representa; `null` se for outra. */
export function familiaDoCss(css: string | null | undefined): IdDaFamilia | null {
  if (!css) return null;
  const nome = primeiroNome(css);
  return FAMILIAS.find((familia) => primeiroNome(familia.css) === nome)?.id ?? null;
}

export const TAMANHOS: readonly number[] = [14, 15, 16, 17, 18, 20, 22, 24, 28, 32];
export const TAMANHO_PADRAO = 17;

/** "18px" → 18; `null` se não for um tamanho em pixels. */
export function lerTamanho(css: string | null | undefined): number | null {
  const achado = /^\s*(\d+(?:\.\d+)?)px\s*$/.exec(css ?? "");
  return achado ? Number(achado[1]) : null;
}

/** O degrau acima (+1) ou abaixo (-1) de um tamanho, parando nas pontas da lista. */
export function passoDeTamanho(atual: number, sentido: 1 | -1): number {
  const alvo = sentido === 1 ? TAMANHOS.find((t) => t > atual) : [...TAMANHOS].reverse().find((t) => t < atual);
  return alvo ?? (sentido === 1 ? TAMANHOS[TAMANHOS.length - 1] : TAMANHOS[0]);
}

export const ENTRELINHAS: readonly number[] = [1.2, 1.5, 1.8, 2.1];

export function rotuloDaEntrelinha(valor: number): string {
  return valor.toFixed(1).replace(".", ",");
}

/** Lê um `line-height` guardado e o leva ao degrau mais próximo; `null` se não houver número. */
export function entrelinhaDoCss(css: string | null | undefined): number | null {
  const numero = Number.parseFloat(css ?? "");
  if (!Number.isFinite(numero)) return null;
  return ENTRELINHAS.reduce((melhor, valor) => (Math.abs(valor - numero) < Math.abs(melhor - numero) ? valor : melhor));
}

export interface CorDeTexto {
  nome: string;
  valor: string;
}

// Meios-tons: nenhuma cor chega a 4,5:1 no fundo escuro e no branco ao mesmo tempo, mas estas
// ficam em 3,2:1 ou mais nos dois (limite de texto grande), e o "padrão" acompanha a superfície.
export const CORES: readonly CorDeTexto[] = [
  { nome: "Vermelho", valor: "#e5484d" },
  { nome: "Laranja", valor: "#e0701a" },
  { nome: "Verde", valor: "#2e9e5e" },
  { nome: "Turquesa", valor: "#1b9aa6" },
  { nome: "Azul", valor: "#3b7cf0" },
  { nome: "Violeta", valor: "#8f63f0" },
  { nome: "Rosa", valor: "#d6409f" },
  { nome: "Cinza", valor: "#7d7d7d" },
];

/** Compara cores como o navegador as devolve (hex em minúsculas ou `rgb(...)`). */
export function mesmaCor(a: string | null | undefined, b: string | null | undefined): boolean {
  return normalizarCor(a) !== null && normalizarCor(a) === normalizarCor(b);
}

function normalizarCor(cor: string | null | undefined): string | null {
  if (!cor) return null;
  const texto = cor.trim().toLowerCase();
  const rgb = /^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/.exec(texto);
  if (rgb) return `#${[rgb[1], rgb[2], rgb[3]].map((n) => Number(n).toString(16).padStart(2, "0")).join("")}`;
  return /^#[0-9a-f]{6}$/.test(texto) ? texto : null;
}
