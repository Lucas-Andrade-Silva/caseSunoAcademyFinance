// O período que a pessoa escolhe quando a consulta acha mais de 2 notícias novas: contagem por
// período e por origem, o gráfico de barras por dia e os atalhos de 7, 15 e 30 dias. Lógica pura
// (Vitest cobre). As datas são "AAAA-MM-DD", comparadas como texto.

/** O teto de documentos por download, o mesmo de `MAXIMO_POR_DOWNLOAD` em `origens/atualizacao.py`. */
export const MAXIMO_POR_DOWNLOAD = 40;

interface ComData {
  data: string;
}

interface ComOrigem extends ComData {
  origem: string;
}

export function noPeriodo<T extends ComData>(lista: readonly T[], de: string, ate: string): T[] {
  return lista.filter((entrada) => entrada.data >= de && entrada.data <= ate);
}

/** Quantas há de cada origem, na ordem em que a origem aparece primeiro. */
export function porOrigem(lista: readonly ComOrigem[]): { origem: string; total: number }[] {
  const contagem = new Map<string, number>();
  for (const entrada of lista) {
    contagem.set(entrada.origem, (contagem.get(entrada.origem) ?? 0) + 1);
  }
  return [...contagem].map(([origem, total]) => ({ origem, total }));
}

function somarDias(dataIso: string, dias: number): string {
  const [ano, mes, dia] = dataIso.split("-").map(Number);
  return new Date(Date.UTC(ano, mes - 1, dia + dias)).toISOString().slice(0, 10);
}

/** Um item por dia de `desde` a `ate`, com quantas notícias caem nele. */
export function porDia(
  lista: readonly ComData[],
  desde: string,
  ate: string,
): { data: string; total: number }[] {
  const contagem = new Map<string, number>();
  for (const entrada of lista) {
    contagem.set(entrada.data, (contagem.get(entrada.data) ?? 0) + 1);
  }
  const dias: { data: string; total: number }[] = [];
  for (let dia = desde; dia <= ate; dia = somarDias(dia, 1)) {
    dias.push({ data: dia, total: contagem.get(dia) ?? 0 });
  }
  return dias;
}

/** O início de um atalho "últimos N dias" (hoje incluído), sem passar do começo da janela. */
export function inicioDoAtalho(dias: number, desde: string, ate: string): string {
  const inicio = somarDias(ate, -(dias - 1));
  return inicio < desde ? desde : inicio;
}

/** "2026-10-08" → "08/10". */
export function diaEMes(dataIso: string): string {
  const [, mes, dia] = dataIso.split("-");
  return `${dia}/${mes}`;
}
