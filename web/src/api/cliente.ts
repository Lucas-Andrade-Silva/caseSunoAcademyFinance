// O cliente TypeScript da API, tipado pelo OpenAPI gerado em `schema.d.ts` (ADR 0005).
// Nunca editado à mão: `scripts/gerar-cliente.{ps1,sh}` regenera `schema.d.ts` a partir de
// `web/openapi.json`, que por sua vez sai de `python -m suno.api.openapi`. Divergência entre
// cliente e servidor vira erro de tipo aqui, não bug descoberto em produção.

import createClient from "openapi-fetch";
import type { paths, components } from "./schema";

/** Constrói o cliente tipado. `baseUrl` vazio usa a mesma origem da SPA (produção). */
export function criarCliente(baseUrl: string = "") {
  return createClient<paths>({ baseUrl });
}

export type Cliente = ReturnType<typeof criarCliente>;

// Tipos de conveniência, extraídos de `components["schemas"]` para quem só quer o formato
// de um recurso sem carregar o tipo de rota inteiro.
export type Execucao = components["schemas"]["Execucao"];
export type HistoricoCelula = components["schemas"]["HistoricoCelula"];
export type Laudo = components["schemas"]["Laudo"];
export type Pendencia = components["schemas"]["Pendencia"];
export type PacotePublicacao = components["schemas"]["PacotePublicacao"];
export type Ata = components["schemas"]["Ata"];
export type Ancoras = components["schemas"]["Ancoras"];
export type AncoraNumerica = components["schemas"]["AncoraNumerica"];
