import { describe, expect, it } from "vitest";
import { lerAtuacao, linhaDaAtuacao } from "./atuacao";
import { montarPrompt } from "./instrucao";

const plano = {
  avatar: {
    atuacao: { olhar: "direto para a câmera", gestos: "mínimos", proibido: ["sorriso aberto"] },
    voz: {
      estilo: "natural",
      pausas: { entre_ideias_s: 0.35, depois_de_numero_s: 0.4 },
      pronuncia: { "a.a.": "ao ano", Copom: "cópom" },
    },
  },
  legendas: { y_px: 1360, margem_lateral_px: 84, alinhamento: "esquerda", tamanho_px: 42, peso: "regular", cor: "#E6E6E6", linhas_maximas: 2, palavras_por_linha: "até 5", regras_de_colisao: ["nunca sobre o texto da cena"] },
  cenas: [{ atuacao: { expressao: "acolhedora", gesto: "minimo", entonacao: "ascendente", pausa_depois_s: 0.5 } }],
};

describe("atuação do plano", () => {
  it("lê o padrão, a voz, a pronúncia, as legendas e a cena", () => {
    const a = lerAtuacao(plano)!;
    expect(a.geral[0]).toBe("Olhar: direto para a câmera.");
    expect(a.voz.join(" ")).toContain("0,35 s entre ideias");
    expect(a.pronuncia).toContain('"a.a." → ao ano');
    expect(a.legendas[0]).toContain("1360 px");
    expect(linhaDaAtuacao(a.cenas[0]!)).toBe(
      "Atuação: expressão acolhedora, sorriso contido; um gesto curto de mão; entonação sobe no fim (pergunta); pausa de 0,5 s ao fim.",
    );
  });

  it("plano antigo, sem atuação, devolve null", () => {
    expect(lerAtuacao({ avatar: { voz: {} } })).toBeNull();
    expect(lerAtuacao(null)).toBeNull();
  });

  it("o prompt ganha as seções e a linha da cena", () => {
    const bloco = { inicio_s: 0, fim_s: 4, fala: "Oi.", tela: "", cena: "gancho", entrada: "corte", texto_anima: "nenhuma", texto_entra_em_s: 0, efeito: "nenhum" };
    const texto = montarPrompt({ blocos: [bloco as never], clima: null, ritmo: null, atuacao: lerAtuacao(plano) });
    expect(texto).toContain("ATUAÇÃO DO AVATAR");
    expect(texto).toContain("PRONÚNCIA");
    expect(texto).toContain("LEGENDAS");
    expect(texto).toContain("Atuação: expressão acolhedora");
  });
});
