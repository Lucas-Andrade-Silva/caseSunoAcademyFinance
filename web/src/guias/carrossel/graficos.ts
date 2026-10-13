// A Âncora no quadro: como citá-la (a forma canônica do servidor) e qual gráfico o quadro leva.
// Não inventa número: sem a Âncora, não há gráfico.
import type { AncoraNumerica } from "../../dados/cliente";
import { temCampoDeGrafico } from "./composicoes";
import type { AncoraDeQuadro, Composicao, GraficoDoQuadro } from "./modelo";

const SELIC_ANTERIOR = "selic_anterior";
const SELIC_DECIDIDA = "selic_decidida";

/** Espelha `AncoraNumerica.citacao()` de `src/suno/dominio.py`. */
export function citarAncora(
  ancora: Pick<AncoraNumerica, "valor_literal" | "unidade" | "qualificador">,
): string {
  const { valor_literal: literal, unidade, qualificador } = ancora;
  switch (unidade) {
    case "data":
    case "votos":
    case "numero":
      return literal;
    case "R$":
      return `R$ ${literal}`;
    case "%":
      if (qualificador?.endsWith("+")) return `${qualificador}${literal}%`;
      if (qualificador) return `${literal}% ${qualificador}`;
      return `${literal}%`;
    case "% a.a.":
      return `${literal}% a.a.`;
    default:
      return `${literal} ${unidade}`;
  }
}

export function ancoraDeQuadro(ancora: AncoraNumerica): AncoraDeQuadro {
  return {
    chave: ancora.chave,
    rotulo: ancora.rotulo,
    citacao: citarAncora(ancora),
    valor: ancora.valor ?? null,
  };
}

/**
 * O gráfico do quadro, como o servidor desenha: as duas Selic viram barras Antes e Depois (menos na
 * composição estatística, que só mostra o número); qualquer outra Âncora vira o número grande.
 */
export function escolherGrafico(
  dado: string | null | undefined,
  ancoras: readonly AncoraDeQuadro[],
  composicao: Composicao,
): GraficoDoQuadro | null {
  if (!dado || !temCampoDeGrafico(composicao)) return null;
  const ancora = ancoras.find((a) => a.chave === dado);
  if (!ancora) return null;
  if (composicao === "estatistico") return { jeito: "numero", ancora };
  const antes = ancoras.find((a) => a.chave === SELIC_ANTERIOR);
  const depois = ancoras.find((a) => a.chave === SELIC_DECIDIDA);
  const comparaveis =
    (dado === SELIC_ANTERIOR || dado === SELIC_DECIDIDA) &&
    antes?.valor != null &&
    depois?.valor != null;
  if (comparaveis && antes && depois) return { jeito: "barras", antes, depois };
  return { jeito: "numero", ancora };
}

/** A altura de uma barra de 0 a `maxima` px, em proporção ao maior valor das duas. */
export function alturaDaBarra(valor: number | null, teto: number, maxima: number): number {
  if (!valor || !teto) return 0;
  return Math.round((maxima * valor) / teto);
}

function maiuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function dividir(texto: string, separador: string): [string, string] | null {
  const posicao = texto.indexOf(separador);
  if (posicao < 0) return null;
  const antes = texto.slice(0, posicao).trim();
  const depois = texto.slice(posicao + separador.length).trim();
  return antes && depois ? [antes, depois] : null;
}

/** Divide o corpo em dois painéis sem inventar texto novo (o mesmo critério do servidor). */
export function partesDaComparacao(texto: string): [string, string] {
  for (const [separador, conector] of [
    [", conquanto ", "conquanto "],
    [", embora ", "embora "],
  ] as const) {
    const partes = dividir(texto, separador);
    if (partes) return [partes[0], maiuscula(conector) + partes[1]];
  }
  for (const separador of [";", " enquanto ", " mas ", ". "]) {
    const partes = dividir(texto, separador);
    if (partes) return partes;
  }
  const palavras = texto.split(/\s+/).filter(Boolean);
  const meio = Math.max(1, Math.floor(palavras.length / 2));
  const esquerda = palavras.slice(0, meio).join(" ");
  const direita = palavras.slice(meio).join(" ") || esquerda;
  return [esquerda, direita];
}
