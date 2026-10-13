import { describe, expect, it } from "vitest";
import {
  aparenciaDosAtributos,
  contarPalavras,
  dataDeHoje,
  decodificar,
  derivarEstrutura,
  dividirEmBlocos,
  dividirFrases,
  minutosDeLeitura,
  resumoDasSecoes,
  textoPlano,
} from "./estrutura";

const TEXTO = [
  "<h1>Copom leva a Selic a 14,00% a.a.</h1>",
  "<p>O Copom reduziu a Selic. O placar foi de 7 a 0.</p>",
  "<h2>O que foi decidido</h2>",
  "<p>A taxa caiu para 14,00% a.a. ao fim do encontro, com placar de 7 a 0 entre os membros.</p>",
  "<ul><li><p>Primeiro ponto</p></li><li><p>Segundo ponto</p></li></ul>",
  "<h2>Por quê</h2>",
  "<p>A inflação ainda está acima do alvo.</p>",
].join("\n");

describe("dividirEmBlocos", () => {
  it("separa os blocos de primeiro nível e mantém as listas inteiras", () => {
    const blocos = dividirEmBlocos(TEXTO);
    expect(blocos.map((b) => b.etiqueta)).toEqual(["h1", "p", "h2", "p", "ul", "h2", "p"]);
    expect(blocos[4].interno).toContain("<li><p>Segundo ponto</p></li>");
  });

  it("guarda os atributos da abertura", () => {
    const [bloco] = dividirEmBlocos('<p style="text-align: center">Oi</p>');
    expect(bloco.atributos).toBe(' style="text-align: center"');
    expect(bloco.interno).toBe("Oi");
  });

  it("aceita bloco sem conteúdo e aspas com sinal de maior no atributo", () => {
    const blocos = dividirEmBlocos('<hr><p data-x="a>b">Texto</p>');
    expect(blocos.map((b) => b.etiqueta)).toEqual(["hr", "p"]);
    expect(blocos[1].interno).toBe("Texto");
  });

  it("devolve vazio para texto sem marcas", () => {
    expect(dividirEmBlocos("")).toEqual([]);
    expect(dividirEmBlocos("só texto")).toEqual([]);
  });
});

describe("textoPlano e decodificar", () => {
  it("tira as marcas, junta o espaço e decodifica entidades", () => {
    expect(textoPlano("<p>Olá&nbsp;<strong>mundo</strong></p><p>A &amp; B</p>")).toBe("Olá mundo A & B");
  });

  it("não reabre uma marca que vinha escapada", () => {
    expect(textoPlano("<p>&lt;b&gt;negrito&lt;/b&gt;</p>")).toBe("<b>negrito</b>");
  });

  it("decodifica entidades numéricas e deixa as desconhecidas", () => {
    expect(decodificar("&#233;&#xE9;&desconhecida;")).toBe("éé&desconhecida;");
  });
});

describe("contagens", () => {
  it("conta palavras e ignora pontuação solta", () => {
    expect(contarPalavras("A Selic caiu para 14,00% — de novo.")).toBe(7);
    expect(contarPalavras("")).toBe(0);
  });

  it("dá pelo menos um minuto e arredonda para cima", () => {
    expect(minutosDeLeitura(0)).toBe(1);
    expect(minutosDeLeitura(200)).toBe(1);
    expect(minutosDeLeitura(201)).toBe(2);
    expect(minutosDeLeitura(650)).toBe(4);
  });
});

describe("dividirFrases", () => {
  it("não quebra em sigla nem em decimal", () => {
    const frases = dividirFrases("A Selic caiu para 14,00% a.a. ao fim do encontro. O placar foi de 7 a 0. Ninguém divergiu.");
    expect(frases).toEqual([
      "A Selic caiu para 14,00% a.a. ao fim do encontro.",
      "O placar foi de 7 a 0.",
      "Ninguém divergiu.",
    ]);
  });

  it("não quebra a sigla mesmo quando a próxima frase começa em maiúscula", () => {
    expect(dividirFrases("A Selic ficou em 14,00% a.a. O placar foi de 7 a 0.")).toHaveLength(1);
  });

  it("devolve o texto todo quando não há ponto final", () => {
    expect(dividirFrases("Sem ponto final")).toEqual(["Sem ponto final"]);
  });
});

describe("aparenciaDosAtributos", () => {
  it("lê o style como objeto do React, só com o que o editor produz", () => {
    expect(
      aparenciaDosAtributos(' style="text-align: center; line-height: 1.8; position: fixed; font-family: Lora Variable, serif"'),
    ).toEqual({ textAlign: "center", lineHeight: "1.8", fontFamily: "Lora Variable, serif" });
  });

  it("devolve vazio sem style", () => {
    expect(aparenciaDosAtributos("")).toEqual({});
  });
});

describe("dataDeHoje", () => {
  it("escreve a data por extenso em português", () => {
    expect(dataDeHoje(new Date(2026, 9, 12))).toBe("12 de outubro de 2026");
  });
});

describe("derivarEstrutura", () => {
  const estrutura = derivarEstrutura(TEXTO);

  it("tira o título do primeiro h1 e o lide do primeiro parágrafo antes das seções", () => {
    expect(estrutura.titulo).toBe("Copom leva a Selic a 14,00% a.a.");
    expect(estrutura.lide?.interno).toBe("O Copom reduziu a Selic. O placar foi de 7 a 0.");
  });

  it("monta as seções pelos h2 com os blocos de cada uma", () => {
    expect(estrutura.secoes.map((s) => s.titulo)).toEqual(["O que foi decidido", "Por quê"]);
    expect(estrutura.secoes[0].blocos.map((b) => b.etiqueta)).toEqual(["p", "ul"]);
  });

  it("conta palavras e minutos do texto inteiro", () => {
    expect(estrutura.palavras).toBeGreaterThan(30);
    expect(estrutura.minutos).toBe(1);
  });

  it("escolhe como citação uma frase do texto com número, nem curta nem longa", () => {
    expect(estrutura.citacao).toBe(
      "A taxa caiu para 14,00% a.a. ao fim do encontro, com placar de 7 a 0 entre os membros.",
    );
  });

  it("sem lide, as seções começam logo depois do título", () => {
    const sem = derivarEstrutura("<h1>T</h1><h2>A</h2><p>Um.</p>");
    expect(sem.lide).toBeNull();
    expect(sem.secoes).toHaveLength(1);
  });

  it("guarda como seção sem título o que vem depois do lide e antes do primeiro h2", () => {
    const comAbertura = derivarEstrutura("<h1>T</h1><p>Lide.</p><ul><li><p>a</p></li></ul><h2>A</h2><p>Um.</p>");
    expect(comAbertura.lide?.interno).toBe("Lide.");
    expect(comAbertura.secoes.map((s) => s.titulo)).toEqual([null, "A"]);
  });

  it("sem h1, a primeira linha curta vira o título e sai do corpo", () => {
    const sem = derivarEstrutura("<p>Uma linha só</p><p>Corpo do texto.</p>");
    expect(sem.titulo).toBe("Uma linha só");
    expect(sem.lide?.interno).toBe("Corpo do texto.");
  });

  it("sem h1 e com a primeira linha longa, o título é a primeira frase e o corpo fica inteiro", () => {
    const longa = `${"palavra ".repeat(30)}fim. Segunda frase.`;
    const sem = derivarEstrutura(`<p>${longa}</p>`);
    expect(sem.titulo.endsWith("fim.") || sem.titulo.endsWith("…")).toBe(true);
    expect(sem.lide?.interno).toBe(longa);
  });

  it("usa a citação do próprio texto quando há blockquote", () => {
    const comCitacao = derivarEstrutura("<h1>T</h1><blockquote><p>Frase em destaque.</p></blockquote><h2>A</h2><p>Um.</p>");
    expect(comCitacao.citacao).toBe("Frase em destaque.");
  });

  it("não quebra com texto vazio", () => {
    const vazio = derivarEstrutura("");
    expect(vazio.titulo).toBe("Sem título");
    expect(vazio.secoes).toEqual([]);
    expect(vazio.palavras).toBe(0);
    expect(vazio.minutos).toBe(1);
  });
});

describe("resumoDasSecoes", () => {
  it("pega a primeira frase do primeiro parágrafo de cada seção", () => {
    const topicos = resumoDasSecoes(derivarEstrutura(TEXTO));
    expect(topicos).toEqual([
      "A taxa caiu para 14,00% a.a. ao fim do encontro, com placar de 7 a 0 entre os membros.",
      "A inflação ainda está acima do alvo.",
    ]);
  });
});
