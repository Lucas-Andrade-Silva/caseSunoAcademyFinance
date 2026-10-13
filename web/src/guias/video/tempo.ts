// O tempo do roteiro em texto: "0:06" para um instante, "1 min 30" para uma duração. Lógica pura
// (Vitest cobre). As durações usam a mesma escrita das cinco que a pessoa escolhe na geração.
import type { BlocoFala } from "../../dados/cliente";
import { pluralizar } from "../../texto/rotulos";

function emSegundosInteiros(segundos: number): number {
  return Number.isFinite(segundos) && segundos > 0 ? Math.round(segundos) : 0;
}

/** "0:06", "1:27": onde um instante cai no relógio do vídeo. */
export function formatarTempo(segundos: number): string {
  const total = emSegundosInteiros(segundos);
  const resto = String(total % 60).padStart(2, "0");
  return `${Math.floor(total / 60)}:${resto}`;
}

/** "0:00–0:06". O fim de uma cena e o começo da seguinte arredondam igual, então não há buraco. */
export function formatarIntervalo(inicio: number, fim: number): string {
  return `${formatarTempo(inicio)}–${formatarTempo(fim)}`;
}

/** "40 s", "1 min", "1 min 30", "1 min 02": a escrita curta das durações do vídeo. */
export function formatarDuracao(segundos: number): string {
  const total = emSegundosInteiros(segundos);
  if (total < 60) return `${total} s`;
  const resto = total % 60;
  const minutos = Math.floor(total / 60);
  return resto === 0 ? `${minutos} min` : `${minutos} min ${String(resto).padStart(2, "0")}`;
}

/** "40 segundos", "1 minuto e 27 segundos": a mesma duração, por extenso, para o texto do prompt. */
export function duracaoPorExtenso(segundos: number): string {
  const total = emSegundosInteiros(segundos);
  const resto = total % 60;
  const minutos = Math.floor(total / 60);
  if (minutos === 0) return pluralizar(total, "segundo", "segundos");
  const minutosEscritos = pluralizar(minutos, "minuto", "minutos");
  return resto === 0 ? minutosEscritos : `${minutosEscritos} e ${pluralizar(resto, "segundo", "segundos")}`;
}

/** "0,4": segundos com uma casa e vírgula, para tempos curtos dentro de uma cena. */
export function formatarSegundos(segundos: number): string {
  return String(Math.round(segundos * 10) / 10).replace(".", ",");
}

/** O vídeo dura até o fim da última cena. */
export function duracaoDoRoteiro(blocos: readonly Pick<BlocoFala, "fim_s">[]): number {
  return blocos.reduce((maior, bloco) => Math.max(maior, bloco.fim_s), 0);
}

/** "1 min 30 · 8 cenas": a frase curta do salvo no Histórico e da pílula da prévia. */
export function resumoDoRoteiro(blocos: readonly Pick<BlocoFala, "fim_s">[]): string {
  return `${formatarDuracao(duracaoDoRoteiro(blocos))} · ${pluralizar(blocos.length, "cena", "cenas")}`;
}
