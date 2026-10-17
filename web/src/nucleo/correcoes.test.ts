import { describe, expect, it } from "vitest";
import type { Laudo } from "../dados/cliente";
import { indicesComCorrecao, localizarCorrecoes } from "./correcoes";

function laudoReprovado(parcial: Partial<Laudo>): Laudo {
  return {
    audiencia: "iniciante",
    formato: "carrossel",
    medidas: [],
    destino: "reprovado_revisao_humana",
    motivos: ["aderencia"],
    correcoes: [],
    ...parcial,
  };
}

describe("localizarCorrecoes", () => {
  it("encontra em qual quadro está a frase citada pelo Laudo", () => {
    const laudo = laudoReprovado({
      medidas: [{ metrica: "densidade", estado: "medida", valor: 0.1, atingiu: false, observacoes: [] }],
      correcoes: [{
        metrica: "densidade",
        valor_medido: 0.1,
        faixa: { minimo: 0.2, maximo: null },
        instrucao: "Onde cada um está: taxa — slide 2: «A taxa básica orienta o crédito.»",
      }],
    });
    const pontos = localizarCorrecoes(laudo, [
      { indice: 0, local: "Quadro 1 · corpo", texto: "Uma introdução." },
      { indice: 1, local: "Quadro 2 · corpo", texto: "A taxa básica orienta o crédito." },
    ]);
    expect(pontos[0].ocorrencias).toEqual([
      { indice: 1, local: "Quadro 2 · corpo", trecho: "A taxa básica orienta o crédito." },
    ]);
    expect([...indicesComCorrecao(pontos)]).toEqual([1]);
  });

  it("localiza o número sem Âncora a partir da observação", () => {
    const laudo = laudoReprovado({
      medidas: [{
        metrica: "aderencia", estado: "medida", valor: 0.5, atingiu: false,
        observacoes: ["Número sem Âncora que o sustente: 25 de agosto de 2026"],
      }],
      correcoes: [{
        metrica: "aderencia", valor_medido: 0.5, faixa: { minimo: 1, maximo: null },
        instrucao: "Números sem Âncora: 25 de agosto de 2026. Use só os valores das Âncoras.",
      }],
    });
    const pontos = localizarCorrecoes(laudo, [
      { indice: 2, local: "Cena 3 · fala", texto: "A decisão ocorreu em 25 de agosto de 2026." },
    ]);
    expect(pontos[0].ocorrencias[0].local).toBe("Cena 3 · fala");
  });

  it("ignora a citação da Ata quando ela não aparece no conteúdo", () => {
    const laudo = laudoReprovado({
      medidas: [{ metrica: "fidelidade", estado: "medida", valor: 0, atingiu: false, observacoes: [] }],
      correcoes: [{
        metrica: "fidelidade", valor_medido: 0, faixa: { minimo: 1, maximo: null },
        instrucao: "A afirmação «A taxa caiu.» contradiz a Ata: «A taxa foi mantida.»",
      }],
    });
    const pontos = localizarCorrecoes(laudo, [
      { indice: 0, local: "Texto analítico", texto: "A taxa caiu. Isso afeta o crédito." },
    ]);
    expect(pontos[0].ocorrencias).toEqual([
      { indice: 0, local: "Texto analítico", trecho: "A taxa caiu." },
    ]);
  });

  it("trata legibilidade como um problema do conteúdo inteiro", () => {
    const laudo = laudoReprovado({
      medidas: [{ metrica: "flesch_br", estado: "medida", valor: 20, atingiu: false, observacoes: ["Texto difícil."] }],
      correcoes: [{
        metrica: "flesch_br", valor_medido: 20, faixa: { minimo: 50, maximo: null }, instrucao: "Encurte as frases.",
      }],
    });
    expect(localizarCorrecoes(laudo, [{ indice: 0, local: "Texto", texto: "Uma frase." }])[0].ocorrencias).toEqual([]);
  });

  it("mostra falha de extração mesmo sem uma Correção", () => {
    const laudo = laudoReprovado({
      motivos: ["falha_de_extracao"],
      medidas: [{
        metrica: "integridade", estado: "medida", valor: 0.5, atingiu: false,
        observacoes: ["Âncora essencial ausente: decisao_numero_principal"],
      }],
    });
    expect(localizarCorrecoes(laudo, [])[0]).toMatchObject({
      metrica: "integridade",
      instrucao: "Âncora essencial ausente: decisao_numero_principal",
    });
  });
});
