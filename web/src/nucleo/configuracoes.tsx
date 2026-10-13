// As preferências da pessoa: o modo de geração (Demo roda sem rede, Real usa o provedor) e o
// nome que aparece no avatar. Ficam no navegador. Sem escolha feita, o modo é Real quando o
// servidor tem provedor configurado e Demo quando não tem.
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { obterSaude, type ModoDeGeracao } from "../dados/cliente";
import { gravar, ler } from "./armazenamento";
import { usarDados } from "./dados";

const CHAVE = "suno.configuracoes";

interface Guardado {
  modo: ModoDeGeracao | null;
  nome: string;
}

interface Configuracoes {
  /** O modo que vale agora: a escolha da pessoa, ou o padrão do servidor. */
  modo: ModoDeGeracao;
  /** Só é `true` quando o servidor tem provedor configurado para o modo Real. */
  realDisponivel: boolean;
  nome: string;
  definirModo: (modo: ModoDeGeracao) => void;
  definirNome: (nome: string) => void;
}

const Contexto = createContext<Configuracoes | null>(null);

export function ProvedorDeConfiguracoes({ children }: { children: ReactNode }) {
  const [guardado, definirGuardado] = useState<Guardado>(() =>
    ler<Guardado>("local", CHAVE, { modo: null, nome: "" }),
  );
  const { dados: saude } = usarDados("saude", obterSaude);
  const realDisponivel = saude?.real_disponivel ?? false;

  const mudar = useCallback((proximo: Guardado) => {
    definirGuardado(proximo);
    gravar("local", CHAVE, proximo);
  }, []);

  const valor = useMemo<Configuracoes>(
    () => ({
      modo: guardado.modo ?? (realDisponivel ? "real" : "demo"),
      realDisponivel,
      nome: guardado.nome,
      definirModo: (modo) => mudar({ ...guardado, modo }),
      definirNome: (nome) => mudar({ ...guardado, nome }),
    }),
    [guardado, realDisponivel, mudar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usarConfiguracoes(): Configuracoes {
  const contexto = useContext(Contexto);
  if (contexto === null) throw new Error("usarConfiguracoes fora do ProvedorDeConfiguracoes");
  return contexto;
}
