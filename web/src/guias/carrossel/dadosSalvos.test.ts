import { describe, expect, it } from "vitest";
import { dadosParaSalvar, lerDadosSalvos } from "./dadosSalvos";
import type { Montagem } from "./modelo";
import { PALETA_PADRAO } from "./paletas";

const montagem: Montagem = {
  audiencia: "iniciante",
  slides: [
    { tipo: "hook", titulo: "Capa", corpo: "Texto." },
    { tipo: "ponto", titulo: "Selic", corpo: "Texto.", dado: "selic_decidida" },
  ],
  composicao: "estatistico",
  referenciaId: "ref-1",
  paleta: PALETA_PADRAO,
  icones: ["juros", "banco"],
  ancoras: [{ chave: "selic_decidida", rotulo: "Selic decidida", citacao: "14,00% a.a.", valor: 14 }],
};

describe("lerDadosSalvos", () => {
  it("lê de volta o que dadosParaSalvar guardou (passando pelo JSON do localStorage)", () => {
    const guardado: unknown = JSON.parse(JSON.stringify(dadosParaSalvar(montagem, null)));
    const lido = lerDadosSalvos(guardado);
    expect(lido).not.toBeNull();
    expect(lido?.slides).toHaveLength(2);
    expect(lido?.composicao).toBe("estatistico");
    expect(lido?.referenciaId).toBe("ref-1");
    expect(lido?.paleta.id).toBe(PALETA_PADRAO.id);
    expect(lido?.icones).toEqual(["juros", "banco"]);
    expect(lido?.ancoras).toHaveLength(1);
    expect(lido?.laudo).toBeNull();
  });

  it("recusa o que não é um carrossel salvo", () => {
    expect(lerDadosSalvos(null)).toBeNull();
    expect(lerDadosSalvos("texto")).toBeNull();
    expect(lerDadosSalvos({})).toBeNull();
    expect(lerDadosSalvos({ ...dadosParaSalvar(montagem, null), slides: [] })).toBeNull();
    expect(lerDadosSalvos({ ...dadosParaSalvar(montagem, null), slides: [{ titulo: 1 }] })).toBeNull();
    expect(lerDadosSalvos({ ...dadosParaSalvar(montagem, null), composicao: "outra" })).toBeNull();
    expect(lerDadosSalvos({ ...dadosParaSalvar(montagem, null), paleta: { id: "x" } })).toBeNull();
  });

  it("descarta ícones e Âncoras inválidos sem recusar o salvo", () => {
    const lido = lerDadosSalvos({
      ...dadosParaSalvar(montagem, null),
      icones: ["juros", "foguete", 3],
      ancoras: [{ chave: "a" }, ...montagem.ancoras],
    });
    expect(lido?.icones).toEqual(["juros"]);
    expect(lido?.ancoras).toHaveLength(1);
  });

  it("referência ausente vira nula", () => {
    const { referenciaId: _fora, ...resto } = dadosParaSalvar(montagem, null);
    expect(lerDadosSalvos(resto)?.referenciaId).toBeNull();
  });
});
