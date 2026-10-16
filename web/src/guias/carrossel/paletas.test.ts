import { describe, expect, it } from "vitest";
import { PALETAS, PALETA_PADRAO, contraste, corSobre, ehPaleta, paletaParaServidor, paletaPorId } from "./paletas";

describe("contraste", () => {
  it("preto sobre branco é 21:1 e a mesma cor é 1:1", () => {
    expect(contraste("#000000", "#FFFFFF")).toBeCloseTo(21, 5);
    expect(contraste("#336699", "#336699")).toBeCloseTo(1, 5);
  });

  it("não depende da ordem", () => {
    expect(contraste("#FF1A1A", "#140809")).toBeCloseTo(contraste("#140809", "#FF1A1A"), 10);
  });
});

describe("paletas prontas", () => {
  it("são entre 6 e 8, com ids e nomes únicos", () => {
    expect(PALETAS.length).toBeGreaterThanOrEqual(6);
    expect(PALETAS.length).toBeLessThanOrEqual(8);
    expect(new Set(PALETAS.map((p) => p.id)).size).toBe(PALETAS.length);
    expect(new Set(PALETAS.map((p) => p.nome)).size).toBe(PALETAS.length);
  });

  it.each(PALETAS.map((p) => [p.nome, p] as const))("%s: texto sobre fundo passa de 4,5:1", (_nome, paleta) => {
    expect(contraste(paleta.texto, paleta.fundo)).toBeGreaterThanOrEqual(4.5);
  });

  it.each(PALETAS.map((p) => [p.nome, p] as const))(
    "%s: o destaque se lê sobre o fundo como texto grande (3:1)",
    (_nome, paleta) => {
      expect(contraste(paleta.destaque, paleta.fundo)).toBeGreaterThanOrEqual(3);
    },
  );

  it.each(PALETAS.map((p) => [p.nome, p] as const))(
    "%s: o realce do título (texto grande sobre o destaque) passa de 3:1",
    (_nome, paleta) => {
      const cor = corSobre(paleta.destaque, paleta.texto, paleta.fundo);
      expect(contraste(cor, paleta.destaque)).toBeGreaterThanOrEqual(3);
    },
  );

  it("a primeira é a do render do servidor", () => {
    expect(PALETA_PADRAO.fundo).toBe("#140809");
    expect(PALETA_PADRAO.destaque).toBe("#FF1A1A");
  });
});

describe("paletaPorId e ehPaleta", () => {
  it("id desconhecido volta à padrão", () => {
    expect(paletaPorId("nao-existe")).toBe(PALETA_PADRAO);
    expect(paletaPorId(null)).toBe(PALETA_PADRAO);
    expect(paletaPorId("papel").nome).toBe("Papel");
  });

  it("confere as quatro cores", () => {
    expect(ehPaleta(PALETA_PADRAO)).toBe(true);
    expect(ehPaleta({ ...PALETA_PADRAO, apoio: "vermelho" })).toBe(false);
    expect(ehPaleta({ id: "x" })).toBe(false);
  });
});

describe("paleta para o servidor", () => {
  it("a Suno mantém as cores do post: nada vai ao servidor", () => {
    expect(paletaParaServidor(PALETA_PADRAO)).toBeUndefined();
  });

  it("as outras vão como fundo,texto,destaque,apoio", () => {
    expect(paletaParaServidor(paletaPorId("floresta"))).toBe("#0C1A14,#F1FBF5,#3DDC84,#1B6B45");
  });
});
