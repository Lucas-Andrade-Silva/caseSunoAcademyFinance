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
      "qualidade",
      "recomendacao",
    ]);
  });

  it("marca o Limiar na escala da própria métrica", () => {
    const [flesch, aderencia] = barrasDoLaudo(laudo(medidas));
    expect(flesch.marcas).toEqual([50]);
    expect(aderencia.marcas).toEqual([100]);
  });

  it("Compliance é cheio sem Recomendação e curto quando há", () => {
    const compliance = (barras: ReturnType<typeof barrasDoLaudo>) =>
      barras.find((b) => b.metrica === "recomendacao")!;
    const limpa = compliance(barrasDoLaudo(laudo([medidas[0]])));
    expect(limpa.largura).toBe(100);
    expect(limpa.valor).toBe("sem Recomendação");
    const suja = compliance(
      barrasDoLaudo(laudo([{ ...medidas[0], atingiu: false } as Laudo["medidas"][number]])),
    );
    expect(suja.largura).toBeLessThan(100);
    expect(suja.atingiu).toBe(false);
  });

  it("sem Laudo não há barras", () => {
    expect(barrasDoLaudo(null)).toEqual([]);
  });

  it("sem o Jev, a Qualidade aparece em cinza como não avaliada", () => {
    const qualidade = barrasDoLaudo(laudo(medidas)).find((b) => b.metrica === "qualidade")!;
    expect(qualidade.valor).toBe("não avaliada");
    expect(qualidade.atingiu).toBeNull();
    expect(qualidade.largura).toBe(0);
    expect(qualidade.marcas).toEqual([]);
  });
});

describe("celulaBloqueada", () => {
  it("só a Recomendação bloqueia", () => {
    expect(celulaBloqueada({ motivos: ["recomendacao"] })).toBe(true);
    expect(celulaBloqueada({ motivos: ["flesch_br"] })).toBe(false);
    expect(celulaBloqueada(null)).toBe(false);
  });
});

describe("Qualidade do Jev", () => {
  const medidas = [
    { metrica: "recomendacao", estado: "medida", valor: 0, faixa: { minimo: null, maximo: 1 }, atingiu: true },
    { metrica: "qualidade", estado: "medida", valor: 0.33, faixa: { minimo: 0.6, maximo: null }, atingiu: false },
    { metrica: "integridade", estado: "medida", valor: 1, faixa: { minimo: 1, maximo: null }, atingiu: true },
  ] as Laudo["medidas"];

  it("aparece depois da Integridade e antes do Compliance, em porcentagem, com o Limiar marcado", () => {
    const barras = barrasDoLaudo(laudo(medidas));
    expect(barras.map((b) => b.metrica)).toEqual(["integridade", "qualidade", "recomendacao"]);
    const qualidade = barras[1];
    expect(qualidade.rotulo).toBe("Qualidade");
    expect(qualidade.largura).toBe(33);
    expect(qualidade.marcas).toEqual([60]);
    expect(qualidade.atingiu).toBe(false);
  });
});
