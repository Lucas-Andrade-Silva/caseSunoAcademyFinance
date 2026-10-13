import { describe, expect, it } from "vitest";
import { nomeDoQuadro, nomeDoZip } from "./nomesDeArquivo";

describe("nomeDoZip", () => {
  it("leva a audiência", () => {
    expect(nomeDoZip("iniciante")).toBe("carrossel-iniciante.zip");
    expect(nomeDoZip("avancado")).toBe("carrossel-avancado.zip");
  });
});

describe("nomeDoQuadro", () => {
  it("numera a partir de 01, com dois dígitos", () => {
    expect(nomeDoQuadro(0)).toBe("slide-01.png");
    expect(nomeDoQuadro(8)).toBe("slide-09.png");
    expect(nomeDoQuadro(9)).toBe("slide-10.png");
  });
});
