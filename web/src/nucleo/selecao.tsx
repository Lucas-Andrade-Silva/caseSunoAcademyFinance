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
import { usarDados } from "./dados";
import { recentes } from "./janela";

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
  /** As Atas guardadas, na janela de 30 dias e ainda existentes em disco. */
  atasGuardadas: ResumoDaAta[];
  /** Tira tudo (guardada e rascunho). */
  limpar: () => void;
}

const Contexto = createContext<Selecao | null>(null);

function iguais(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((id) => b.includes(id));
}

export function ProvedorDeSelecao({ children }: { children: ReactNode }) {
  const [guardada, definirGuardada] = useState<string[]>(lerGuardada);
  const [rascunho, definirRascunho] = useState<string[]>(lerGuardada);
  const { dados } = usarDados("origens", listarOrigens);

  const todasAsAtas = useMemo(
    () => recentes((dados?.origens ?? []).flatMap((origem) => origem.atas)),
    [dados],
  );

  // Uma notícia que saiu da janela de 30 dias (ou do disco) deixa de contar como marcada.
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
      guardada
        .map((id) => todasAsAtas.find((ata) => ata.identificador === id))
        .filter((ata): ata is ResumoDaAta => ata !== undefined),
    [guardada, todasAsAtas],
  );

  const alternar = useCallback(
    (identificador: string) => {
      if (!rascunho.includes(identificador) && rascunho.length >= MAXIMO_DE_NOTICIAS) {
        return false;
      }
      definirRascunho(alternarSelecao(rascunho, identificador));
      return true;
    },
    [rascunho],
  );

  const atualizar = useCallback(() => {
    definirGuardada(rascunho);
    gravar("sessao", CHAVE, rascunho);
  }, [rascunho]);

  const limpar = useCallback(() => {
    definirGuardada([]);
    definirRascunho([]);
    gravar("sessao", CHAVE, []);
  }, []);

  const valor = useMemo<Selecao>(
    () => ({
      rascunho,
      guardada,
      alternar,
      atualizar,
      pendente: !iguais(rascunho, guardada),
      atasGuardadas,
      limpar,
    }),
    [rascunho, guardada, alternar, atualizar, atasGuardadas, limpar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usarSelecao(): Selecao {
  const contexto = useContext(Contexto);
  if (contexto === null) throw new Error("usarSelecao fora do ProvedorDeSelecao");
  return contexto;
}
