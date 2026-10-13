import { describe, expect, it } from "vitest";
import type { Slide } from "../../dados/cliente";
import { direcaoDaImagem } from "./direcaoDaImagem";
import type { GraficoDoQuadro } from "./modelo";

function quadro(parcial: Partial<Slide> = {}): Slide {
  return { tipo: "ponto", titulo: "Quanto ficou", corpo: "A Selic foi para 14,00% a.a.", ...parcial };
}

const selic: GraficoDoQuadro = {
  jeito: "numero",
  ancora: { chave: "selic_decidida", rotulo: "Selic decidida", citacao: "14,00% a.a.", valor: 14 },
};

describe("direcaoDaImagem", () => {
  it("o estatístico põe o número da Âncora no centro, na cor de destaque", () => {
    const frase = direcaoDaImagem(quadro({ dado: "selic_decidida" }), "estatistico", 1, 5, selic);
    expect(frase).toContain("número grande na cor de destaque");
    expect(frase).toContain("14,00% a.a.");
    expect(frase).toContain("Selic decidida");
  });

  it("o infográfico com as duas Selic descreve as barras Antes e Depois", () => {
    const barras: GraficoDoQuadro = {
      jeito: "barras",
      antes: { chave: "selic_anterior", rotulo: "Selic anterior", citacao: "14,25% a.a.", valor: 14.25 },
      depois: { chave: "selic_decidida", rotulo: "Selic decidida", citacao: "14,00% a.a.", valor: 14 },
    };
    const frase = direcaoDaImagem(quadro({ dado: "selic_decidida" }), "infografico", 1, 5, barras);
    expect(frase).toContain("Antes e Depois");
    expect(frase).toContain("14,25% a.a.");
    expect(frase).toContain("14,00% a.a.");
  });

  it("o comparativo fala em dois painéis, A contra B", () => {
    expect(direcaoDaImagem(quadro(), "comparativo", 2, 5)).toContain("ponto A contra ponto B");
  });

  it("o narrativo cita a etapa e o total", () => {
    expect(direcaoDaImagem(quadro(), "narrativo", 2, 6)).toContain("Etapa 3 de 6");
  });

  it("o minimalista pede respiro, e a capa e o fechamento mudam a frase", () => {
    const ponto = direcaoDaImagem(quadro(), "minimalista", 1, 5);
    const capa = direcaoDaImagem(quadro({ tipo: "hook" }), "minimalista", 0, 5);
    const fecho = direcaoDaImagem(quadro({ tipo: "cta" }), "minimalista", 4, 5);
    expect(ponto).toContain("respiro");
    expect(new Set([ponto, capa, fecho]).size).toBe(3);
  });

  it("o editorial muda entre capa, ponto e fechamento", () => {
    const frases = (["hook", "ponto", "cta"] as const).map((tipo) =>
      direcaoDaImagem(quadro({ tipo }), "editorial", 0, 5),
    );
    expect(new Set(frases).size).toBe(3);
  });

  it("acrescenta o realce quando o destaque está no título", () => {
    const frase = direcaoDaImagem(quadro({ titulo: "A decisão da reunião", destaque: "decisão" }), "editorial", 1, 5);
    expect(frase).toContain("Realce em “decisão” no título.");
  });

  it("ignora o destaque que não aparece no título", () => {
    const frase = direcaoDaImagem(quadro({ destaque: "inexistente" }), "editorial", 1, 5);
    expect(frase).not.toContain("Realce");
  });

  it("sem gráfico, as composições de número não inventam um", () => {
    for (const composicao of ["infografico", "comparativo", "estatistico"] as const) {
      expect(direcaoDaImagem(quadro(), composicao, 1, 5)).not.toMatch(/\d/);
    }
  });

  it("é determinística: a mesma entrada dá a mesma frase", () => {
    const a = direcaoDaImagem(quadro({ dado: "selic_decidida" }), "estatistico", 1, 5, selic);
    const b = direcaoDaImagem(quadro({ dado: "selic_decidida" }), "estatistico", 1, 5, selic);
    expect(a).toBe(b);
  });
});
