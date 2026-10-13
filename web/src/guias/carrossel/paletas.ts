// As paletas prontas do carrossel e a conta de contraste (WCAG) que as sustenta. Cada paleta tem
// quatro cores: `fundo`, `texto`, `destaque` (formas, números, marca) e `apoio` (formas escuras).
// A primeira é a do render do servidor; as outras mudam só as cores, nunca o desenho.
import type { Paleta } from "./modelo";

export const PALETAS: readonly Paleta[] = [
  { id: "suno", nome: "Suno", fundo: "#140809", texto: "#FFFFFF", destaque: "#FF1A1A", apoio: "#AF0404" },
  { id: "noite", nome: "Noite", fundo: "#0B1220", texto: "#F4F7FF", destaque: "#4C9BFF", apoio: "#1D3F8F" },
  { id: "floresta", nome: "Floresta", fundo: "#0C1A14", texto: "#F1FBF5", destaque: "#3DDC84", apoio: "#1B6B45" },
  { id: "ambar", nome: "Âmbar", fundo: "#17110A", texto: "#FFF7EA", destaque: "#FFB02E", apoio: "#9A5B00" },
  { id: "violeta", nome: "Violeta", fundo: "#140F22", texto: "#F7F2FF", destaque: "#A56BFF", apoio: "#5A2EA6" },
  { id: "lima", nome: "Lima", fundo: "#151515", texto: "#F5F5F0", destaque: "#C6F135", apoio: "#5E6B1C" },
  { id: "papel", nome: "Papel", fundo: "#F6F1E7", texto: "#1B1B1B", destaque: "#C42B16", apoio: "#7A1A0C" },
  { id: "oceano", nome: "Oceano", fundo: "#07252B", texto: "#EAFBFF", destaque: "#FF6B6B", apoio: "#0E5C6B" },
];

export const PALETA_PADRAO: Paleta = PALETAS[0];

export function paletaPorId(id: string | null | undefined): Paleta {
  return PALETAS.find((paleta) => paleta.id === id) ?? PALETA_PADRAO;
}

function componente(hexadecimal: string, inicio: number): number {
  const valor = parseInt(hexadecimal.slice(inicio, inicio + 2), 16) / 255;
  return valor <= 0.03928 ? valor / 12.92 : ((valor + 0.055) / 1.055) ** 2.4;
}

/** Luminância relativa de uma cor `#RRGGBB`, de 0 (preto) a 1 (branco). */
export function luminancia(cor: string): number {
  const hexadecimal = cor.replace("#", "");
  return 0.2126 * componente(hexadecimal, 0) + 0.7152 * componente(hexadecimal, 2) + 0.0722 * componente(hexadecimal, 4);
}

/** A razão de contraste de duas cores, de 1 a 21. */
export function contraste(a: string, b: string): number {
  const [maior, menor] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (maior + 0.05) / (menor + 0.05);
}

/** Das duas cores de texto possíveis, a que se lê melhor sobre `base` (o realce do título usa). */
export function corSobre(base: string, opcaoA: string, opcaoB: string): string {
  return contraste(base, opcaoA) >= contraste(base, opcaoB) ? opcaoA : opcaoB;
}

const HEXADECIMAL = /^#[0-9a-fA-F]{6}$/;

export function ehPaleta(valor: unknown): valor is Paleta {
  if (typeof valor !== "object" || valor === null) return false;
  const p = valor as Record<string, unknown>;
  return (
    typeof p.id === "string" &&
    typeof p.nome === "string" &&
    [p.fundo, p.texto, p.destaque, p.apoio].every((cor) => typeof cor === "string" && HEXADECIMAL.test(cor))
  );
}
