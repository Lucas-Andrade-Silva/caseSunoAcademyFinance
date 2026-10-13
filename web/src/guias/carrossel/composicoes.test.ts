import { describe, expect, it } from "vitest";
import {
  COMPOSICOES,
  aceitaQuadro,
  composicaoDoQuadro,
  ehComposicao,
  rotuloDaComposicao,
  rotuloDoPapel,
} from "./composicoes";

describe("composições do servidor que o editor não desenha", () => {
  it("as famílias visuais não são composições do editor, mas têm rótulo", () => {
    expect(ehComposicao("explicativo_capa")).toBe(false);
    expect(ehComposicao("editorial")).toBe(true);
    expect(rotuloDaComposicao("explicativo_capa")).toBe("Família Explicativo");
    expect(rotuloDaComposicao("jornal_texto")).toBe("Família Jornal");
    expect(rotuloDaComposicao("editorial")).toBe("Editorial");
  });
});

describe("composicaoDoQuadro", () => {
  it("usa a preferida quando o papel permite", () => {
    expect(composicaoDoQuadro({ tipo: "ponto" }, "narrativo", false)).toBe("narrativo");
    expect(composicaoDoQuadro({ tipo: "hook" }, "minimalista", false)).toBe("minimalista");
    expect(composicaoDoQuadro({ tipo: "ponto" }, "infografico", true)).toBe("infografico");
  });

  it("composição de número sem a Âncora cai no editorial", () => {
    expect(composicaoDoQuadro({ tipo: "ponto" }, "estatistico", false)).toBe("editorial");
    expect(composicaoDoQuadro({ tipo: "citacao" }, "infografico", false)).toBe("editorial");
  });

  it("infográfico e comparativo não aceitam gancho nem CTA", () => {
    expect(composicaoDoQuadro({ tipo: "hook" }, "comparativo", true)).toBe("editorial");
    expect(composicaoDoQuadro({ tipo: "hook" }, "infografico", true)).toBe("editorial");
    expect(composicaoDoQuadro({ tipo: "cta" }, "comparativo", true)).toBe("minimalista");
    expect(composicaoDoQuadro({ tipo: "cta" }, "infografico", true)).toBe("minimalista");
  });

  it("o estatístico aceita o CTA quando há número", () => {
    expect(composicaoDoQuadro({ tipo: "cta" }, "estatistico", true)).toBe("estatistico");
  });

  it("o comparativo não exige número", () => {
    expect(aceitaQuadro("comparativo", { tipo: "ponto" }, false)).toBe(true);
  });

  it("devolve sempre uma composição que aceita o quadro", () => {
    for (const { valor } of COMPOSICOES) {
      for (const papel of ["hook", "ponto", "citacao", "cta"] as const) {
        for (const temDado of [true, false]) {
          const escolhida = composicaoDoQuadro({ tipo: papel }, valor, temDado);
          expect(aceitaQuadro(escolhida, { tipo: papel }, temDado)).toBe(true);
        }
      }
    }
  });
});

describe("catálogo", () => {
  it("tem as seis composições do servidor", () => {
    expect(COMPOSICOES.map((c) => c.valor).sort()).toEqual(
      ["comparativo", "editorial", "estatistico", "infografico", "minimalista", "narrativo"],
    );
  });

  it("reconhece só valores do catálogo", () => {
    expect(ehComposicao("editorial")).toBe(true);
    expect(ehComposicao("outra")).toBe(false);
    expect(ehComposicao(null)).toBe(false);
  });

  it("rotula os papéis em português", () => {
    expect(rotuloDoPapel("hook")).toBe("Gancho");
    expect(rotuloDoPapel("citacao")).toBe("Citação");
    expect(rotuloDoPapel("cta")).toBe("CTA");
    expect(rotuloDoPapel("ponto")).toBe("Ponto");
  });
});
