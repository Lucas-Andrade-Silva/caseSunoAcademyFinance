// As notícias escolhidas na Ingestão. Dois conjuntos, de no máximo 3 cada:
//   - `rascunho`: o que está marcado na tela agora;
//   - `guardada`: o que o botão ATUALIZAR confirmou e as guias de conteúdo usam.
// A guardada vive no `sessionStorage`: recarregar mantém, fechar a aba larga. Quem sai da
// plataforma sem gerar começa do zero (regra do produto).
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { listarOrigens, type ResumoDaAta } from "../dados/cliente";
import { alternarSelecao } from "../lib/fontes";
import { ler, gravar } from "./armazenamento";
import { usarConfiguracoes } from "./configuracoes";
import { usarDados } from "./dados";
import { noticiasDoModo } from "./janela";

const CHAVE = "suno.noticias-guardadas";
export const MAXIMO_DE_NOTICIAS = 3;

function lerGuardada(): string[] {
  const valor = ler<unknown>("sessao", CHAVE, []);
  return Array.isArray(valor)
    ? valor.filter((v): v is string => typeof v === "string").slice(0, MAXIMO_DE_NOTICIAS)
    : [];
}

interface Selecao {
  rascunho: readonly string[];
  guardada: readonly string[];
  /** Marca ou desmarca no rascunho; devolve `false` quando já há 3 e a Ata não estava marcada. */
  alternar: (identificador: string) => boolean;
  /** Confirma o rascunho: é o que o botão ATUALIZAR faz. */
  atualizar: () => void;
  /** O rascunho difere do que está guardado. */
  pendente: boolean;
  /** As Atas guardadas que ainda pertencem ao acervo do modo atual. */
  atasGuardadas: ResumoDaAta[];
  /** Tira tudo (guardada e rascunho). */
  limpar: () => void;
}

const Contexto = createContext<Selecao | null>(null);

function iguais(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((id) => b.includes(id));
}

export function ProvedorDeSelecao({ children }: { children: ReactNode }) {
  const { modo } = usarConfiguracoes();
  const [guardada, definirGuardada] = useState<string[]>(lerGuardada);
  const [rascunho, definirRascunho] = useState<string[]>(lerGuardada);
  const { dados } = usarDados("origens", listarOrigens);

  const todasAsAtas = useMemo(
    () => noticiasDoModo((dados?.origens ?? []).flatMap((origem) => origem.atas), modo),
    [dados, modo],
  );
  const permitidas = useMemo(() => new Set(todasAsAtas.map((ata) => ata.identificador)), [todasAsAtas]);
  // Filtrar também durante a renderização evita expor a seleção do modo anterior por um quadro.
  const guardadaDoModo = useMemo(
    () => dados === undefined ? guardada : guardada.filter((id) => permitidas.has(id)),
    [dados, guardada, permitidas],
  );
  const rascunhoDoModo = useMemo(
    () => dados === undefined ? rascunho : rascunho.filter((id) => permitidas.has(id)),
    [dados, rascunho, permitidas],
  );

  // A troca de modo remove notícias incompatíveis; a janela de 30 dias vale apenas no Real.
  useEffect(() => {
    if (dados === undefined) return;
    const existentes = new Set(todasAsAtas.map((ata) => ata.identificador));
    const valida = (ids: readonly string[]) => ids.filter((id) => existentes.has(id));
    definirGuardada((atuais) => {
      const proxima = valida(atuais);
      if (proxima.length === atuais.length) return atuais;
      gravar("sessao", CHAVE, proxima);
      return proxima;
    });
    definirRascunho((atuais) => {
      const proxima = valida(atuais);
      return proxima.length === atuais.length ? atuais : proxima;
    });
  }, [dados, todasAsAtas]);

  const atasGuardadas = useMemo(
    () =>
      guardadaDoModo
        .map((id) => todasAsAtas.find((ata) => ata.identificador === id))
        .filter((ata): ata is ResumoDaAta => ata !== undefined),
    [guardadaDoModo, todasAsAtas],
  );

  const alternar = useCallback(
    (identificador: string) => {
      if (!permitidas.has(identificador)) return false;
      if (!rascunhoDoModo.includes(identificador) && rascunhoDoModo.length >= MAXIMO_DE_NOTICIAS) {
        return false;
      }
      definirRascunho(alternarSelecao(rascunhoDoModo, identificador));
      return true;
    },
    [rascunhoDoModo, permitidas],
  );

  const atualizar = useCallback(() => {
    definirGuardada(rascunhoDoModo);
    gravar("sessao", CHAVE, rascunhoDoModo);
  }, [rascunhoDoModo]);

  const limpar = useCallback(() => {
    definirGuardada([]);
    definirRascunho([]);
    gravar("sessao", CHAVE, []);
  }, []);

  const valor = useMemo<Selecao>(
    () => ({
      rascunho: rascunhoDoModo,
      guardada: guardadaDoModo,
      alternar,
      atualizar,
      pendente: !iguais(rascunhoDoModo, guardadaDoModo),
      atasGuardadas,
      limpar,
    }),
    [rascunhoDoModo, guardadaDoModo, alternar, atualizar, atasGuardadas, limpar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usarSelecao(): Selecao {
  const contexto = useContext(Contexto);
  if (contexto === null) throw new Error("usarSelecao fora do ProvedorDeSelecao");
  return contexto;
}
