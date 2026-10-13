// Os nomes dos arquivos que o botão Exportar carrossel entrega: o zip da audiência e, dentro dele,
// um PNG por quadro. Separado de `exportar.ts` para o Vitest ler sem carregar a biblioteca de imagem.

/** `carrossel-iniciante.zip`. */
export function nomeDoZip(audiencia: string): string {
  return `carrossel-${audiencia}.zip`;
}

/** `slide-01.png`, `slide-02.png`…: o mesmo nome que o render do servidor grava. */
export function nomeDoQuadro(indice: number): string {
  return `slide-${String(indice + 1).padStart(2, "0")}.png`;
}
