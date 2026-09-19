// Camada de acesso à API. Fina de propósito: todo `fetch` da SPA passa por aqui, sobre
// `criarCliente()` de `web/src/api/cliente.ts` (do Agente 11, gerado do OpenAPI — ADR 0005).
// Componentes e páginas nunca importam `../api/*` diretamente; se o schema mudar, só este
// arquivo precisa mudar.

import { criarCliente } from "../api/cliente";
import type { components } from "../api/schema";

export const api = criarCliente();

export type Audiencia = components["schemas"]["Audiencia"];
export type Formato = components["schemas"]["Formato"];
export type Ata = components["schemas"]["Ata"];
export type AtaResumo = components["schemas"]["AtaResumo"];
export type Execucao = components["schemas"]["Execucao"];
export type ExecucaoResumo = components["schemas"]["ExecucaoResumo"];
export type Ancoras = components["schemas"]["Ancoras"];
export type AncoraNumerica = components["schemas"]["AncoraNumerica"];
export type AncoraTextual = components["schemas"]["AncoraTextual"];
export type HistoricoCelula = components["schemas"]["HistoricoCelula"];
export type Tentativa = components["schemas"]["Tentativa"];
export type Celula = components["schemas"]["Celula"];
export type Conteudo = components["schemas"]["Conteudo"];
export type Slide = components["schemas"]["Slide"];
export type BlocoFala = components["schemas"]["BlocoFala"];
export type Laudo = components["schemas"]["Laudo"];
export type Medida = components["schemas"]["Medida"];
export type Metrica = components["schemas"]["Metrica"];
export type EstadoMedida = components["schemas"]["EstadoMedida"];
export type Destino = components["schemas"]["Destino"];
export type MotivoReprovacao = components["schemas"]["MotivoReprovacao"];
export type Correcao = components["schemas"]["Correcao"];
export type Faixa = components["schemas"]["Faixa"];
export type Pendencia = components["schemas"]["Pendencia"];
export type Filas = components["schemas"]["Filas"];
export type PacotePublicacao = components["schemas"]["PacotePublicacao"];
export type ImagemSlide = components["schemas"]["ImagemSlide"];
export type ConferenciaVisual = components["schemas"]["ConferenciaVisual"];
export type MedicaoVisual = components["schemas"]["MedicaoVisual"];
export type ParecerVisao = components["schemas"]["ParecerVisao"];
export type Saude = components["schemas"]["Saude"];

export const AUDIENCIAS: readonly Audiencia[] = ["iniciante", "intermediario", "avancado"];
export const FORMATOS: readonly Formato[] = ["texto_analitico", "carrossel", "roteiro"];

export class ErroApi extends Error {
  constructor(
    public readonly status: number,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

/** openapi-fetch devolve `{data, error, response}`; aqui vira valor ou `ErroApi`. */
async function extrair<T>(
  promessa: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const resultado = await promessa;
  if (resultado.data !== undefined) {
    return resultado.data;
  }
  const detalhe =
    resultado.error !== undefined && resultado.error !== null
      ? JSON.stringify(resultado.error)
      : resultado.response.statusText;
  throw new ErroApi(resultado.response.status, detalhe);
}

export function listarAtas(): Promise<AtaResumo[]> {
  return extrair(api.GET("/api/atas", {}));
}

export function obterAta(identificador: string): Promise<Ata> {
  return extrair(api.GET("/api/atas/{identificador}", { params: { path: { identificador } } }));
}

export function listarExecucoes(): Promise<ExecucaoResumo[]> {
  return extrair(api.GET("/api/execucoes", {}));
}

export function obterExecucao(identificador: string): Promise<Execucao> {
  return extrair(
    api.GET("/api/execucoes/{identificador}", { params: { path: { identificador } } }),
  );
}

export function obterAncoras(identificador: string): Promise<Ancoras> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/ancoras", { params: { path: { identificador } } }),
  );
}

export function obterCelula(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
): Promise<HistoricoCelula> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}", {
      params: { path: { identificador, audiencia, formato } },
    }),
  );
}

export function obterAncorasDaCelula(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
): Promise<AncoraNumerica[]> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/ancoras", {
      params: { path: { identificador, audiencia, formato } },
    }),
  );
}

export function listarPacotes(identificador: string): Promise<PacotePublicacao[]> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/pacotes", { params: { path: { identificador } } }),
  );
}

export function obterFilas(identificador: string): Promise<Filas> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/filas", { params: { path: { identificador } } }),
  );
}

export function resolverH4(
  identificador: string,
  indice: number,
  decisao: string,
): Promise<Pendencia> {
  return extrair(
    api.POST("/api/execucoes/{identificador}/filas/h4/{indice}/resolver", {
      params: { path: { identificador, indice } },
      body: { decisao },
    }),
  );
}

export function aprovarPacote(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
): Promise<PacotePublicacao> {
  return extrair(
    api.POST("/api/execucoes/{identificador}/pacotes/{audiencia}/{formato}/aprovar", {
      params: { path: { identificador, audiencia, formato } },
    }),
  );
}

export function obterSaude(): Promise<Saude> {
  return extrair(api.GET("/api/saude", {}));
}

/**
 * `pacote.json` guarda o caminho como o `pathlib.Path` gravou em disco no servidor
 * (ex. `data\execucoes\demo-copom-280\pacote\avancado-carrossel\slide-01.png`), não o
 * `caminho` relativo que a rota `/arquivos/{caminho}` espera. Reduz para a parte depois
 * de `data/execucoes/<identificador>/` e troca `\` por `/` antes de montar a URL.
 */
export function urlDoArquivo(identificador: string, caminhoArmazenado: string): string {
  const normalizado = caminhoArmazenado.replaceAll("\\", "/");
  const prefixo = `data/execucoes/${identificador}/`;
  const posicao = normalizado.indexOf(prefixo);
  const relativo = posicao === -1 ? normalizado : normalizado.slice(posicao + prefixo.length);
  return `/api/execucoes/${encodeURIComponent(identificador)}/arquivos/${relativo}`;
}
