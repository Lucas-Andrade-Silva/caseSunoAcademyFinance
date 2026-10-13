// O Laudo em barras horizontais, para as guias Carrossel e Vídeo. Lógica pura (Vitest cobre).
// Cada barra mostra a medida na própria escala (Flesch-BR de 0 a 100; as demais de 0 a 1, em %),
// com os limites do Limiar como marcas e a cor dizendo se atingiu. Compliance não é escala: é
// "sem Recomendação" ou "Recomendação detectada".
import type { Faixa, Laudo, Medida } from "../dados/cliente";
import { formatarNumero, resumirFaixa } from "../texto/rotulos";

export interface BarraDoLaudo {
  metrica: string;
  rotulo: string;
  /** De 0 a 100, o comprimento da barra. */
  largura: number;
  /** Onde ficam as marcas do Limiar, de 0 a 100; vazio quando a medida não tem escala. */
  marcas: number[];
  valor: string;
  faixa: string;
  /** `null` quando não há base para julgar. */
  atingiu: boolean | null;
}

const ROTULOS: Record<string, string> = {
  integridade: "Integridade",
  flesch_br: "Flesch-BR",
  densidade: "Densidade",
  aderencia: "Aderência",
  recomendacao: "Compliance",
};

/** A ordem em que as barras aparecem. */
const ORDEM = ["flesch_br", "densidade", "aderencia", "integridade", "recomendacao"];

function limitar(valor: number): number {
  return Math.min(100, Math.max(0, valor));
}

/** Largura da barra de uma medida, de 0 a 100. Flesch-BR já vem em 0 a 100; as demais, em 0 a 1. */
export function larguraDaBarra(medida: { metrica: string; valor?: number | null }): number {
  if (medida.valor === null || medida.valor === undefined) return 0;
  const percentual = medida.metrica === "flesch_br" ? medida.valor : medida.valor * 100;
  return limitar(percentual);
}

function marcasDaFaixa(metrica: string, faixa: Faixa | null | undefined): number[] {
  if (!faixa) return [];
  const escala = metrica === "flesch_br" ? 1 : 100;
  return [faixa.minimo, faixa.maximo]
    .filter((limite): limite is number => limite !== null && limite !== undefined)
    .map((limite) => limitar(limite * escala));
}

function barraDe(medida: Medida): BarraDoLaudo {
  const ausente = medida.estado === "ausente";
  if (medida.metrica === "recomendacao") {
    const limpa = medida.atingiu === true;
    return {
      metrica: medida.metrica,
      rotulo: ROTULOS.recomendacao,
      largura: ausente ? 0 : limpa ? 100 : 18,
      marcas: [],
      valor: ausente ? "—" : limpa ? "sem Recomendação" : "Recomendação detectada",
      faixa: "",
      atingiu: ausente ? null : medida.atingiu ?? null,
    };
  }
  const emPercentual = medida.metrica !== "flesch_br";
  const valor =
    medida.valor === null || medida.valor === undefined
      ? "—"
      : emPercentual
        ? `${formatarNumero(Math.round(medida.valor * 1000) / 10)}%`
        : formatarNumero(Math.round(medida.valor * 10) / 10);
  return {
    metrica: medida.metrica,
    rotulo: ROTULOS[medida.metrica] ?? medida.metrica,
    largura: larguraDaBarra(medida),
    marcas: marcasDaFaixa(medida.metrica, medida.faixa),
    valor,
    faixa: resumirFaixa(medida.faixa),
    atingiu: ausente ? null : medida.atingiu ?? null,
  };
}

export function barrasDoLaudo(laudo: Laudo | null | undefined): BarraDoLaudo[] {
  if (!laudo) return [];
  return [...laudo.medidas]
    .sort((a, b) => ORDEM.indexOf(a.metrica) - ORDEM.indexOf(b.metrica))
    .map(barraDe);
}

/** Só espelha a regra do servidor: Laudo com Recomendação não vira Pacote nem é aprovado. */
export function celulaBloqueada(
  laudo: { motivos?: readonly string[] | null } | null | undefined,
): boolean {
  return laudo?.motivos?.includes("recomendacao") ?? false;
}
