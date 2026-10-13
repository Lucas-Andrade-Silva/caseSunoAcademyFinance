// O que a pessoa salvou nas guias de conteúdo. Fica no navegador (`localStorage`), no máximo
// `LIMITE` entradas, as mais novas primeiro. Cada guia define o formato do próprio `dados` e o
// componente que mostra a prévia dele (`guias/<guia>/PreviaSalva.tsx`).
//
// Reabrir um salvo: o Histórico chama `pedirAbertura(salvo)`, que leva a pessoa à guia certa; a
// guia lê `paraAbrir`, restaura o estado e chama `consumirAbertura()`.
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import type { Audiencia } from "../dados/cliente";
import { gravar, ler } from "./armazenamento";
import { GUIAS } from "./guias";

const CHAVE = "suno.historico";
const LIMITE = 60;

export type EspecieSalva = "texto" | "carrossel" | "video";

export interface Salvo<Dados = unknown> {
  id: string;
  especie: EspecieSalva;
  titulo: string;
  /** Uma frase curta para a linha do Histórico: "E-mail · 320 palavras", "5 quadros". */
  resumo: string;
  audiencia: Audiencia;
  criadoEm: string;
  /** A Saída de onde o conteúdo veio, quando ainda existe. */
  execucaoId: string | null;
  /** O que a guia precisa para reabrir: cada guia define e lê o próprio formato. */
  dados: Dados;
}

export type NovoSalvo<Dados = unknown> = Omit<Salvo<Dados>, "id" | "criadoEm">;

interface Historico {
  salvos: readonly Salvo[];
  salvar: (novo: NovoSalvo) => Salvo;
  remover: (id: string) => void;
  limpar: () => void;
  paraAbrir: Salvo | null;
  pedirAbertura: (salvo: Salvo) => void;
  consumirAbertura: () => void;
}

const Contexto = createContext<Historico | null>(null);

function lerSalvos(): Salvo[] {
  const valor = ler<unknown>("local", CHAVE, []);
  return Array.isArray(valor) ? (valor as Salvo[]) : [];
}

function novoId(): string {
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

export function ProvedorDeHistorico({ children }: { children: ReactNode }) {
  const [salvos, definirSalvos] = useState<Salvo[]>(lerSalvos);
  const [paraAbrir, definirParaAbrir] = useState<Salvo | null>(null);
  const navegar = useNavigate();

  const salvar = useCallback((novo: NovoSalvo) => {
    const salvo: Salvo = { ...novo, id: novoId(), criadoEm: new Date().toISOString() };
    definirSalvos((atuais) => {
      const proximos = [salvo, ...atuais].slice(0, LIMITE);
      gravar("local", CHAVE, proximos);
      return proximos;
    });
    return salvo;
  }, []);

  const remover = useCallback((id: string) => {
    definirSalvos((atuais) => {
      const proximos = atuais.filter((salvo) => salvo.id !== id);
      gravar("local", CHAVE, proximos);
      return proximos;
    });
  }, []);

  const limpar = useCallback(() => {
    definirSalvos([]);
    gravar("local", CHAVE, []);
  }, []);

  const pedirAbertura = useCallback(
    (salvo: Salvo) => {
      definirParaAbrir(salvo);
      const guia = GUIAS.find((g) => g.id === (salvo.especie === "video" ? "video" : salvo.especie));
      navegar(guia?.caminho ?? "/ingestao");
    },
    [navegar],
  );

  const consumirAbertura = useCallback(() => definirParaAbrir(null), []);

  const valor = useMemo<Historico>(
    () => ({ salvos, salvar, remover, limpar, paraAbrir, pedirAbertura, consumirAbertura }),
    [salvos, salvar, remover, limpar, paraAbrir, pedirAbertura, consumirAbertura],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usarHistorico(): Historico {
  const contexto = useContext(Contexto);
  if (contexto === null) throw new Error("usarHistorico fora do ProvedorDeHistorico");
  return contexto;
}
