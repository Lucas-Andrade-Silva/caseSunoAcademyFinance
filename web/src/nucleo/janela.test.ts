import { describe, expect, it } from "vitest";
import { dentroDaJanela, diasDesde, recentes } from "./janela";

const HOJE = new Date(2026, 9, 12, 15, 30); // 12/10/2026, à tarde

describe("diasDesde", () => {
  it("conta dias corridos, sem olhar a hora", () => {
    expect(diasDesde("2026-10-12", HOJE)).toBe(0);
    expect(diasDesde("2026-10-11", HOJE)).toBe(1);
    expect(diasDesde("2026-09-12", HOJE)).toBe(30);
  });

  it("data ilegível volta null", () => {
    expect(diasDesde("ontem", HOJE)).toBeNull();
  });
});

describe("dentroDaJanela", () => {
  it("30 dias atrás ainda vale; 31 já não", () => {
    expect(dentroDaJanela("2026-09-12", HOJE)).toBe(true);
    expect(dentroDaJanela("2026-09-11", HOJE)).toBe(false);
  });

  it("a Ata do Copom de 05/08 (68 dias) fica de fora e a de 16/09 (26 dias) entra", () => {
    expect(dentroDaJanela("2026-08-05", HOJE)).toBe(false);
    expect(dentroDaJanela("2026-09-16", HOJE)).toBe(true);
  });

  it("data de hoje e do futuro valem", () => {
    expect(dentroDaJanela("2026-10-12", HOJE)).toBe(true);
    expect(dentroDaJanela("2026-10-20", HOJE)).toBe(true);
  });

  it("data ilegível fica de fora", () => {
    expect(dentroDaJanela("", HOJE)).toBe(false);
  });
});

describe("recentes", () => {
  it("filtra e põe a mais nova primeiro", () => {
    const atas = [
      { id: "velha", data_referencia: "2026-08-05" },
      { id: "meio", data_referencia: "2026-10-01" },
      { id: "nova", data_referencia: "2026-10-10" },
    ];
    expect(recentes(atas, HOJE).map((a) => a.id)).toEqual(["nova", "meio"]);
  });
});
