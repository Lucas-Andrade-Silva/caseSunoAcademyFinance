// A seleção da Matriz no passo "Configurar" da Curadoria: marcar uma Célula, uma linha (uma
// Audiência inteira) ou uma coluna (um Formato inteiro). Lógica pura, coberta pelo Vitest.
// O resultado é sempre a lista na ordem da Matriz, que é a ordem em que o servidor grava.

export interface Posicao {
  audiencia: string;
  formato: string;
}

/** A mesma ordem de `MATRIZ` em src/suno/dominio.py. */
export const AUDIENCIAS_NA_ORDEM = ["iniciante", "intermediario", "avancado"] as const;
export const FORMATOS_NA_ORDEM = ["texto_analitico", "carrossel", "roteiro"] as const;

export function matrizInteira(): Posicao[] {
  return AUDIENCIAS_NA_ORDEM.flatMap((audiencia) =>
    FORMATOS_NA_ORDEM.map((formato) => ({ audiencia, formato })),
  );
}

function chave(posicao: Posicao): string {
  return `${posicao.audiencia}:${posicao.formato}`;
}

/** Tira repetição e põe na ordem da Matriz. Posição fora da Matriz é descartada. */
function emOrdem(selecao: readonly Posicao[]): Posicao[] {
  const marcadas = new Set(selecao.map(chave));
  return matrizInteira().filter((posicao) => marcadas.has(chave(posicao)));
}

export function estaSelecionada(selecao: readonly Posicao[], posicao: Posicao): boolean {
  return selecao.some((outra) => chave(outra) === chave(posicao));
}

export function alternarCelula(selecao: readonly Posicao[], posicao: Posicao): Posicao[] {
  if (estaSelecionada(selecao, posicao)) {
    return emOrdem(selecao.filter((outra) => chave(outra) !== chave(posicao)));
  }
  return emOrdem([...selecao, posicao]);
}

export function linhaCompleta(selecao: readonly Posicao[], audiencia: string): boolean {
  return FORMATOS_NA_ORDEM.every((formato) => estaSelecionada(selecao, { audiencia, formato }));
}

export function colunaCompleta(selecao: readonly Posicao[], formato: string): boolean {
  return AUDIENCIAS_NA_ORDEM.every((audiencia) =>
    estaSelecionada(selecao, { audiencia, formato }),
  );
}

/** Linha cheia limpa a linha; senão a completa. */
export function alternarLinha(selecao: readonly Posicao[], audiencia: string): Posicao[] {
  if (linhaCompleta(selecao, audiencia)) {
    return emOrdem(selecao.filter((posicao) => posicao.audiencia !== audiencia));
  }
  const linha = FORMATOS_NA_ORDEM.map((formato) => ({ audiencia, formato }));
  return emOrdem([...selecao, ...linha]);
}

/** Coluna cheia limpa a coluna; senão a completa. */
export function alternarColuna(selecao: readonly Posicao[], formato: string): Posicao[] {
  if (colunaCompleta(selecao, formato)) {
    return emOrdem(selecao.filter((posicao) => posicao.formato !== formato));
  }
  const coluna = AUDIENCIAS_NA_ORDEM.map((audiencia) => ({ audiencia, formato }));
  return emOrdem([...selecao, ...coluna]);
}

export function resumirPedido(selecao: readonly Posicao[]): string {
  if (selecao.length === 0) return "nenhuma Célula";
  return `${selecao.length} ${selecao.length === 1 ? "Célula" : "Células"}`;
}
