// Acompanha uma geração em segundo plano: consulta o andamento a cada 1,5 s enquanto o job está
// na fila ou gerando e para quando ele chega a um estado final. Um erro de rede passageiro não
// derruba a tela: tenta de novo. 404 (a Saída não tem andamento) para de tentar.
import { useEffect, useRef, useState } from "react";
import { ErroApi, mensagemDeFalha, obterAndamento, type Andamento } from "../dados/cliente";

const INTERVALO_MS = 1500;
const ESTADOS_FINAIS = ["concluida", "interrompida", "falhou"];

export function geracaoTerminou(andamento: Andamento): boolean {
  return ESTADOS_FINAIS.includes(andamento.estado);
}

interface AcompanhamentoDaGeracao {
  andamento: Andamento | null;
  erro: Error | null;
}

/** `aoConcluir` roda uma vez, quando o job chega a `concluida` (e só então). */
export function usarAndamento(
  identificador: string,
  aoConcluir?: (andamento: Andamento) => void,
): AcompanhamentoDaGeracao {
  const [andamento, definirAndamento] = useState<Andamento | null>(null);
  const [erro, definirErro] = useState<Error | null>(null);
  const aoConcluirRef = useRef(aoConcluir);
  aoConcluirRef.current = aoConcluir;

  useEffect(() => {
    let ativo = true;
    let temporizador: number | undefined;
    let avisou = false;
    definirAndamento(null);
    definirErro(null);

    async function consultar() {
      try {
        const atual = await obterAndamento(identificador);
        if (!ativo) return;
        definirAndamento(atual);
        definirErro(null);
        if (geracaoTerminou(atual)) {
          if (atual.estado === "concluida" && !avisou) {
            avisou = true;
            aoConcluirRef.current?.(atual);
          }
          return;
        }
        temporizador = window.setTimeout(consultar, INTERVALO_MS);
      } catch (falha: unknown) {
        if (!ativo) return;
        definirErro(new Error(mensagemDeFalha(falha)));
        if (falha instanceof ErroApi && falha.status === 404) return;
        temporizador = window.setTimeout(consultar, INTERVALO_MS * 2);
      }
    }

    void consultar();
    return () => {
      ativo = false;
      window.clearTimeout(temporizador);
    };
  }, [identificador]);

  return { andamento, erro };
}
