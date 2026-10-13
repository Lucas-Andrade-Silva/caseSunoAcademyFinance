import { describe, expect, it } from "vitest";
import {
  duracaoDoRoteiro,
  duracaoPorExtenso,
  formatarDuracao,
  formatarIntervalo,
  formatarSegundos,
  formatarTempo,
  resumoDoRoteiro,
} from "./tempo";

describe("formatarTempo", () => {
  it("escreve minutos e segundos com dois dígitos nos segundos", () => {
    expect(formatarTempo(0)).toBe("0:00");
    expect(formatarTempo(6)).toBe("0:06");
    expect(formatarTempo(87)).toBe("1:27");
    expect(formatarTempo(600)).toBe("10:00");
  });

  it("arredonda para o segundo mais próximo", () => {
    expect(formatarTempo(5.6)).toBe("0:06");
    expect(formatarTempo(21.6)).toBe("0:22");
    expect(formatarTempo(59.6)).toBe("1:00");
  });

  it("trata o que não é tempo como zero", () => {
    expect(formatarTempo(-3)).toBe("0:00");
    expect(formatarTempo(Number.NaN)).toBe("0:00");
  });
});

describe("formatarIntervalo", () => {
  it("separa início e fim com travessão", () => {
    expect(formatarIntervalo(0, 6)).toBe("0:00–0:06");
  });

  it("o fim de uma cena e o começo da seguinte caem no mesmo segundo", () => {
    expect(formatarIntervalo(14, 21.6).split("–")[1]).toBe(formatarIntervalo(21.6, 31.2).split("–")[0]);
  });
});

describe("formatarDuracao", () => {
  it("usa a escrita das durações escolhidas na geração", () => {
    expect(formatarDuracao(40)).toBe("40 s");
    expect(formatarDuracao(60)).toBe("1 min");
    expect(formatarDuracao(90)).toBe("1 min 30");
    expect(formatarDuracao(120)).toBe("2 min");
    expect(formatarDuracao(180)).toBe("3 min");
  });

  it("mostra a duração medida, que raramente é redonda", () => {
    expect(formatarDuracao(87.3)).toBe("1 min 27");
    expect(formatarDuracao(62)).toBe("1 min 02");
  });
});

describe("duracaoPorExtenso", () => {
  it("escreve segundos, minutos e os dois juntos", () => {
    expect(duracaoPorExtenso(40)).toBe("40 segundos");
    expect(duracaoPorExtenso(1)).toBe("1 segundo");
    expect(duracaoPorExtenso(60)).toBe("1 minuto");
    expect(duracaoPorExtenso(87)).toBe("1 minuto e 27 segundos");
    expect(duracaoPorExtenso(121)).toBe("2 minutos e 1 segundo");
  });
});

describe("formatarSegundos", () => {
  it("usa vírgula e no máximo uma casa", () => {
    expect(formatarSegundos(0.4)).toBe("0,4");
    expect(formatarSegundos(1)).toBe("1");
    expect(formatarSegundos(1.26)).toBe("1,3");
  });
});

describe("duracaoDoRoteiro e resumoDoRoteiro", () => {
  const blocos = [{ fim_s: 8 }, { fim_s: 21.6 }, { fim_s: 87.3 }];

  it("o vídeo dura até o fim da última cena", () => {
    expect(duracaoDoRoteiro(blocos)).toBe(87.3);
    expect(duracaoDoRoteiro([])).toBe(0);
  });

  it("não depende da ordem dos blocos", () => {
    expect(duracaoDoRoteiro([{ fim_s: 30 }, { fim_s: 10 }])).toBe(30);
  });

  it("o resumo traz a duração e a contagem de cenas", () => {
    expect(resumoDoRoteiro(blocos)).toBe("1 min 27 · 3 cenas");
    expect(resumoDoRoteiro([{ fim_s: 90 }])).toBe("1 min 30 · 1 cena");
  });
});
