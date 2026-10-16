// As seis composições do render do servidor (`src/suno/pacote/direcao_de_arte.py`) e a regra de
// qual delas vale para cada quadro. A pessoa escolhe uma; ela vira a preferida e vale onde o papel
// do quadro permite. Onde não permite, o quadro cai numa composição que cabe, como faz o servidor.
import type { Slide } from "../../dados/cliente";
import type { Composicao } from "./modelo";

export interface InfoDaComposicao {
  valor: Composicao;
  rotulo: string;
}

export const COMPOSICOES: readonly InfoDaComposicao[] = [
  { valor: "editorial", rotulo: "Editorial" },
  { valor: "minimalista", rotulo: "Minimalista" },
  { valor: "infografico", rotulo: "Infográfico" },
  { valor: "comparativo", rotulo: "Comparativo" },
  { valor: "estatistico", rotulo: "Estatístico" },
  { valor: "narrativo", rotulo: "Narrativo" },
];

export const COMPOSICAO_PADRAO: Composicao = "editorial";

const VALORES = new Set<string>(COMPOSICOES.map((c) => c.valor));

export function ehComposicao(valor: unknown): valor is Composicao {
  return typeof valor === "string" && VALORES.has(valor);
}

/** As famílias visuais do servidor: o prefixo do nome da composição diz a qual ela pertence. */
const ROTULOS_DAS_FAMILIAS: Readonly<Record<string, string>> = {
  noticia: "Notícia",
  explicativo: "Explicativo",
  jornal: "Jornal",
  dados: "Dados",
  asset: "Asset",
};

/** A família de uma composição do servidor (o prefixo do nome), ou `null` nas seis que o editor desenha. */
export function familiaDaComposicao(composicao: string): string | null {
  if (ehComposicao(composicao)) return null;
  return composicao.split("_", 1)[0] ?? null;
}

export function rotuloDaFamilia(familia: string): string {
  return ROTULOS_DAS_FAMILIAS[familia] ?? familia;
}

/** Rótulo de qualquer composição do servidor, inclusive as das famílias (que o editor não desenha). */
export function rotuloDaComposicao(composicao: string): string {
  const desenhavel = COMPOSICOES.find((c) => c.valor === composicao);
  if (desenhavel) return desenhavel.rotulo;
  const familia = ROTULOS_DAS_FAMILIAS[composicao.split("_", 1)[0] ?? ""];
  return familia ? `Família ${familia}` : composicao;
}

/** O papel do quadro no carrossel: gancho (`hook`), ponto, citação ou CTA. */
export type PapelDoQuadro = Slide["tipo"];

const TODOS_OS_PAPEIS: readonly PapelDoQuadro[] = ["hook", "ponto", "citacao", "cta"];

/** Os papéis que cada composição aceita, como no catálogo do servidor. */
const PAPEIS_ACEITOS: Record<Composicao, readonly PapelDoQuadro[]> = {
  editorial: TODOS_OS_PAPEIS,
  minimalista: TODOS_OS_PAPEIS,
  narrativo: TODOS_OS_PAPEIS,
  infografico: ["ponto", "citacao"],
  comparativo: ["ponto", "citacao"],
  estatistico: ["ponto", "citacao", "cta"],
};

/** As que só fazem sentido com um número para mostrar. */
const EXIGE_DADO: ReadonlySet<Composicao> = new Set<Composicao>(["infografico", "estatistico"]);

/** As que reservam o campo do gráfico (o servidor preenche `{{GRAFICO}}` só nestas). */
const COM_GRAFICO: ReadonlySet<Composicao> = new Set<Composicao>([
  "infografico",
  "comparativo",
  "estatistico",
]);

export function temCampoDeGrafico(composicao: Composicao): boolean {
  return COM_GRAFICO.has(composicao);
}

export function papelDoQuadro(slide: Pick<Slide, "tipo">): PapelDoQuadro {
  return slide.tipo ?? "ponto";
}

export function rotuloDoPapel(papel: PapelDoQuadro): string {
  switch (papel) {
    case "hook":
      return "Gancho";
    case "citacao":
      return "Citação";
    case "cta":
      return "CTA";
    default:
      return "Ponto";
  }
}

/** `temDado` é "a Âncora do quadro chegou": sem número não há o que mostrar numa composição de número. */
export function aceitaQuadro(composicao: Composicao, slide: Pick<Slide, "tipo">, temDado: boolean): boolean {
  if (EXIGE_DADO.has(composicao) && !temDado) return false;
  return PAPEIS_ACEITOS[composicao].includes(papelDoQuadro(slide));
}

/** A composição que vale para o quadro: a preferida, quando cabe; senão a que o servidor usaria. */
export function composicaoDoQuadro(
  slide: Pick<Slide, "tipo">,
  preferida: Composicao,
  temDado: boolean,
): Composicao {
  if (aceitaQuadro(preferida, slide, temDado)) return preferida;
  return papelDoQuadro(slide) === "cta" ? "minimalista" : "editorial";
}
