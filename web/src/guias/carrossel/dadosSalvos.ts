// O que "Salvar no histórico" guarda de um carrossel e como ler de volta. O `dados` do Histórico é
// `unknown` (cada guia define o seu); aqui a leitura confere o formato antes de a guia confiar nele,
// porque o `localStorage` pode ter dados de uma versão antiga ou editados à mão.
import type { Laudo, Slide } from "../../dados/cliente";
import { ehComposicao } from "./composicoes";
import { ICONES_VALIDOS } from "./idsDeIcones";
import type { AncoraDeQuadro, Composicao, IdDoIcone, Montagem, Paleta } from "./modelo";
import { ehPaleta } from "./paletas";

/** O carrossel gerado e, quando havia, o Laudo da Célula (para as barras ao reabrir). */
export interface DadosDoCarrossel {
  slides: Slide[];
  composicao: Composicao;
  referenciaId: string | null;
  paleta: Paleta;
  icones: IdDoIcone[];
  ancoras: AncoraDeQuadro[];
  laudo: Laudo | null;
}

export function dadosParaSalvar(montagem: Montagem, laudo: Laudo | null): DadosDoCarrossel {
  const { slides, composicao, referenciaId, paleta, icones, ancoras } = montagem;
  return { slides, composicao, referenciaId, paleta, icones, ancoras, laudo };
}

function ehSlide(valor: unknown): valor is Slide {
  if (typeof valor !== "object" || valor === null) return false;
  const s = valor as Record<string, unknown>;
  return typeof s.titulo === "string" && typeof s.corpo === "string";
}

function ehAncora(valor: unknown): valor is AncoraDeQuadro {
  if (typeof valor !== "object" || valor === null) return false;
  const a = valor as Record<string, unknown>;
  return (
    typeof a.chave === "string" &&
    typeof a.rotulo === "string" &&
    typeof a.citacao === "string" &&
    (a.valor === null || typeof a.valor === "number")
  );
}

/** `null` quando o salvo não tem o formato esperado. */
export function lerDadosSalvos(bruto: unknown): DadosDoCarrossel | null {
  if (typeof bruto !== "object" || bruto === null) return null;
  const d = bruto as Record<string, unknown>;
  if (!Array.isArray(d.slides) || d.slides.length === 0 || !d.slides.every(ehSlide)) return null;
  if (!ehComposicao(d.composicao) || !ehPaleta(d.paleta)) return null;
  return {
    slides: d.slides,
    composicao: d.composicao,
    referenciaId: typeof d.referenciaId === "string" ? d.referenciaId : null,
    paleta: d.paleta,
    icones: Array.isArray(d.icones)
      ? d.icones.filter((id): id is IdDoIcone => typeof id === "string" && ICONES_VALIDOS.has(id))
      : [],
    ancoras: Array.isArray(d.ancoras) ? d.ancoras.filter(ehAncora) : [],
    laudo: typeof d.laudo === "object" && d.laudo !== null ? (d.laudo as Laudo) : null,
  };
}
