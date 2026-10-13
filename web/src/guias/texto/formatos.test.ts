import { describe, expect, it } from "vitest";
import { markdownParaHtml } from "./conversao";
import { CHAVE_DAS_EDICOES, comEdicao, SEM_EDICOES, validarEdicoes, valemPara } from "./edicoes";
import { lerDados, resumoDoTexto } from "./formatos";

describe("lerDados", () => {
  it("aceita o que a guia grava", () => {
    expect(lerDados({ formato: "site", html: "<p>Oi</p>" })).toEqual({ formato: "site", html: "<p>Oi</p>" });
  });

  it("recusa formato desconhecido, HTML vazio e lixo", () => {
    expect(lerDados({ formato: "podcast", html: "<p>Oi</p>" })).toBeNull();
    expect(lerDados({ formato: "email", html: "   " })).toBeNull();
    expect(lerDados({ formato: "email" })).toBeNull();
    expect(lerDados("texto")).toBeNull();
    expect(lerDados(null)).toBeNull();
  });
});

describe("resumoDoTexto", () => {
  it("junta o formato e a contagem de palavras", () => {
    expect(resumoDoTexto("email", "<h1>Título aqui</h1><p>Um dois três quatro.</p>")).toBe("E-mail · 6 palavras");
    expect(resumoDoTexto("artigo", "<p>Só</p>")).toBe("Artigo · 1 palavra");
  });
});

describe("markdownParaHtml", () => {
  it("converte títulos, parágrafos e ênfase", () => {
    const html = markdownParaHtml("# Título\n\n## Seção\n\nTexto com **negrito** e *itálico*.");
    expect(html).toContain("<h1>Título</h1>");
    expect(html).toContain("<h2>Seção</h2>");
    expect(html).toContain("<strong>negrito</strong>");
    expect(html).toContain("<em>itálico</em>");
  });

  it("não deixa passar HTML cru nem endereço de link", () => {
    const html = markdownParaHtml('Veja <script>alert(1)</script> e [aqui](javascript:alert(1)) ![x](a.png)');
    expect(html).not.toContain("<script");
    expect(html).not.toContain("javascript:");
    expect(html).not.toContain("<a ");
    expect(html).not.toContain("<img");
    expect(html).toContain("aqui");
  });
});

describe("edições da sessão", () => {
  it("só vale para a Saída em que foi feita", () => {
    const edicoes = comEdicao(SEM_EDICOES, "exec-1", "iniciante", "<p>A</p>");
    expect(valemPara(edicoes, "exec-1")).toEqual({ iniciante: "<p>A</p>" });
    expect(valemPara(edicoes, "exec-2")).toEqual({});
    expect(valemPara(edicoes, null)).toEqual({});
  });

  it("junta as audiências da mesma Saída e descarta as de outra", () => {
    const a = comEdicao(SEM_EDICOES, "exec-1", "iniciante", "<p>A</p>");
    const b = comEdicao(a, "exec-1", "avancado", "<p>B</p>");
    expect(b.html).toEqual({ iniciante: "<p>A</p>", avancado: "<p>B</p>" });
    const c = comEdicao(b, "exec-2", "avancado", "<p>C</p>");
    expect(c.html).toEqual({ avancado: "<p>C</p>" });
  });

  it("valida o que veio do navegador", () => {
    expect(validarEdicoes(null)).toEqual(SEM_EDICOES);
    expect(validarEdicoes({ execucaoId: 3, html: { iniciante: "<p>A</p>", avancado: 7, outra: "x" } })).toEqual({
      execucaoId: null,
      html: { iniciante: "<p>A</p>" },
    });
    expect(CHAVE_DAS_EDICOES).toMatch(/^suno\./);
  });
});
