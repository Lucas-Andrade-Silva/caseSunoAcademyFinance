import { describe, expect, it } from "vitest";
import type { ResumoDaAta } from "../dados/cliente";
import { corpoDaSaida, motivoDeRecusa } from "./pedido";

function ata(identificador: string, mudar: Partial<ResumoDaAta> = {}): ResumoDaAta {
  return {
    identificador,
    origem: "copom",
    categoria: "copom",
    titulo: `Ata ${identificador}`,
    data_referencia: "2026-10-10",
    resumo: "",
    total_ancoras: 5,
    calibrada: true,
    demo_disponivel: true,
    extracao_completa: true,
    ...mudar,
  };
}

describe("motivoDeRecusa", () => {
  it("sem notícia ou sem audiência não gera", () => {
    expect(motivoDeRecusa({ atas: [], modo: "real", audiencias: ["iniciante"] })).toMatch(/notícia/);
    expect(motivoDeRecusa({ atas: [ata("a")], modo: "real", audiencias: [] })).toMatch(/audiência/);
  });

  it("uma notícia no modo Real passa", () => {
    expect(motivoDeRecusa({ atas: [ata("a")], modo: "real", audiencias: ["iniciante"] })).toBeNull();
  });

  it("várias notícias só geram no modo Real", () => {
    const duas = [ata("a"), ata("b")];
    expect(motivoDeRecusa({ atas: duas, modo: "demo", audiencias: ["iniciante"] })).toMatch(/Real/);
    expect(motivoDeRecusa({ atas: duas, modo: "real", audiencias: ["iniciante"] })).toBeNull();
  });

  it("a Demo exige respostas prontas", () => {
    const semDemo = [ata("a", { demo_disponivel: false })];
    expect(motivoDeRecusa({ atas: semDemo, modo: "demo", audiencias: ["iniciante"] })).toMatch(/Demo/);
  });

  it("extração incompleta não gasta cota", () => {
    const ruim = [ata("a", { extracao_completa: false })];
    expect(motivoDeRecusa({ atas: ruim, modo: "real", audiencias: ["iniciante"] })).toMatch(/número/);
  });
});

describe("corpoDaSaida", () => {
  it("uma Ata vai em `ata`, e o pedido tem uma posição por audiência", () => {
    const corpo = corpoDaSaida({
      formato: "texto_analitico",
      audiencias: ["iniciante", "avancado"],
      atas: [ata("a")],
      modo: "real",
    });
    expect(corpo.ata).toBe("a");
    expect(corpo.itens).toBeUndefined();
    expect(corpo.pedido).toEqual([
      { audiencia: "iniciante", formato: "texto_analitico" },
      { audiencia: "avancado", formato: "texto_analitico" },
    ]);
    expect(corpo.nome).toBe("Ata a · Texto analítico");
  });

  it("várias Atas vão em `itens` (Visão unida)", () => {
    const corpo = corpoDaSaida({
      formato: "roteiro",
      audiencias: ["intermediario"],
      atas: [ata("a"), ata("b")],
      modo: "real",
      extras: { duracao: "90" },
    });
    expect(corpo.ata).toBeUndefined();
    expect(corpo.itens).toEqual(["a", "b"]);
    expect(corpo.duracao).toBe("90");
  });

  it("composição e referência visual vão juntas, só no Carrossel", () => {
    const comAmbas = corpoDaSaida({
      formato: "carrossel",
      audiencias: ["iniciante"],
      atas: [ata("a")],
      modo: "demo",
      extras: { composicaoVisual: "editorial", referenciaVisual: "x" },
    });
    expect(comAmbas.composicao_visual).toBe("editorial");
    expect(comAmbas.referencia_visual).toBe("x");

    const soUma = corpoDaSaida({
      formato: "carrossel",
      audiencias: ["iniciante"],
      atas: [ata("a")],
      modo: "demo",
      extras: { composicaoVisual: "editorial" },
    });
    expect(soUma.composicao_visual).toBeUndefined();
  });

  it("o nome cabe em 120 caracteres", () => {
    const comprida = ata("a", { titulo: "x".repeat(300) });
    const corpo = corpoDaSaida({
      formato: "carrossel",
      audiencias: ["iniciante"],
      atas: [comprida],
      modo: "real",
    });
    expect((corpo.nome ?? "").length).toBeLessThanOrEqual(120);
  });
});
