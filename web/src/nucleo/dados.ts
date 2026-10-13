// Cache de dados do app. Tudo o que as guias leem da API é buscado uma vez, na abertura
// (`precarregar`), e fica aqui: trocar de guia nunca mostra "carregando". Quem precisa do dado
// pede com `usarDados`; um recarregamento mantém o valor antigo na tela até o novo chegar.
import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";
import { mensagemDeFalha } from "../dados/cliente";

interface Entrada<T> {
  dados: T | undefined;
  erro: Error | null;
  buscando: boolean;
}

const VAZIA: Entrada<never> = { dados: undefined, erro: null, buscando: false };

const entradas = new Map<string, Entrada<unknown>>();
const ouvintes = new Map<string, Set<() => void>>();
const emVoo = new Map<string, Promise<unknown>>();

function ler<T>(chave: string): Entrada<T> {
  return (entradas.get(chave) as Entrada<T> | undefined) ?? VAZIA;
}

function escrever<T>(chave: string, entrada: Entrada<T>): void {
  entradas.set(chave, entrada);
  ouvintes.get(chave)?.forEach((ouvinte) => ouvinte());
}

function assinar(chave: string, ouvinte: () => void): () => void {
  let conjunto = ouvintes.get(chave);
  if (!conjunto) {
    conjunto = new Set();
    ouvintes.set(chave, conjunto);
  }
  const grupo = conjunto;
  grupo.add(ouvinte);
  return () => {
    grupo.delete(ouvinte);
  };
}

/** Busca e guarda. Duas chamadas seguidas da mesma chave dividem a mesma requisição. */
export function buscar<T>(chave: string, origem: () => Promise<T>): Promise<T | undefined> {
  const andando = emVoo.get(chave);
  if (andando) return andando as Promise<T | undefined>;
  escrever(chave, { ...ler<T>(chave), buscando: true });
  const promessa = origem()
    .then((dados) => {
      escrever<T>(chave, { dados, erro: null, buscando: false });
      return dados as T | undefined;
    })
    .catch((falha: unknown) => {
      escrever<T>(chave, {
        ...ler<T>(chave),
        erro: new Error(mensagemDeFalha(falha)),
        buscando: false,
      });
      return undefined;
    })
    .finally(() => emVoo.delete(chave));
  emVoo.set(chave, promessa);
  return promessa;
}

/** Dispara a busca se a chave ainda não tem dado. Chamada na abertura do app. */
export function precarregar<T>(chave: string, origem: () => Promise<T>): void {
  const atual = ler<T>(chave);
  if (atual.dados === undefined && !emVoo.has(chave)) void buscar(chave, origem);
}

/** O que já está guardado para a chave, sem assinar nada (uso fora de componente). */
export function guardado<T>(chave: string): T | undefined {
  return ler<T>(chave).dados;
}

interface Opcoes<T> {
  /** Intervalo (ms) de uma atualização silenciosa, calculado do dado atual; `null` não atualiza. */
  atualizarACada?: (dados: T) => number | null;
}

interface Dados<T> {
  dados: T | undefined;
  erro: Error | null;
  /** Só é `true` na primeira busca, quando ainda não há nada para mostrar. */
  carregando: boolean;
  recarregar: () => Promise<T | undefined>;
}

export function usarDados<T>(
  chave: string,
  origem: () => Promise<T>,
  opcoes?: Opcoes<T>,
): Dados<T> {
  const entrada = useSyncExternalStore(
    (ouvinte) => assinar(chave, ouvinte),
    () => ler<T>(chave),
  );
  const origemRef = useRef(origem);
  origemRef.current = origem;

  useEffect(() => {
    precarregar(chave, () => origemRef.current());
  }, [chave]);

  const intervalo =
    entrada.dados !== undefined ? (opcoes?.atualizarACada?.(entrada.dados) ?? null) : null;
  useEffect(() => {
    if (intervalo === null) return;
    const temporizador = window.setInterval(() => {
      void buscar(chave, () => origemRef.current());
    }, intervalo);
    return () => window.clearInterval(temporizador);
  }, [chave, intervalo]);

  // Sem nada para mostrar e com erro (o servidor ainda subindo, por exemplo): tenta de novo.
  const semDadoComErro = entrada.dados === undefined && entrada.erro !== null;
  useEffect(() => {
    if (!semDadoComErro) return;
    const temporizador = window.setTimeout(() => {
      void buscar(chave, () => origemRef.current());
    }, 4000);
    return () => window.clearTimeout(temporizador);
  }, [chave, semDadoComErro, entrada.erro]);

  const recarregar = useCallback(() => buscar(chave, () => origemRef.current()), [chave]);

  return {
    dados: entrada.dados,
    erro: entrada.erro,
    carregando: entrada.dados === undefined && entrada.erro === null,
    recarregar,
  };
}
