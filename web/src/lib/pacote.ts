// Quando o botão "Montar Pacotes" faz sentido. Só espelha a regra do servidor (rota
// `POST .../pacotes/montar`, `Execucao.celula_liberada` e `matriz_liberada`), para a tela dizer o
// motivo em vez de deixar o botão sem explicação.

interface EntradaDoPacote {
  /** O destino final do Laudo da Célula. */
  destinoDaCelula: string;
  /** Um revisor aprovou esta Célula (H4): vale mesmo que o Laudo a tenha reprovado. */
  aprovadaPorRevisor?: boolean;
}

const ROTULOS_DE_COMPOSICAO: Record<string, string> = {
  editorial: "Editorial",
  minimalista: "Minimalista",
  infografico: "Infográfico",
  comparativo: "Comparativo",
  estatistico: "Estatístico",
  narrativo: "Narrativo",
};

export function rotuloDaComposicao(composicao: string): string {
  return ROTULOS_DE_COMPOSICAO[composicao] ?? composicao;
}

export function itensDaDistribuicao(
  distribuicao: Record<string, number> | null | undefined,
): Array<{ composicao: string; rotulo: string; total: number }> {
  return Object.entries(distribuicao ?? {})
    .filter(([, total]) => total > 0)
    .sort(([a], [b]) => a.localeCompare(b, "pt-BR"))
    .map(([composicao, total]) => ({
      composicao,
      rotulo: rotuloDaComposicao(composicao),
      total,
    }));
}

/** O motivo de não haver Pacote, ou `null` quando ele pode ser montado. */
export function motivoSemPacote(entrada: EntradaDoPacote): string | null {
  if (entrada.destinoDaCelula !== "aprovado" && !entrada.aprovadaPorRevisor) {
    return "Só Célula aprovada pelo Laudo ou por um revisor gera Pacote.";
  }
  return null;
}
