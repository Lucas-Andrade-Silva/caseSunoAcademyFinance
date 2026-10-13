// A pré-carga: na abertura o app busca tudo o que as guias vão ler e guarda no cache (`dados.ts`),
// para que trocar de guia nunca mostre "carregando". O texto de cada notícia recente também vem
// antes de a pessoa abri-la.
import { useEffect } from "react";
import {
  listarExecucoes,
  listarOrigens,
  listarReferenciasVisuais,
  obterAta,
  obterSaude,
} from "../dados/cliente";
import { precarregar, usarDados } from "./dados";
import { recentes } from "./janela";

export const CHAVES = {
  origens: "origens",
  execucoes: "execucoes",
  saude: "saude",
  referencias: "referencias",
  ata: (identificador: string) => `ata:${identificador}`,
} as const;

export function usarPrecarga(): void {
  useEffect(() => {
    precarregar(CHAVES.origens, listarOrigens);
    precarregar(CHAVES.execucoes, listarExecucoes);
    precarregar(CHAVES.saude, obterSaude);
    precarregar(CHAVES.referencias, listarReferenciasVisuais);
  }, []);

  const { dados } = usarDados(CHAVES.origens, listarOrigens);
  useEffect(() => {
    const atas = recentes((dados?.origens ?? []).flatMap((origem) => origem.atas));
    for (const ata of atas) {
      precarregar(CHAVES.ata(ata.identificador), () => obterAta(ata.identificador));
    }
  }, [dados]);
}
