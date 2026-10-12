// A seleção de Atas (as bolinhas dos cartões em Fontes) vive no app inteiro: a Curadoria lê o que
// foi marcado em Fontes. Fica guardada no navegador (try/catch: modo privado ou site data
// bloqueado nunca derrubam a tela).
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { alternarSelecao, limparInexistentes } from "../lib/fontes";

const CHAVE = "suno.atas-selecionadas";

function ler(): string[] {
  try {
    const bruto = window.localStorage.getItem(CHAVE);
    const valor: unknown = bruto ? JSON.parse(bruto) : [];
    return Array.isArray(valor) ? valor.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function guardar(selecao: readonly string[]): void {
  try {
    window.localStorage.setItem(CHAVE, JSON.stringify(selecao));
  } catch {
    /* sem armazenamento: a seleção vale só até recarregar a página */
  }
}

interface Selecao {
  selecao: string[];
  alternar: (identificador: string) => void;
  limpar: () => void;
  /** Tira o que sumiu do disco; chamada quando a lista de Atas chega. */
  conferir: (existentes: ReadonlySet<string>) => void;
}

const Contexto = createContext<Selecao | null>(null);

export function ProvedorDeSelecao({ children }: { children: ReactNode }) {
  const [selecao, definir] = useState<string[]>(ler);

  const mudar = useCallback((proxima: string[]) => {
    definir(proxima);
    guardar(proxima);
  }, []);

  const valor = useMemo<Selecao>(
    () => ({
      selecao,
      alternar: (identificador) => mudar(alternarSelecao(selecao, identificador)),
      limpar: () => mudar([]),
      conferir: (existentes) => {
        const valida = limparInexistentes(selecao, existentes);
        if (valida.length !== selecao.length) mudar(valida);
      },
    }),
    [selecao, mudar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usarSelecaoDeAtas(): Selecao {
  const contexto = useContext(Contexto);
  if (contexto === null) {
    throw new Error("usarSelecaoDeAtas fora do ProvedorDeSelecao");
  }
  return contexto;
}
