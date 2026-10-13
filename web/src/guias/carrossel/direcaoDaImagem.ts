// Como deve ser a imagem de um quadro, em uma frase concreta. Determinística: sai do papel do
// quadro, da composição que vale para ele, do gráfico (quando há Âncora) e do destaque do título.
// Descreve o desenho que o render do servidor faz; as cores seguem a paleta escolhida, por isso o
// texto fala em "cor de destaque" e não em vermelho.
import type { Slide } from "../../dados/cliente";
import { papelDoQuadro, type PapelDoQuadro } from "./composicoes";
import type { Composicao, GraficoDoQuadro } from "./modelo";

function oGrafico(grafico: GraficoDoQuadro): string {
  if (grafico.jeito === "barras") {
    return `duas barras, Antes e Depois: ${grafico.antes.citacao} e ${grafico.depois.citacao}`;
  }
  return `número grande na cor de destaque: ${grafico.ancora.citacao} (${grafico.ancora.rotulo})`;
}

function base(
  composicao: Composicao,
  papel: PapelDoQuadro,
  indice: number,
  total: number,
  grafico: GraficoDoQuadro | null,
): string {
  switch (composicao) {
    case "minimalista":
      if (papel === "hook") {
        return "Capa limpa: título centralizado em maiúsculas, uma linha de destaque e muito respiro, com só um círculo discreto ao fundo.";
      }
      if (papel === "cta") {
        return "Fechamento limpo: título centralizado, linha de destaque e uma frase de apoio, com muito respiro.";
      }
      return "Título centralizado em maiúsculas, linha de destaque e uma frase de apoio, com poucos elementos e muito respiro.";
    case "infografico":
      return grafico
        ? `Painel de texto à esquerda, com formas orgânicas e uma linha de tendência ao fundo; à direita, ${oGrafico(grafico)}.`
        : "Título no alto e painel de texto, com formas orgânicas e uma linha de tendência ao fundo.";
    case "comparativo":
      return grafico
        ? `Dois painéis lado a lado, ponto A contra ponto B; embaixo, ${oGrafico(grafico)}.`
        : "Dois painéis lado a lado, ponto A contra ponto B, sob o título.";
    case "estatistico":
      return grafico
        ? `Título no alto e painel de texto embaixo, com anéis concêntricos ao fundo; no centro, ${oGrafico(grafico)}.`
        : "Título no alto e painel de texto, com anéis concêntricos ao fundo.";
    case "narrativo":
      return `Etapa ${indice + 1} de ${total}: numeral gigante e translúcido atrás do título, painel de texto com régua de destaque embaixo.`;
    default:
      if (papel === "hook") {
        return "Capa: título enorme em maiúsculas à esquerda, painel de apoio à direita e formas orgânicas nos cantos.";
      }
      if (papel === "cta") {
        return "Fechamento: título em maiúsculas à esquerda, painel de apoio com régua de destaque e formas orgânicas nos cantos.";
      }
      return "Título em maiúsculas à esquerda, painel de apoio à direita e formas orgânicas nos cantos.";
  }
}

export function direcaoDaImagem(
  slide: Slide,
  composicao: Composicao,
  indice: number,
  total: number,
  grafico: GraficoDoQuadro | null = null,
): string {
  const frase = base(composicao, papelDoQuadro(slide), indice, total, grafico);
  const destaque = slide.destaque && slide.titulo.includes(slide.destaque) ? slide.destaque : null;
  return destaque ? `${frase} Realce em “${destaque}” no título.` : frase;
}
