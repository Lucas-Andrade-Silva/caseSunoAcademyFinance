import { describe, expect, it } from "vitest";
import {
  celulaBloqueada,
  chaveDaPosicao,
  chipsDaPosicao,
  contarAguardando,
  contarPosicoes,
  estadoDaPosicao,
  filtrarSaidas,
  larguraDaBarra,
  maisRecentesPrimeiro,
  normalizarBusca,
  vizinhas,
  type PosicaoParaTela,
} from "./matriz";

function posicao(parcial: Partial<PosicaoParaTela> = {}): PosicaoParaTela {
  return {
    audiencia: "iniciante",
    formato: "carrossel",
    destino: "aprovado",
    decisao: null,
    bloqueada: false,
    sem_conteudo: false,
    revisao_comite: false,
    ...parcial,
  };
}

describe("estadoDaPosicao", () => {
  it("decisão de aprovar pinta de verde", () => {
    expect(estadoDaPosicao(posicao({ decisao: "aprovada" }))).toBe("aprovada");
  });

  it("decisão de reprovar, bloqueio e falta de conteúdo pintam de vermelho", () => {
    expect(estadoDaPosicao(posicao({ decisao: "reprovada" }))).toBe("reprovada");
    expect(estadoDaPosicao(posicao({ bloqueada: true }))).toBe("reprovada");
    expect(
      estadoDaPosicao(posicao({ sem_conteudo: true, destino: "reprovado_revisao_humana" })),
    ).toBe("reprovada");
  });

  it("revisão humana pelo Laudo ou pelo comitê pinta de âmbar", () => {
    expect(estadoDaPosicao(posicao({ destino: "reprovado_revisao_humana" }))).toBe("revisao");
    expect(estadoDaPosicao(posicao({ revisao_comite: true }))).toBe("revisao");
  });

  it("Laudo ok sem decisão espera a decisão", () => {
    expect(estadoDaPosicao(posicao())).toBe("aguardando");
  });

  it("a decisão humana vale mais que a revisão pedida pelo Laudo", () => {
    expect(
      estadoDaPosicao(posicao({ destino: "reprovado_revisao_humana", decisao: "aprovada" })),
    ).toBe("aprovada");
  });
});

describe("chipsDaPosicao", () => {
  it("Célula limpa e pendente", () => {
    expect(chipsDaPosicao(posicao())).toEqual({
      laudo: { texto: "Laudo ok", tom: "ok" },
      decisao: { texto: "Pendente", tom: "neutro" },
    });
  });

  it("Célula bloqueada mostra Compliance e Bloqueada", () => {
    expect(chipsDaPosicao(posicao({ bloqueada: true, destino: "reprovado_revisao_humana" }))).toEqual({
      laudo: { texto: "Compliance", tom: "ruim" },
      decisao: { texto: "Bloqueada", tom: "ruim" },
    });
  });

  it("revisão humana e comitê aparecem em âmbar", () => {
    expect(chipsDaPosicao(posicao({ destino: "reprovado_revisao_humana" })).laudo).toEqual({
      texto: "Revisão humana",
      tom: "alerta",
    });
    expect(chipsDaPosicao(posicao({ revisao_comite: true })).laudo).toEqual({
      texto: "Revisão: comitê",
      tom: "alerta",
    });
  });

  it("decisões humanas aparecem no segundo chip", () => {
    expect(chipsDaPosicao(posicao({ decisao: "aprovada" })).decisao).toEqual({
      texto: "Você aprovou",
      tom: "forte",
    });
    expect(chipsDaPosicao(posicao({ decisao: "reprovada" })).decisao).toEqual({
      texto: "Você reprovou",
      tom: "ruim",
    });
  });

  it("sem conteúdo mostra que a geração parou", () => {
    expect(
      chipsDaPosicao(posicao({ sem_conteudo: true, destino: "reprovado_revisao_humana" })),
    ).toEqual({
      laudo: { texto: "Sem conteúdo", tom: "ruim" },
      decisao: { texto: "Parou", tom: "ruim" },
    });
  });

  it("Célula em correção aparece em âmbar", () => {
    expect(chipsDaPosicao(posicao({ destino: "reprovado_corrigivel" })).laudo).toEqual({
      texto: "Em correção",
      tom: "alerta",
    });
  });
});

describe("contarPosicoes", () => {
  it("reproduz o exemplo do mockup: 5 Células, 3 com Laudo ok, 1 em revisão, 1 bloqueada, 1 aprovada por você", () => {
    const posicoes = [
      posicao({ audiencia: "iniciante", formato: "texto_analitico", decisao: "aprovada" }),
      posicao({ audiencia: "iniciante", formato: "carrossel" }),
      posicao({
        audiencia: "intermediario",
        formato: "texto_analitico",
        destino: "reprovado_revisao_humana",
      }),
      posicao({ audiencia: "intermediario", formato: "roteiro" }),
      posicao({
        audiencia: "avancado",
        formato: "carrossel",
        destino: "reprovado_revisao_humana",
        bloqueada: true,
      }),
    ];

    expect(contarPosicoes(posicoes)).toEqual({
      total: 5,
      laudoOk: 3,
      emRevisao: 1,
      bloqueadas: 1,
      aprovadasPorVoce: 1,
      aguardando: 3,
    });
  });

  it("lista vazia zera tudo", () => {
    expect(contarPosicoes([])).toEqual({
      total: 0,
      laudoOk: 0,
      emRevisao: 0,
      bloqueadas: 0,
      aprovadasPorVoce: 0,
      aguardando: 0,
    });
  });
});

describe("saídas: contagem, filtro e ordem", () => {
  const saidas = [
    {
      nome: "Copom 280 · pauta juros",
      identificador: "copom-280-gemini-20261009",
      ata: "copom-280-2026-08-05",
      status: "aguardando_revisao",
      iniciada_em: "2026-10-09T14:32:00Z",
    },
    {
      nome: "Empresa Exemplo · aquisição",
      identificador: "cvm-001",
      ata: "fato-relevante-001",
      status: "concluida",
      iniciada_em: "2026-10-08T10:05:00Z",
    },
    {
      nome: "Demo Copom 280 · Matriz completa",
      identificador: "demo-copom-280",
      ata: "copom-280-2026-08-05",
      status: "aguardando_revisao",
      iniciada_em: "2026-09-18T12:51:00Z",
    },
  ];

  it("conta as Saídas aguardando revisão", () => {
    expect(contarAguardando(saidas)).toBe(2);
  });

  it("filtra por status", () => {
    const resultado = filtrarSaidas(saidas, { busca: "", status: "concluida" });
    expect(resultado.map((s) => s.identificador)).toEqual(["cvm-001"]);
  });

  it("busca sem diferenciar acento nem caixa, no nome, no identificador e na Ata", () => {
    expect(filtrarSaidas(saidas, { busca: "AQUISICAO", status: "todas" })).toHaveLength(1);
    expect(filtrarSaidas(saidas, { busca: "demo-copom", status: "todas" })).toHaveLength(1);
    expect(filtrarSaidas(saidas, { busca: "copom-280-2026", status: "todas" })).toHaveLength(2);
  });

  it("busca e status se combinam", () => {
    const resultado = filtrarSaidas(saidas, { busca: "copom", status: "aguardando_revisao" });
    expect(resultado).toHaveLength(2);
    expect(filtrarSaidas(saidas, { busca: "copom", status: "concluida" })).toHaveLength(0);
  });

  it("normalizarBusca tira acento e espaços nas pontas", () => {
    expect(normalizarBusca("  Aquisição  ")).toBe("aquisicao");
  });

  it("ordena da mais recente para a mais antiga sem mudar o original", () => {
    const ordenadas = maisRecentesPrimeiro([saidas[2], saidas[1], saidas[0]]);
    expect(ordenadas.map((s) => s.identificador)).toEqual([
      "copom-280-gemini-20261009",
      "cvm-001",
      "demo-copom-280",
    ]);
  });
});

describe("larguraDaBarra", () => {
  it("Flesch-BR já está em 0 a 100", () => {
    expect(larguraDaBarra({ metrica: "flesch_br", valor: 89.15 })).toBeCloseTo(89.15);
  });

  it("as demais métricas estão em 0 a 1", () => {
    expect(larguraDaBarra({ metrica: "densidade", valor: 0.0288 })).toBeCloseTo(2.88);
    expect(larguraDaBarra({ metrica: "aderencia", valor: 1 })).toBe(100);
  });

  it("valor ausente fica em zero e nunca passa de 0 a 100", () => {
    expect(larguraDaBarra({ metrica: "aderencia", valor: null })).toBe(0);
    expect(larguraDaBarra({ metrica: "aderencia" })).toBe(0);
    expect(larguraDaBarra({ metrica: "flesch_br", valor: 150 })).toBe(100);
    expect(larguraDaBarra({ metrica: "flesch_br", valor: -10 })).toBe(0);
  });
});

describe("celulaBloqueada", () => {
  it("só Recomendação no Laudo bloqueia", () => {
    expect(celulaBloqueada({ motivos: ["recomendacao"] })).toBe(true);
    expect(celulaBloqueada({ motivos: ["flesch_br"] })).toBe(false);
    expect(celulaBloqueada({ motivos: [] })).toBe(false);
    expect(celulaBloqueada(null)).toBe(false);
    expect(celulaBloqueada(undefined)).toBe(false);
  });
});

describe("vizinhas e chaveDaPosicao", () => {
  const pedidas = [
    { audiencia: "iniciante", formato: "texto_analitico" },
    { audiencia: "iniciante", formato: "carrossel" },
    { audiencia: "avancado", formato: "roteiro" },
  ];

  it("acha a anterior e a próxima na ordem pedida", () => {
    const resultado = vizinhas(pedidas, "iniciante", "carrossel");
    expect(resultado.anterior).toEqual(pedidas[0]);
    expect(resultado.proxima).toEqual(pedidas[2]);
  });

  it("a primeira não tem anterior e a última não tem próxima", () => {
    expect(vizinhas(pedidas, "iniciante", "texto_analitico").anterior).toBeNull();
    expect(vizinhas(pedidas, "avancado", "roteiro").proxima).toBeNull();
  });

  it("posição que não foi pedida não tem vizinhas", () => {
    expect(vizinhas(pedidas, "avancado", "texto_analitico")).toEqual({
      anterior: null,
      proxima: null,
    });
  });

  it("a chave junta Audiência e Formato", () => {
    expect(chaveDaPosicao("iniciante", "carrossel")).toBe("iniciante:carrossel");
  });
});
