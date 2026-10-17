import { describe, expect, it } from "vitest";
import type { Laudo } from "../../dados/cliente";
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

const LAUDO: Laudo = {
  audiencia: "iniciante",
  formato: "carrossel",
  destino: "aprovado",
  medidas: [],
  motivos: [],
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

  it("preserva o Laudo quando o texto avaliado corresponde aos slides salvos", () => {
    const guardado = JSON.parse(JSON.stringify(dadosParaSalvar(montagem, LAUDO)));
    expect(guardado.textoAvaliado).toBe('[{"titulo":"Capa","corpo":"Texto."},{"titulo":"Selic","corpo":"Texto."}]');
    expect(lerDadosSalvos(guardado)?.laudo).toEqual(LAUDO);
  });

  it("um salvo legado sem texto avaliado continua legível, mas sem aprovação", () => {
    const { textoAvaliado: _fora, ...legado } = dadosParaSalvar(montagem, LAUDO);
    const lido = lerDadosSalvos(legado);
    expect(lido?.slides).toEqual(montagem.slides);
    expect(lido?.laudo).toBeNull();
  });

  it.each(["titulo", "corpo"] as const)("alterar %s invalida o Laudo guardado", (campo) => {
    const guardado = dadosParaSalvar(montagem, LAUDO);
    const lido = lerDadosSalvos({
      ...guardado,
      slides: guardado.slides.map((slide, indice) => indice === 0 ? { ...slide, [campo]: "Compre ações agora." } : slide),
    });
    expect(lido?.slides[0][campo]).toBe("Compre ações agora.");
    expect(lido?.laudo).toBeNull();
  });

  it("uma assinatura diferente não empresta aprovação aos mesmos slides", () => {
    const guardado = dadosParaSalvar(montagem, LAUDO);
    expect(lerDadosSalvos({ ...guardado, textoAvaliado: `${guardado.textoAvaliado} ` })?.laudo).toBeNull();
  });

  it.each(["reprovado_corrigivel", "reprovado_revisao_humana"] as const)(
    "preserva o destino %s ao reabrir a versão avaliada",
    (destino) => {
      const reprovado: Laudo = { ...LAUDO, destino, motivos: ["recomendacao"] };
      const lido = lerDadosSalvos(dadosParaSalvar(montagem, reprovado));
      expect(lido?.laudo).toEqual(reprovado);
      expect(lido?.laudo?.destino).not.toBe("aprovado");
    },
  );
});
