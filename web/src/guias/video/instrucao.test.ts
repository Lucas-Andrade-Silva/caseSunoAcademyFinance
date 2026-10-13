import { describe, expect, it } from "vitest";
import type { BlocoFala } from "../../dados/cliente";
import { montarPrompt } from "./instrucao";
import type { ClimaDoNarrador, RitmoDoNarrador } from "./jeitos";

function bloco(parcial: Partial<BlocoFala> = {}): BlocoFala {
  return {
    inicio_s: 0,
    fim_s: 8,
    fala: "Você sabe como o Banco Central decide os juros?",
    tela: "",
    cena: "texto_destaque",
    icone: null,
    entrada: "corte",
    texto_anima: "fade",
    texto_entra_em_s: 0,
    efeito: "nenhum",
    ...parcial,
  };
}

const ROTEIRO: BlocoFala[] = [
  bloco({
    fim_s: 8,
    cena: "gancho",
    icone: "pergunta",
    tela: "Como o Banco Central decide os juros?",
    texto_anima: "digitar",
  }),
  bloco({
    inicio_s: 8,
    fim_s: 21.6,
    fala: "Eles definiram a Selic, a taxa básica de juros, em 13,75% a.a.",
    tela: "Selic em 13,75% a.a.",
    cena: "dado_grande",
    icone: "juros",
    entrada: "deslizar_cima",
    texto_anima: "pop",
    texto_entra_em_s: 0.4,
    efeito: "contagem",
  }),
];

function prompt(clima: ClimaDoNarrador | null = null, ritmo: RitmoDoNarrador | null = null, blocos = ROTEIRO) {
  return montarPrompt({ blocos, clima, ritmo });
}

describe("montarPrompt: o formato e a duração", () => {
  it("pede vídeo vertical 9:16 com a duração do último bloco", () => {
    const texto = prompt();
    expect(texto).toContain("vertical em formato 9:16");
    expect(texto).toContain("duração de 22 segundos");
  });

  it("escreve a duração em minutos quando passa de um", () => {
    const texto = prompt(null, null, [bloco({ fim_s: 87.3 })]);
    expect(texto).toContain("duração de 1 minuto e 27 segundos");
  });

  it("sem blocos não há o que montar", () => {
    expect(prompt(null, null, [])).toBe("");
  });
});

describe("montarPrompt: os jeitos", () => {
  it("cada clima muda o texto do narrador e da edição", () => {
    const textos = (["descontraido", "serio", "engracado"] as const).map((clima) => prompt(clima));
    expect(new Set(textos).size).toBe(3);
    expect(textos[0]).toContain("sorriso discreto");
    expect(textos[1]).toContain("voz grave e calma");
    expect(textos[2]).toContain("sem piada com o dado");
  });

  it("cada ritmo traz as palavras por minuto e muda a edição", () => {
    const devagar = prompt(null, "devagar");
    const rapido = prompt(null, "rapido");
    expect(devagar).toContain("130 palavras por minuto");
    expect(devagar).toContain("pausas curtas");
    expect(rapido).toContain("170 palavras por minuto");
    expect(rapido).toContain("Cortes mais curtos");
    expect(devagar).not.toContain("170 palavras");
    expect(rapido).not.toContain("130 palavras");
  });

  it("clima e ritmo combinam", () => {
    const texto = prompt("serio", "rapido");
    expect(texto).toContain("voz grave e calma");
    expect(texto).toContain("170 palavras por minuto");
    expect(texto).toContain("Visual sóbrio");
    expect(texto).toContain("Cortes mais curtos");
  });

  it("sem escolha, vale o jeito neutro e o ritmo do próprio roteiro", () => {
    const texto = prompt();
    expect(texto).toContain("Tom: natural e claro");
    expect(texto).toContain("150 palavras por minuto");
    expect(texto).toContain("Edição sóbria");
    expect(texto).not.toContain("130 palavras");
    expect(texto).not.toContain("170 palavras");
  });
});

describe("montarPrompt: as cenas", () => {
  it("a fala sai literal, entre aspas, sem tocar nos números", () => {
    const texto = prompt();
    for (const cena of ROTEIRO) expect(texto).toContain(`Fala (leia exatamente assim): “${cena.fala}”`);
    expect(texto).toContain("13,75% a.a.");
  });

  it("a fala com aspas, travessão e quebra de linha não é alterada", () => {
    const fala = 'Ele disse "agora" — e foi isso.\nOutra linha.';
    expect(prompt(null, null, [bloco({ fala })])).toContain(`“${fala}”`);
  });

  it("numera as cenas, com o tempo e o nome da cena", () => {
    const texto = prompt();
    expect(texto).toContain("Cena 1 · 0:00–0:08 · Gancho");
    expect(texto).toContain("Cena 2 · 0:08–0:22 · Dado grande");
  });

  it("escreve a direção que o bloco traz", () => {
    const texto = prompt();
    expect(texto).toContain("Na tela: “Selic em 13,75% a.a.”");
    expect(texto).toContain("Animação do texto: cresce de pequeno ao tamanho final (pop), 0,4 s depois do início da cena.");
    expect(texto).toContain("Ícone: Taxa de juros.");
    expect(texto).toContain("Entrada da cena: a cena entra subindo.");
    expect(texto).toContain("Efeito: o número sobe até o valor final.");
    expect(texto).toContain("Animação do texto: aparece letra por letra, como digitado.");
  });

  it("o que é corte, nenhum ou nulo não vira linha", () => {
    const texto = prompt(null, null, [bloco()]);
    expect(texto).not.toContain("Ícone:");
    expect(texto).not.toContain("Entrada da cena:");
    expect(texto).not.toContain("Efeito:");
    expect(texto).not.toContain("Na tela");
    expect(texto).not.toContain("Animação do texto");
    expect(texto).not.toContain("null");
    expect(texto).not.toContain("undefined");
  });

  it("não cita o tempo de entrada do texto quando ele aparece junto com a cena", () => {
    const texto = prompt(null, null, [bloco({ tela: "Selic", texto_entra_em_s: 0 })]);
    expect(texto).toContain("Animação do texto: surge com fade.");
    expect(texto).not.toContain("depois do início");
  });

  it("a rubrica com várias partes vira lista dita em ordem", () => {
    const lista = prompt(null, null, [bloco({ cena: "lista", tela: "Inflação | Juros | Emprego" })]);
    expect(lista).toContain("Na tela, em sequência: “Inflação”; “Juros”; “Emprego”");
    const lados = prompt(null, null, [bloco({ cena: "comparacao", tela: "Antes | Depois" })]);
    expect(lados).toContain("Na tela, dois lados: “Antes”; “Depois”");
  });

  it("descreve onde o avatar fica em cada layout", () => {
    expect(prompt()).toContain("Layout: abertura, com o avatar grande no centro");
    expect(prompt(null, null, [bloco({ cena: "comparacao" })])).toContain("sem o avatar na tela");
  });

  it("um nome fora do catálogo aparece como veio, sem derrubar a montagem", () => {
    const texto = prompt(null, null, [bloco({ icone: "icone_novo" as BlocoFala["icone"], cena: "cena_nova" as BlocoFala["cena"] })]);
    expect(texto).toContain("Cena 1 · 0:00–0:08 · Cena nova");
    expect(texto).toContain("Ícone: Icone novo.");
  });
});

describe("montarPrompt: as regras", () => {
  it("fecha com as regras de conteúdo e de edição", () => {
    const texto = prompt();
    expect(texto.endsWith("- Sem logotipos, marcas ou imagens de terceiros.")).toBe(true);
    expect(texto).toContain("exatamente como estão, sem arredondar");
    expect(texto).toContain("Não prometa retorno");
    expect(texto).toContain("não recomende comprar, vender ou manter");
    expect(texto).toContain("Legendas embutidas");
  });

  it("não inventa dado: toda taxa em % do prompt vem do roteiro", () => {
    const texto = prompt("engracado", "rapido", [bloco({ fala: "A Selic ficou em 14,25% a.a. em 2026.", tela: "14,25%" })]);
    expect(texto).toContain("14,25% a.a. em 2026");
    expect(texto.match(/\d+(?:,\d+)?%/g)).toEqual(["14,25%", "14,25%"]);
  });
});
