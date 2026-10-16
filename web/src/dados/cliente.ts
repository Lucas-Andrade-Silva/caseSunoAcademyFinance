// Camada de acesso à API. Fina de propósito: todo `fetch` da SPA passa por aqui, sobre
// `criarCliente()` de `web/src/api/cliente.ts` (do Agente 11, gerado do OpenAPI — ADR 0005).
// Componentes e páginas nunca importam `../api/*` diretamente; se o schema mudar, só este
// arquivo precisa mudar.

import { criarCliente } from "../api/cliente";
import type { components } from "../api/schema";

const api = criarCliente();

export type Audiencia = components["schemas"]["Audiencia"];
export type Formato = components["schemas"]["Formato"];
export type Ata = components["schemas"]["Ata"];
export type Execucao = components["schemas"]["Execucao"];
export type ExecucaoResumo = components["schemas"]["ExecucaoResumo"];
export type AncoraNumerica = components["schemas"]["AncoraNumerica"];
export type Conteudo = components["schemas"]["Conteudo"];
export type BlocoFala = components["schemas"]["BlocoFala"];
export type Laudo = components["schemas"]["Laudo"];
export type Medida = components["schemas"]["Medida"];
export type Metrica = components["schemas"]["Metrica"];
export type Destino = components["schemas"]["Destino"];
export type MotivoReprovacao = components["schemas"]["MotivoReprovacao"];
export type Faixa = components["schemas"]["Faixa"];
export type PacotePublicacao = components["schemas"]["PacotePublicacao"];
type Saude = components["schemas"]["Saude"];
export type ConfiguracoesComEstado = components["schemas"]["ConfiguracoesComEstado"];
export type ConfiguracoesDoSistema = components["schemas"]["ConfiguracoesDoSistema"];
export type PosicaoResumo = components["schemas"]["PosicaoResumo"];
export type DecisaoHumana = components["schemas"]["DecisaoHumana"];
type EstadoDecisao = components["schemas"]["EstadoDecisao"];
export type FormatoExportacao = components["schemas"]["FormatoExportacao"];
export type Andamento = components["schemas"]["Andamento"];
export type AndamentoDaCelula = components["schemas"]["AndamentoDaCelula"];
export type ModoDeGeracao = components["schemas"]["ModoDeGeracao"];
export type NovaSaida = components["schemas"]["NovaSaida"];
type Origem = components["schemas"]["Origem"];
export type OrigemComAtas = components["schemas"]["OrigemComAtas"];
type ListaDeOrigens = components["schemas"]["ListaDeOrigens"];
export type ResumoDaAta = components["schemas"]["ResumoDaAta"];
export type Sugestao = components["schemas"]["Sugestao"];
type Sugestoes = components["schemas"]["Sugestoes"];
export type EstadoDaAtualizacao = components["schemas"]["EstadoDaAtualizacao"];
export type Disponivel = components["schemas"]["Disponivel"];
export type EstadoDaMontagem = components["schemas"]["EstadoDaMontagem"];
export type ComposicaoCarrossel = components["schemas"]["ComposicaoCarrossel"];
export type FamiliaVisual = components["schemas"]["FamiliaVisual"];
export type PapeisDaFamilia = components["schemas"]["PapeisDaFamilia"];
export type Slide = components["schemas"]["Slide"];

export type DuracaoDoVideo = components["schemas"]["DuracaoDoVideo"];
export type PlanoDeEdicao = components["schemas"]["PlanoDeEdicao"];
export type ReferenciaVisual = components["schemas"]["ReferenciaVisual"];
type NovaReferenciaVisual = components["schemas"]["NovaReferenciaVisual"];
type PerfilDeReferencia = components["schemas"]["PerfilDeReferencia"];
type ResultadoDaColeta = components["schemas"]["ResultadoDaColeta"];
export type SetorDaReferencia = components["schemas"]["SetorDaReferencia"];
type DescobertaDeReferencias = components["schemas"]["DescobertaDeReferencias"];

export const AUDIENCIAS: readonly Audiencia[] = [
  "iniciante",
  "intermediario",
  "avancado",
];
export const FORMATOS: readonly Formato[] = [
  "texto_analitico",
  "carrossel",
  "roteiro",
];

export class ErroApi extends Error {
  constructor(
    public readonly status: number,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

/**
 * A frase de uma falha para a tela. `fetch` levanta `TypeError` ("Failed to fetch") quando o servidor
 * não responde: em português e com o que fazer, em vez da mensagem do navegador.
 */
export function mensagemDeFalha(falha: unknown): string {
  if (falha instanceof TypeError) {
    return "Sem conexão com o servidor. Confira se ele está rodando e tente de novo.";
  }
  return falha instanceof Error ? falha.message : String(falha);
}

/** openapi-fetch devolve `{data, error, response}`; aqui vira valor ou `ErroApi`. */
async function extrair<T>(
  promessa: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const resultado = await promessa;
  if (resultado.data !== undefined) {
    return resultado.data;
  }
  throw new ErroApi(
    resultado.response.status,
    detalheDoErro(resultado.error, resultado.response.statusText),
  );
}

/** O FastAPI responde `{"detail": "..."}`: a tela mostra a frase, não o JSON. */
function detalheDoErro(erro: unknown, alternativa: string): string {
  if (erro && typeof erro === "object" && "detail" in erro) {
    const detalhe = (erro as { detail: unknown }).detail;
    if (typeof detalhe === "string") return detalhe;
  }
  return erro === undefined || erro === null
    ? alternativa
    : JSON.stringify(erro);
}

export function obterAta(identificador: string): Promise<Ata> {
  return extrair(
    api.GET("/api/atas/{identificador}", {
      params: { path: { identificador } },
    }),
  );
}

export function listarExecucoes(): Promise<ExecucaoResumo[]> {
  return extrair(api.GET("/api/execucoes", {}));
}

export function obterExecucao(identificador: string): Promise<Execucao> {
  return extrair(
    api.GET("/api/execucoes/{identificador}", {
      params: { path: { identificador } },
    }),
  );
}

export function obterAncorasDaCelula(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
): Promise<AncoraNumerica[]> {
  return extrair(
    api.GET(
      "/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/ancoras",
      {
        params: { path: { identificador, audiencia, formato } },
      },
    ),
  );
}

/** O plano de edição do Roteiro aprovado: JSON para avatar sintético e a tabela legível. */
export function obterPlanoDeEdicao(
  identificador: string,
  audiencia: Audiencia,
): Promise<PlanoDeEdicao> {
  return extrair(
    api.GET(
      "/api/execucoes/{identificador}/celulas/{audiencia}/roteiro/plano",
      {
        params: { path: { identificador, audiencia } },
      },
    ),
  );
}

export function listarPacotes(
  identificador: string,
): Promise<PacotePublicacao[]> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/pacotes", {
      params: { path: { identificador } },
    }),
  );
}

export function aprovarPacote(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
  feedback?: { revisor?: string; observacao?: string },
): Promise<PacotePublicacao> {
  return extrair(
    api.POST(
      "/api/execucoes/{identificador}/pacotes/{audiencia}/{formato}/aprovar",
      {
        params: { path: { identificador, audiencia, formato } },
        body: feedback,
      },
    ),
  );
}

export function obterConfiguracoesDoSistema(): Promise<ConfiguracoesComEstado> {
  return extrair(api.GET("/api/configuracoes", {}));
}

export function salvarConfiguracoesDoSistema(
  configuracoes: ConfiguracoesDoSistema,
): Promise<ConfiguracoesComEstado> {
  return extrair(api.PUT("/api/configuracoes", { body: configuracoes }));
}

export function restaurarConfiguracoesDoSistema(): Promise<ConfiguracoesComEstado> {
  return extrair(api.DELETE("/api/configuracoes", {}));
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
export function urlDoArquivo(
  identificador: string,
  caminhoArmazenado: string,
): string {
  const normalizado = caminhoArmazenado.replaceAll("\\", "/");
  const prefixo = `data/execucoes/${identificador}/`;
  const posicao = normalizado.indexOf(prefixo);
  const relativo =
    posicao === -1 ? normalizado : normalizado.slice(posicao + prefixo.length);
  return `/api/execucoes/${encodeURIComponent(identificador)}/arquivos/${relativo}`;
}

export function obterResumo(identificador: string): Promise<ExecucaoResumo> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/resumo", {
      params: { path: { identificador } },
    }),
  );
}

export function renomearExecucao(
  identificador: string,
  nome: string,
): Promise<ExecucaoResumo> {
  return extrair(
    api.PATCH("/api/execucoes/{identificador}", {
      params: { path: { identificador } },
      body: { nome },
    }),
  );
}

export async function excluirExecucao(identificador: string): Promise<void> {
  const { error, response } = await api.DELETE(
    "/api/execucoes/{identificador}",
    {
      params: { path: { identificador } },
    },
  );
  if (!response.ok)
    throw new ErroApi(
      response.status,
      detalheDoErro(error, response.statusText),
    );
}

export function registrarDecisao(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
  corpo: {
    estado: EstadoDecisao;
    motivo: string | null;
    revisor: string | null;
  },
): Promise<DecisaoHumana> {
  return extrair(
    api.POST(
      "/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/decisao",
      {
        params: { path: { identificador, audiencia, formato } },
        body: corpo,
      },
    ),
  );
}

/** O texto que a pessoa corrigiu, na ordem da Célula: só o campo do Formato dela vale. */
export type EdicaoDeTexto = components["schemas"]["EdicaoDeTexto"];

/**
 * Grava o texto corrigido na Célula e o julga de novo no servidor (sem LLM). Devolve o Laudo novo,
 * que o Pacote e o render passam a usar junto com o texto editado.
 */
export async function editarTextoDaCelula(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
  corpo: EdicaoDeTexto,
): Promise<Laudo> {
  const historico = await extrair(
    api.PUT("/api/execucoes/{identificador}/celulas/{audiencia}/{formato}/texto", {
      params: { path: { identificador, audiencia, formato } },
      body: corpo,
    }),
  );
  const laudo = historico.tentativas?.at(-1)?.laudo;
  if (!laudo) throw new ErroApi(502, "O servidor não devolveu o Laudo.");
  return laudo;
}

/** Inicia a geração em segundo plano. Responde na hora com o andamento (202). */
export function criarSaida(corpo: NovaSaida): Promise<Andamento> {
  return extrair(api.POST("/api/execucoes", { body: corpo }));
}

export function obterAndamento(identificador: string): Promise<Andamento> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/andamento", {
      params: { path: { identificador } },
    }),
  );
}

/** Monta os Pacotes das Células aprovadas, em segundo plano. */
/** `referenciaVisual` troca o design da Saída antes de montar (a família do exemplo escolhido). */
export function montarPacotes(
  identificador: string,
  audiencia?: Audiencia,
  formato?: Formato,
  referenciaVisual?: string,
  paleta?: string,
): Promise<EstadoDaMontagem> {
  return extrair(
    api.POST("/api/execucoes/{identificador}/pacotes/montar", {
      params: {
        path: { identificador },
        query: { audiencia, formato, referencia_visual: referenciaVisual, paleta },
      },
    }),
  );
}

export function obterMontagem(
  identificador: string,
): Promise<EstadoDaMontagem> {
  return extrair(
    api.GET("/api/execucoes/{identificador}/pacotes/montagem", {
      params: { path: { identificador } },
    }),
  );
}

/** As Origens (a "Fonte", na tela) com as Atas que cada uma tem em disco. */
export function listarOrigens(): Promise<ListaDeOrigens> {
  return extrair(api.GET("/api/fontes", {}));
}

export function alterarOrigem(
  identificador: string,
  ativa: boolean,
): Promise<Origem> {
  return extrair(
    api.PATCH("/api/fontes/{identificador}", {
      params: { path: { identificador } },
      body: { ativa },
    }),
  );
}

/** Busca nas Origens ligadas, em segundo plano. Responde na hora com o estado. */
export function atualizarFontes(): Promise<EstadoDaAtualizacao> {
  return extrair(api.POST("/api/fontes/atualizar", {}));
}

export function obterAtualizacao(): Promise<EstadoDaAtualizacao> {
  return extrair(api.GET("/api/fontes/atualizacao", {}));
}

/** Baixa o que a consulta achou no período (datas "AAAA-MM-DD", incluídas). */
export function baixarPeriodo(de: string, ate: string): Promise<EstadoDaAtualizacao> {
  return extrair(api.POST("/api/fontes/atualizar/baixar", { body: { de, ate } }));
}

/** Descarta a consulta que espera o período. */
export function cancelarAtualizacao(): Promise<EstadoDaAtualizacao> {
  return extrair(api.POST("/api/fontes/atualizar/cancelar", {}));
}

export function obterSugestoes(): Promise<Sugestoes> {
  return extrair(api.GET("/api/curadoria/sugestoes", {}));
}

/** Padrões visuais curados no SQLite e usados pela direção de arte. */
export function listarReferenciasVisuais(): Promise<ReferenciaVisual[]> {
  return extrair(api.GET("/api/referencias-visuais", {}));
}

export function listarFamiliasVisuais(): Promise<PapeisDaFamilia[]> {
  return extrair(api.GET("/api/familias-visuais", {}));
}

export function importarReferenciaVisual(
  corpo: NovaReferenciaVisual,
): Promise<ReferenciaVisual> {
  return extrair(api.POST("/api/referencias-visuais", { body: corpo }));
}

export function alterarAprovacaoDaReferencia(
  identificador: string,
  aprovada: boolean,
): Promise<ReferenciaVisual> {
  return extrair(
    api.PATCH("/api/referencias-visuais/{identificador}", {
      params: { path: { identificador } },
      body: { aprovada },
    }),
  );
}

export async function analisarImagemDaReferencia(
  identificador: string,
  arquivo: File,
): Promise<ReferenciaVisual> {
  const resposta = await fetch(
    `/api/referencias-visuais/${encodeURIComponent(identificador)}/imagem`,
    {
      method: "POST",
      headers: { "content-type": arquivo.type || "application/octet-stream" },
      body: arquivo,
    },
  );
  const corpo: unknown = await resposta.json().catch(() => undefined);
  if (!resposta.ok) {
    throw new ErroApi(
      resposta.status,
      detalheDoErro(corpo, resposta.statusText),
    );
  }
  return corpo as ReferenciaVisual;
}

/** `paleta` na forma da rota (`fundo,texto,destaque,apoio`); sem ela, as cores do post. */
function comPaleta(url: string, paleta: string | undefined): string {
  return paleta ? `${url}?paleta=${encodeURIComponent(paleta)}` : url;
}

/** O Layout da referência com o texto de exemplo, recolorido, em HTML. */
export function urlDaPreviaDaReferencia(identificador: string, paleta?: string): string {
  return comPaleta(`/api/referencias-visuais/${encodeURIComponent(identificador)}/previa`, paleta);
}

/** Um slide do carrossel já montado, recolorido com `paleta`, em HTML. `slide` começa em 1. */
export function urlDaPreviaDoSlide(
  identificador: string,
  audiencia: Audiencia,
  slide: number,
  paleta?: string,
): string {
  return comPaleta(
    `/api/execucoes/${encodeURIComponent(identificador)}/pacotes/${audiencia}/carrossel/${slide}/previa`,
    paleta,
  );
}

export function urlDaImagemDaReferencia(
  identificador: string,
  versao = 0,
): string {
  return `/api/referencias-visuais/${encodeURIComponent(identificador)}/imagem?v=${versao}`;
}

export function listarPerfisDeReferencia(): Promise<PerfilDeReferencia[]> {
  return extrair(api.GET("/api/referencias-visuais/coleta/perfis", {}));
}

export function adicionarPerfilDeReferencia(
  usuario: string,
): Promise<PerfilDeReferencia> {
  return extrair(
    api.POST("/api/referencias-visuais/coleta/perfis", {
      body: { usuario },
    }),
  );
}

export function descobrirReferencias(
  janelaDias: number,
  setor: SetorDaReferencia | null,
): Promise<DescobertaDeReferencias> {
  return extrair(
    api.GET("/api/referencias-visuais/descoberta", {
      params: {
        query: {
          janela_dias: janelaDias,
          ...(setor ? { setor } : {}),
        },
      },
    }),
  );
}

export function coletarReferencias(
  janelaDias: number,
): Promise<ResultadoDaColeta> {
  return extrair(
    api.POST("/api/referencias-visuais/coleta/executar", {
      body: { janela_dias: janelaDias },
    }),
  );
}

/**
 * Importa um PDF ou um texto. A rota recebe o arquivo cru no corpo (sem multipart) e o título e a
 * data na query, por isso aqui é `fetch` direto e não o cliente tipado.
 */
export async function importarComunicado(
  arquivo: File,
  titulo: string,
  dataReferencia: string | null,
): Promise<ResumoDaAta> {
  const consulta = new URLSearchParams({ titulo });
  if (dataReferencia) consulta.set("data_referencia", dataReferencia);
  const resposta = await fetch(`/api/fontes/importar?${consulta.toString()}`, {
    method: "POST",
    headers: { "content-type": arquivo.type || "application/octet-stream" },
    body: arquivo,
  });
  const corpo: unknown = await resposta.json().catch(() => undefined);
  if (!resposta.ok) {
    throw new ErroApi(
      resposta.status,
      detalheDoErro(corpo, resposta.statusText),
    );
  }
  return corpo as ResumoDaAta;
}

/** Endereço do download; o navegador baixa direto, sem passar pelo cliente tipado. */
export function urlDeExportacao(
  identificador: string,
  formato: FormatoExportacao,
): string {
  return `/api/execucoes/${encodeURIComponent(identificador)}/exportar?formato=${formato}`;
}

/** O .zip do Pacote (slides, legenda com hashtags e vídeo), para publicar à mão. */
export function urlDoZipDoPacote(
  identificador: string,
  audiencia: Audiencia,
  formato: Formato,
): string {
  return `/api/execucoes/${encodeURIComponent(identificador)}/pacotes/${audiencia}/${formato}/baixar`;
}
