import { describe, expect, it } from "vitest";
import type { Laudo } from "../dados/cliente";
import { barrasDoLaudo, celulaBloqueada, larguraDaBarra } from "./laudo";

function laudo(medidas: Laudo["medidas"]): Laudo {
  return {
    audiencia: "iniciante",
    formato: "carrossel",
    medidas,
    destino: "aprovado",
  } as Laudo;
}

describe("larguraDaBarra", () => {
  it("Flesch-BR já vem em 0 a 100; as outras vêm em 0 a 1", () => {
    expect(larguraDaBarra({ metrica: "flesch_br", valor: 55 })).toBe(55);
    expect(larguraDaBarra({ metrica: "aderencia", valor: 0.5 })).toBe(50);
  });

  it("limita entre 0 e 100 (o Flesch-BR do Avançado pode ser negativo)", () => {
    expect(larguraDaBarra({ metrica: "flesch_br", valor: -2.7 })).toBe(0);
    expect(larguraDaBarra({ metrica: "flesch_br", valor: 130 })).toBe(100);
  });

  it("sem valor, a barra é vazia", () => {
    expect(larguraDaBarra({ metrica: "densidade", valor: null })).toBe(0);
  });
});

describe("barrasDoLaudo", () => {
  const medidas = [
    { metrica: "recomendacao", estado: "medida", valor: 0, faixa: { minimo: null, maximo: 1 }, atingiu: true },
    { metrica: "aderencia", estado: "medida", valor: 1, faixa: { minimo: 1, maximo: null }, atingiu: true },
    { metrica: "flesch_br", estado: "medida", valor: 55.5, faixa: { minimo: 50, maximo: null }, atingiu: true },
  ] as Laudo["medidas"];

  it("ordena: Flesch-BR primeiro, Compliance por último", () => {
    expect(barrasDoLaudo(laudo(medidas)).map((b) => b.metrica)).toEqual([
      "flesch_br",
      "aderencia",
      "recomendacao",
    ]);
  });

  it("marca o Limiar na escala da própria métrica", () => {
    const [flesch, aderencia] = barrasDoLaudo(laudo(medidas));
    expect(flesch.marcas).toEqual([50]);
    expect(aderencia.marcas).toEqual([100]);
  });

  it("Compliance é cheio sem Recomendação e curto quando há", () => {
    const limpa = barrasDoLaudo(laudo([medidas[0]]))[0];
    expect(limpa.largura).toBe(100);
    expect(limpa.valor).toBe("sem Recomendação");
    const suja = barrasDoLaudo(
      laudo([{ ...medidas[0], atingiu: false } as Laudo["medidas"][number]]),
    )[0];
    expect(suja.largura).toBeLessThan(100);
    expect(suja.atingiu).toBe(false);
  });

  it("sem Laudo não há barras", () => {
    expect(barrasDoLaudo(null)).toEqual([]);
  });
});

describe("celulaBloqueada", () => {
  it("só a Recomendação bloqueia", () => {
    expect(celulaBloqueada({ motivos: ["recomendacao"] })).toBe(true);
    expect(celulaBloqueada({ motivos: ["flesch_br"] })).toBe(false);
    expect(celulaBloqueada(null)).toBe(false);
  });
});
