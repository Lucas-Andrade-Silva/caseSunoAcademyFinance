// O que a guia Vídeo guarda no Histórico e como lê de volta. O `localStorage` pode ter qualquer
// coisa (versão antiga, edição à mão), então a leitura confere cada campo e completa os da Direção
// de cena que faltarem, em vez de confiar no formato. Lógica pura (Vitest cobre).
import type { BlocoFala } from "../../dados/cliente";
import type { BarraDoLaudo } from "../../nucleo/laudo";
import { ehClima, ehRitmo, type ClimaDoNarrador, type RitmoDoNarrador } from "./jeitos";
import { montarPrompt } from "./instrucao";

export interface DadosDoVideo {
  blocos: BlocoFala[];
  clima: ClimaDoNarrador | null;
  ritmo: RitmoDoNarrador | null;
  /** O prompt como estava quando a pessoa salvou. */
  instrucao: string;
  /** O Laudo da Célula em barras, para a prévia mostrar a avaliação de quando foi salvo. */
  barras: BarraDoLaudo[];
}

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function textoOu<V extends string>(valor: unknown, padrao: V): V {
  return typeof valor === "string" && valor !== "" ? (valor as V) : padrao;
}

function lerBloco(valor: unknown): BlocoFala | null {
  if (!ehObjeto(valor)) return null;
  const { inicio_s, fim_s, fala } = valor;
  if (typeof inicio_s !== "number" || typeof fim_s !== "number" || typeof fala !== "string") return null;
  return {
    inicio_s,
    fim_s,
    fala,
    tela: typeof valor.tela === "string" ? valor.tela : "",
    cena: textoOu(valor.cena, "texto_destaque"),
    icone: typeof valor.icone === "string" ? (valor.icone as BlocoFala["icone"]) : null,
    entrada: textoOu(valor.entrada, "corte"),
    texto_anima: textoOu(valor.texto_anima, "fade"),
    texto_entra_em_s: typeof valor.texto_entra_em_s === "number" ? valor.texto_entra_em_s : 0,
    efeito: textoOu(valor.efeito, "nenhum"),
  };
}

function lerBarra(valor: unknown): BarraDoLaudo | null {
  if (!ehObjeto(valor)) return null;
  const { metrica, rotulo, largura, valor: medida, faixa } = valor;
  if (typeof metrica !== "string" || typeof rotulo !== "string" || typeof largura !== "number") return null;
  return {
    metrica,
    rotulo,
    largura,
    marcas: Array.isArray(valor.marcas) ? valor.marcas.filter((m): m is number => typeof m === "number") : [],
    valor: typeof medida === "string" ? medida : "",
    faixa: typeof faixa === "string" ? faixa : "",
    atingiu: typeof valor.atingiu === "boolean" ? valor.atingiu : null,
  };
}

function lerLista<T>(valor: unknown, ler: (elemento: unknown) => T | null): T[] {
  if (!Array.isArray(valor)) return [];
  return valor.map(ler).filter((lido): lido is T => lido !== null);
}

/** Os dados de um salvo de vídeo, ou `null` quando não há roteiro para mostrar. */
export function lerDadosDoVideo(valor: unknown): DadosDoVideo | null {
  if (!ehObjeto(valor)) return null;
  const blocos = lerLista(valor.blocos, lerBloco);
  if (blocos.length === 0) return null;
  const clima = ehClima(valor.clima) ? valor.clima : null;
  const ritmo = ehRitmo(valor.ritmo) ? valor.ritmo : null;
  return {
    blocos,
    clima,
    ritmo,
    instrucao:
      typeof valor.instrucao === "string" && valor.instrucao !== ""
        ? valor.instrucao
        : montarPrompt({ blocos, clima, ritmo }),
    barras: lerLista(valor.barras, lerBarra),
  };
}
