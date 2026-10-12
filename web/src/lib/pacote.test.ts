import { describe, expect, it } from "vitest";
import {
  itensDaDistribuicao,
  motivoSemPacote,
  rotuloDaComposicao,
} from "./pacote";

describe("direção de arte", () => {
  it("traduz os nomes e ordena a distribuição", () => {
    expect(rotuloDaComposicao("infografico")).toBe("Infográfico");
    expect(
      itensDaDistribuicao({ narrativo: 2, editorial: 1, minimalista: 0 }),
    ).toEqual([
      { composicao: "editorial", rotulo: "Editorial", total: 1 },
      { composicao: "narrativo", rotulo: "Narrativo", total: 2 },
    ]);
  });
});

describe("motivoSemPacote", () => {
  it("Célula aprovada numa Matriz aprovada pode montar", () => {
    expect(
      motivoSemPacote({
        destinoDaCelula: "aprovado",
      }),
    ).toBeNull();
  });

  it("Célula aprovada pode montar independentemente das demais", () => {
    expect(
      motivoSemPacote({ destinoDaCelula: "aprovado" }),
    ).toBeNull();
  });

  it("Célula que o Laudo não aprovou não gera Pacote", () => {
    for (const destino of [
      "reprovado_revisao_humana",
      "reprovado_corrigivel",
    ]) {
      expect(
        motivoSemPacote({
          destinoDaCelula: destino,
        }),
      ).toContain("aprovada pelo Laudo");
    }
  });

  it("Célula reprovada no Laudo e aprovada por revisor pode montar", () => {
    expect(
      motivoSemPacote({
        destinoDaCelula: "reprovado_revisao_humana",
        aprovadaPorRevisor: true,
      }),
    ).toBeNull();
  });
});
