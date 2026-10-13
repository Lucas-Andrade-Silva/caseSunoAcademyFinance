import { describe, expect, it } from "vitest";
import type { Slide } from "../../dados/cliente";
import { IDS_DE_ICONES } from "./idsDeIcones";
import { distribuirIcones, montarQuadros, montarQuadrosDeExemplo } from "./montagem";
import type { AncoraDeQuadro, IdDoIcone } from "./modelo";

const TODOS: IdDoIcone[] = IDS_DE_ICONES.map((icone) => icone.id);

const ancoras: AncoraDeQuadro[] = [
  { chave: "selic_anterior", rotulo: "Selic anterior", citacao: "14,25% a.a.", valor: 14.25 },
  { chave: "selic_decidida", rotulo: "Selic decidida", citacao: "14,00% a.a.", valor: 14 },
  { chave: "placar_votacao", rotulo: "Placar", citacao: "7 a 0", valor: 7 },
];

const slides: Slide[] = [
  { tipo: "hook", titulo: "Capa", corpo: "Texto." },
  { tipo: "ponto", titulo: "Selic", corpo: "Texto.", dado: "selic_decidida" },
  { tipo: "ponto", titulo: "Placar", corpo: "Texto.", dado: "placar_votacao" },
  { tipo: "ponto", titulo: "Sem número", corpo: "Texto.", dado: "ipca_projecao_horizonte" },
  { tipo: "cta", titulo: "Fim", corpo: "Texto." },
];

describe("distribuirIcones", () => {
  it("não perde nenhum ícone e não repete", () => {
    const quadros = distribuirIcones(TODOS, slides.map((s) => s.dado));
    const todos = quadros.flat();
    expect(todos.sort()).toEqual([...TODOS].sort());
  });

  it("sem ícones ou sem quadros, nada se perde nem quebra", () => {
    expect(distribuirIcones([], [null, null])).toEqual([[], []]);
    expect(distribuirIcones(["banco"], [])).toEqual([]);
  });

  it("um ícone escolhido duas vezes aparece uma só", () => {
    expect(distribuirIcones(["banco", "banco"], [null, null]).flat()).toEqual(["banco"]);
  });

  it("o ícone vai ao quadro do dado que combina com ele", () => {
    const quadros = distribuirIcones(["juros", "balanca"], slides.map((s) => s.dado));
    expect(quadros[1]).toContain("juros");
    expect(quadros[2]).toContain("balanca");
  });

  it("os que não combinam com nenhum se espalham por igual", () => {
    const quadros = distribuirIcones(["banco", "bolso", "alerta", "lupa", "relogio"], [null, null, null]);
    const tamanhos = quadros.map((q) => q.length);
    expect(Math.max(...tamanhos) - Math.min(...tamanhos)).toBeLessThanOrEqual(1);
  });

  it("com mais ícones do que quadros, cada ícone ainda aparece", () => {
    const quadros = distribuirIcones(TODOS, [null, null]);
    expect(quadros.flat()).toHaveLength(TODOS.length);
  });
});

describe("montarQuadros", () => {
  it("numera os quadros e leva o total", () => {
    const quadros = montarQuadros({ slides, preferida: "editorial", ancoras, icones: [] });
    expect(quadros.map((q) => q.indice)).toEqual([0, 1, 2, 3, 4]);
    expect(quadros.every((q) => q.total === 5)).toBe(true);
  });

  it("escolhe a composição por quadro: a preferida onde cabe, o editorial onde não", () => {
    const quadros = montarQuadros({ slides, preferida: "estatistico", ancoras, icones: [] });
    expect(quadros.map((q) => q.composicao)).toEqual([
      "editorial", // gancho não aceita o estatístico
      "estatistico",
      "estatistico",
      "editorial", // a Âncora não veio
      "minimalista", // CTA sem número cai no minimalista
    ]);
  });

  it("monta o gráfico só quando a Âncora existe", () => {
    const quadros = montarQuadros({ slides, preferida: "infografico", ancoras, icones: [] });
    expect(quadros[1].grafico?.jeito).toBe("barras");
    expect(quadros[2].grafico?.jeito).toBe("numero");
    expect(quadros[3].grafico).toBeNull();
    expect(quadros[0].grafico).toBeNull();
  });

  it("o estatístico mostra o número até para a Selic", () => {
    const quadros = montarQuadros({ slides, preferida: "estatistico", ancoras, icones: [] });
    expect(quadros[1].grafico?.jeito).toBe("numero");
  });

  it("composição sem campo de gráfico não leva gráfico", () => {
    const quadros = montarQuadros({ slides, preferida: "narrativo", ancoras, icones: [] });
    expect(quadros.every((q) => q.grafico === null)).toBe(true);
  });

  it("os ícones pedidos aparecem todos no carrossel", () => {
    const quadros = montarQuadros({ slides, preferida: "editorial", ancoras, icones: ["juros", "check", "lupa"] });
    expect(quadros.flatMap((q) => q.icones).sort()).toEqual(["check", "juros", "lupa"]);
  });

  it("sem quadros devolve lista vazia", () => {
    expect(montarQuadros({ slides: [], preferida: "editorial", ancoras, icones: ["banco"] })).toEqual([]);
  });
});

describe("montarQuadrosDeExemplo", () => {
  const referencia = { titulo: "Tesouro Selic ou CDB?", tema: "comparação de investimentos", composicao: "comparativo" } as const;

  it("monta cinco quadros, o primeiro com o título da referência", () => {
    const quadros = montarQuadrosDeExemplo(referencia);
    expect(quadros).toHaveLength(5);
    expect(quadros[0].slide.titulo).toBe("Tesouro Selic ou CDB?");
    expect(quadros[0].slide.tipo).toBe("hook");
    expect(quadros.map((q) => q.slide.tipo)).toEqual(["hook", "ponto", "ponto", "citacao", "cta"]);
  });

  it("todos usam a composição da referência", () => {
    expect(montarQuadrosDeExemplo(referencia).every((q) => q.composicao === "comparativo")).toBe(true);
  });

  it("o número é um marcador, nunca um valor real", () => {
    const grafico = montarQuadrosDeExemplo(referencia)[2].grafico;
    expect(grafico?.jeito).toBe("barras");
    if (grafico?.jeito === "barras") {
      expect(grafico.antes.citacao).toBe("XX,X%");
      expect(grafico.depois.citacao).toBe("XX,X%");
    }
  });

  it("só as composições com campo de gráfico levam gráfico", () => {
    const editorial = montarQuadrosDeExemplo({ ...referencia, composicao: "editorial" });
    expect(editorial.every((q) => q.grafico === null)).toBe(true);
    const estatistico = montarQuadrosDeExemplo({ ...referencia, composicao: "estatistico" });
    expect(estatistico[2].grafico?.jeito).toBe("numero");
  });
});
