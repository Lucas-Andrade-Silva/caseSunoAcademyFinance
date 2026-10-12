// Gancho (hook) genérico de carregando/erro/pronto para as páginas que leem da API.
import { useEffect, useState } from "react";
import { mensagemDeFalha } from "../dados/cliente";

export type EstadoRequisicao<T> =
  | { situacao: "carregando" }
  | { situacao: "erro"; erro: Error }
  | { situacao: "pronto"; dados: T };

interface OpcoesDeRequisicao<T> {
  /**
   * Intervalo (ms) de uma atualização silenciosa, calculado dos dados que já estão na tela, ou
   * `null` para não atualizar. Sem piscar "Carregando…"; se uma atualização falhar, a tela
   * mantém o que já tinha.
   */
  atualizarACada?: (dados: T) => number | null;
}

/** Chama `buscar()` de novo sempre que algum valor de `chaves` mudar. */
export function usarRequisicao<T>(
  buscar: () => Promise<T>,
  chaves: readonly unknown[],
  opcoes?: OpcoesDeRequisicao<T>,
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
            erro: new Error(mensagemDeFalha(erro)),
          });
        }
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, chaves);

  const intervalo =
    estado.situacao === "pronto" ? (opcoes?.atualizarACada?.(estado.dados) ?? null) : null;
  useEffect(() => {
    if (intervalo === null) return;
    let cancelado = false;
    const temporizador = window.setInterval(() => {
      buscar()
        .then((dados) => {
          if (!cancelado) definirEstado({ situacao: "pronto", dados });
        })
        .catch(() => {
          /* mantém o que já está na tela */
        });
    }, intervalo);
    return () => {
      cancelado = true;
      window.clearInterval(temporizador);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalo, ...chaves]);

  return estado;
}
