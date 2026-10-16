import { describe, expect, it } from "vitest";
import type { PapeisDaFamilia, ReferenciaVisual } from "../../dados/cliente";
import { SUNO_ESCURO, familiaDaReferencia, opcoesDeFamilia, papeisQueFaltam, referenciaDaComposicao } from "./familias";

function ref(identificador: string, composicao: string, aprovada = true): ReferenciaVisual {
  return { identificador, composicao, aprovada, titulo: identificador } as ReferenciaVisual;
}

const REFERENCIAS = [
  ref("asset-aviso", "asset_aviso"),
  ref("asset-capa", "asset_capa"),
  ref("comparativo", "comparativo"),
  ref("dados-cta", "dados_cta"),
  ref("dados-texto", "dados_texto_grande"),
  ref("jornal-capa", "jornal_capa", false),
];

const FAMILIAS: PapeisDaFamilia[] = [
  { familia: "asset", papeis: ["cta", "hook"] },
  { familia: "dados", papeis: ["citacao", "cta", "hook", "ponto"] },
];

const SLIDES = [{ tipo: "hook" as const }, { tipo: "ponto" as const }, { tipo: "citacao" as const }, { tipo: "cta" as const }];

describe("famílias do carrossel", () => {
  it("abre com o Suno escuro e uma opção por família aprovada", () => {
    const opcoes = opcoesDeFamilia(REFERENCIAS, FAMILIAS, SLIDES);
    expect(opcoes.map((o) => o.valor)).toEqual([SUNO_ESCURO, "asset", "dados"]);
  });

  it("põe a capa da família como primeiro layout", () => {
    const asset = opcoesDeFamilia(REFERENCIAS, FAMILIAS, SLIDES).find((o) => o.valor === "asset");
    expect(asset?.layouts.map((r) => r.identificador)).toEqual(["asset-capa", "asset-aviso"]);
  });

  it("deixa o fecho da família por último", () => {
    const dados = opcoesDeFamilia(REFERENCIAS, FAMILIAS, SLIDES).find((o) => o.valor === "dados");
    expect(dados?.layouts.map((r) => r.identificador)).toEqual(["dados-texto", "dados-cta"]);
  });

  it("marca como indisponível a família que não cobre os papéis dos quadros", () => {
    const opcoes = opcoesDeFamilia(REFERENCIAS, FAMILIAS, SLIDES);
    expect(opcoes.find((o) => o.valor === "asset")?.indisponivel).toBe("Sem layout para ponto e citação");
    expect(opcoes.find((o) => o.valor === "dados")?.indisponivel).toBeNull();
  });

  it("não bloqueia enquanto não sabe os papéis das famílias", () => {
    expect(opcoesDeFamilia(REFERENCIAS, undefined, SLIDES).every((o) => o.indisponivel === null)).toBe(true);
  });

  it("lista cada papel que falta uma vez só", () => {
    expect(papeisQueFaltam(["hook"], [{ tipo: "ponto" }, { tipo: "ponto" }, { tipo: "cta" }])).toEqual(["Ponto", "CTA"]);
  });

  it("acha a família e a referência da composição", () => {
    expect(familiaDaReferencia(ref("x", "dados_cta"))).toBe("dados");
    expect(familiaDaReferencia(ref("x", "comparativo"))).toBe(SUNO_ESCURO);
    expect(familiaDaReferencia(null)).toBe(SUNO_ESCURO);
    expect(referenciaDaComposicao(REFERENCIAS, "comparativo")).toBe("comparativo");
    expect(referenciaDaComposicao(REFERENCIAS, "narrativo")).toBeNull();
  });
});
