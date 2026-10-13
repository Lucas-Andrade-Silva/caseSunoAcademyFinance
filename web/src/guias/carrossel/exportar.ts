// Exportar carrossel: fotografa cada quadro em 1080 x 1350 px (html-to-image), junta os PNGs num zip
// (fflate) e entrega o arquivo. As fontes vão embutidas na imagem (`cssDasFamilias`), então o PNG
// sai com Anton e Poppins mesmo sem rede e sem as fontes instaladas.
import { zipSync } from "fflate";
import { toPng } from "html-to-image";
import { ALTURA_DO_QUADRO, LARGURA_DO_QUADRO } from "./modelo";
import { nomeDoQuadro } from "./nomesDeArquivo";
import { cssDasFamilias } from "./tipografia";

function bytesDoDataUrl(dataUrl: string): Uint8Array {
  const binario = atob(dataUrl.slice(dataUrl.indexOf(",") + 1));
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i += 1) bytes[i] = binario.charCodeAt(i);
  return bytes;
}

/** Um PNG por quadro, na ordem dos nós, já em bytes. */
export async function fotografarQuadros(nos: readonly HTMLElement[]): Promise<Uint8Array[]> {
  const fontEmbedCSS = await cssDasFamilias();
  const imagens: Uint8Array[] = [];
  // Um de cada vez: cada fotografia clona a árvore inteira e a memória agradece.
  for (const no of nos) {
    const dataUrl = await toPng(no, {
      width: LARGURA_DO_QUADRO,
      height: ALTURA_DO_QUADRO,
      pixelRatio: 1,
      fontEmbedCSS,
    });
    imagens.push(bytesDoDataUrl(dataUrl));
  }
  return imagens;
}

/** O zip com `slide-01.png`, `slide-02.png`… PNG já é comprimido, então o zip só guarda. */
export function zipDosQuadros(imagens: readonly Uint8Array[]): Uint8Array {
  const arquivos: Record<string, Uint8Array> = {};
  imagens.forEach((bytes, indice) => {
    arquivos[nomeDoQuadro(indice)] = bytes;
  });
  return zipSync(arquivos, { level: 0 });
}

export function baixarArquivo(bytes: Uint8Array, nome: string): void {
  const copia = new Uint8Array(bytes);
  const endereco = URL.createObjectURL(new Blob([copia], { type: "application/zip" }));
  const ancora = document.createElement("a");
  ancora.href = endereco;
  ancora.download = nome;
  document.body.appendChild(ancora);
  ancora.click();
  ancora.remove();
  window.setTimeout(() => URL.revokeObjectURL(endereco), 10_000);
}
