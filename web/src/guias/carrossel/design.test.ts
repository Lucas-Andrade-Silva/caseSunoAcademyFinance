import { describe, expect, it } from "vitest";
import type { ReferenciaVisual } from "../../dados/cliente";
import { extrasDoDesign, mesmoDesign } from "./design";

function referencia(identificador: string, composicao: ReferenciaVisual["composicao"], aprovada = true): ReferenciaVisual {
  return { identificador, composicao, aprovada } as ReferenciaVisual;
}

const referencias = [
  referencia("ed-1", "editorial"),
  referencia("ed-2", "editorial"),
  referencia("es-1", "estatistico", false),
  referencia("co-1", "comparativo"),
];

describe("extrasDoDesign", () => {
  it("leva composição e referência juntas, como o servidor exige", () => {
    expect(extrasDoDesign({ composicao: "comparativo", referencia: "co-1" }, referencias)).toEqual({
      composicaoVisual: "comparativo",
      referenciaVisual: "co-1",
    });
  });

  it("sem referência escolhida, usa a primeira aprovada da composição", () => {
    expect(extrasDoDesign({ composicao: "editorial", referencia: null }, referencias)).toEqual({
      composicaoVisual: "editorial",
      referenciaVisual: "ed-1",
    });
  });

  it("a referência de outra composição não vale", () => {
    expect(extrasDoDesign({ composicao: "editorial", referencia: "co-1" }, referencias)?.referenciaVisual).toBe("ed-1");
  });

  it("referência não aprovada não vale", () => {
    expect(extrasDoDesign({ composicao: "estatistico", referencia: "es-1" }, referencias)).toBeUndefined();
  });

  it("sem design ou sem lista, o pedido segue sem extras", () => {
    expect(extrasDoDesign(null, referencias)).toBeUndefined();
    expect(extrasDoDesign({ composicao: "editorial", referencia: null }, undefined)).toBeUndefined();
  });
});

describe("mesmoDesign", () => {
  it("compara composição e referência", () => {
    const a = { composicao: "editorial", referencia: "ed-1" } as const;
    expect(mesmoDesign(a, { ...a })).toBe(true);
    expect(mesmoDesign(a, { ...a, referencia: null })).toBe(false);
    expect(mesmoDesign(a, { ...a, composicao: "narrativo" })).toBe(false);
    expect(mesmoDesign(null, null)).toBe(true);
    expect(mesmoDesign(a, null)).toBe(false);
  });
});
