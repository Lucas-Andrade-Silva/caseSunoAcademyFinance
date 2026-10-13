// Os nomes do catálogo de Direção de cena (suno.video.design) em português legível, para a tela e
// para o texto do prompt. Cada tabela é indexada pelo valor do schema: se o catálogo do servidor
// ganhar um nome, o TypeScript acusa aqui. O que é padrão (entrada em corte, efeito nenhum) não
// tem frase: quem consulta recebe `null` e não escreve nada.
import type { BlocoFala } from "../../dados/cliente";
import { rotuloDaDirecao } from "../../texto/rotulos";

type NomeDaCena = BlocoFala["cena"];
type NomeDoIcone = NonNullable<BlocoFala["icone"]>;
type NomeDaEntrada = Exclude<BlocoFala["entrada"], "corte">;
type NomeDaAnimacao = BlocoFala["texto_anima"];
type NomeDoEfeito = Exclude<BlocoFala["efeito"], "nenhum">;

// O layout espelha `CENAS` em suno.video.design: onde cai o texto e o que o avatar faz.
const CENAS: Record<NomeDaCena, { nome: string; layout: string }> = {
  gancho: {
    nome: "Gancho",
    layout: "abertura, com o avatar grande no centro e o texto no terço superior",
  },
  dado_grande: {
    nome: "Dado grande",
    layout: "o número em destaque no centro e o avatar pequeno no canto inferior direito",
  },
  texto_destaque: {
    nome: "Texto em destaque",
    layout: "uma ideia curta em texto grande no terço superior e o avatar pequeno no canto inferior direito",
  },
  lista: {
    nome: "Lista",
    layout: "itens curtos em sequência no centro e o avatar pequeno no canto inferior direito",
  },
  comparacao: {
    nome: "Comparação",
    layout: "dois lados no centro, sem o avatar na tela (só a voz)",
  },
  citacao: {
    nome: "Citação",
    layout: "um trecho curto no centro e o avatar pequeno no canto inferior direito",
  },
  encerramento: {
    nome: "Encerramento",
    layout: "fechamento, com o avatar grande no centro e o texto no terço superior",
  },
};

const ICONES: Record<NomeDoIcone, string> = {
  juros: "Taxa de juros",
  inflacao: "Inflação",
  grafico_alta: "Gráfico em alta",
  grafico_queda: "Gráfico em queda",
  grafico_estavel: "Gráfico estável",
  calendario: "Calendário",
  banco: "Banco",
  bolso: "Bolso",
  alerta: "Alerta",
  lupa: "Lupa",
  documento: "Documento",
  balanca: "Balança",
  relogio: "Relógio",
  pergunta: "Ponto de interrogação",
  check: "Marca de confirmação",
};

const ENTRADAS: Record<NomeDaEntrada, string> = {
  fade: "dissolve suave (fade)",
  deslizar_esquerda: "a cena entra deslizando pela direita",
  deslizar_cima: "a cena entra subindo",
  zoom: "aproximação rápida (zoom)",
};

const ANIMACOES_DO_TEXTO: Record<NomeDaAnimacao, string> = {
  aparecer: "aparece inteiro de uma vez",
  fade: "surge com fade",
  deslizar_baixo: "desce de cima até o lugar",
  pop: "cresce de pequeno ao tamanho final (pop)",
  digitar: "aparece letra por letra, como digitado",
};

const EFEITOS: Record<NomeDoEfeito, string> = {
  zoom_lento: "aproximação lenta durante toda a cena",
  pulso: "o texto pulsa uma vez, destacando o ponto",
  sublinhado: "uma barra de destaque sob o texto",
  contagem: "o número sobe até o valor final",
};

function procurar<V>(catalogo: Record<string, V>, chave: string | null | undefined): V | undefined {
  return chave ? catalogo[chave] : undefined;
}

function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** "Dado grande". Um nome fora do catálogo aparece como veio, sem sublinhado. */
export function nomeDaCena(cena: string): string {
  return procurar(CENAS, cena)?.nome ?? capitalizar(rotuloDaDirecao(cena));
}

/** "Calendário"; `null` quando a cena não tem ícone. */
export function nomeDoIcone(icone: string | null | undefined): string | null {
  if (!icone) return null;
  return procurar(ICONES, icone) ?? capitalizar(rotuloDaDirecao(icone));
}

/** "Dado grande · Calendário": o que a Direção de cena escolheu, para a linha discreta da cena. */
export function direcaoDaCena(bloco: Pick<BlocoFala, "cena" | "icone">): string {
  return [nomeDaCena(bloco.cena), nomeDoIcone(bloco.icone)].filter(Boolean).join(" · ");
}

/** Onde o texto cai e o que o avatar faz na cena. */
export function layoutDaCena(cena: string): string | null {
  return procurar(CENAS, cena)?.layout ?? null;
}

/** Como a cena entra; `null` no corte, que é o padrão e não pede instrução. */
export function entradaPorExtenso(entrada: string | null | undefined): string | null {
  if (!entrada || entrada === "corte") return null;
  return procurar(ENTRADAS, entrada) ?? rotuloDaDirecao(entrada);
}

/** Como o texto da tela aparece. */
export function animacaoPorExtenso(animacao: string | null | undefined): string | null {
  if (!animacao) return null;
  return procurar(ANIMACOES_DO_TEXTO, animacao) ?? rotuloDaDirecao(animacao);
}

/** O efeito contínuo da cena; `null` quando não há (o padrão). */
export function efeitoPorExtenso(efeito: string | null | undefined): string | null {
  if (!efeito || efeito === "nenhum") return null;
  return procurar(EFEITOS, efeito) ?? rotuloDaDirecao(efeito);
}
