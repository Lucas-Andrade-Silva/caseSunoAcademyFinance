// Lógica pura da guia Fontes e do passo "Escolher" da Curadoria: a seleção por bolinha e o selo
// "não calibrado". Nada aqui toca React nem a rede, por isso o Vitest cobre.
// Na tela é "Fonte" e "item"; no código é Origem e Ata (CONTEXT.md).

const CATEGORIA_CALIBRADA = "copom";

/** Limiares e Léxico foram medidos só com Atas do Copom. */
export function ehCalibrada(categoria: string): boolean {
  return categoria === CATEGORIA_CALIBRADA;
}

export function seloDaAta(categoria: string): string | null {
  return ehCalibrada(categoria) ? null : "não calibrado";
}

export function alternarSelecao(selecao: readonly string[], identificador: string): string[] {
  return selecao.includes(identificador)
    ? selecao.filter((outro) => outro !== identificador)
    : [...selecao, identificador];
}

export function contarSelecionadas(
  selecao: readonly string[],
  atas: readonly { identificador: string }[],
): number {
  const existentes = new Set(atas.map((ata) => ata.identificador));
  return selecao.filter((identificador) => existentes.has(identificador)).length;
}

/** A seleção guardada no navegador pode apontar para uma Ata que já não existe em disco. */
export function limparInexistentes(
  selecao: readonly string[],
  existentes: ReadonlySet<string>,
): string[] {
  return selecao.filter((identificador) => existentes.has(identificador));
}

const MAXIMO_DA_VISAO_UNIDA = 5;

export type ModoDaEscolha = "destaque" | "unida";

interface PodeUsar {
  ok: boolean;
  motivo: string | null;
  /** Um item vira Destaque único; de 2 a 5 viram Visão unida. */
  modo: ModoDaEscolha | null;
}

export function podeUsarSelecao(selecao: readonly string[]): PodeUsar {
  if (selecao.length === 0) {
    return { ok: false, motivo: "Marque uma Ata nas Fontes.", modo: null };
  }
  if (selecao.length > MAXIMO_DA_VISAO_UNIDA) {
    return {
      ok: false,
      motivo: `A Visão unida junta no máximo ${MAXIMO_DA_VISAO_UNIDA} itens.`,
      modo: null,
    };
  }
  return { ok: true, motivo: null, modo: selecao.length === 1 ? "destaque" : "unida" };
}

/** O nome padrão de uma Saída: o título da Ata, ou "Visão unida: A + B", no limite de 120. */
export function nomePadrao(titulos: readonly string[], limite = 120): string {
  const bruto = titulos.length === 1 ? titulos[0] : `Visão unida: ${titulos.join(" + ")}`;
  return bruto.length <= limite ? bruto : `${bruto.slice(0, limite - 1).trimEnd()}…`;
}

/** "2026-08-05" → "05/08". Data estranha volta como veio. */
export function dataDoDia(dataIso: string): string {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dataIso);
  return partes ? `${partes[3]}/${partes[2]}` : dataIso;
}
