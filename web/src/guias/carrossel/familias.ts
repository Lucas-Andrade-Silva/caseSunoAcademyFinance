// A Família visual do carrossel decide quem o desenha e o que dá para ajustar. O Suno escuro (os seis
// Layouts antigos) é desenhado pelo editor do navegador: tipo, paleta e ícones, com a prévia ao vivo.
// As outras (Notícia, Dados…) são recriadas dos posts reais da Suno e montadas no servidor: o tipo
// escolhe o Layout preferido, e cores e fontes são as do post real, por isso a paleta não vale nelas.
import type { PapeisDaFamilia, ReferenciaVisual, Slide } from "../../dados/cliente";
import { familiaDaComposicao, papelDoQuadro, rotuloDaFamilia, rotuloDoPapel } from "./composicoes";
import type { Composicao } from "./modelo";

/** O mesmo nome que o servidor dá à família dos seis Layouts antigos. */
export const SUNO_ESCURO = "suno_escuro";

export interface OpcaoDeFamilia {
  /** O nome da família no servidor. */
  valor: string;
  rotulo: string;
  /** Os Layouts da família (as referências aprovadas dela); vazio no Suno escuro, que usa os tipos. */
  layouts: ReferenciaVisual[];
  /** Por que a família não monta este carrossel, ou `null` quando monta. */
  indisponivel: string | null;
}

/** Os papéis dos quadros que a família não sabe desenhar. */
export function papeisQueFaltam(cobertos: readonly string[], slides: readonly Pick<Slide, "tipo">[]): string[] {
  const faltam = new Set(slides.map(papelDoQuadro).filter((papel) => !cobertos.includes(papel)));
  return [...faltam].map(rotuloDoPapel);
}

/** A capa primeiro, porque é o Layout que mais diz da família; o fecho (CTA, aviso legal) por último. */
function capaPrimeiro(a: ReferenciaVisual, b: ReferenciaVisual): number {
  const ordem = (r: ReferenciaVisual) =>
    r.composicao.endsWith("_capa") ? 0 : /_(cta|aviso)$/.test(r.composicao) ? 2 : 1;
  return ordem(a) - ordem(b);
}

export function opcoesDeFamilia(
  referencias: readonly ReferenciaVisual[],
  papeisDasFamilias: readonly PapeisDaFamilia[] | undefined,
  slides: readonly Pick<Slide, "tipo">[],
): OpcaoDeFamilia[] {
  const porFamilia = new Map<string, ReferenciaVisual[]>();
  for (const referencia of referencias) {
    const familia = familiaDaComposicao(referencia.composicao);
    if (!referencia.aprovada || familia === null) continue;
    porFamilia.set(familia, [...(porFamilia.get(familia) ?? []), referencia]);
  }
  const opcoes: OpcaoDeFamilia[] = [{ valor: SUNO_ESCURO, rotulo: "Suno escuro", layouts: [], indisponivel: null }];
  for (const [familia, layouts] of porFamilia) {
    const cobertos = papeisDasFamilias?.find((f) => f.familia === familia)?.papeis;
    const faltam = cobertos ? papeisQueFaltam(cobertos, slides) : [];
    opcoes.push({
      valor: familia,
      rotulo: rotuloDaFamilia(familia),
      layouts: [...layouts].sort(capaPrimeiro),
      indisponivel: faltam.length > 0 ? `Sem layout para ${faltam.join(" e ").toLowerCase()}` : null,
    });
  }
  return opcoes;
}

/** A família de uma referência escolhida; sem referência, ou numa das seis composições, Suno escuro. */
export function familiaDaReferencia(referencia: Pick<ReferenciaVisual, "composicao"> | null): string {
  return (referencia && familiaDaComposicao(referencia.composicao)) ?? SUNO_ESCURO;
}

/** No Suno escuro, a composição leva junto a referência aprovada dela (a instrução de design que vai ao servidor). */
export function referenciaDaComposicao(referencias: readonly ReferenciaVisual[], composicao: Composicao): string | null {
  return referencias.find((r) => r.aprovada && r.composicao === composicao)?.identificador ?? null;
}
