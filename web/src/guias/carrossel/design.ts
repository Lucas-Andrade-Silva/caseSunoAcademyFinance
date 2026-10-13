// O que a pessoa guarda no navegador entre uma sessão e outra: o design (composição + referência),
// que vale como padrão ao gerar, e a paleta. Também traduz o design para o que o pedido leva ao
// servidor, que exige composição e referência juntas e da mesma composição.
import type { ReferenciaVisual } from "../../dados/cliente";
import { apagar, gravar, ler } from "../../nucleo/armazenamento";
import type { ExtrasDaGeracao } from "../../nucleo/pedido";
import { ehComposicao } from "./composicoes";
import type { Design } from "./modelo";
import { paletaPorId } from "./paletas";

const CHAVE_DO_DESIGN = "suno.carrossel.design";
const CHAVE_DA_PALETA = "suno.carrossel.paleta";

export function lerDesign(): Design | null {
  const bruto = ler<unknown>("local", CHAVE_DO_DESIGN, null);
  if (typeof bruto !== "object" || bruto === null) return null;
  const { composicao, referencia } = bruto as Record<string, unknown>;
  if (!ehComposicao(composicao)) return null;
  return { composicao, referencia: typeof referencia === "string" ? referencia : null };
}

export function gravarDesign(design: Design | null): void {
  if (design) gravar("local", CHAVE_DO_DESIGN, design);
  else apagar("local", CHAVE_DO_DESIGN);
}

export function lerIdDaPaleta(): string {
  return paletaPorId(ler<string | null>("local", CHAVE_DA_PALETA, null)).id;
}

export function gravarIdDaPaleta(id: string): void {
  gravar("local", CHAVE_DA_PALETA, id);
}

export function mesmoDesign(a: Design | null, b: Design | null): boolean {
  if (a === null || b === null) return a === b;
  return a.composicao === b.composicao && a.referencia === b.referencia;
}

/**
 * O que o pedido leva ao servidor. Sem referência escolhida vale a primeira aprovada da composição;
 * sem nenhuma, o pedido segue sem design (o servidor escolhe sozinho).
 */
export function extrasDoDesign(
  design: Design | null,
  referencias: readonly ReferenciaVisual[] | undefined,
): ExtrasDaGeracao | undefined {
  if (!design || !referencias) return undefined;
  const certa = (referencia: ReferenciaVisual) =>
    referencia.aprovada && referencia.composicao === design.composicao;
  const escolhida = design.referencia
    ? referencias.find((r) => r.identificador === design.referencia && certa(r))
    : undefined;
  const referencia = escolhida ?? referencias.find(certa);
  if (!referencia) return undefined;
  return { composicaoVisual: design.composicao, referenciaVisual: referencia.identificador };
}
