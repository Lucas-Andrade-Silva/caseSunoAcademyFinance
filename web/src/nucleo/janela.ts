// A janela de notícias: a Ingestão só mostra o que tem até 30 dias (a mesma janela da busca
// no servidor, `JANELA_DA_BUSCA_EM_DIAS` em `origens/coleta.py`). Lógica pura, coberta pelo
// Vitest. A data de uma Ata é só um dia (sem hora), comparada com o dia de hoje.

export const JANELA_EM_DIAS = 30;

const MS_POR_DIA = 86_400_000;

function meiaNoite(data: Date): number {
  return Date.UTC(data.getFullYear(), data.getMonth(), data.getDate());
}

/** Quantos dias se passaram desde `dataIso` ("2026-09-16"); data ilegível volta `null`. */
export function diasDesde(dataIso: string, hoje: Date = new Date()): number | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(dataIso);
  if (!partes) return null;
  const dia = Date.UTC(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3]));
  return Math.round((meiaNoite(hoje) - dia) / MS_POR_DIA);
}

/** Data ilegível fica de fora: sem saber o dia, não dá para dizer que é recente. */
export function dentroDaJanela(
  dataIso: string,
  hoje: Date = new Date(),
  dias: number = JANELA_EM_DIAS,
): boolean {
  const passados = diasDesde(dataIso, hoje);
  return passados !== null && passados <= dias;
}

export function recentes<T extends { data_referencia: string }>(
  atas: readonly T[],
  hoje: Date = new Date(),
): T[] {
  return atas
    .filter((ata) => dentroDaJanela(ata.data_referencia, hoje))
    .sort((a, b) => b.data_referencia.localeCompare(a.data_referencia));
}
