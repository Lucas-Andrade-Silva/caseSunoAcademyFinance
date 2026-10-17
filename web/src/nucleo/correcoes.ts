import type { Laudo, Metrica } from "../dados/cliente";

export interface CampoCorrigivel {
  /** Índice do quadro ou da cena; no texto analítico vale zero. */
  indice: number;
  local: string;
  texto: string;
}

export interface OcorrenciaDaCorrecao {
  indice: number;
  local: string;
  trecho: string;
}

export interface PontoDaCorrecao {
  metrica: Metrica;
  instrucao: string;
  ocorrencias: OcorrenciaDaCorrecao[];
}

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase("pt-BR");
}

function trechosEntreAspas(texto: string): string[] {
  return [...texto.matchAll(/«([^»]+)»/g)].map((resultado) => resultado[1].trim());
}

function trechoDaObservacao(texto: string): string | null {
  const numero = texto.match(/^Número sem Âncora que o sustente:\s*(.+)$/i)?.[1];
  if (numero) return numero.trim();
  const recomendacao = texto.match(/^Recomendação \([^)]*\):\s*(.+)$/i)?.[1];
  return recomendacao?.trim() ?? null;
}

function candidatosDosTextos(textos: readonly string[]): string[] {
  const candidatos = textos.flatMap((texto) => [
    ...trechosEntreAspas(texto),
    ...(trechoDaObservacao(texto) ? [trechoDaObservacao(texto) as string] : []),
  ]);
  return [...new Set(candidatos.filter(Boolean))];
}

function localizar(candidatos: readonly string[], campos: readonly CampoCorrigivel[]): OcorrenciaDaCorrecao[] {
  const achados: OcorrenciaDaCorrecao[] = [];
  for (const campo of campos) {
    const campoNormalizado = normalizar(campo.texto);
    const trecho = candidatos.find((candidato) => campoNormalizado.includes(normalizar(candidato)));
    if (!trecho) continue;
    achados.push({ indice: campo.indice, local: campo.local, trecho });
  }
  return achados;
}

/**
 * Liga as evidências legíveis do Laudo aos campos que a pessoa pode editar. O servidor continua
 * sendo a única fonte do julgamento; esta função apenas encontra, no conteúdo atual, as frases e
 * os números que ele já apontou.
 */
export function localizarCorrecoes(
  laudo: Laudo | null | undefined,
  campos: readonly CampoCorrigivel[],
): PontoDaCorrecao[] {
  if (!laudo || laudo.destino === "aprovado") return [];
  const porMetrica = new Map(laudo.medidas.map((medida) => [medida.metrica, medida]));
  const pontos: PontoDaCorrecao[] = (laudo.correcoes ?? []).map((correcao) => {
    const observacoes = porMetrica.get(correcao.metrica)?.observacoes ?? [];
    const candidatos = candidatosDosTextos([correcao.instrucao, ...observacoes]);
    return {
      metrica: correcao.metrica,
      instrucao: correcao.instrucao,
      ocorrencias: localizar(candidatos, campos),
    };
  });

  // Integridade da extração não tem Correção porque reescrever não recupera uma Âncora ausente.
  // Ainda assim, a pessoa precisa ver esse motivo no mesmo lugar que os demais bloqueios.
  for (const medida of laudo.medidas) {
    if (medida.atingiu !== false || pontos.some((ponto) => ponto.metrica === medida.metrica)) continue;
    pontos.push({
      metrica: medida.metrica,
      instrucao: medida.observacoes?.join(" ") || "Esta medida ficou fora do Limiar.",
      ocorrencias: localizar(candidatosDosTextos(medida.observacoes ?? []), campos),
    });
  }
  return pontos;
}

export function indicesComCorrecao(pontos: readonly PontoDaCorrecao[]): ReadonlySet<number> {
  return new Set(pontos.flatMap((ponto) => ponto.ocorrencias.map((ocorrencia) => ocorrencia.indice)));
}
