import { describe, expect, it } from "vitest";
import { alturaDaBarra, citarAncora, escolherGrafico, partesDaComparacao } from "./graficos";
import type { AncoraDeQuadro } from "./modelo";

describe("citarAncora (a mesma forma do servidor)", () => {
  it("percentual ao ano leva o a.a. colado ao número", () => {
    expect(citarAncora({ valor_literal: "14,00", unidade: "% a.a.", qualificador: null })).toBe("14,00% a.a.");
  });

  it("percentual simples, com e sem qualificador", () => {
    expect(citarAncora({ valor_literal: "5,1", unidade: "%", qualificador: null })).toBe("5,1%");
    expect(citarAncora({ valor_literal: "110", unidade: "%", qualificador: "do CDI" })).toBe("110% do CDI");
    expect(citarAncora({ valor_literal: "2", unidade: "%", qualificador: "CDI+" })).toBe("CDI+2%");
  });

  it("data, votos e número voltam como a Ata escreve", () => {
    expect(citarAncora({ valor_literal: "7 a 0", unidade: "votos", qualificador: null })).toBe("7 a 0");
    expect(citarAncora({ valor_literal: "4 e 5 de agosto de 2026", unidade: "data", qualificador: null })).toBe(
      "4 e 5 de agosto de 2026",
    );
    expect(citarAncora({ valor_literal: "280", unidade: "numero", qualificador: null })).toBe("280");
  });

  it("reais, pontos-base e pontos percentuais", () => {
    expect(citarAncora({ valor_literal: "1.000", unidade: "R$", qualificador: null })).toBe("R$ 1.000");
    expect(citarAncora({ valor_literal: "25", unidade: "pb", qualificador: null })).toBe("25 pb");
    expect(citarAncora({ valor_literal: "0,25", unidade: "p.p.", qualificador: null })).toBe("0,25 p.p.");
  });
});

const antes: AncoraDeQuadro = { chave: "selic_anterior", rotulo: "Selic anterior", citacao: "14,25% a.a.", valor: 14.25 };
const depois: AncoraDeQuadro = { chave: "selic_decidida", rotulo: "Selic decidida", citacao: "14,00% a.a.", valor: 14 };
const ipca: AncoraDeQuadro = { chave: "ipca_projecao_ano_corrente", rotulo: "IPCA", citacao: "5,1%", valor: 5.1 };

describe("escolherGrafico", () => {
  it("as duas Selic viram barras Antes e Depois", () => {
    const grafico = escolherGrafico("selic_decidida", [antes, depois], "infografico");
    expect(grafico).toEqual({ jeito: "barras", antes, depois });
  });

  it("falta uma das duas Selic: vira o número da Âncora", () => {
    expect(escolherGrafico("selic_decidida", [depois], "comparativo")).toEqual({ jeito: "numero", ancora: depois });
  });

  it("o estatístico mostra sempre o número", () => {
    expect(escolherGrafico("selic_decidida", [antes, depois], "estatistico")).toEqual({ jeito: "numero", ancora: depois });
  });

  it("outra Âncora vira o número grande", () => {
    expect(escolherGrafico("ipca_projecao_ano_corrente", [antes, depois, ipca], "infografico")).toEqual({
      jeito: "numero",
      ancora: ipca,
    });
  });

  it("sem a Âncora, ou sem dado, não há gráfico", () => {
    expect(escolherGrafico("ipca_projecao_horizonte", [antes, depois], "infografico")).toBeNull();
    expect(escolherGrafico(null, [antes, depois], "infografico")).toBeNull();
    expect(escolherGrafico(undefined, [antes, depois], "estatistico")).toBeNull();
  });

  it("composição sem campo de gráfico não leva gráfico", () => {
    expect(escolherGrafico("selic_decidida", [antes, depois], "editorial")).toBeNull();
    expect(escolherGrafico("selic_decidida", [antes, depois], "narrativo")).toBeNull();
  });
});

describe("alturaDaBarra", () => {
  it("é proporcional ao maior valor", () => {
    expect(alturaDaBarra(14, 14, 260)).toBe(260);
    expect(alturaDaBarra(7, 14, 260)).toBe(130);
  });

  it("sem valor ou sem teto, a barra é vazia", () => {
    expect(alturaDaBarra(null, 14, 260)).toBe(0);
    expect(alturaDaBarra(14, 0, 260)).toBe(0);
  });
});

describe("partesDaComparacao", () => {
  it("separa em 'conquanto' e 'embora', mantendo o conector", () => {
    expect(partesDaComparacao("A inflação cedeu, conquanto siga alta")).toEqual([
      "A inflação cedeu",
      "Conquanto siga alta",
    ]);
    expect(partesDaComparacao("O juro caiu, embora o crédito siga caro")).toEqual([
      "O juro caiu",
      "Embora o crédito siga caro",
    ]);
  });

  it("separa em ponto e vírgula, 'enquanto', 'mas' e ponto final", () => {
    expect(partesDaComparacao("Subiu; caiu")).toEqual(["Subiu", "caiu"]);
    expect(partesDaComparacao("Um sobe enquanto outro cai")).toEqual(["Um sobe", "outro cai"]);
    expect(partesDaComparacao("Subiu mas voltou")).toEqual(["Subiu", "voltou"]);
    expect(partesDaComparacao("Primeira frase. Segunda frase.")).toEqual(["Primeira frase", "Segunda frase."]);
  });

  it("sem separador, divide as palavras ao meio e não inventa texto", () => {
    expect(partesDaComparacao("um dois três quatro")).toEqual(["um dois", "três quatro"]);
    expect(partesDaComparacao("sozinha")).toEqual(["sozinha", "sozinha"]);
  });
});
