// Monta os quadros do carrossel: a composição de cada um, o gráfico da Âncora e onde cada ícone
// pedido aparece. Lógica pura (Vitest cobre); o desenho fica em `Quadro.tsx`.
import type { ReferenciaVisual, Slide } from "../../dados/cliente";
import { composicaoDoQuadro, ehComposicao, temCampoDeGrafico } from "./composicoes";
import { escolherGrafico } from "./graficos";
import type {
  AncoraDeQuadro,
  Composicao,
  GraficoDoQuadro,
  IdDoIcone,
  Montagem,
  QuadroMontado,
} from "./modelo";

/** Que ícone combina com que Âncora: o ícone vai, de preferência, ao quadro que mostra aquele dado. */
const AFINIDADE: Partial<Record<IdDoIcone, (dado: string) => boolean>> = {
  juros: (dado) => dado.startsWith("selic") || dado === "variacao_pb",
  inflacao: (dado) => dado.startsWith("ipca") || dado === "alvo_inflacao",
  calendario: (dado) => dado.startsWith("data_"),
  balanca: (dado) => dado === "placar_votacao",
};

/**
 * Reparte os ícones pelos quadros sem perder nenhum: cada ícone cai uma vez, no quadro cujo dado
 * combina com ele; os demais vão, um a um, para o quadro que tem menos ícones até então.
 */
export function distribuirIcones(
  icones: readonly IdDoIcone[],
  dados: readonly (string | null | undefined)[],
): IdDoIcone[][] {
  const quadros: IdDoIcone[][] = dados.map(() => []);
  if (quadros.length === 0) return quadros;
  const sobras: IdDoIcone[] = [];
  for (const icone of new Set(icones)) {
    const combina = AFINIDADE[icone];
    const alvo = combina ? dados.findIndex((dado) => !!dado && combina(dado)) : -1;
    if (alvo >= 0) quadros[alvo].push(icone);
    else sobras.push(icone);
  }
  for (const icone of sobras) {
    let menor = 0;
    for (let i = 1; i < quadros.length; i += 1) {
      if (quadros[i].length < quadros[menor].length) menor = i;
    }
    quadros[menor].push(icone);
  }
  return quadros;
}

interface EntradaDaMontagem {
  slides: readonly Slide[];
  /** A composição escolhida: vale onde o papel do quadro permite. */
  preferida: Composicao;
  ancoras: readonly AncoraDeQuadro[];
  icones: readonly IdDoIcone[];
}

export function montarQuadros({ slides, preferida, ancoras, icones }: EntradaDaMontagem): QuadroMontado[] {
  const porQuadro = distribuirIcones(
    icones,
    slides.map((slide) => slide.dado),
  );
  return slides.map((slide, indice) => {
    const temDado = !!slide.dado && ancoras.some((a) => a.chave === slide.dado);
    const composicao = composicaoDoQuadro(slide, preferida, temDado);
    return {
      slide,
      composicao,
      grafico: escolherGrafico(slide.dado, ancoras, composicao),
      icones: porQuadro[indice],
      indice,
      total: slides.length,
    };
  });
}

/** Os quadros de um carrossel já gerado (e de um salvo): a mesma conta, com tudo congelado. */
export function quadrosDaMontagem(montagem: Pick<Montagem, "slides" | "composicao" | "ancoras" | "icones">): QuadroMontado[] {
  return montarQuadros({
    slides: montagem.slides,
    preferida: montagem.composicao,
    ancoras: montagem.ancoras,
    icones: montagem.icones,
  });
}

// ---- Quadros de exemplo, para ver uma referência dentro do celular ------------------------

/** O número de exemplo: o quadro mostra o formato do gráfico, nunca um valor de verdade. */
const NUMERO_DE_EXEMPLO = "XX,X%";

function ancoraDeExemplo(chave: string, rotulo: string, valor: number): AncoraDeQuadro {
  return { chave, rotulo, citacao: NUMERO_DE_EXEMPLO, valor };
}

function graficoDeExemplo(composicao: Composicao): GraficoDoQuadro | null {
  if (!temCampoDeGrafico(composicao)) return null;
  if (composicao === "estatistico") {
    return { jeito: "numero", ancora: ancoraDeExemplo("exemplo", "Indicador de exemplo", 12) };
  }
  return {
    jeito: "barras",
    antes: ancoraDeExemplo("exemplo_antes", "Antes", 14),
    depois: ancoraDeExemplo("exemplo_depois", "Depois", 10),
  };
}

const TEXTOS_DE_EXEMPLO: readonly Pick<Slide, "tipo" | "titulo" | "corpo">[] = [
  { tipo: "ponto", titulo: "Um ponto de cada vez", corpo: "Cada quadro traz uma ideia curta, escrita para a audiência escolhida." },
  { tipo: "ponto", titulo: "O número em destaque", corpo: "Quando há um dado, ele ganha a maior hierarquia do quadro." },
  { tipo: "citacao", titulo: "Uma frase para guardar", corpo: "A citação segue a mesma linguagem visual dos outros quadros." },
  { tipo: "cta", titulo: "Salve para consultar depois", corpo: "O último quadro convida a seguir a conta e a ler o comunicado completo." },
];

/**
 * Quadros de exemplo para ver uma referência dentro do celular: o primeiro leva o título dela e
 * todos usam a composição dela. O texto é fixo e o número é um marcador; nada aqui é conteúdo real.
 */
export function montarQuadrosDeExemplo(referencia: Pick<ReferenciaVisual, "titulo" | "tema" | "composicao">): QuadroMontado[] {
  // O editor só desenha as seis composições; a família visual cai na preferida do editor.
  const composicao: Composicao = ehComposicao(referencia.composicao) ? referencia.composicao : "editorial";
  const slides: Slide[] = [
    {
      tipo: "hook",
      titulo: referencia.titulo,
      corpo: `Tema: ${referencia.tema}. Conteúdo de exemplo para ver o ritmo e o respiro do carrossel.`,
    },
    ...TEXTOS_DE_EXEMPLO.map((texto) => ({ ...texto })),
  ];
  return slides.map((slide, indice) => ({
    slide,
    composicao,
    grafico: indice === 2 ? graficoDeExemplo(composicao) : null,
    icones: [],
    indice,
    total: slides.length,
  }));
}
