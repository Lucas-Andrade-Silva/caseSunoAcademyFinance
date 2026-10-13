// Os tipos que as peças da guia Carrossel trocam entre si. Sem visual e sem rede: os arquivos
// puros (composições, paletas, montagem, direção da imagem) só dependem daqui.
import type { Audiencia, ComposicaoCarrossel, Slide } from "../../dados/cliente";

/**
 * As composições que o editor do navegador sabe desenhar. O servidor tem outras (as famílias
 * visuais, `ComposicaoCarrossel` completo): elas só existem no render do servidor, por ora.
 */
export type Composicao = Extract<
  ComposicaoCarrossel,
  "editorial" | "minimalista" | "infografico" | "comparativo" | "estatistico" | "narrativo"
>;

/** O tamanho do quadro que o servidor renderiza e que a exportação entrega. */
export const LARGURA_DO_QUADRO = 1080;
export const ALTURA_DO_QUADRO = 1350;

/** Os nomes do catálogo de ícones do vídeo (`IconeDeCena`, em `src/suno/dominio.py`). */
export type IdDoIcone =
  | "juros"
  | "inflacao"
  | "grafico_alta"
  | "grafico_queda"
  | "grafico_estavel"
  | "calendario"
  | "banco"
  | "bolso"
  | "alerta"
  | "lupa"
  | "documento"
  | "balanca"
  | "relogio"
  | "pergunta"
  | "check";

/** Quatro cores em hexadecimal de seis dígitos; `texto` sobre `fundo` passa de 4,5:1. */
export interface Paleta {
  id: string;
  nome: string;
  fundo: string;
  texto: string;
  destaque: string;
  apoio: string;
}

/** O que o quadro usa de uma Âncora: o texto citado e, quando existe, o valor para a altura da barra. */
export interface AncoraDeQuadro {
  chave: string;
  rotulo: string;
  citacao: string;
  valor: number | null;
}

export type GraficoDoQuadro =
  | { jeito: "numero"; ancora: AncoraDeQuadro }
  | { jeito: "barras"; antes: AncoraDeQuadro; depois: AncoraDeQuadro };

/** Um quadro pronto para desenhar: o texto, a composição que vale para ele e o que vai junto. */
export interface QuadroMontado {
  slide: Slide;
  composicao: Composicao;
  grafico: GraficoDoQuadro | null;
  icones: IdDoIcone[];
  indice: number;
  total: number;
}

/** O que "Salvar design" guarda e o pedido leva ao servidor. */
export interface Design {
  composicao: Composicao;
  referencia: string | null;
}

/** Um carrossel gerado na guia: tudo o que o desenho do quadro precisa, congelado. */
export interface Montagem {
  audiencia: Audiencia;
  slides: Slide[];
  composicao: Composicao;
  referenciaId: string | null;
  paleta: Paleta;
  icones: IdDoIcone[];
  ancoras: AncoraDeQuadro[];
}
