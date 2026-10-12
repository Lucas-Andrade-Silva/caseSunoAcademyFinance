// O cliente TypeScript da API, tipado pelo OpenAPI gerado em `schema.d.ts` (ADR 0005).
// Nunca editado à mão: `scripts/gerar-cliente.{ps1,sh}` regenera `schema.d.ts` a partir de
// `web/openapi.json`, que por sua vez sai de `python -m suno.api.openapi`. Divergência entre
// cliente e servidor vira erro de tipo aqui, não bug descoberto em produção.

import createClient from "openapi-fetch";
import type { paths } from "./schema";

/** Constrói o cliente tipado. `baseUrl` vazio usa a mesma origem da SPA (produção). */
export function criarCliente(baseUrl: string = "") {
  return createClient<paths>({ baseUrl });
}
