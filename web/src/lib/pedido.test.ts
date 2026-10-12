import { describe, expect, it } from "vitest";
import {
  alternarCelula,
  alternarColuna,
  alternarLinha,
  colunaCompleta,
  estaSelecionada,
  linhaCompleta,
  matrizInteira,
  resumirPedido,
  type Posicao,
} from "./pedido";

const p = (audiencia: string, formato: string): Posicao => ({ audiencia, formato });

describe("matrizInteira", () => {
  it("são as nove, Audiências nas linhas e Formatos nas colunas", () => {
    const todas = matrizInteira();
    expect(todas).toHaveLength(9);
    expect(todas[0]).toEqual(p("iniciante", "texto_analitico"));
    expect(todas[1]).toEqual(p("iniciante", "carrossel"));
    expect(todas[3]).toEqual(p("intermediario", "texto_analitico"));
    expect(todas[8]).toEqual(p("avancado", "roteiro"));
  });
});

describe("alternarCelula", () => {
  it("marca uma Célula que não estava marcada", () => {
    const depois = alternarCelula([], p("iniciante", "carrossel"));
    expect(depois).toEqual([p("iniciante", "carrossel")]);
  });

  it("desmarca uma que estava marcada", () => {
    const antes = [p("iniciante", "carrossel"), p("avancado", "roteiro")];
    expect(alternarCelula(antes, p("iniciante", "carrossel"))).toEqual([p("avancado", "roteiro")]);
  });

  it("devolve sempre na ordem da Matriz, qualquer que seja a ordem dos cliques", () => {
    let selecao: Posicao[] = [];
    selecao = alternarCelula(selecao, p("avancado", "roteiro"));
    selecao = alternarCelula(selecao, p("iniciante", "texto_analitico"));
    selecao = alternarCelula(selecao, p("intermediario", "carrossel"));
    expect(selecao).toEqual([
      p("iniciante", "texto_analitico"),
      p("intermediario", "carrossel"),
      p("avancado", "roteiro"),
    ]);
  });

  it("não muda a lista original", () => {
    const antes = [p("iniciante", "carrossel")];
    alternarCelula(antes, p("avancado", "roteiro"));
    expect(antes).toEqual([p("iniciante", "carrossel")]);
  });
});

describe("alternarLinha", () => {
  it("linha incompleta é completada", () => {
    const antes = [p("iniciante", "carrossel")];
    const depois = alternarLinha(antes, "iniciante");
    expect(depois).toEqual([
      p("iniciante", "texto_analitico"),
      p("iniciante", "carrossel"),
      p("iniciante", "roteiro"),
    ]);
  });

  it("linha completa é limpa e as outras ficam", () => {
    const antes = [...matrizInteira()];
    const depois = alternarLinha(antes, "intermediario");
    expect(depois).toHaveLength(6);
    expect(depois.some((c) => c.audiencia === "intermediario")).toBe(false);
  });

  it("linha vazia vira completa", () => {
    expect(alternarLinha([], "avancado")).toHaveLength(3);
  });
});

describe("alternarColuna", () => {
  it("coluna incompleta é completada", () => {
    const depois = alternarColuna([p("avancado", "roteiro")], "roteiro");
    expect(depois).toEqual([
      p("iniciante", "roteiro"),
      p("intermediario", "roteiro"),
      p("avancado", "roteiro"),
    ]);
  });

  it("coluna completa é limpa", () => {
    const depois = alternarColuna(matrizInteira(), "carrossel");
    expect(depois).toHaveLength(6);
    expect(depois.some((c) => c.formato === "carrossel")).toBe(false);
  });
});

describe("linhaCompleta, colunaCompleta e estaSelecionada", () => {
  it("só são completas com as três Células", () => {
    const selecao = [p("iniciante", "texto_analitico"), p("iniciante", "carrossel")];
    expect(linhaCompleta(selecao, "iniciante")).toBe(false);
    expect(colunaCompleta(selecao, "carrossel")).toBe(false);
    expect(linhaCompleta(matrizInteira(), "iniciante")).toBe(true);
    expect(colunaCompleta(matrizInteira(), "roteiro")).toBe(true);
  });

  it("estaSelecionada compara Audiência e Formato", () => {
    const selecao = [p("iniciante", "carrossel")];
    expect(estaSelecionada(selecao, p("iniciante", "carrossel"))).toBe(true);
    expect(estaSelecionada(selecao, p("iniciante", "roteiro"))).toBe(false);
  });
});

describe("resumirPedido", () => {
  it("diz quantas Células, no singular e no plural", () => {
    expect(resumirPedido([])).toBe("nenhuma Célula");
    expect(resumirPedido([p("iniciante", "carrossel")])).toBe("1 Célula");
    expect(resumirPedido(matrizInteira())).toBe("9 Células");
  });
});
