import { describe, expect, it } from "vitest";
import {
  alternarSelecao,
  contarSelecionadas,
  dataDoDia,
  ehCalibrada,
  limparInexistentes,
  nomePadrao,
  podeUsarSelecao,
  seloDaAta,
} from "./fontes";

describe("seloDaAta e ehCalibrada", () => {
  it("só o Copom é calibrado", () => {
    expect(ehCalibrada("copom")).toBe(true);
    expect(ehCalibrada("comunicado_relevante")).toBe(false);
    expect(ehCalibrada("release")).toBe(false);
    expect(ehCalibrada("importada")).toBe(false);
  });

  it("fora do Copom o selo é 'não calibrado'", () => {
    expect(seloDaAta("copom")).toBeNull();
    expect(seloDaAta("importada")).toBe("não calibrado");
    expect(seloDaAta("comunicado_relevante")).toBe("não calibrado");
  });
});

describe("alternarSelecao", () => {
  it("marca uma Ata que não estava marcada", () => {
    expect(alternarSelecao([], "a")).toEqual(["a"]);
  });

  it("desmarca uma que estava marcada", () => {
    expect(alternarSelecao(["a", "b"], "a")).toEqual(["b"]);
  });

  it("mantém a ordem em que foram marcadas", () => {
    expect(alternarSelecao(alternarSelecao(["x"], "z"), "y")).toEqual(["x", "z", "y"]);
  });

  it("não muda a lista original", () => {
    const antes = ["a"];
    alternarSelecao(antes, "b");
    expect(antes).toEqual(["a"]);
  });
});

describe("contarSelecionadas", () => {
  it("conta só as que existem na Origem", () => {
    const atas = [{ identificador: "a" }, { identificador: "b" }, { identificador: "c" }];
    expect(contarSelecionadas(["a", "c", "fantasma"], atas)).toBe(2);
    expect(contarSelecionadas([], atas)).toBe(0);
  });
});

describe("limparInexistentes", () => {
  it("tira da seleção o que sumiu do disco", () => {
    expect(limparInexistentes(["a", "b", "c"], new Set(["b", "c", "d"]))).toEqual(["b", "c"]);
  });
});

describe("podeUsarSelecao", () => {
  it("sem nada marcado não há o que usar", () => {
    expect(podeUsarSelecao([])).toEqual({
      ok: false,
      motivo: "Marque uma Ata nas Fontes.",
      modo: null,
    });
  });

  it("uma Ata é Destaque único e de duas a cinco são Visão unida", () => {
    expect(podeUsarSelecao(["a"])).toEqual({ ok: true, motivo: null, modo: "destaque" });
    expect(podeUsarSelecao(["a", "b"]).modo).toBe("unida");
    expect(podeUsarSelecao(["a", "b", "c", "d", "e"])).toEqual({
      ok: true,
      motivo: null,
      modo: "unida",
    });
  });

  it("mais de cinco passa do limite da Visão unida", () => {
    const seis = podeUsarSelecao(["a", "b", "c", "d", "e", "f"]);
    expect(seis.ok).toBe(false);
    expect(seis.motivo).toContain("no máximo 5");
    expect(seis.modo).toBeNull();
  });
});

describe("nomePadrao", () => {
  it("uma Ata usa o próprio título", () => {
    expect(nomePadrao(["280ª Reunião"])).toBe("280ª Reunião");
  });

  it("várias viram 'Visão unida: A + B'", () => {
    expect(nomePadrao(["A", "B", "C"])).toBe("Visão unida: A + B + C");
  });

  it("respeita o limite de caracteres do servidor", () => {
    const longo = nomePadrao(["x".repeat(100), "y".repeat(100)]);
    expect(longo.length).toBeLessThanOrEqual(120);
    expect(longo.endsWith("…")).toBe(true);
  });
});

describe("dataDoDia", () => {
  it("formata a data da Ata sem mexer no fuso", () => {
    expect(dataDoDia("2026-08-05")).toBe("05/08");
    expect(dataDoDia("2026-10-09")).toBe("09/10");
  });

  it("data estranha volta como veio", () => {
    expect(dataDoDia("amanhã")).toBe("amanhã");
  });
});
