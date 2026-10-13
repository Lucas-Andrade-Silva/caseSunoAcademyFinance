// As guias do app, na ordem da barra lateral. A ordem importa: a vista que entra desliza do lado
// em que a guia está na barra. Configurações fica embaixo, separada, e é a última da ordem.
import type { Formato } from "../dados/cliente";

export type IdDaGuia =
  | "ingestao"
  | "texto"
  | "carrossel"
  | "video"
  | "historico"
  | "configuracoes";

export interface Guia {
  id: IdDaGuia;
  caminho: string;
  rotulo: string;
  /** O Formato que a guia gera, quando gera. */
  formato: Formato | null;
}

export const GUIAS: readonly Guia[] = [
  { id: "ingestao", caminho: "/ingestao", rotulo: "Ingestão", formato: null },
  { id: "texto", caminho: "/texto", rotulo: "Texto analítico", formato: "texto_analitico" },
  { id: "carrossel", caminho: "/carrossel", rotulo: "Carrossel", formato: "carrossel" },
  { id: "video", caminho: "/video", rotulo: "Vídeo", formato: "roteiro" },
  { id: "historico", caminho: "/historico", rotulo: "Histórico", formato: null },
  { id: "configuracoes", caminho: "/configuracoes", rotulo: "Configurações", formato: null },
];

export const GUIA_INICIAL = GUIAS[0];

/** A guia de um caminho do navegador; `null` quando o caminho não é de nenhuma. */
export function guiaDoCaminho(caminho: string): Guia | null {
  return GUIAS.find((guia) => caminho === guia.caminho || caminho.startsWith(`${guia.caminho}/`)) ?? null;
}

/** A guia que gera um Formato. */
export function guiaDoFormato(formato: Formato): Guia {
  return GUIAS.find((guia) => guia.formato === formato) ?? GUIA_INICIAL;
}
