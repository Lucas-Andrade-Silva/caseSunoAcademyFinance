// O texto que a pessoa aplicou ou reabriu do Histórico, por audiência. Vale para uma Saída só
// (`execucaoId`): ao gerar de novo, o que ficou para trás deixa de valer. Fica no `sessionStorage`
// para sobreviver a um recarregamento da página.
import { AUDIENCIAS, type Audiencia } from "../../dados/cliente";
import { ler } from "../../nucleo/armazenamento";

export const CHAVE_DAS_EDICOES = "suno.texto.edicoes";

export type HtmlPorAudiencia = Partial<Record<Audiencia, string>>;

export interface EdicoesDaSessao {
  execucaoId: string | null;
  html: HtmlPorAudiencia;
}

export const SEM_EDICOES: EdicoesDaSessao = { execucaoId: null, html: {} };

export function validarEdicoes(bruto: unknown): EdicoesDaSessao {
  if (typeof bruto !== "object" || bruto === null) return SEM_EDICOES;
  const { execucaoId, html } = bruto as Record<string, unknown>;
  if (typeof html !== "object" || html === null) return SEM_EDICOES;
  const limpo: HtmlPorAudiencia = {};
  for (const audiencia of AUDIENCIAS) {
    const valor = (html as Record<string, unknown>)[audiencia];
    if (typeof valor === "string" && valor.trim() !== "") limpo[audiencia] = valor;
  }
  return { execucaoId: typeof execucaoId === "string" ? execucaoId : null, html: limpo };
}

export function lerEdicoes(): EdicoesDaSessao {
  return validarEdicoes(ler<unknown>("sessao", CHAVE_DAS_EDICOES, null));
}

/** O que vale para a Saída atual: as edições de outra Saída não entram. */
export function valemPara(edicoes: EdicoesDaSessao, execucaoId: string | null): HtmlPorAudiencia {
  return edicoes.execucaoId === execucaoId ? edicoes.html : {};
}

/** Põe o HTML de uma audiência, descartando o que era de outra Saída. */
export function comEdicao(
  edicoes: EdicoesDaSessao,
  execucaoId: string | null,
  audiencia: Audiencia,
  html: string,
): EdicoesDaSessao {
  return { execucaoId, html: { ...valemPara(edicoes, execucaoId), [audiencia]: html } };
}
