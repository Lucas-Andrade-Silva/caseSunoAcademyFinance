import { describe, expect, it } from "vitest";
import {
  ENTRELINHAS,
  FAMILIAS,
  entrelinhaDoCss,
  familiaDoCss,
  lerTamanho,
  mesmaCor,
  passoDeTamanho,
  rotuloDaEntrelinha,
} from "./ajustes";

describe("familiaDoCss", () => {
  it("reconhece cada família pelo primeiro nome, com ou sem aspas", () => {
    for (const familia of FAMILIAS) expect(familiaDoCss(familia.css)).toBe(familia.id);
    expect(familiaDoCss('"Lora Variable", Georgia, serif')).toBe("lora");
    expect(familiaDoCss("'Space Mono', monospace")).toBe("space");
  });

  it("devolve nulo para outra família ou para nada", () => {
    expect(familiaDoCss("Arial, sans-serif")).toBeNull();
    expect(familiaDoCss(null)).toBeNull();
    expect(familiaDoCss("")).toBeNull();
  });
});

describe("tamanho", () => {
  it("lê pixels e recusa outras unidades", () => {
    expect(lerTamanho("18px")).toBe(18);
    expect(lerTamanho(" 17.5px ")).toBe(17.5);
    expect(lerTamanho("1.2em")).toBeNull();
    expect(lerTamanho(null)).toBeNull();
  });

  it("anda um degrau e para nas pontas", () => {
    expect(passoDeTamanho(17, 1)).toBe(18);
    expect(passoDeTamanho(17, -1)).toBe(16);
    expect(passoDeTamanho(19, 1)).toBe(20);
    expect(passoDeTamanho(19, -1)).toBe(18);
    expect(passoDeTamanho(32, 1)).toBe(32);
    expect(passoDeTamanho(14, -1)).toBe(14);
  });
});

describe("entrelinha", () => {
  it("escreve com vírgula e leva o valor guardado ao degrau mais próximo", () => {
    expect(rotuloDaEntrelinha(1.5)).toBe("1,5");
    expect(entrelinhaDoCss("1.5")).toBe(1.5);
    expect(entrelinhaDoCss("1.7")).toBe(1.8);
    expect(entrelinhaDoCss(null)).toBeNull();
    expect(ENTRELINHAS).toContain(2.1);
  });
});

describe("mesmaCor", () => {
  it("compara hex e rgb como o navegador devolve", () => {
    expect(mesmaCor("#E5484D", "rgb(229, 72, 77)")).toBe(true);
    expect(mesmaCor("#e5484d", "#2e9e5e")).toBe(false);
    expect(mesmaCor(null, null)).toBe(false);
  });
});
