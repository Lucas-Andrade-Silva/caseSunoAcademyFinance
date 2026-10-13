// Os jeitos de vídeo que a pessoa escolhe: um clima do narrador (descontraído, sério ou engraçado)
// e um ritmo (devagar ou rápido). Os dois grupos combinam, e qualquer um pode ficar sem escolha.
// Na tela o grupo se chama "Tom"; no código é `clima`, porque Tom é uma dimensão do Comitê.

export type ClimaDoNarrador = "descontraido" | "serio" | "engracado";
export type RitmoDoNarrador = "devagar" | "rapido";

export interface OpcaoDeJeito<V extends string> {
  valor: V;
  rotulo: string;
}

export const CLIMAS: readonly OpcaoDeJeito<ClimaDoNarrador>[] = [
  { valor: "descontraido", rotulo: "Descontraído" },
  { valor: "serio", rotulo: "Sério" },
  { valor: "engracado", rotulo: "Engraçado" },
];

export const RITMOS: readonly OpcaoDeJeito<RitmoDoNarrador>[] = [
  { valor: "devagar", rotulo: "Devagar" },
  { valor: "rapido", rotulo: "Rápido" },
];

export function ehClima(valor: unknown): valor is ClimaDoNarrador {
  return CLIMAS.some((opcao) => opcao.valor === valor);
}

export function ehRitmo(valor: unknown): valor is RitmoDoNarrador {
  return RITMOS.some((opcao) => opcao.valor === valor);
}

/** "Descontraído · Rápido"; vazio quando nenhum jeito foi escolhido. */
export function rotuloDosJeitos(
  clima: ClimaDoNarrador | null,
  ritmo: RitmoDoNarrador | null,
): string {
  const rotulos = [
    CLIMAS.find((opcao) => opcao.valor === clima)?.rotulo,
    RITMOS.find((opcao) => opcao.valor === ritmo)?.rotulo,
  ];
  return rotulos.filter(Boolean).join(" · ");
}
