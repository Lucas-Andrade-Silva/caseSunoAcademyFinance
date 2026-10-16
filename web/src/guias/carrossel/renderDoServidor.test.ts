import { describe, expect, it } from "vitest";
import type { EstadoDaMontagem, PacotePublicacao } from "../../dados/cliente";
import { LIMITE_MS, montarNoServidor, urlsDosQuadros, type Dependencias } from "./renderDoServidor";

const estado = (e: EstadoDaMontagem["estado"], mensagem = ""): EstadoDaMontagem => ({
  identificador: "x",
  estado: e,
  mensagem,
  total: 1,
});

function pacote(): PacotePublicacao {
  return {
    audiencia: "iniciante",
    formato: "carrossel",
    imagens: [
      { indice: 1, caminho: "data/execucoes/x/pacote/iniciante-carrossel/slide-02.png", largura: 1080, altura: 1350 },
      { indice: 0, caminho: "data/execucoes/x/pacote/iniciante-carrossel/slide-01.png", largura: 1080, altura: 1350 },
    ],
  } as PacotePublicacao;
}

function dependencias(estados: EstadoDaMontagem[], pacotes: PacotePublicacao[] = [pacote()]) {
  const chamadas: string[] = [];
  let tempo = 0;
  const fila = [...estados];
  const dep: Dependencias = {
    montar: async (_id, audiencia, referencia, paleta) => {
      chamadas.push(`montar:${audiencia}:${referencia}${paleta ? `:${paleta}` : ""}`);
      return fila.shift() ?? estado("ok");
    },
    estado: async () => fila.shift() ?? estado("ok"),
    pacotes: async () => pacotes,
    esperar: async (ms) => {
      tempo += ms;
    },
    agora: () => tempo,
  };
  return { dep, chamadas };
}

describe("montarNoServidor", () => {
  it("pede a montagem com a referência, espera terminar e devolve os quadros em ordem", async () => {
    const { dep, chamadas } = dependencias([estado("rodando"), estado("rodando"), estado("ok")]);
    const urls = await montarNoServidor("x", "iniciante", "noticia-foto", "#000000,#FFFFFF,#FF0000,#880000", dep);
    expect(chamadas).toEqual(["montar:iniciante:noticia-foto:#000000,#FFFFFF,#FF0000,#880000"]);
    expect(urls).toHaveLength(2);
    expect(urls[0]).toMatch(/\/arquivos\/pacote\/iniciante-carrossel\/slide-01\.png\?v=\d+$/);
    expect(urls[1]).toContain("slide-02.png");
  });

  it("erro de montagem vira exceção com a mensagem do servidor", async () => {
    const { dep } = dependencias([estado("erro", "o render falhou")]);
    await expect(montarNoServidor("x", "iniciante", "r", undefined, dep)).rejects.toThrow("o render falhou");
  });

  it("desiste depois do limite de tempo", async () => {
    const sempreRodando = Array.from({ length: Math.ceil(LIMITE_MS / 1500) + 5 }, () => estado("rodando"));
    const { dep } = dependencias(sempreRodando);
    await expect(montarNoServidor("x", "iniciante", "r", undefined, dep)).rejects.toThrow(/demorou/);
  });

  it("sem quadros no Pacote do carrossel, avisa", async () => {
    const { dep } = dependencias([estado("ok")], []);
    await expect(montarNoServidor("x", "iniciante", "r", undefined, dep)).rejects.toThrow(/não devolveu/);
  });
});

describe("urlsDosQuadros", () => {
  it("ordena pelo índice e acrescenta a versão", () => {
    const urls = urlsDosQuadros("x", pacote(), 7);
    expect(urls.map((u) => u.split("/").pop())).toEqual(["slide-01.png?v=7", "slide-02.png?v=7"]);
  });
});
