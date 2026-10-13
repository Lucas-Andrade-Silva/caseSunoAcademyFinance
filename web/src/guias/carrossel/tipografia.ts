// As duas famílias do quadro: Anton nos títulos e Poppins no texto, as mesmas do render do servidor
// e ambas OFL. Só o subconjunto latino, que cobre o português. Importar este arquivo registra as
// famílias; `garantirFontes` espera o navegador carregá-las (o ajuste de tamanho mede depois disso)
// e `cssDasFamilias` entrega o @font-face em base64 que a exportação em PNG embute na imagem.
import "@fontsource/anton/latin-400.css";
import "@fontsource/poppins/latin-400.css";
import "@fontsource/poppins/latin-600.css";
import "@fontsource/poppins/latin-700.css";
import anton400 from "@fontsource/anton/files/anton-latin-400-normal.woff2?url";
import poppins400 from "@fontsource/poppins/files/poppins-latin-400-normal.woff2?url";
import poppins600 from "@fontsource/poppins/files/poppins-latin-600-normal.woff2?url";
import poppins700 from "@fontsource/poppins/files/poppins-latin-700-normal.woff2?url";

const FAMILIAS = [
  { familia: "Anton", peso: 400, arquivo: anton400 },
  { familia: "Poppins", peso: 400, arquivo: poppins400 },
  { familia: "Poppins", peso: 600, arquivo: poppins600 },
  { familia: "Poppins", peso: 700, arquivo: poppins700 },
] as const;

let carregadas: Promise<void> | null = null;

/** Resolve quando Anton e Poppins (400, 600 e 700) estão prontas para medir e desenhar. */
export function garantirFontes(): Promise<void> {
  carregadas ??= (
    typeof document === "undefined" || !document.fonts
      ? Promise.resolve([])
      : Promise.all(FAMILIAS.map((f) => document.fonts.load(`${f.peso} 40px "${f.familia}"`)))
  ).then(
    () => undefined,
    () => undefined,
  );
  return carregadas;
}

function paraDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader();
    leitor.onload = () => resolver(String(leitor.result));
    leitor.onerror = () => rejeitar(leitor.error);
    leitor.readAsDataURL(blob);
  });
}

let css: Promise<string> | null = null;

/** O @font-face das quatro fontes com os arquivos embutidos: a imagem exportada não depende de rede. */
export function cssDasFamilias(): Promise<string> {
  css ??= Promise.all(
    FAMILIAS.map(async (f) => {
      const resposta = await fetch(f.arquivo);
      const dados = await paraDataUrl(new Blob([await resposta.arrayBuffer()], { type: "font/woff2" }));
      return `@font-face{font-family:"${f.familia}";font-style:normal;font-weight:${f.peso};src:url(${dados}) format("woff2");}`;
    }),
  ).then((regras) => regras.join("\n"));
  css.catch(() => {
    css = null;
  });
  return css;
}
