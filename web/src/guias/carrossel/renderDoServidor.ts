// O carrossel com o design de uma família visual só existe no render do servidor (Puppeteer): o
// editor do navegador desenha apenas as seis composições antigas. Aqui a guia pede a montagem do
// Pacote com a referência escolhida, espera terminar e devolve as URLs dos quadros prontos.
import {
  listarPacotes,
  montarPacotes,
  obterMontagem,
  urlDoArquivo,
  type Audiencia,
  type EstadoDaMontagem,
  type PacotePublicacao,
} from "../../dados/cliente";

export interface Dependencias {
  montar: (execucaoId: string, audiencia: Audiencia, referencia: string, paleta?: string) => Promise<EstadoDaMontagem>;
  estado: (execucaoId: string) => Promise<EstadoDaMontagem>;
  pacotes: (execucaoId: string) => Promise<PacotePublicacao[]>;
  esperar: (ms: number) => Promise<void>;
  agora: () => number;
}

export const INTERVALO_MS = 1500;
export const LIMITE_MS = 240_000;

const reais: Dependencias = {
  montar: (id, audiencia, referencia, paleta) => montarPacotes(id, audiencia, "carrossel", referencia, paleta),
  estado: obterMontagem,
  pacotes: listarPacotes,
  esperar: (ms) => new Promise((resolver) => window.setTimeout(resolver, ms)),
  agora: () => Date.now(),
};

/** As URLs dos quadros, na ordem; `versao` evita que o navegador mostre o render anterior. */
export function urlsDosQuadros(execucaoId: string, pacote: PacotePublicacao, versao: number): string[] {
  return [...(pacote.imagens ?? [])]
    .sort((a, b) => a.indice - b.indice)
    .map((imagem) => `${urlDoArquivo(execucaoId, imagem.caminho)}?v=${versao}`);
}

export async function montarNoServidor(
  execucaoId: string,
  audiencia: Audiencia,
  referenciaId: string,
  paleta?: string,
  dependencias: Dependencias = reais,
): Promise<string[]> {
  const { montar, estado, pacotes, esperar, agora } = dependencias;
  const inicio = agora();
  let atual = await montar(execucaoId, audiencia, referenciaId, paleta);
  while (atual.estado === "rodando") {
    if (agora() - inicio > LIMITE_MS) throw new Error("A montagem demorou demais. Tente de novo.");
    await esperar(INTERVALO_MS);
    atual = await estado(execucaoId);
  }
  if (atual.estado === "erro") throw new Error(atual.mensagem || "Não consegui montar o carrossel no servidor.");
  const doCarrossel = (await pacotes(execucaoId)).find((p) => p.audiencia === audiencia && p.formato === "carrossel");
  if (!doCarrossel || (doCarrossel.imagens ?? []).length === 0) {
    throw new Error("O servidor não devolveu os quadros deste carrossel.");
  }
  return urlsDosQuadros(execucaoId, doCarrossel, agora());
}
