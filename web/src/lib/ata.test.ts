import { describe, expect, it } from "vitest";
import { estruturarAta, juntarLinhas } from "./ata";

const TEXTO = `1    bcb.gov.br

Ata da Reunião do
Comitê de Política Monetária — Copom
15 e 16 de setembro de 2026
281ª

281ª Reunião
COPOM
15 e 16 de setembro
2    bcb.gov.br

Data: 15 e 16 de setembro de 2026

Presentes:
Fulano

Os membros do Copom analisaram a evolução
e a economia.

281ª Reunião
COPOM
15 e 16 de setembro
3    bcb.gov.br
A) Atualização da conjuntura
1. O ambiente externo permanece
incerto.
2. A política fiscal tem um impacto da

1 A menos de menção explícita em contrário.

281ª Reunião
COPOM
15 e 16 de setembro
4    bcb.gov.br
curva de juros.
B) Cenários
3. Fim.`;

describe("estruturarAta", () => {
  const ata = estruturarAta(TEXTO);

  it("separa a capa, sem os cabeçalhos de página", () => {
    expect(ata.capa).toEqual([
      "Ata da Reunião do",
      "Comitê de Política Monetária — Copom",
      "15 e 16 de setembro de 2026",
      "281ª",
    ]);
  });

  it("separa a ficha da reunião", () => {
    expect(ata.ficha[0]).toBe("Data: 15 e 16 de setembro de 2026");
    expect(ata.ficha).toContain("Fulano");
  });

  it("reconhece seções e parágrafos numerados, juntando as linhas quebradas", () => {
    expect(ata.corpo[0]).toEqual({
      tipo: "paragrafo",
      numero: null,
      texto: "Os membros do Copom analisaram a evolução e a economia.",
    });
    expect(ata.corpo[1]).toEqual({ tipo: "secao", texto: "A) Atualização da conjuntura" });
    expect(ata.corpo[2]).toMatchObject({ numero: "1", texto: "O ambiente externo permanece incerto." });
  });

  it("religa o parágrafo cortado pela quebra de página e tira a nota de rodapé do meio", () => {
    expect(ata.corpo[3]).toEqual({
      tipo: "paragrafo",
      numero: "2",
      texto: "A política fiscal tem um impacto da curva de juros.",
    });
    expect(ata.notas).toEqual(["1 A menos de menção explícita em contrário."]);
    expect(ata.corpo[4]).toEqual({ tipo: "secao", texto: "B) Cenários" });
  });

  it("sem capa nem ficha, tudo vira corpo", () => {
    const outro = estruturarAta("Primeiro parágrafo.\n\nSegundo parágrafo.");
    expect(outro.capa).toEqual([]);
    expect(outro.corpo).toHaveLength(2);
  });
});

describe("juntarLinhas", () => {
  it("conserta espaço solto antes de pontuação e de hífen", () => {
    expect(juntarLinhas(["situando -se abaixo", "do limite ."])).toBe("situando-se abaixo do limite.");
  });
});

describe("tabelas", () => {
  it("vira legenda, cabeçalho e linhas de células", () => {
    const ata = estruturarAta(
      "A) Seção\n1. Texto.\n\nTabela 1\nProjeções\n(%)\n\nÍndice de preços 2026  2027 1º tri 2028\nIPCA  5,2   3,9  3,2",
    );
    expect(ata.corpo.at(-1)).toEqual({
      tipo: "tabela",
      legenda: ["Tabela 1", "Projeções", "(%)"],
      cabecalho: ["Índice de preços", "2026", "2027", "1º tri 2028"],
      linhas: [["IPCA", "5,2", "3,9", "3,2"]],
    });
  });
});
