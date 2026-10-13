import { describe, expect, it } from "vitest";
import { diaEMes, inicioDoAtalho, noPeriodo, porDia, porOrigem } from "./periodo";

const LISTA = [
  { origem: "b3_oficios", data: "2026-10-09" },
  { origem: "bcb_resolucoes", data: "2026-10-08" },
  { origem: "b3_oficios", data: "2026-10-08" },
  { origem: "cvm_demonstracoes", data: "2026-09-20" },
];

describe("noPeriodo", () => {
  it("inclui as duas pontas e deixa de fora o resto", () => {
    expect(noPeriodo(LISTA, "2026-10-08", "2026-10-09")).toHaveLength(3);
    expect(noPeriodo(LISTA, "2026-10-09", "2026-10-09")).toHaveLength(1);
    expect(noPeriodo(LISTA, "2026-10-10", "2026-10-12")).toHaveLength(0);
  });
});

describe("porOrigem", () => {
  it("conta por origem na ordem em que aparecem", () => {
    expect(porOrigem(LISTA)).toEqual([
      { origem: "b3_oficios", total: 2 },
      { origem: "bcb_resolucoes", total: 1 },
      { origem: "cvm_demonstracoes", total: 1 },
    ]);
  });
});

describe("porDia", () => {
  it("devolve um item por dia, com zero nos vazios, cruzando o mês", () => {
    const dias = porDia(LISTA, "2026-09-29", "2026-10-02");
    expect(dias.map((d) => d.data)).toEqual(["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]);
    expect(dias.every((d) => d.total === 0)).toBe(true);
  });

  it("soma as notícias do mesmo dia", () => {
    expect(porDia(LISTA, "2026-10-08", "2026-10-09")).toEqual([
      { data: "2026-10-08", total: 2 },
      { data: "2026-10-09", total: 1 },
    ]);
  });
});

describe("inicioDoAtalho", () => {
  it("7 dias contam o último dia: de 06/10 a 12/10", () => {
    expect(inicioDoAtalho(7, "2026-09-12", "2026-10-12")).toBe("2026-10-06");
  });

  it("não passa do começo da janela", () => {
    expect(inicioDoAtalho(60, "2026-09-12", "2026-10-12")).toBe("2026-09-12");
  });
});

describe("diaEMes", () => {
  it("dia e mês", () => {
    expect(diaEMes("2026-10-08")).toBe("08/10");
  });
});
