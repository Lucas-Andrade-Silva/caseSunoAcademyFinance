import { describe, expect, it } from "vitest";
import type { BlocoFala, Laudo } from "../../dados/cliente";
import type { BarraDoLaudo } from "../../nucleo/laudo";
import { montarPrompt } from "./instrucao";
import { rotuloDosJeitos } from "./jeitos";
import { lerDadosDoVideo, type DadosDoVideo } from "./salvo";

const BLOCO: BlocoFala = {
  inicio_s: 0,
  fim_s: 6,
  fala: "O juro caiu.",
  tela: "O JURO CAIU",
  cena: "gancho",
  icone: "juros",
  entrada: "corte",
  texto_anima: "digitar",
  texto_entra_em_s: 0,
  efeito: "nenhum",
};

const BARRA: BarraDoLaudo = {
  metrica: "flesch_br",
  rotulo: "Flesch-BR",
  largura: 61,
  marcas: [50, 80],
  valor: "61",
  faixa: "50–80",
  atingiu: true,
};

function dados(parcial: Partial<DadosDoVideo> = {}): DadosDoVideo {
  return { blocos: [BLOCO], clima: "serio", ritmo: "devagar", instrucao: "o prompt", barras: [BARRA], laudo: null, ...parcial };
}

const LAUDO: Laudo = {
  audiencia: "iniciante",
  formato: "roteiro",
  destino: "aprovado",
  medidas: [],
  motivos: [],
};
const TEXTO_AVALIADO = '[{"fala":"O juro caiu.","tela":"O JURO CAIU"}]';

describe("lerDadosDoVideo", () => {
  it("devolve o que foi guardado, depois de passar pelo JSON do navegador", () => {
    const guardado = JSON.parse(JSON.stringify(dados()));
    expect(lerDadosDoVideo(guardado)).toEqual(dados());
  });

  it("recusa o que não é um roteiro", () => {
    expect(lerDadosDoVideo(null)).toBeNull();
    expect(lerDadosDoVideo("texto")).toBeNull();
    expect(lerDadosDoVideo([])).toBeNull();
    expect(lerDadosDoVideo({})).toBeNull();
    expect(lerDadosDoVideo({ blocos: [] })).toBeNull();
    expect(lerDadosDoVideo({ blocos: [{ fala: "sem tempo" }] })).toBeNull();
  });

  it("ignora os blocos inválidos e guarda os bons", () => {
    const lido = lerDadosDoVideo({ ...dados(), blocos: [BLOCO, null, { inicio_s: 1 }] });
    expect(lido?.blocos).toHaveLength(1);
  });

  it("completa a Direção de cena de um bloco antigo, que só tinha fala e tela", () => {
    const antigo = { inicio_s: 0, fim_s: 5, fala: "Oi.", tela: "Oi" };
    const lido = lerDadosDoVideo({ blocos: [antigo] });
    expect(lido?.blocos[0]).toMatchObject({
      cena: "texto_destaque",
      icone: null,
      entrada: "corte",
      texto_anima: "fade",
      texto_entra_em_s: 0,
      efeito: "nenhum",
    });
  });

  it("um jeito desconhecido vira nenhum, sem perder o resto", () => {
    const lido = lerDadosDoVideo({ ...dados(), clima: "furioso", ritmo: 3 });
    expect(lido).not.toBeNull();
    expect(lido?.clima).toBeNull();
    expect(lido?.ritmo).toBeNull();
  });

  it("sem o prompt guardado, monta de novo a partir do roteiro e dos jeitos", () => {
    const lido = lerDadosDoVideo({ ...dados(), instrucao: undefined });
    expect(lido?.instrucao).toBe(montarPrompt({ blocos: [BLOCO], clima: "serio", ritmo: "devagar" }));
  });

  it("barras malformadas somem; as boas ficam", () => {
    const lido = lerDadosDoVideo({ ...dados(), barras: [BARRA, { rotulo: "sem escala" }, 7] });
    expect(lido?.barras).toEqual([BARRA]);
    expect(lerDadosDoVideo({ ...dados(), barras: "nada" })?.barras).toEqual([]);
  });

  it("preserva o Laudo quando o texto avaliado corresponde ao salvo", () => {
    const guardado = JSON.parse(JSON.stringify(dados({ laudo: LAUDO, textoAvaliado: TEXTO_AVALIADO })));
    expect(lerDadosDoVideo(guardado)?.laudo).toEqual(LAUDO);
  });

  it("um salvo legado sem texto avaliado continua legível, mas sem aprovação", () => {
    const lido = lerDadosDoVideo(dados({ laudo: LAUDO }));
    expect(lido?.blocos).toEqual([BLOCO]);
    expect(lido?.laudo).toBeNull();
  });

  it.each(["fala", "tela"] as const)("alterar %s invalida o Laudo guardado", (campo) => {
    const lido = lerDadosDoVideo(dados({
      laudo: LAUDO,
      textoAvaliado: TEXTO_AVALIADO,
      blocos: [{ ...BLOCO, [campo]: "Compre ações agora." }],
    }));
    expect(lido?.blocos[0][campo]).toBe("Compre ações agora.");
    expect(lido?.laudo).toBeNull();
  });

  it("uma assinatura diferente não empresta aprovação ao mesmo roteiro", () => {
    expect(lerDadosDoVideo(dados({ laudo: LAUDO, textoAvaliado: `${TEXTO_AVALIADO} ` }))?.laudo).toBeNull();
  });

  it("não empresta o Laudo de outra audiência ao roteiro salvo", () => {
    expect(lerDadosDoVideo(dados({ laudo: LAUDO, textoAvaliado: TEXTO_AVALIADO }), "avancado")?.laudo).toBeNull();
  });

  it.each(["reprovado_corrigivel", "reprovado_revisao_humana"] as const)(
    "preserva o destino %s ao reabrir a versão avaliada",
    (destino) => {
      const reprovado: Laudo = { ...LAUDO, destino, motivos: ["recomendacao"] };
      const lido = lerDadosDoVideo(dados({ laudo: reprovado, textoAvaliado: TEXTO_AVALIADO }));
      expect(lido?.laudo).toEqual(reprovado);
      expect(lido?.laudo?.destino).not.toBe("aprovado");
    },
  );
});

describe("rotuloDosJeitos", () => {
  it("junta o clima e o ritmo escolhidos", () => {
    expect(rotuloDosJeitos("descontraido", "rapido")).toBe("Descontraído · Rápido");
    expect(rotuloDosJeitos("engracado", null)).toBe("Engraçado");
    expect(rotuloDosJeitos(null, "devagar")).toBe("Devagar");
  });

  it("fica vazio quando nada foi escolhido", () => {
    expect(rotuloDosJeitos(null, null)).toBe("");
  });
});
