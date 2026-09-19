// Gancho (hook) genérico de carregando/erro/pronto para as páginas que leem da API.
import { useEffect, useState } from "react";

export type EstadoRequisicao<T> =
  | { situacao: "carregando" }
  | { situacao: "erro"; erro: Error }
  | { situacao: "pronto"; dados: T };

/** Chama `buscar()` de novo sempre que algum valor de `chaves` mudar. */
export function usarRequisicao<T>(
  buscar: () => Promise<T>,
  chaves: readonly unknown[],
): EstadoRequisicao<T> {
  const [estado, definirEstado] = useState<EstadoRequisicao<T>>({ situacao: "carregando" });

  useEffect(() => {
    let cancelado = false;
    definirEstado({ situacao: "carregando" });
    buscar()
      .then((dados) => {
        if (!cancelado) {
          definirEstado({ situacao: "pronto", dados });
        }
      })
      .catch((erro: unknown) => {
        if (!cancelado) {
          definirEstado({
            situacao: "erro",
            erro: erro instanceof Error ? erro : new Error(String(erro)),
          });
        }
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, chaves);

  return estado;
}
